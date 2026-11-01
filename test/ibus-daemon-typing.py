# Types into the engine through a real ibus-daemon, as an IBus client that keeps the text a simple
# app would show. The daemon commits the preedit itself on reset and focus out, as an app does when
# the engine asks for it. Run by run-with-daemon.sh.
import ctypes
import glob
import os
import sys
import time
import warnings

import gi

gi.require_version("IBus", "1.0")
from gi.repository import GLib, GObject, IBus  # noqa: E402

failures = 0

# PyGObject reports GLib criticals as Python warnings. One here means the test touched a freed
# object, which only sometimes crashes, so it fails every time instead.
glib_warnings = []
warnings.showwarning = lambda message, *_args, **_kwargs: glib_warnings.append(str(message))

# IBus checks the text or property it passed to a signal once the handlers return, and frees it if
# it is still floating. PyGObject takes that floating reference and drops it with the Python
# object, so the check would read freed memory unless the test keeps the object.
kept = []


def listen(ic, signal, handler):
    def keep(*args):
        kept.extend(arg for arg in args if isinstance(arg, GObject.Object) and arg is not ic)
        return handler(*args)

    ic.connect(signal, keep)


def pump(ms):
    context = GLib.MainContext.default()
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        context.iteration(False)
        time.sleep(0.001)


def connect():
    IBus.init()
    end = time.monotonic() + 10
    while time.monotonic() < end:
        bus = IBus.Bus()
        if bus.is_connected():
            return bus
        time.sleep(0.1)
    sys.exit("cannot connect to ibus-daemon")


bus = connect()

xlib = ctypes.CDLL("libX11.so.6")
xtst = ctypes.CDLL("libXtst.so.6")
xlib.XOpenDisplay.restype = ctypes.c_void_p
xlib.XOpenDisplay.argtypes = [ctypes.c_char_p]
xlib.XFlush.argtypes = [ctypes.c_void_p]
xtst.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
# The private X server run-with-daemon.sh starts, where the engine watches clicks.
no_x = bool(os.environ.get("NGOSEN_TEST_NO_X"))
display = None if no_x else xlib.XOpenDisplay(None)
if not no_x and not display:
    sys.exit("cannot open the X display")


def click():
    xtst.XTestFakeButtonEvent(display, 1, True, 0)
    xtst.XTestFakeButtonEvent(display, 1, False, 0)
    xlib.XFlush(display)
    pump(100)


class App:
    # app_commits: the app commits the preedit itself on reset and focus out, as the GTK modules of
    # IBus do; otherwise ibus-daemon does it for the app.
    def __init__(
        self,
        name,
        purpose=IBus.InputPurpose.FREE_FORM,
        app_commits=False,
        hints=0,
        surrounding=True,
        qt_through_shell=False,
        resets_after_key=False,
        reports_anchor=True,
    ):
        self.text = ""
        self.commits = []
        self.preedit = ""
        self.preedits = []
        # GNOME Shell turns a deletion into bytes using the text the app last reported. Qt on Wayland
        # sends the text after a deletion only along with some other change, such as the cursor
        # moving on screen: qt_through_shell is how many keys in a row must delete before the
        # report stops.
        self.qt_through_shell = qt_through_shell
        # Firefox on X11 resets the input context after each key the engine lets through.
        self.resets_after_key = resets_after_key
        # The GTK 3 module reports the cursor alone, with no selection.
        self.reports_anchor = reports_anchor
        self.reported = ""
        # None keeps the cursor at the end of the text; select() moves it and sets an anchor.
        self.cursor = None
        self.anchor = None
        self.deleted = False
        self.deleting_keys = 0
        self.preedit_mode = IBus.PreeditFocusMode.CLEAR
        self.passed = []
        self.requests = 0
        self.app_commits = app_commits
        self.ic = bus.create_input_context(name)
        caps = IBus.Capabilite.FOCUS | IBus.Capabilite.PREEDIT_TEXT
        if surrounding:
            caps |= IBus.Capabilite.SURROUNDING_TEXT
        self.ic.set_capabilities(caps)
        listen(self.ic, "commit-text", self.on_commit)
        listen(self.ic, "delete-surrounding-text", self.on_delete)
        listen(self.ic, "require-surrounding-text", self.on_require)
        listen(self.ic, "forward-key-event", self.on_forward)
        if app_commits:
            self.ic.set_client_commit_preedit(True)
            listen(self.ic, "update-preedit-text-with-mode", self.on_preedit_with_mode)
        else:
            listen(self.ic, "update-preedit-text", self.on_preedit)
        listen(self.ic, "hide-preedit-text", self.on_hide_preedit)
        self.ic.set_content_type(purpose, hints)
        self.ic.focus_in()
        # An input context of a plain client cannot pick its own engine.
        bus.set_global_engine("ngosen")
        pump(500)
        engine = self.ic.get_engine()
        if engine is None or engine.get_name() != "ngosen":
            sys.exit("the engine did not start")
        self.report()

    def report(self):
        if not (
            self.qt_through_shell and self.deleted and self.deleting_keys >= self.qt_through_shell
        ):
            self.reported = self.text
        n = len(self.reported) if self.cursor is None else self.cursor
        anchor = self.anchor if self.cursor is not None and self.reports_anchor else n
        self.ic.set_surrounding_text(IBus.Text.new_from_string(self.reported), n, anchor)

    def select(self, start, end):
        self.cursor, self.anchor = end, start
        self.report()
        pump(200)

    # Text typed or committed replaces the selection, as in a text field.
    def insert(self, text):
        if self.cursor is None:
            self.text += text
            return
        start, end = sorted((self.cursor, self.anchor))
        self.text = self.text[:start] + text + self.text[end:]
        self.cursor = self.anchor = start + len(text)

    def backspace(self):
        if self.cursor is None:
            self.text = self.text[:-1]
        elif self.cursor != self.anchor:
            self.insert("")
        elif self.cursor > 0:
            self.text = self.text[: self.cursor - 1] + self.text[self.cursor :]
            self.cursor = self.anchor = self.cursor - 1

    def on_commit(self, _ic, text):
        self.commits.append(text.get_text())
        self.insert(text.get_text())
        self.report()

    def on_delete(self, _ic, offset, count):
        if self.cursor is not None:
            start = self.cursor + offset
            self.text = self.text[:start] + self.text[start + count :]
            self.cursor = self.anchor = start
            self.report()
            return
        if self.qt_through_shell:
            if not self.deleted:
                self.deleting_keys += 1
            self.deleted = True
            end = len(self.reported) + offset + count
            size = len(self.reported[end - count : end].encode())
            count = len(self.text.encode()[-size:].decode(errors="replace"))
            offset = -count
        start = len(self.text) + offset
        self.text = self.text[:start] + self.text[start + count :]
        self.report()

    def on_require(self, _ic):
        self.requests += 1

    def on_forward(self, _ic, keyval, _keycode, state):
        if keyval == IBus.KEY_BackSpace and not state & IBus.ModifierType.RELEASE_MASK:
            self.backspace()
            self.report()

    def on_preedit(self, _ic, text, _cursor, visible):
        self.preedit = text.get_text() if visible else ""
        if self.preedit:
            self.preedits.append(self.preedit)

    def on_preedit_with_mode(self, _ic, text, _cursor, visible, mode):
        self.preedit = text.get_text() if visible else ""
        if self.preedit:
            self.preedits.append(self.preedit)
        self.preedit_mode = mode

    def on_hide_preedit(self, _ic):
        self.preedit = ""

    def commit_preedit(self):
        if self.app_commits and self.preedit and self.preedit_mode == IBus.PreeditFocusMode.COMMIT:
            self.commits.append(self.preedit)
            self.text += self.preedit
            self.preedit = ""

    def reset(self):
        self.commit_preedit()
        self.ic.reset()
        pump(200)

    # Asks like GTK does by default: the reply comes through the main loop in order with the commits
    # sent before it. A blocking call would see the reply before those commits.
    def key(self, keyval, state=0):
        replies = []

        def done(ic, result):
            handled = ic.process_key_event_async_finish(result)
            replies.append(handled)
            if not handled:
                self.passed.append(IBus.keyval_name(keyval))
                char = IBus.keyval_to_unicode(keyval)
                if keyval in (IBus.KEY_Return, IBus.KEY_KP_Enter):
                    self.text += "\n"
                elif keyval == IBus.KEY_BackSpace:
                    self.backspace()
                elif char and char != "\0":
                    self.insert(char)
                self.report()
                if self.resets_after_key:
                    ic.reset()

        if not self.deleted:
            self.deleting_keys = 0
        self.deleted = False
        self.ic.process_key_event_async(keyval, 0, state, -1, None, done)
        end = time.monotonic() + 5
        while not replies and time.monotonic() < end:
            GLib.MainContext.default().iteration(True)
        self.ic.process_key_event(keyval, 0, state | IBus.ModifierType.RELEASE_MASK)
        pump(40)

    def type(self, keys):
        for c in keys:
            self.key(IBus.unicode_to_keyval(c))
        pump(200)

    def tap_ctrl(self):
        self.ic.process_key_event(IBus.KEY_Control_L, 0, 0)
        self.ic.process_key_event(
            IBus.KEY_Control_L, 0, IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.RELEASE_MASK
        )
        pump(200)

    def close(self):
        self.commit_preedit()
        self.ic.focus_out()
        pump(200)


