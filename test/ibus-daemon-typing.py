# Types into the engine through a real ibus-daemon, as an IBus client that keeps the text a simple
# app would show. The daemon commits the preedit itself on reset and focus out, as an app does when
# the engine asks for it. Run by run-with-daemon.sh.
import os
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
    def __init__(self, name, purpose=IBus.InputPurpose.FREE_FORM, app_commits=False):
        self.text = ""
        self.commits = []
        self.preedit = ""
        self.preedit_mode = IBus.PreeditFocusMode.CLEAR
        self.passed = []
        self.app_commits = app_commits
        self.ic = bus.create_input_context(name)
        caps = IBus.Capabilite.FOCUS | IBus.Capabilite.PREEDIT_TEXT | IBus.Capabilite.SURROUNDING_TEXT
        self.ic.set_capabilities(caps)
        self.ic.connect("commit-text", self.on_commit)
        if app_commits:
            self.ic.set_client_commit_preedit(True)
            self.ic.connect("update-preedit-text-with-mode", self.on_preedit_with_mode)
        else:
            self.ic.connect("update-preedit-text", self.on_preedit)
        self.ic.connect("hide-preedit-text", self.on_hide_preedit)
        self.ic.set_content_type(purpose, 0)
        self.ic.focus_in()
        # An input context of a plain client cannot pick its own engine.
        bus.set_global_engine("ngosen")
        pump(500)
        engine = self.ic.get_engine()
        if engine is None or engine.get_name() != "ngosen":
            sys.exit("the engine did not start")
        self.report()

    def report(self):
        n = len(self.text)
        self.ic.set_surrounding_text(IBus.Text.new_from_string(self.text), n, n)

    def on_commit(self, _ic, text):
        self.commits.append(text.get_text())
        self.text += text.get_text()
        self.report()

    def on_preedit(self, _ic, text, _cursor, visible):
        self.preedit = text.get_text() if visible else ""

    def on_preedit_with_mode(self, _ic, text, _cursor, visible, mode):
        self.preedit = text.get_text() if visible else ""
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
                elif char:
                    self.text += chr(char)
                self.report()

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
        self.ic.process_key_event(IBus.KEY_Control_L, 0, IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.RELEASE_MASK)
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
    check(app.commits == ["viê", "a "], f"app reset ({who}): the word stays and the next one starts fresh", app.commits)
    app.close()

    app = App("focus-out", app_commits=app_commits)
    app.type("viee")
    app.close()
    check(app.commits == ["viê"], f"focus out ({who}): one commit", app.commits)
    app.ic.focus_in()
    pump(200)
    app.type("a ")
    check(app.commits == ["viê", "a "], f"focus out ({who}): the next word starts fresh", app.commits)
    app.close()

app = App("enter")
app.type("viee")
app.key(IBus.KEY_Return)
pump(200)
check(app.commits == ["viê"], "enter: commits", app.commits)
check(app.passed == ["Return"], "enter: keys the app got", app.passed)
check(app.text == "viê\n", "enter: the word comes before the new line", app.text)
app.close()

log_path = os.environ["NGOSEN_IBUS_LOG_FILE"]


def typed_log(purpose):
    open(log_path, "w").close()
    app = App("log", purpose)
    app.type("vieetj ")
    app.close()
    with open(log_path) as f:
        return f.read()


plain = typed_log(IBus.InputPurpose.FREE_FORM)
check("việt" in plain, "log: a plain field logs what was typed", plain)
for purpose in (IBus.InputPurpose.PASSWORD, IBus.InputPurpose.PIN):
    hidden = typed_log(purpose)
    leaked = [w for w in ("việt", "viê") if w in hidden]
    check(not leaked, f"log: {purpose.value_nick} field keeps no typed text", leaked)

if failures == 0:
    print("all IBus daemon checks passed")
sys.exit(1 if failures else 0)
