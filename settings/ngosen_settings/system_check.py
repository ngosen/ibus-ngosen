# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Checks how IBus is set up on this machine and builds the text of a bug report."""

import glob
import os
import re
import subprocess
from dataclasses import dataclass
from urllib.parse import urlencode

from .i18n import _

ISSUE_URL = "https://github.com/ngosen/ibus-ngosen/issues/new"
MESSENGER_URL = "https://m.me/61595753582618"

IM_VARIABLES = ("GTK_IM_MODULE", "QT_IM_MODULE", "XMODIFIERS")

OK, WARN, FAIL = "ok", "warn", "fail"

ENGINE = "ngosen"
GNOME_SOURCES = "org.gnome.desktop.input-sources"

START_IBUS, RESTART_IBUS, ADD_SOURCE = "start-ibus", "restart-ibus", "add-source"


@dataclass
class Facts:
    env: dict
    ibus_running: bool = False
    # False when IBus started before Ngó Sen was installed, so it does not know the engine yet.
    engine_known: bool = True
    engine_replaced: bool = False
    # None outside GNOME, where IBus keeps its own list.
    in_gnome_sources: bool = None
    fcitx_running: bool = False
    # A GTK module of fcitx5 is installed, which GTK may pick on X11 when nothing names one.
    fcitx_gtk_module: bool = False
    distro: str = ""
    ibus_version: str = ""
    ngosen_version: str = ""
    gnome_shell_version: str = ""

    @property
    def session(self):
        return self.env.get("XDG_SESSION_TYPE", "").lower()

    @property
    def desktops(self):
        return [d.upper() for d in self.env.get("XDG_CURRENT_DESKTOP", "").split(":") if d]

    @property
    def gnome(self):
        return "GNOME" in self.desktops


@dataclass
class Finding:
    level: str
    title: str
    fix: str = ""
    # What the window can do about it (a fix action above), and the command to copy when that fails.
    action: str = ""
    command: str = ""


def steps(facts):
    """Every check that applies to this machine, passed or not, in the order to fix them."""
    if not facts.ibus_running:
        return [
            Finding(
                FAIL,
                _("IBus is not running"),
                _("Log out and back in, or run ibus start."),
                START_IBUS,
                "ibus start",
            )
        ]
    found = [Finding(OK, _("IBus is running"))]
    if facts.engine_replaced:
        found.append(_restart_finding(_("IBus still runs Ngó Sen from before the update")))
    elif not facts.engine_known:
        found.append(_restart_finding(_("IBus started before Ngó Sen was installed")))
    found += _source_findings(facts)
    found += _variable_findings(facts)
    if facts.fcitx_running:
        found.append(
            Finding(
                WARN,
                _("fcitx5 is running next to IBus"),
                _("Two input methods compete for keys; stop fcitx5 from starting at login."),
            )
        )
    return found


def _restart_finding(title):
    return Finding(
        WARN,
        title,
        _("Restart IBus, or log out and back in, to start the installed version."),
        RESTART_IBUS,
        "ibus restart",
    )


def _source_findings(facts):
    if facts.in_gnome_sources is None:
        return []
    if facts.in_gnome_sources:
        return [Finding(OK, _("Ngó Sen is in the input sources"))]
    return [
        Finding(
            FAIL,
            _("Ngó Sen is not in the input sources"),
            _("Settings › Keyboard › Input Sources: add “Vietnamese (Ngó Sen)”."),
            ADD_SOURCE,
        )
    ]