def check(ok, what, got):
    global failures
    if not ok:
        failures += 1
        print(f"FAIL {what}: {got!r}")


def finish():
    check(
        glib_warnings == [], "GLib warnings", glib_warnings[:3] + [f"{len(glib_warnings)} in all"]
    )
    if failures == 0:
        print("all IBus daemon checks passed")
    sys.exit(1 if failures else 0)


app = App("space")
app.type("vieetj ")
check(app.commits == ["việt "], "space: commits", app.commits)
check(app.preedit == "", "space: preedit", app.preedit)
app.close()

# GNOME Shell sends its Super+Space shortcut with only MOD4 set, not SUPER_MASK.
app = App("super-space")
app.type("vieetj ")
app.key(IBus.KEY_space, IBus.ModifierType.MOD4_MASK)
pump(200)
check(app.commits == ["việt "], "super space: no extra commit", app.commits)
check(app.passed == ["space"], "super space: the shortcut reaches GNOME Shell", app.passed)
app.close()

app = App("ctrl-tap")
app.type("viee")
check(app.preedit == "viê", "ctrl tap: preedit while typing", app.preedit)
app.tap_ctrl()
check(app.commits == ["viê"], "ctrl tap: commits", app.commits)
check(app.preedit == "", "ctrl tap: preedit", app.preedit)
app.close()

for app_commits, who in ((False, "daemon commits"), (True, "app commits")):
    app = App("app-reset", app_commits=app_commits)
    app.type("viee")
    app.reset()
    app.type("a ")
    check(
        app.commits == ["viê", "a "],
        f"app reset ({who}): the word stays and the next one starts fresh",
        app.commits,
    )
    app.close()

    app = App("focus-out", app_commits=app_commits)
    app.type("viee")
    app.close()
    check(app.commits == ["viê"], f"focus out ({who}): one commit", app.commits)
    app.ic.focus_in()
    pump(200)
    app.type("a ")
    check(
        app.commits == ["viê", "a "], f"focus out ({who}): the next word starts fresh", app.commits
    )
    app.close()

app = App("enter")
app.type("viee")
app.key(IBus.KEY_Return)
pump(200)
check(app.commits == ["viê"], "enter: commits", app.commits)
check(app.passed == ["Return"], "enter: keys the app got", app.passed)
check(app.text == "viê\n", "enter: the word comes before the new line", app.text)
app.close()

# A password is sent as typed: "aa" and "dd" would otherwise become "â" and "đ".
for purpose in (IBus.InputPurpose.PASSWORD, IBus.InputPurpose.PIN):
    app = App("password", purpose)
    app.type("aa dd ")
    check(
        app.text == "aa dd ",
        f"{purpose.value_nick}: the keys reach the app unchanged",
        (app.text, app.passed),
    )
    check(
        app.commits == [] and app.preedit == "",
        f"{purpose.value_nick}: nothing typed by the engine",
        (app.commits, app.preedit),
    )
    app.close()

# ibus-daemon commits the preedit itself before it switches the engine away.
for app_commits, who in ((False, "daemon commits"), (True, "app commits")):
    app = App("switch", app_commits=app_commits)
    app.type("viee")
    bus.set_global_engine("xkb:us::eng")
    pump(500)
    check(app.commits == ["viê"], f"engine switch ({who}): the word stays", app.commits)
    app.close()

