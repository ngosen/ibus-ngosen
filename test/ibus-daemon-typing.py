# Types into the engine through a real ibus-daemon, as an IBus client that keeps the text a simple
# app would show. The daemon commits the preedit itself on reset and focus out, as an app does when
# the engine asks for it. Run by run-with-daemon.sh.
import os
import shutil
import sys
import time

import gi

gi.require_version("IBus", "1.0")
from gi.repository import GLib, IBus  # noqa: E402

failures = 0


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
        self.reported = ""
        self.deleted = False
        self.deleting_keys = 0
        self.preedit_mode = IBus.PreeditFocusMode.CLEAR
        self.passed = []
        self.app_commits = app_commits
        self.ic = bus.create_input_context(name)
        caps = IBus.Capabilite.FOCUS | IBus.Capabilite.PREEDIT_TEXT
        if surrounding:
            caps |= IBus.Capabilite.SURROUNDING_TEXT
        self.ic.set_capabilities(caps)
        self.ic.connect("commit-text", self.on_commit)
        self.ic.connect("delete-surrounding-text", self.on_delete)
        if app_commits:
            self.ic.set_client_commit_preedit(True)
            self.ic.connect("update-preedit-text-with-mode", self.on_preedit_with_mode)
        else:
            self.ic.connect("update-preedit-text", self.on_preedit)
        self.ic.connect("hide-preedit-text", self.on_hide_preedit)
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
                elif char and char != "\0":
                    self.text += char
                self.report()

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


app = App("space")
app.type("vieetj ")
check(app.commits == ["việt "], "space: commits", app.commits)
check(app.preedit == "", "space: preedit", app.preedit)
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
for app_commits, who in ((False, "daemon commits"), (True, "app commits")):
    app = App("direct", app_commits=app_commits)
    app.type("vieetj ")
    check(app.text == "việt ", f"direct ({who}): the word", app.text)
    check(app.preedits == [], f"direct ({who}): no underline", app.preedits)
    app.type("a")
    app.key(IBus.KEY_BackSpace)
    pump(200)
    check(app.text == "việt ", f"direct ({who}): BackSpace removes the word", app.text)
    app.type("ko ")
    check(app.text == "việt không ", f"direct ({who}): a macro replaces the word", app.text)
    app.type("vie")
    app.reset()
    app.type("e ")
    check(
        app.text == "việt không viee ",
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
    app.close()

# Qt reports the text around the cursor only once the field has text.
app = App("flag later", surrounding=False)
app.type("vieetj ")
app.ic.set_capabilities(
    IBus.Capabilite.FOCUS | IBus.Capabilite.PREEDIT_TEXT | IBus.Capabilite.SURROUNDING_TEXT
)
app.report()
pump(100)
app.type("nam tieesng ")
check(app.text == "việt nam tiếng ", "direct, flag after the first word: the words", app.text)
app.close()

# A click the app does not announce: the text stays and only the cursor moves.
app = App("click")
app.type("vie")
app.ic.set_surrounding_text(IBus.Text.new_from_string(app.text), 0, 0)
pump(100)
app.type("a")
check(app.text == "viea", "direct, unannounced click: the next key deletes nothing", app.text)
app.close()

app = App("click inside")
app.type("vie")
app.ic.set_surrounding_text(IBus.Text.new_from_string(app.text), 1, 1)
pump(100)
app.type("e")
check(app.text == "viee", "direct, click inside the word: the next key deletes nothing", app.text)
app.close()

# VS Code reports the cursor at the start and then back after the word.
app = App("back and forth")
app.type("v")
for cursor in (0, 1):
    app.ic.set_surrounding_text(IBus.Text.new_from_string("vv"), cursor, cursor)
    pump(100)
app.type("ieetj ")
check(app.text == "việt ", "direct, cursor reported back and forth: the word", app.text)
app.close()

app = App("no surrounding", surrounding=False)
app.type("vieetj ")
check(app.text == "việt ", "direct, terminal: the word", app.text)
check("việt" in app.preedits, "direct, terminal: underlined", app.preedits)
app.close()
set_setting("DirectTyping", "False")


def checked_items(props):
    found = set()
    i = 0
    while props is not None and (prop := props.get(i)) is not None:
        if prop.get_state() == IBus.PropState.CHECKED:
            found.add(prop.get_key())
        found |= checked_items(prop.get_sub_props())
        i += 1
    return found


# A click in the GNOME input source menu, which the panel sends as a property activation.
menus = []
app = App("menu")
app.ic.set_capabilities(
    IBus.Capabilite.FOCUS
    | IBus.Capabilite.PREEDIT_TEXT
    | IBus.Capabilite.SURROUNDING_TEXT
    | IBus.Capabilite.PROPERTY
)
app.ic.connect("register-properties", lambda _ic, props: menus.append(checked_items(props)))
app.ic.property_activate("InputMethod/VNI", IBus.PropState.CHECKED)
pump(1000)
with open(settings_path) as f:
    saved = f.read()
check("InputMethod=VNI" in saved, "menu: the choice is saved", saved)
check(
    bool(menus) and "InputMethod/VNI" in menus[-1] and "InputMethod/Telex" not in menus[-1],
    "menu: shows the new choice",
    menus,
)
app.type("vie65t ")
check(app.commits == ["việt "], "menu: the next word uses the new choice", app.commits)
app.ic.property_activate("SpellCheck", IBus.PropState.UNCHECKED)
pump(1000)
with open(settings_path) as f:
    check("SpellCheck=False" in f.read(), "menu: a toggle is saved", settings_path)
app.close()

if failures == 0:
    print("all IBus daemon checks passed")
sys.exit(1 if failures else 0)