def _variable_findings(facts):
    found = []
    for variable, apps in (("GTK_IM_MODULE", _("GTK apps")), ("QT_IM_MODULE", _("Qt apps"))):
        value = facts.env.get(variable, "")
        # The wayland module reaches IBus through the compositor.
        if value and value != "ibus" and not (value == "wayland" and facts.session == "wayland"):
            # GNOME connects apps to IBus itself; elsewhere the variable has to name it.
            if facts.gnome:
                fix = _("Remove {} from the session environment.").format(variable)
            else:
                fix = _("Set {} in the session environment.").format(f"{variable}=ibus")
            title = _("{apps} use another input method ({value})").format(apps=apps, value=value)
            found.append(Finding(FAIL, title, fix))
    # Apps that talk to IBus themselves on Wayland bypass GNOME Shell, and no click can be told apart
    # from a reset there, so Sen keeps the underline in them.
    if facts.gnome and facts.session == "wayland" and facts.env.get("GTK_IM_MODULE") == "ibus":
        found.append(
            Finding(
                WARN,
                _("GTK apps keep the underline: GNOME Wayland does not need GTK_IM_MODULE"),
                _("Remove {} from the session environment.").format("GTK_IM_MODULE"),
            )
        )
    if (
        facts.session == "x11"
        and facts.fcitx_gtk_module
        and not facts.fcitx_running
        and not facts.env.get("GTK_IM_MODULE")
    ):
        found.append(
            Finding(
                WARN,
                _("GTK apps may pick fcitx5, which is not running"),
                _("Set {} in the session environment, or remove fcitx5.").format(
                    "GTK_IM_MODULE=ibus"
                ),
            )
        )
    if facts.env.get("XMODIFIERS") == "@im=ibus":
        found.append(Finding(OK, _("Older X11 apps use IBus")))
    else:
        found.append(
            Finding(
                WARN,
                _("Older X11 apps (xterm, Alacritty) have no input method"),
                _("Set {} in the session environment.").format("XMODIFIERS=@im=ibus"),
            )
        )
    return found


def fix_label(action):
    return {
        START_IBUS: _("Start IBus"),
        RESTART_IBUS: _("Restart IBus"),
        ADD_SOURCE: _("Add Ngó Sen"),
    }[action]


def fixed_message(action):
    return {
        START_IBUS: _("Started IBus."),
        RESTART_IBUS: _("Restarted IBus."),
        ADD_SOURCE: _("Added Ngó Sen to the input sources."),
    }[action]


# IBus takes a moment to come back on the bus after starting.
SETTLE_MS = {START_IBUS: 1500, RESTART_IBUS: 1500}
# A slow machine may need longer; check again this often before calling the fix failed.
RETRY_MS, RETRIES = 500, 8
# Restarting last, so it also picks up the input source just added.
FIX_ORDER = (START_IBUS, ADD_SOURCE, RESTART_IBUS)


def summary(found, failed=()):
    """Heading and text above the steps; failed fixes have no button left."""
    problems = [f for f in found if f.level != OK]
    if not problems:
        return _("This machine is ready"), _("Try typing in any app.")
    title = _("Steps left to fix: {}").format(len(problems))
    fixable = sum(1 for f in problems if f.action and f.action not in failed)
    if fixable > 1:
        text = _(
            "Use the button on a step, or fix them all at once. Ngó Sen only changes this "
            "account's settings."
        )
    elif fixable:
        text = _("Use the button on the step. Ngó Sen only changes this account's settings.")
    else:
        text = _("Each step says what to do.")
    return title, text


def failed_text(finding):
    if not finding.command:
        return finding.fix
    return _("Could not fix this.") + " " + finding.fix


def with_ngosen(sources):
    """The GNOME input sources once Ngó Sen is added after the others."""
    if ("ibus", ENGINE) in sources:
        return list(sources)
    return list(sources) + [("ibus", ENGINE)]


def run_fix(action, sources):
    """Runs a step's fix. Returns (done, undo), where undo puts things back or is None.

    sources is an object with get() and set(list) for the GNOME input sources.
    """
    if action == ADD_SOURCE:
        before = sources.get()
        if before is None or not sources.set(with_ngosen(before)):
            return False, None
        return True, lambda: _remove_ngosen(sources)
    if action == RESTART_IBUS:
        return _succeeds(["ibus", "restart"]), None
    if action == START_IBUS:
        return _succeeds(["ibus", "start"]), None
    return False, None