log_path = os.environ["NGOSEN_IBUS_LOG_FILE"]


def typed_log(hints):
    open(log_path, "w").close()
    app = App("log", hints=hints)
    app.type("vieetj ")
    app.close()
    check(app.commits == ["việt "], f"log: hints {hints} still type Vietnamese", app.commits)
    with open(log_path) as f:
        return f.read()


plain = typed_log(0)
check("việt" in plain, "log: a plain field logs what was typed", plain)
hidden = typed_log(IBus.InputHints.PRIVATE)
leaked = [w for w in ("việt", "viê") if w in hidden]
check(not leaked, "log: a private field keeps no typed text", leaked)

config_dir = os.path.join(os.environ["XDG_CONFIG_HOME"], "ngosen")
user_dictionary = os.path.join(os.environ["XDG_DATA_HOME"], "ngosen", "vietnamese.cm.dict")
settings_path = os.path.join(config_dir, "ngosen.conf")


# As the settings window saves: a temporary file renamed over the old one.
def write_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w") as f:
        f.write(text)
    os.replace(path + ".tmp", path)
    pump(1000)


def set_setting(key, value):
    with open(settings_path) as f:
        lines = [line for line in f.read().splitlines() if not line.startswith(key + "=")]
    write_file(settings_path, "\n".join(lines + [f"{key}={value}"]) + "\n")


with open(settings_path) as f:
    check(
        "EnableDictionary=False" in f.read(),
        "settings: the first run writes every key",
        settings_path,
    )

# Without a click watcher a reset may be a click, so X11 apps keep the preedit.
if no_x:
    set_setting("DirectTyping", "True")
    app = App("gtk3-im:firefox", resets_after_key=True)
    app.type("xin vieetj ")
    check(
        app.text == "xin việt ",
        "no click watcher, X11 app resetting after each key: the words",
        app.text,
    )
    check("việt" in app.preedits, "no click watcher, X11 app: underlined", app.preedits)
    app.close()
    app = App("toggle-reset")
    ctrl, shift = IBus.ModifierType.CONTROL_MASK, IBus.ModifierType.SHIFT_MASK
    app.ic.process_key_event(IBus.KEY_Control_L, 0, 0)
    app.ic.process_key_event(IBus.KEY_Shift_L, 0, ctrl)
    app.ic.reset()
    pump(20)
    app.ic.process_key_event(IBus.KEY_Shift_L, 0, ctrl | shift | IBus.ModifierType.RELEASE_MASK)
    app.ic.process_key_event(IBus.KEY_Control_L, 0, ctrl | IBus.ModifierType.RELEASE_MASK)
    pump(200)
    mark = os.path.join(os.environ["XDG_STATE_HOME"], "ngosen", "english")
    check(os.path.exists(mark), "no click watcher: a reset between the keys still taps", mark)
    app.close()
    finish()

open(log_path, "w").close()
write_file(os.path.join(config_dir, "notes.txt"), "not a setting\n")
app = App("stray file")
app.type("a ")
app.close()
with open(log_path) as f:
    check(
        "Settings reloaded" not in f.read(), "settings: a stray file triggers no reload", log_path
    )

app = App("reload")
app.type("vie")
set_setting("InputMethod", "VNI")
app.type("etj ")
check(
    app.commits == ["việt "], "settings changed mid-word: the word keeps the old ones", app.commits
)
app.type("vie65t ")
check(
    app.commits == ["việt ", "việt "],
    "settings changed mid-word: the next word uses the new ones",
    app.commits,
)
app.close()
set_setting("InputMethod", "Telex")

# The X11 IBus modules report the text around the cursor, which tells where a line starts.
set_setting("CapitalizeStartOfText", "True")
app = App("gtk3-im:gedit")
app.text = "abc\n"
app.report()
pump(100)
app.type("vieetj ")
check(app.commits == ["Việt "], "preedit, X11 app: capitalizes at the start of a line", app.commits)
app.close()
set_setting("CapitalizeStartOfText", "False")

write_file(os.path.join(config_dir, "ngosen-macro-table.conf"), "[Macro/0]\nKey=ko\nValue=không\n")
app = App("macro")
app.type("ko ")
check(app.commits == ["không "], "macro: expands on space", app.commits)
app.close()

open(log_path, "w").close()
# A new user's first word list goes into a folder that did not exist when the engine started.
check(
    not os.path.isdir(os.path.dirname(user_dictionary))
    or not os.listdir(os.path.dirname(user_dictionary)),
    "dictionary: no word list before the first one",
    user_dictionary,
)
with open(os.environ["NGOSEN_IBUS_DICTIONARY"]) as f:
    write_file(user_dictionary, f.read())
app = App("dictionary")
app.type("a ")
app.close()
with open(log_path) as f:
    check("Settings reloaded" in f.read(), "dictionary: the first word list reloads", log_path)
set_setting("EnableDictionary", "False")
app = App("dictionary")
app.type("a ")
app.close()
with open(log_path) as f:
    check(
        f"Dictionary: {user_dictionary}" not in f.read(),
        "dictionary: the packaged one with the custom dictionary off",
        user_dictionary,
    )
set_setting("EnableDictionary", "True")
app = App("dictionary")
app.type("a ")
app.close()
with open(log_path) as f:
    check(
        f"Dictionary: {user_dictionary}" in f.read(),
        "dictionary: the user's one with the custom dictionary on",
        user_dictionary,
    )
open(log_path, "w").close()
with open(user_dictionary) as f:
    write_file(user_dictionary, f.read() + "ngosen\n")
app = App("dictionary")
app.type("a ")
app.close()
with open(log_path) as f:
    check("Settings reloaded" in f.read(), "dictionary: a new word list reloads", log_path)

# Straight into a field that can delete around the cursor, underlined in one that cannot.
set_setting("DirectTyping", "True")


# An empty field has reported no text yet, so the core underlines its first word.
def field_with_text(**kwargs):
    app = App("gnome-shell", **kwargs)
    app.type("xin ")
    app.preedits.clear()
    return app


app = App("gnome-shell")
app.type("xin vieetj ")
check(app.text == "xin việt ", "direct, empty field: the words", app.text)
check(
    "xin" in app.preedits and not any("v" in p for p in app.preedits),
    "direct, empty field: only the first word underlined",
    app.preedits,
)
app.close()

