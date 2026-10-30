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
        self.reported = ""
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
        n = len(self.reported)
        self.ic.set_surrounding_text(IBus.Text.new_from_string(self.reported), n, n)

    def on_commit(self, _ic, text):
        self.commits.append(text.get_text())
        self.text += text.get_text()
        self.report()

    # The cursor stays at the end of the text.
    def on_delete(self, _ic, offset, count):
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
            self.text = self.text[:-1]
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
                    self.text = self.text[:-1]
                elif char and char != "\0":
                    self.text += char
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
check(
    app.text == "việt nam " and "việt" in app.preedits,
    "direct, next field on the same engine: its first word underlined",
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

    def register(self, props):
        if self.states is None and props.get(0) is not None:
            self.states = prop_states(props)

    def update(self, prop):
        if self.states is not None and prop.get_key() in self.states:
            self.states[prop.get_key()] = prop.get_state()

    def checked(self):
        return {
            key for key, state in (self.states or {}).items() if state == IBus.PropState.CHECKED
        }


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
    menu_labels.get("SpellCheck") == "Kiểm tra chính tả",
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
app.ic.property_activate("SpellCheck", IBus.PropState.UNCHECKED)
pump(1000)
with open(settings_path) as f:
    check("SpellCheck=False" in f.read(), "menu: a toggle is saved", settings_path)
# As when the settings window changes it while the field keeps focus and no key is typed.
set_setting("EnableMacro", "False")
pump(1000)
check(
    "EnableMacro" not in gnome.checked(),
    "menu: a change in the settings file shows at once",
    gnome.checked(),
)
set_setting("EnableMacro", "True")
app.ic.property_activate("SaveTypingLog", IBus.PropState.UNCHECKED)
pump(500)
state_dir = os.path.join(os.environ["HOME"], ".local", "state", "ngosen")
saved_logs = sorted(glob.glob(os.path.join(state_dir, "typing-*.log")))
check(len(saved_logs) == 1, "menu: saves a typing log", saved_logs)
if saved_logs:
    with open(saved_logs[0]) as f:
        check("việt" in f.read(), "menu: the typing log holds the last words", saved_logs[0])
    modes = (os.stat(state_dir).st_mode & 0o777, os.stat(saved_logs[0]).st_mode & 0o777)
    check(modes == (0o700, 0o600), "menu: only the user can read the typing log", modes)
app.close()
finish()