def _remove_ngosen(sources):
    # Only the added source goes, so changes made in GNOME Settings since then stay.
    current = sources.get()
    return current is not None and sources.set([s for s in current if s != ("ibus", ENGINE)])


def _succeeds(cmd):
    # Not pipes: a daemon it starts keeps them open, and reading them would wait for it.
    out = subprocess.DEVNULL
    try:
        return subprocess.run(cmd, stdout=out, stderr=out, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


class Fixes:
    """What the check page's fix buttons are doing; the page only draws it."""

    def __init__(self, sources):
        self.sources = sources
        self.busy = set()
        self.failed = set()
        self._retries = 0

    def fixable(self, findings):
        return [f.action for f in findings if f.action and f.action not in self.failed]

    def run(self, actions):
        """Runs the fixes; returns (done, undos, ms to wait before checking again)."""
        done, undos = [], {}
        for action in sorted(actions, key=FIX_ORDER.index):
            ok, undo = run_fix(action, self.sources)
            if not ok:
                self.failed.add(action)
                continue
            done.append(action)
            if undo:
                undos[action] = undo
        return done, undos, max((SETTLE_MS.get(a, 0) for a in done), default=0)

    def settle_again(self, done, findings):
        """ms to wait before checking again while a slow fix may still be taking effect, or 0."""
        left = {f.action for f in findings}
        slow = set(done) & set(SETTLE_MS)
        # A restarted IBus shows as not running until it is back on the bus.
        if slow and left & (slow | {START_IBUS}) and self._retries < RETRIES:
            self._retries += 1
            return RETRY_MS
        self._retries = 0
        return 0

    def finish(self, done, undos, findings):
        """After checking again: the message to show and its undo, empty when nothing got fixed."""
        self.busy = set()
        left = {f.action for f in findings}
        # A fix that ran but left its step did not work.
        self.failed |= left & set(done)
        # A restart that left IBus stopped shows only the start step.
        if RESTART_IBUS in done and START_IBUS in left:
            self.failed.add(RESTART_IBUS)
            left = left | {RESTART_IBUS}
        self.failed &= left
        fixed = [a for a in done if a not in left]
        if not fixed:
            return "", None
        steps_undone = [undos[a] for a in fixed if a in undos]
        message = " ".join(fixed_message(a) for a in fixed)
        return message, self._undo(steps_undone) if steps_undone else None

    @staticmethod
    def _undo(undos):
        def undo():
            return all([step() for step in reversed(undos)])

        return undo


def report(facts, findings):
    """Plain text for the bug report, which the user reviews before sending."""
    marks = {OK: "OK", WARN: "!", FAIL: "X"}
    desktop = ":".join(facts.desktops) or "?"
    lines = [
        f"Ngó Sen {facts.ngosen_version or '?'}, IBus {facts.ibus_version or '?'}",
        f"{facts.distro or '?'}, {desktop}, {facts.session or '?'}",
        " ".join(f"{v}={facts.env.get(v) or '(unset)'}" for v in IM_VARIABLES),
    ]
    if facts.gnome_shell_version:
        lines.append(f"GNOME Shell {facts.gnome_shell_version}")
    lines.append("")
    lines += [f"[{marks[f.level]}] {f.title}" for f in findings] or ["[OK] no setup problem found"]
    return "\n".join(lines)


def issue_url(facts, text):
    query = {"template": "bug_report.yml", "setup": text}
    if facts.ngosen_version:
        query["version"] = facts.ngosen_version
    if facts.distro:
        query["distro"] = facts.distro
    return f"{ISSUE_URL}?{urlencode(query)}"


def collect(sources, ngosen_version="", env=None, proc="/proc"):
    env = dict(os.environ if env is None else env)
    facts = Facts(env={k: v for k, v in env.items() if k in IM_VARIABLES or k.startswith("XDG_")})
    facts.ngosen_version = ngosen_version
    facts.distro = _distro()
    facts.ibus_running = ibus_owns_session(env, proc)
    if facts.ibus_running:
        facts.ibus_version = _output(["ibus", "version"]).strip().removeprefix("IBus ")
        facts.engine_known = engine_listed(_output(["ibus", "list-engine"]))
    facts.engine_replaced = runs_replaced_engine(proc)
    facts.fcitx_running = bool(_pids_named("fcitx5", proc))
    facts.fcitx_gtk_module = bool(_fcitx_gtk_modules())
    if facts.gnome:
        facts.gnome_shell_version = _output(["gnome-shell", "--version"]).strip()
        facts.gnome_shell_version = facts.gnome_shell_version.removeprefix("GNOME Shell ")
        current = sources.get()
        facts.in_gnome_sources = None if current is None else ("ibus", ENGINE) in current
    return facts


def engine_listed(text):
    """Whether ibus list-engine names Ngó Sen; a list that could not be read does not count."""
    names = engine_names(text)
    return not names or ENGINE in names


def engine_names(text):
    """Engine names in what ibus list-engine prints: an indented "name - long name" each."""
    return re.findall(r"^\s+(\S+) - ", text, re.M)


def _distro():
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return ""


def _output(cmd):
    env = {**os.environ, "LC_ALL": "C"}
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=3, env=env).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _fcitx_gtk_modules():
    patterns = (
        "/usr/lib*/gtk-[34].0/*/immodules/*fcitx5*.so",
        "/usr/lib/*/gtk-[34].0/*/immodules/*fcitx5*.so",
    )
    return [path for pattern in patterns for path in glob.glob(pattern)]