for app_commits, who in ((False, "daemon commits"), (True, "app commits")):
    app = field_with_text(app_commits=app_commits)
    app.type("vieetj ")
    check(app.text == "xin việt ", f"direct ({who}): the word", app.text)
    check(app.preedits == [], f"direct ({who}): no underline", app.preedits)
    app.type("a")
    app.key(IBus.KEY_BackSpace)
    pump(200)
    check(app.text == "xin việt ", f"direct ({who}): BackSpace removes the word", app.text)
    app.type("ko ")
    check(app.text == "xin việt không ", f"direct ({who}): a macro replaces the word", app.text)
    app.type("vie")
    app.reset()
    app.type("e ")
    check(
        app.text == "xin việt không viee ",
        f"direct ({who}): after a click the next key deletes nothing",
        app.text,
    )
    app.type("dd")
    app.key(IBus.KEY_Return)
    pump(200)
    check(app.text.endswith("viee đ\n"), f"direct ({who}): Enter after the word", app.text)
    app.close()

for keys in (1, 2):
    app = App("gnome-shell", qt_through_shell=keys)
    app.type("nam tieesng")
    app.key(IBus.KEY_BackSpace)
    app.key(IBus.KEY_BackSpace)
    app.type("ng ")
    check(app.text == "nam tiếng ", f"direct, Qt through GNOME Shell ({keys}): the words", app.text)
    check(
        not any("t" in p for p in app.preedits),
        f"direct, Qt through GNOME Shell ({keys}): the second word not underlined",
        app.preedits,
    )
    app.close()

# Qt reports the text around the cursor only once the field has text.
app = App("gnome-shell", surrounding=False)
app.type("vieetj ")
app.ic.set_capabilities(
    IBus.Capabilite.FOCUS | IBus.Capabilite.PREEDIT_TEXT | IBus.Capabilite.SURROUNDING_TEXT
)
app.report()
pump(100)
app.preedits.clear()
app.type("nam tieesng ")
check(app.text == "việt nam tiếng ", "direct, flag after the first word: the words", app.text)
check(app.preedits == [], "direct, flag after the first word: no underline after it", app.preedits)
app.close()

# A click the app does not announce: the text stays and only the cursor moves.
app = field_with_text()
app.type("vie")
app.ic.set_surrounding_text(IBus.Text.new_from_string(app.text), 0, 0)
pump(100)
app.type("a")
check(app.text == "xin viea", "direct, unannounced click: the next key deletes nothing", app.text)
app.close()

app = field_with_text()
app.type("vie")
app.ic.set_surrounding_text(IBus.Text.new_from_string(app.text), 5, 5)
pump(100)
app.type("e")
# The core underlines a word begun inside another one.
check(
    app.text == "xin vie" and app.preedit == "e",
    "direct, click inside the word: the next key deletes nothing",
    (app.text, app.preedit),
)
app.close()

# GNOME Shell keeps one input context for every field, so its engine moves between fields.
app = field_with_text()
app.ic.focus_out()
pump(100)
app.text = ""
requests = app.requests
app.ic.focus_in()
app.report()
pump(100)
# libibus clients such as GNOME Shell send the text only after a request.
check(
    app.requests > requests,
    "direct, next field on the same engine: the app is asked for its text",
    app.requests,
)
app.type("vieetj nam ")
# The empty report the field sends after focus is enough for its first word.
check(
    app.text == "việt nam " and app.preedits == [],
    "direct, next field on the same engine: its first word typed in the field",
    (app.text, app.preedits),
)
app.close()

# VS Code reports the cursor at the start and then back after the word.
app = field_with_text()
app.type("v")
for cursor in (0, 5):
    app.ic.set_surrounding_text(IBus.Text.new_from_string(app.text), cursor, cursor)
    pump(100)
app.type("ieetj ")
check(app.text == "xin việt ", "direct, cursor reported back and forth: the word", app.text)
check(app.preedits == [], "direct, cursor reported back and forth: no underline", app.preedits)
app.close()

app = App("gnome-shell", surrounding=False)
app.type("vieetj ")
check(app.text == "việt ", "direct, terminal: the word", app.text)
check("việt" in app.preedits, "direct, terminal: underlined", app.preedits)
app.close()

# On X11 the engine's BackSpace reaches the app, so the word goes straight in even where the IBus
# GTK module claims surrounding text it does not have, as in a terminal.
app = App("gtk3-im:gnome-terminal-server")
app.type("vieetj ")
check(app.text == "việt ", "direct, X11 app: the word", app.text)
check(app.preedits == [], "direct, X11 app: no underline", app.preedits)
app.close()

# Chromium and Electron report no text on X11.
app = App("gtk3-im:google-chrome", surrounding=False)
app.type("vieetj ")
check(app.text == "việt ", "direct, X11 app without text: the word", app.text)
check("việt" in app.preedits, "direct, X11 app without text: underlined", app.preedits)
app.close()

app = App("gtk3-im:firefox", resets_after_key=True)
app.type("xin vieetj ")
check(app.text == "xin việt ", "direct, X11 app resetting after each key: the words", app.text)
app.close()

# A click on X11 resets the context and moves the cursor the app reports.
app = App("gtk3-im:gedit")
app.type("xin vie")
click()
app.ic.reset()
app.ic.set_surrounding_text(IBus.Text.new_from_string(app.text), 0, 0)
pump(100)
app.type("e")
check(app.text == "xin viee", "direct, X11 app: a click mid-word deletes nothing", app.text)
app.close()

app = App("gtk3-im:gedit")
app.type("xin vie")
click()
app.ic.reset()
app.text = "abc def"
app.report()
pump(100)
app.type("e")
check(
    app.text == "abc defe", "direct, X11 app: a click onto another line deletes nothing", app.text
)
app.close()

# VTE claims surrounding text and never reports any.
app = App("gtk3-im:gnome-terminal-server")
app.report = lambda: None
app.type("xin vie")
click()
app.ic.reset()
pump(100)
app.type("e")
check(app.text == "xin viee", "direct, terminal claiming text: a click deletes nothing", app.text)
app.close()

# Without the text, the reset is all that tells a click.
app = App("gtk3-im:xterm", surrounding=False)
app.type("xin vie")
click()
app.ic.reset()
pump(100)
app.type("e ")
check(
    app.text == "xin viee ",
    "direct, X11 app without text: a click mid-word deletes nothing",
    app.text,
)
app.close()

set_setting("CapitalizeStartOfText", "True")
app = App("gtk3-im:gedit")
app.text = "abc\n"
app.report()
pump(100)
app.type("vieetj ")
check(app.text == "abc\nViệt ", "direct, X11 app: capitalizes at the start of a line", app.text)
app.close()
set_setting("CapitalizeStartOfText", "False")

# The Chrome address bar drops some deletions, which leaves letters of the old word behind.
app = App("gnome-shell", IBus.InputPurpose.URL)
app.type("vieetj ")
check(app.text == "việt ", "direct, address bar: the word", app.text)
check("việt" in app.preedits, "direct, address bar: underlined", app.preedits)
app.close()


# A tone key typed over a selected word puts the tone on that word. Only X11 apps get the key itself:
# through GNOME Shell a word typed over a selection goes into the preedit.
def retone_selection():
    app = App("gtk3-im:gedit", reports_anchor=False)
    app.type("xin chao xyz")
    check(app.text == "xin chao xyz", "direct, before selecting: the words", app.text)
    # Selecting with the mouse clicks, and the app resets the context.
    click()
    app.ic.reset()
    app.select(4, 8)
    app.type("f")
    return app


app = retone_selection()
check(app.text == "xin chào xyz", "direct, tone key over a selected word: retoned", app.text)
app.key(IBus.KEY_Tab)
pump(200)
check(
    app.text == "xin f xyz",
    "direct, tone key over a selected word: Tab puts the key back",
    app.text,
)
app.close()
set_setting("RetoneSelection", "False")
app = retone_selection()
check(app.text == "xin f xyz", "direct, retone off: the key replaces the word", app.text)
app.close()
set_setting("RetoneSelection", "True")


# A tone key typed right after a word the user clicked behind retones it too, in every app.
def retone_after_click(name):
    app = App(name)
    app.type("xin chao")
    click()
    app.ic.reset()
    app.select(8, 8)
    app.type("f")
    pump(200)
    return app


for name in ("gnome-shell", "gtk3-im:gedit"):
    app = retone_after_click(name)
    check(
        app.text == "xin chào", f"direct, {name}, tone key after a clicked word: retoned", app.text
    )
    app.key(IBus.KEY_Tab)
    pump(200)
    check(
        app.text == "xin chaof",
        f"direct, {name}, after a clicked word: Tab puts the key back",
        app.text,
    )
    app.close()
set_setting("RetoneSelection", "False")
app = retone_after_click("gnome-shell")
check(app.text == "xin chaof", "direct, retone off: the key after a clicked word stays", app.text)
app.close()
set_setting("RetoneSelection", "True")
set_setting("DirectTyping", "False")

# XIM clients such as Alacritty keep the preedit across a click and send no reset.
app = App("xim", surrounding=False)
app.type("xin vie")
click()
app.type("e ")
check(app.text == "xin viee ", "XIM app: a click mid-word keeps the word", app.text)
app.close()


def labels(props):
    found = {}
    i = 0
    while props is not None and (prop := props.get(i)) is not None:
        found[prop.get_key()] = prop.get_label().get_text()
        found.update(labels(prop.get_sub_props()))
        i += 1
    return found


def checked_items(props):
    found = set()
    i = 0
    while props is not None and (prop := props.get(i)) is not None:
        if prop.get_state() == IBus.PropState.CHECKED:
            found.add(prop.get_key())
        found |= checked_items(prop.get_sub_props())
        i += 1
    return found


def prop_states(props):
    found = {}
    i = 0
    while props is not None and (prop := props.get(i)) is not None:
        found[prop.get_key()] = prop.get_state()
        found.update(prop_states(prop.get_sub_props()))
        i += 1
    return found


# GNOME Shell takes the whole menu once after the engine is chosen, then only single updates.
class GnomeMenu:
    def __init__(self):
        self.states = None
        self.labels = {}

    def register(self, props):
        if self.states is None and props.get(0) is not None:
            self.states = prop_states(props)
            self.labels = labels(props)

    def update(self, prop):
        if self.states is not None and prop.get_key() in self.states:
            self.states[prop.get_key()] = prop.get_state()
            self.labels[prop.get_key()] = prop.get_label().get_text()

    def checked(self):
        return {
            key for key, state in (self.states or {}).items() if state == IBus.PropState.CHECKED
        }


english_mark = os.path.join(os.environ["XDG_STATE_HOME"], "ngosen", "english")


# Ctrl held, then Shift, then both let go: the way a tap of the toggle key reaches the engine.
def tap_ctrl_shift(app, extra=0, hold_ms=0):
    ctrl, shift = IBus.ModifierType.CONTROL_MASK, IBus.ModifierType.SHIFT_MASK
    release = IBus.ModifierType.RELEASE_MASK
    app.ic.process_key_event(IBus.KEY_Control_L, 0, extra)
    app.ic.process_key_event(IBus.KEY_Shift_L, 0, extra | ctrl)
    pump(hold_ms)
    app.ic.process_key_event(IBus.KEY_Shift_L, 0, extra | ctrl | shift | release)
    app.ic.process_key_event(IBus.KEY_Control_L, 0, extra | ctrl | release)
    pump(200)


app = App("toggle")
app.type("vieetj")
tap_ctrl_shift(app)
check(app.commits == ["việt"], "toggle: the word being typed is committed once", app.commits)
check(os.path.exists(english_mark), "toggle: English is remembered", english_mark)
app.type(" vieetj")
check(
    app.commits == ["việt"] and app.text == "việt vieetj", "toggle: English goes through", app.text
)
tap_ctrl_shift(app, IBus.ModifierType.MOD2_MASK)
check(not os.path.exists(english_mark), "toggle: a tap with NumLock on switches back", english_mark)
app.type(" vieetj ")
check(app.text == "việt vieetj việt ", "toggle: Vietnamese again", app.text)
app.close()

app = App("toggle-not-a-tap")
ctrl_shift = IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.SHIFT_MASK
app.ic.process_key_event(IBus.KEY_Control_L, 0, 0)
app.ic.process_key_event(IBus.KEY_Shift_L, 0, IBus.ModifierType.CONTROL_MASK)
app.key(IBus.KEY_T, ctrl_shift)
app.ic.process_key_event(IBus.KEY_Shift_L, 0, ctrl_shift | IBus.ModifierType.RELEASE_MASK)
app.ic.process_key_event(
    IBus.KEY_Control_L, 0, IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.RELEASE_MASK
)
pump(200)
check(not os.path.exists(english_mark), "toggle: Ctrl+Shift+T is not a tap", english_mark)
tap_ctrl_shift(app, hold_ms=800)
check(not os.path.exists(english_mark), "toggle: a long hold is not a tap", english_mark)
app.close()