def _pids_named(name, proc="/proc"):
    """Directories under proc of this user's processes called name."""
    try:
        pids = [p for p in os.listdir(proc) if p.isdigit()]
    except OSError:
        return []
    uid = os.getuid()
    found = []
    for pid in pids:
        path = os.path.join(proc, pid)
        try:
            if os.stat(path).st_uid != uid:
                continue
            # Any process can pick a name that is not UTF-8.
            with open(os.path.join(path, "comm"), encoding="utf-8", errors="replace") as f:
                if f.read().strip() == name:
                    found.append(path)
        except OSError:
            continue
    return found


def _machine_id():
    for path in ("/var/lib/dbus/machine-id", "/etc/machine-id"):
        try:
            with open(path, encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            continue
    return ""


def _ibus_address_name(env):
    """Display part of the address file name, as IBus builds it."""
    if env.get("WAYLAND_DISPLAY"):
        return "unix-" + env["WAYLAND_DISPLAY"]
    host, _sep, rest = env.get("DISPLAY", ":0").partition(":")
    return f"{host or 'unix'}-{rest.split('.')[0] or '0'}"


def ibus_owns_session(env, proc="/proc", machine_id=None):
    """Whether this session's IBus address file names a running ibus-daemon.

    fcitx5 writes its own pid there when it takes the session; that does not count.
    """
    path = env.get("IBUS_ADDRESS_FILE")
    if not path:
        config_home = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
        name = f"{machine_id or _machine_id()}-{_ibus_address_name(env)}"
        path = os.path.join(config_home, "ibus", "bus", name)
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            match = re.search(r"^IBUS_DAEMON_PID=(\d+)", f.read(), re.M)
    except FileNotFoundError:
        # IBus started with IBUS_ADDRESS or under another display name writes no file found here.
        return bool(_pids_named("ibus-daemon", proc))
    except OSError:
        return False
    if match is None:
        return False
    try:
        with open(
            os.path.join(proc, match.group(1), "comm"), encoding="utf-8", errors="replace"
        ) as f:
            return f.read().strip() == "ibus-daemon"
    except OSError:
        return False


def runs_replaced_engine(proc="/proc"):
    """Whether the running engine is a program an update has replaced.

    Updating the package does not restart the engine, so it keeps typing with the old code.
    """
    # The kernel keeps the first 15 characters of a program name.
    for path in _pids_named("ibus-engine-ngosen"[:15], proc):
        try:
            if os.readlink(os.path.join(path, "exe")).endswith(" (deleted)"):
                return True
        except OSError:
            continue
    return False