# Firefox on X11 resets after every key it is let through, the modifiers too. The engine tells those
# resets from clicks only where it watches clicks itself.
app = App("toggle-reset")
ctrl, shift = IBus.ModifierType.CONTROL_MASK, IBus.ModifierType.SHIFT_MASK
release = IBus.ModifierType.RELEASE_MASK


def reset_quickly():
    app.ic.reset()
    pump(20)


app.ic.process_key_event(IBus.KEY_Control_L, 0, 0)
reset_quickly()
app.ic.process_key_event(IBus.KEY_Shift_L, 0, ctrl)
reset_quickly()
app.ic.process_key_event(IBus.KEY_Shift_L, 0, ctrl | shift | release)
reset_quickly()
app.ic.process_key_event(IBus.KEY_Control_L, 0, ctrl | release)
pump(200)
check(os.path.exists(english_mark), "toggle: a reset between the keys still taps", english_mark)
# Leave Vietnamese on even when the check failed, so later checks fail only for their own reason.
if os.path.exists(english_mark):
    tap_ctrl_shift(app)
app.close()

app = App("toggle-click")
app.ic.process_key_event(IBus.KEY_Control_L, 0, 0)
app.ic.process_key_event(IBus.KEY_Shift_L, 0, ctrl)
click()
app.ic.process_key_event(IBus.KEY_Shift_L, 0, ctrl | shift | release)
app.ic.process_key_event(IBus.KEY_Control_L, 0, ctrl | release)
pump(200)
check(
    not os.path.exists(english_mark),
    "toggle: a click while Ctrl+Shift is held does not switch",
    english_mark,
)
if os.path.exists(english_mark):
    tap_ctrl_shift(app)
app.close()

# Ctrl stays down for a Ctrl+click after the Shift tap, a click the engine cannot see on Wayland.
app = App("toggle-ctrl-held")
app.ic.process_key_event(IBus.KEY_Control_L, 0, 0)
app.ic.process_key_event(IBus.KEY_Shift_L, 0, ctrl)
app.ic.process_key_event(IBus.KEY_Shift_L, 0, ctrl | shift | release)
pump(700)
app.ic.process_key_event(IBus.KEY_Control_L, 0, ctrl | release)
pump(200)
check(
    not os.path.exists(english_mark),
    "toggle: Ctrl held long after a quick Shift is a hold",
    english_mark,
)
if os.path.exists(english_mark):
    tap_ctrl_shift(app)
app.close()

# A compositor grab can eat the last release; the next tap must not depend on it.
app = App("toggle-lost-release")
app.ic.process_key_event(IBus.KEY_Control_L, 0, 0)
app.ic.process_key_event(IBus.KEY_Shift_L, 0, ctrl)
app.ic.process_key_event(IBus.KEY_Shift_L, 0, ctrl | shift | release)
pump(700)
tap_ctrl_shift(app)
check(
    os.path.exists(english_mark), "toggle: a tap after a lost release still switches", english_mark
)
if os.path.exists(english_mark):
    tap_ctrl_shift(app)
app.close()

# As in the fcitx5 edition, the tap counts once every modifier is up.
app = App("toggle-ctrl-v")
app.ic.process_key_event(IBus.KEY_Control_L, 0, 0)
app.ic.process_key_event(IBus.KEY_Shift_L, 0, ctrl)
app.ic.process_key_event(IBus.KEY_Shift_L, 0, ctrl | shift | release)
app.key(IBus.KEY_v, ctrl)
app.ic.process_key_event(IBus.KEY_Control_L, 0, ctrl | release)
pump(200)
check(
    not os.path.exists(english_mark), "toggle: Ctrl+Shift then Ctrl+V does not switch", english_mark
)
if os.path.exists(english_mark):
    tap_ctrl_shift(app)
app.close()

app = App("toggle-password", purpose=IBus.InputPurpose.PASSWORD)
tap_ctrl_shift(app)
check(not os.path.exists(english_mark), "toggle: nothing in a password field", english_mark)
app.close()

# Each settings change rebuilds the engine, which must keep typing English.
app = App("toggle-settings")
tap_ctrl_shift(app)
set_setting("SpellCheck", "True")
app.type("vieetj ")
check(
    app.text == "vieetj " and app.commits == [],
    "toggle: English stays after a settings change",
    app.text,
)
app.close()
app = App("toggle-new-field")
app.type("vieetj ")
check(app.text == "vieetj ", "toggle: English in a field opened after the switch", app.text)
tap_ctrl_shift(app)
app.close()

set_setting("DirectTyping", "True")
app = App("toggle-direct")
app.type("vieetj")
tap_ctrl_shift(app)
app.type(" abc")
check(app.text == "việt abc", "toggle: a word typed straight in stays once", app.text)
tap_ctrl_shift(app)
app.type(" vieetj ")
check(app.text == "việt abc việt ", "toggle: typing straight in again after English", app.text)
app.close()
app = App("toggle-direct-twice", surrounding=True)
tap_ctrl_shift(app)
tap_ctrl_shift(app)
app.type("vieetj ")
check(app.text == "việt ", "toggle: there and back before the first word", app.text)
app.close()


# The mode menu: its key ends the word, then a key picks Sen, underline or English for every app.
def menu_app(name):
    app = App(name)
    # Without this capability IBus draws the menu in its own panel instead of telling the app.
    app.ic.set_capabilities(
        IBus.Capabilite.FOCUS
        | IBus.Capabilite.PREEDIT_TEXT
        | IBus.Capabilite.SURROUNDING_TEXT
        | IBus.Capabilite.LOOKUP_TABLE
    )
    app.menu = None
    # IBus frees the table after the signal, so keep its labels rather than the table.
    listen(
        app.ic,
        "update-lookup-table",
        lambda _ic, table, visible: setattr(
            app,
            "menu",
            [table.get_candidate(i).get_text() for i in range(table.get_number_of_candidates())]
            if visible
            else None,
        ),
    )
    app.ic.connect("hide-lookup-table", lambda _ic: setattr(app, "menu", None))
    return app


def setting(key):
    with open(settings_path) as f:
        return next((line for line in f.read().splitlines() if line.startswith(key + "=")), "")


app = menu_app("menu")
app.type("vieetj")
app.key(IBus.KEY_grave)
pump(200)
check(app.text == "việt", "menu: its key ends the word", app.text)
items = app.menu or []
check(items == ["Gõ Sen", "Gạch chân", "Tiếng Anh"], "menu: ` shows the three modes", items)
app.key(IBus.KEY_q)
pump(500)
check(app.menu is None, "menu: a pick closes it", app.menu)
check(
    setting("DirectTyping") == "DirectTyping=False",
    "menu: q turns Sen off",
    setting("DirectTyping"),
)
app.type(" vieetj")
check(
    "việt" in app.preedits and app.text == "việt ",
    "menu: the next word is underlined",
    app.preedits,
)
app.key(IBus.KEY_grave)
app.key(IBus.KEY_1)
pump(500)
check(
    setting("DirectTyping") == "DirectTyping=True", "menu: 1 turns Sen on", setting("DirectTyping")
)
app.key(IBus.KEY_grave)
app.key(IBus.KEY_grave)
pump(200)
check(app.text == "việt việt`", "menu: ` twice types `", app.text)
app.key(IBus.KEY_grave)
app.key(IBus.KEY_Escape)
pump(200)
check(
    app.menu is None and app.text == "việt việt`", "menu: Esc closes it and types nothing", app.text
)
app.key(IBus.KEY_grave)
app.key(IBus.KEY_e)
pump(500)
check(os.path.exists(english_mark), "menu: e switches to English", english_mark)
app.type(" vieetj`")
check(app.text == "việt việt` vieetj`", "menu: in English ` types itself", app.text)
tap_ctrl_shift(app)
app.close()

set_setting("ModeMenuKey", "Shift+asciitilde")
app = menu_app("menu-tilde")
app.key(IBus.KEY_grave)
app.key(IBus.KEY_asciitilde, IBus.ModifierType.SHIFT_MASK)
pump(200)
check(app.text == "`" and app.menu is not None, "menu: Shift+~ opens it instead of `", app.text)
app.key(IBus.KEY_asciitilde, IBus.ModifierType.SHIFT_MASK)
pump(200)
check(app.text == "`~" and app.menu is None, "menu: Shift+~ twice types ~", app.text)
app.close()
set_setting("ModeMenuKey", "grave")

app = menu_app("menu-password")
app.ic.set_content_type(IBus.InputPurpose.PASSWORD, 0)
app.key(IBus.KEY_grave)
pump(200)
check(app.text == "`" and app.menu is None, "menu: a password field types `", app.text)
app.close()

set_setting("InputMethod", "VIQR")
app = menu_app("menu-viqr")
app.type("a` ")
check(app.text == "à " and app.menu is None, "menu: VIQR keeps ` for its tone", app.text)
app.close()
set_setting("InputMethod", "Telex")
set_setting("DirectTyping", "False")

set_setting("ToggleKey", "Alt+z")
app = App("toggle-note")
# Without this capability IBus shows the note in its own panel instead of telling the app.
app.ic.set_capabilities(
    IBus.Capabilite.FOCUS | IBus.Capabilite.PREEDIT_TEXT | IBus.Capabilite.AUXILIARY_TEXT
)
note = []
listen(
    app.ic,
    "update-auxiliary-text",
    lambda _ic, text, visible: note.append(text.get_text() if visible else ""),
)
app.ic.connect("hide-auxiliary-text", lambda _ic: note.append(""))
# Alt+Z switches on the press, so its releases come after the note.
alt = IBus.ModifierType.MOD1_MASK
app.ic.process_key_event(IBus.KEY_Alt_L, 0, 0)
app.key(IBus.KEY_z, alt)
app.ic.process_key_event(IBus.KEY_Alt_L, 0, alt | IBus.ModifierType.RELEASE_MASK)
pump(200)
check(note[-1:] == ["Tiếng Anh"], "toggle: the note stays after the keys are let go", note)
app.type("a")
check(note[-1:] == [""], "toggle: the note goes at the next key", note)
app.key(IBus.KEY_z, alt)
app.close()

app = App("toggle-alt-z")
app.type("vieetj")
app.key(IBus.KEY_z, IBus.ModifierType.MOD1_MASK)
check(os.path.exists(english_mark), "toggle: Alt+Z switches on the press", english_mark)
check(app.commits == ["việt"], "toggle: Alt+Z commits the word being typed once", app.commits)
check("z" not in app.passed, "toggle: the app never sees Alt+Z", app.passed)
app.key(IBus.KEY_z, IBus.ModifierType.MOD1_MASK)
check(not os.path.exists(english_mark), "toggle: Alt+Z again switches back", english_mark)
# A held key repeats its press before any release.
alt = IBus.ModifierType.MOD1_MASK
app.ic.process_key_event(IBus.KEY_z, 0, alt)
app.ic.process_key_event(IBus.KEY_z, 0, alt)
app.ic.process_key_event(IBus.KEY_z, 0, alt | IBus.ModifierType.RELEASE_MASK)
app.ic.process_key_event(IBus.KEY_Alt_L, 0, alt | IBus.ModifierType.RELEASE_MASK)
pump(200)
check(os.path.exists(english_mark), "toggle: holding Alt+Z switches once", english_mark)
# A grab can eat the release of Z too; the next Alt+Z must still switch.
app.ic.process_key_event(IBus.KEY_z, 0, alt)
app.ic.process_key_event(IBus.KEY_Alt_L, 0, alt | IBus.ModifierType.RELEASE_MASK)
pump(200)
app.key(IBus.KEY_z, alt)
check(os.path.exists(english_mark), "toggle: Alt+Z after a lost Z release switches", english_mark)
if not os.path.exists(english_mark):
    app.key(IBus.KEY_z, alt)
app.key(IBus.KEY_z, IBus.ModifierType.MOD1_MASK)
tap_ctrl_shift(app)
check(
    not os.path.exists(english_mark),
    "toggle: Ctrl+Shift does nothing once Alt+Z is set",
    english_mark,
)
app.close()
set_setting("ToggleKey", "")
app = App("toggle-off")
tap_ctrl_shift(app)
check(not os.path.exists(english_mark), "toggle: no key when turned off", english_mark)
app.close()
set_setting("ToggleKey", "Control+Shift_L Control+Shift_R Shift+Control_L Shift+Control_R")

# A click in the GNOME input source menu, which the panel sends as a property activation.
menus = []
menu_labels = {}
gnome = GnomeMenu()
app = App("menu")
app.ic.set_capabilities(
    IBus.Capabilite.FOCUS
    | IBus.Capabilite.PREEDIT_TEXT
    | IBus.Capabilite.SURROUNDING_TEXT
    | IBus.Capabilite.PROPERTY
)
listen(app.ic, "register-properties", lambda _ic, props: menus.append(checked_items(props)))
listen(app.ic, "register-properties", lambda _ic, props: menu_labels.update(labels(props)))
listen(app.ic, "register-properties", lambda _ic, props: gnome.register(props))
listen(app.ic, "update-property", lambda _ic, prop: gnome.update(prop))
symbols = []
listen(
    app.ic,
    "update-property",
    lambda _ic, prop: (
        symbols.append(prop.get_symbol().get_text()) if prop.get_key() == "InputMode" else None
    ),
)
app.ic.focus_out()
app.ic.focus_in()
pump(300)
check(gnome.states is not None, "menu: GNOME gets the menu", gnome.states)
# GNOME Shell rebuilds its menu on each item update, which stalls it when every focus change sends them.
updates = []
listen(app.ic, "update-property", lambda _ic, prop: updates.append(prop.get_key()))
for _ in range(3):
    app.ic.focus_out()
    app.ic.focus_in()
    pump(100)
check(updates == [], "menu: a focus change resends no unchanged item", len(updates))
app.ic.property_activate("InputMethod/VNI", IBus.PropState.CHECKED)
pump(1000)
with open(settings_path) as f:
    saved = f.read()
check("InputMethod=VNI" in saved, "menu: the choice is saved", saved)
check(
    menu_labels.get("SpellCheck") == "✔ Kiểm tra chính tả",
    "menu: in Vietnamese whatever the desktop language",
    menu_labels.get("SpellCheck"),
)
check(
    bool(menus) and "InputMethod/VNI" in menus[-1] and "InputMethod/Telex" not in menus[-1],
    "menu: shows the new choice",
    menus,
)
check(
    "InputMethod/VNI" in gnome.checked() and "InputMethod/Telex" not in gnome.checked(),
    "menu: GNOME shows the new choice",
    gnome.checked(),
)
app.type("vie65t ")
check(app.commits == ["việt "], "menu: the next word uses the new choice", app.commits)
# GNOME Shell sends the state a plain item shows, so a click on "✔ ..." comes as checked.
app.ic.property_activate("SpellCheck", IBus.PropState.CHECKED)
pump(1000)
with open(settings_path) as f:
    check("SpellCheck=False" in f.read(), "menu: a click turns an on item off", settings_path)
check(
    gnome.labels.get("SpellCheck") == "✖ Kiểm tra chính tả",
    "menu: GNOME shows the new setting",
    gnome.labels.get("SpellCheck"),
)
# The engine reloads settings only between words, while clicks and the menu go by the file.
app.type("vie")
check(app.preedit == "vie", "menu: a word is underlined before the click", app.preedit)
app.ic.property_activate("SpellCheck", IBus.PropState.UNCHECKED)
pump(1000)
check(
    gnome.labels.get("SpellCheck") == "✔ Kiểm tra chính tả",
    "menu: a click while a word is underlined shows the new setting",
    gnome.labels.get("SpellCheck"),
)
app.ic.property_activate("SpellCheck", IBus.PropState.CHECKED)
pump(1000)
with open(settings_path) as f:
    check(
        "SpellCheck=False" in f.read(),
        "menu: two clicks while a word is underlined put the setting back",
        settings_path,
    )
app.type(" ")
# As when the settings window changes it while the field keeps focus and no key is typed.
set_setting("EnableMacro", "False")
pump(1000)
check(
    "EnableMacro" not in gnome.checked(),
    "menu: a change in the settings file shows at once",
    gnome.checked(),
)
set_setting("EnableMacro", "True")
pump(500)
updates.clear()
tap_ctrl_shift(app)
check(updates == ["InputMode"], "menu: the toggle key resends only its own item", updates)
check(symbols[-1:] == ["E"], "menu: the top bar shows E in English", symbols)
check("InputMode" not in gnome.checked(), "menu: the Vietnamese item is unchecked", gnome.checked())
app.ic.property_activate("InputMode", IBus.PropState.CHECKED)
pump(500)
check(symbols[-1:] == ["V"], "menu: clicking the item switches back", symbols)
check(not os.path.exists(english_mark), "menu: the click is remembered", english_mark)
before = len(app.commits)
app.type("vie65t")
app.ic.property_activate("InputMode", IBus.PropState.UNCHECKED)
pump(500)
check(
    app.commits[before:] == ["việt"],
    "menu: the click commits the word being typed once",
    app.commits,
)
app.ic.property_activate("InputMode", IBus.PropState.CHECKED)
pump(500)
# A restore in the settings window writes the marker while a field has focus.
write_file(english_mark, "")
check(symbols[-1:] == ["E"], "menu: a marker written elsewhere switches to English", symbols)
before = len(app.commits)
app.type("vie65t ")
check(app.commits[before:] == [], "menu: English after the marker is written", app.commits)
os.remove(english_mark)
pump(1000)
check(symbols[-1:] == ["V"], "menu: a marker removed elsewhere switches back", symbols)
app.type("vie65t ")
check(app.commits[-1:] == ["việt "], "menu: Vietnamese after the marker is removed", app.commits)
app.ic.property_activate("SaveTypingLog", IBus.PropState.UNCHECKED)
pump(500)
state_dir = os.path.join(os.environ["XDG_STATE_HOME"], "ngosen")
saved_logs = sorted(glob.glob(os.path.join(state_dir, "typing-*.log")))
check(len(saved_logs) == 1, "menu: saves a typing log", saved_logs)
if saved_logs:
    with open(saved_logs[0]) as f:
        check("việt" in f.read(), "menu: the typing log holds the last words", saved_logs[0])
    modes = (os.stat(state_dir).st_mode & 0o777, os.stat(saved_logs[0]).st_mode & 0o777)
    check(modes == (0o700, 0o600), "menu: only the user can read the typing log", modes)
app.close()
finish()
