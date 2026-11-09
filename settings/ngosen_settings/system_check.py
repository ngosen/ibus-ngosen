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

from . import fcitx5_leftovers, keys
from .i18n import _

ISSUE_URL = "https://github.com/ngosen/ibus-ngosen/issues/new"
MESSENGER_URL = "https://m.me/61595753582618"

IM_VARIABLES = ("GTK_IM_MODULE", "QT_IM_MODULE", "XMODIFIERS")

OK, WARN, FAIL = "ok", "warn", "fail"
# Worth knowing but nothing to fix, so it is not counted as a step left.
INFO = "info"

ENGINE = "ngosen"
GNOME_SOURCES = "org.gnome.desktop.input-sources"
FORWARD_KEYS = "forward-keys@ngosen.github.io"

START_IBUS, RESTART_IBUS, ADD_SOURCE = "start-ibus", "restart-ibus", "add-source"
ENABLE_FORWARD_KEYS = "enable-forward-keys"
CLEAN_FCITX5 = "clean-fcitx5"
# Fixes that delete the user's files run only from their own button, never from "Fix all".
MANUAL_ONLY = {CLEAN_FCITX5}

SEN, PREEDIT = "sen", "preedit"
# As the engine reads ngosen-app-rules.conf (src/ngosen-ibus-app-modes.cpp).
APP_MODE_NUMBERS = {1: SEN, 2: SEN, 3: SEN, 4: SEN, 8: SEN, 5: PREEDIT}
NOT_APPS = ("gnome-shell", "QIBusInputContext", "xim")
INI_SPACE = " \t\r\f\v"


@dataclass
class Facts:
    env: dict
    ibus_running: bool = False
    # fcitx5 wrote its pid into this session's IBus address file, so apps reach fcitx5.
    fcitx_owns_session: bool = False
    # The engine ibus engine names, empty when it could not tell.
    current_engine: str = ""
    # The keys GNOME switches input sources with, as the user reads them.
    switch_keys: list = None
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
    # Sen, which types straight into the app; the underlined mode works around the keys GNOME drops.
    direct_typing: bool = False
    # What gnome-extensions info says; empty when GNOME Shell does not know the extension.
    forward_keys_state: str = ""
    has_gnome_portal: bool = False
    # What the fcitx5 edition's installer left on this account (fcitx5_leftovers.Leftovers).
    leftovers: object = None
    # Apps with a typing mode of their own, and how many of them picked Sen.
    picked_apps: int = 0
    sen_apps: int = 0

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
    leftovers = _leftover_findings(facts)
    if not facts.ibus_running:
        if facts.fcitx_owns_session:
            first = Finding(
                FAIL,
                _("fcitx5 holds the input method"),
                _("Stop fcitx5 from starting at login, then log out and back in."),
            )
        else:
            first = Finding(
                FAIL,
                _("IBus is not running"),
                _("Log out and back in, or run ibus start."),
                START_IBUS,
                "ibus start",
            )
        # The fcitx5 edition's files are often why IBus does not get the session.
        return [first] + leftovers
    found = [Finding(OK, _("IBus is running"))]
    if facts.engine_replaced:
        found.append(_restart_finding(_("IBus still runs Ngó Sen from before the update")))
    elif not facts.engine_known:
        found.append(_restart_finding(_("IBus started before Ngó Sen was installed")))
    found += _source_findings(facts)
    found += _engine_findings(facts)
    found += _variable_findings(facts)
    found += _shell_findings(facts)
    found += leftovers
    if facts.fcitx_running and not _leftovers_start_fcitx5(facts.leftovers):
        found.append(
            Finding(
                WARN,
                _("fcitx5 is running next to IBus"),
                _("Two input methods compete for keys; stop fcitx5 from starting at login."),
            )
        )
    return found


def _leftovers_start_fcitx5(leftovers):
    if leftovers is None:
        return False
    kinds = {kind for kind, _path, _command in leftovers.notes}
    return leftovers.fixable or bool(kinds - {fcitx5_leftovers.KIMPANEL_INSTALLED})


def _leftover_findings(facts):
    found = []
    leftovers = facts.leftovers
    if leftovers is None:
        return found
    if leftovers.fixable:
        found.append(
            Finding(
                WARN,
                _("Settings of the fcitx5 edition are left on this account"),
                _("Remove the files the fcitx5 installer wrote, then log out and back in."),
                CLEAN_FCITX5,
            )
        )
    if leftovers.notes:
        lines = [_note_text(kind, path, command) for kind, path, command in leftovers.notes]
        found.append(Finding(WARN, _("fcitx5 settings that only you can change"), "\n".join(lines)))
    return found


def _note_text(kind, path, command):
    path = _short_path(path)
    if kind == fcitx5_leftovers.EDITED_ENVIRONMENT:
        return _("{} sends apps to fcitx5; remove those lines if you do not use fcitx5.").format(
            path
        )
    if kind == fcitx5_leftovers.EDITED_AUTOSTART:
        return _("{} starts fcitx5 at login; remove it if you do not use fcitx5.").format(path)
    if kind == fcitx5_leftovers.SYSTEM_STARTS_FCITX5:
        return _(
            "The fcitx5 package starts fcitx5 at login for every account. To stop it for this "
            "account only, run: {}"
        ).format(command)
    if kind == fcitx5_leftovers.IM_CONFIG_PICK and command:
        return _(
            "im-config still starts fcitx5 at login. If you do not use fcitx5, run: {}"
        ).format(command)
    if kind == fcitx5_leftovers.IM_CONFIG_PICK:
        return _("{} still starts fcitx5 at login; remove its run_im fcitx5 line.").format(path)
    return _(
        "IBus does not use the Input Method Panel extension the fcitx5 installer added: {}"
    ).format(command)


def _short_path(path):
    home = os.path.expanduser("~")
    return "~" + path[len(home) :] if home != "/" and path.startswith(home + "/") else path


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


def _engine_findings(facts):
    # Typing English with another source is normal, so this only says how to switch back.
    if facts.current_engine in ("", ENGINE) or facts.in_gnome_sources is False:
        return []
    # GNOME runs xkb:us::eng for every keyboard layout, so the name stays out of the title.
    title = _("Ngó Sen is not the input source in use")
    if not facts.gnome:
        fix = _("Switch to Ngó Sen from the IBus menu.")
    elif facts.switch_keys:
        fix = _("Switch to Ngó Sen with {}.").format(_(" or ").join(facts.switch_keys))
    else:
        fix = _("Switch to Ngó Sen from the input source menu in the top bar.")
    return [Finding(INFO, title, fix)]


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
    elif facts.env.get("XMODIFIERS") == "@im=fcitx":
        found.append(
            Finding(
                WARN,
                _("Older X11 apps use fcitx5"),
                _("Set {} in the session environment.").format("XMODIFIERS=@im=ibus"),
            )
        )
    else:
        found.append(
            Finding(
                WARN,
                _("Older X11 apps (xterm, Alacritty) have no input method"),
                _("Set {} in the session environment.").format("XMODIFIERS=@im=ibus"),
            )
        )
    return found


def drops_forwarded_keys(version):
    """GNOME 50.0 to 50.3 drop the keys an input method sends on to the app (mutter#4853)."""
    match = re.match(r"50\.(\d+)$", version)
    return match is not None and int(match.group(1)) <= 3


def _shell_findings(facts):
    if not facts.gnome:
        return []
    found = []
    version = facts.gnome_shell_version
    if (facts.direct_typing or facts.sen_apps) and drops_forwarded_keys(version):
        found.append(_forward_keys_finding(facts.forward_keys_state, version))
    # On Wayland only the portal tells which app has the focus.
    if facts.session == "wayland" and not facts.has_gnome_portal:
        found.append(
            Finding(
                WARN,
                _("Ngó Sen cannot tell which app is in use"),
                _(
                    "Install xdg-desktop-portal-gnome, then log out and back in; fixes for single apps and the typing mode picked for each app need it."
                ),
            )
        )
    return found


def _forward_keys_finding(state, version):
    if state == "ACTIVE":
        return Finding(OK, _("The fix for GNOME {} is on").format(version))
    title = _("Sen keeps the underline: GNOME {} drops the keys Ngó Sen sends").format(version)
    # GNOME reads a newly installed extension only at login.
    if not state:
        fix = _("Log out and back in. If this stays, update Ngó Sen or update to GNOME 50.4.")
        return Finding(WARN, title, fix)
    fix = _("Turn on the fix: gnome-extensions enable {}. If keys still drop, log out and back in.")
    command = f"gnome-extensions enable {FORWARD_KEYS}"
    return Finding(WARN, title, fix.format(FORWARD_KEYS), ENABLE_FORWARD_KEYS, command)


def fix_label(action):
    return {
        START_IBUS: _("Start IBus"),
        RESTART_IBUS: _("Restart IBus"),
        ADD_SOURCE: _("Add Ngó Sen"),
        ENABLE_FORWARD_KEYS: _("Turn on"),
        CLEAN_FCITX5: _("Remove"),
    }[action]


def fixed_message(action, removed=()):
    if action == CLEAN_FCITX5:
        reset = fcitx5_leftovers.IM_CONFIG_CHANGE in removed
        paths = ", ".join(_short_path(p) for p in removed if p != fcitx5_leftovers.IM_CONFIG_CHANGE)
        if paths and reset:
            return _(
                "Removed {} and set im-config back to its default. Log out and back in."
            ).format(paths)
        if reset:
            return _("Set im-config back to its default. Log out and back in.")
        return _("Removed {}. Log out and back in.").format(paths)
    return {
        START_IBUS: _("Started IBus."),
        RESTART_IBUS: _("Restarted IBus."),
        ADD_SOURCE: _("Added Ngó Sen to the input sources."),
        ENABLE_FORWARD_KEYS: _("Turned on the GNOME extension."),
    }[action]


# IBus takes a moment to come back on the bus after starting.
SETTLE_MS = {START_IBUS: 1500, RESTART_IBUS: 1500, ENABLE_FORWARD_KEYS: 500}
# A slow machine may need longer; check again this often before calling the fix failed.
RETRY_MS, RETRIES = 500, 8
# Restarting last, so it also picks up the input source just added.
FIX_ORDER = (CLEAN_FCITX5, START_IBUS, ADD_SOURCE, ENABLE_FORWARD_KEYS, RESTART_IBUS)


def summary(found, failed=frozenset()):
    """Heading and text above the steps; failed fixes have no button left."""
    problems = steps_left(found)
    if not problems:
        return _("This machine is ready"), _("Try typing in any app.")
    title = _("Steps left to fix: {}").format(len(problems))
    fixable = sum(1 for f in problems if f.action and f.action not in failed | MANUAL_ONLY)
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


def steps_left(found):
    return [f for f in found if f.level not in (OK, INFO)]


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
    if action == ENABLE_FORWARD_KEYS:
        if not _succeeds(["gnome-extensions", "enable", FORWARD_KEYS]):
            return False, None
        return True, lambda: _succeeds(["gnome-extensions", "disable", FORWARD_KEYS])
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

    def __init__(self, sources, env=None):
        self.sources = sources
        self.env = os.environ if env is None else env
        self.busy = set()
        self.failed = set()
        self.removed = []
        self._retries = 0

    def fixable(self, findings):
        """What "Fix all" runs."""
        skipped = self.failed | MANUAL_ONLY
        return [f.action for f in findings if f.action and f.action not in skipped]

    def run(self, actions):
        """Runs the fixes; returns (done, undos, ms to wait before checking again)."""
        done, undos = [], {}
        for action in sorted(actions, key=FIX_ORDER.index):
            if action == CLEAN_FCITX5:
                ok, undo, self.removed = fcitx5_leftovers.clean(self.env)
            else:
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
        message = " ".join(fixed_message(a, self.removed) for a in fixed)
        return message, self._undo(steps_undone) if steps_undone else None

    @staticmethod
    def _undo(undos):
        def undo():
            return all([step() for step in reversed(undos)])

        return undo


def report(facts, findings):
    """Plain text for the bug report, which the user reviews before sending."""
    marks = {OK: "OK", INFO: "i", WARN: "!", FAIL: "X"}
    desktop = ":".join(facts.desktops) or "?"
    lines = [
        f"Ngó Sen {facts.ngosen_version or '?'}, IBus {facts.ibus_version or '?'}"
        + (f", engine {facts.current_engine}" if facts.current_engine else ""),
        f"{facts.distro or '?'}, {desktop}, {facts.session or '?'}",
        " ".join(f"{v}={facts.env.get(v) or '(unset)'}" for v in IM_VARIABLES),
    ]
    if facts.gnome_shell_version:
        line = f"GNOME Shell {facts.gnome_shell_version}"
        line += f", forward-keys: {facts.forward_keys_state or 'not found'}"
        line += f", portal: {'installed' if facts.has_gnome_portal else 'not installed'}"
        mode = "Sen" if facts.direct_typing else "underlined"
        lines.append(f"{line}, mode: {mode}, apps with their own mode: {facts.picked_apps}")
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


def collect(
    sources, ngosen_version="", env=None, proc="/proc", direct_typing=False, app_modes_file=None
):
    env = dict(os.environ if env is None else env)
    facts = Facts(env={k: v for k, v in env.items() if k in IM_VARIABLES or k.startswith("XDG_")})
    facts.ngosen_version = ngosen_version
    facts.direct_typing = direct_typing
    facts.distro = _distro()
    owner = session_owner(env, proc)
    facts.ibus_running = owner == "ibus"
    facts.fcitx_owns_session = owner == "fcitx5"
    if facts.ibus_running:
        facts.ibus_version = _output(["ibus", "version"]).strip().removeprefix("IBus ")
        facts.engine_known = engine_listed(_output(["ibus", "list-engine"]))
        facts.current_engine = engine_in_use()
    modes = app_modes(_read(app_modes_file)) if app_modes_file else {}
    facts.picked_apps = len(modes)
    facts.sen_apps = sum(1 for mode in modes.values() if mode == SEN)
    facts.engine_replaced = runs_replaced_engine(proc)
    facts.fcitx_running = bool(_pids_named("fcitx5", proc))
    facts.fcitx_gtk_module = bool(_fcitx_gtk_modules())
    if facts.gnome:
        facts.gnome_shell_version = _output(["gnome-shell", "--version"]).strip()
        facts.gnome_shell_version = facts.gnome_shell_version.removeprefix("GNOME Shell ")
        facts.forward_keys_state = extension_state(
            _output(["gnome-extensions", "info", FORWARD_KEYS])
        )
        facts.has_gnome_portal = has_gnome_portal(env)
        current = sources.get()
        facts.in_gnome_sources = None if current is None else ("ibus", ENGINE) in current
        facts.switch_keys = switch_key_names(*sources.switch_keys())
    facts.leftovers = fcitx5_leftovers.find(env)
    return facts


def _read(path):
    try:
        # The engine splits lines at \n only.
        with open(path, encoding="utf-8", errors="replace", newline="") as f:
            return f.read()
    except OSError:
        return ""


def app_modes(text):
    """The typing mode each app picked, read as the engine reads ngosen-app-rules.conf."""
    modes = {}
    for line in text.split("\n"):
        if not line or line[0] == "#":
            continue
        app, equals, number = line.partition("=")
        number = number.strip(INI_SPACE) if equals else ""
        if not (0 < len(number) <= 2 and all(c in "0123456789" for c in number)):
            continue
        app = mode_app_name(app.strip(INI_SPACE))
        mode = APP_MODE_NUMBERS.get(int(number))
        if mode and app:
            modes[app] = mode
    return modes


def mode_app_name(program):
    name = program
    if len(name) > len(".desktop") and name.endswith(".desktop"):
        name = name[: -len(".desktop")]
    # As the core names an IBus client: "gtk3-im:firefox", and a snap's "firefox_firefox".
    colon = name.find(":")
    if colon != -1 and name[:colon].endswith("-im"):
        name = name[colon + 1 :]
    underscore = name.find("_")
    if underscore != -1 and name[:underscore] == name[underscore + 1 :]:
        name = name[:underscore]
    return "" if name in NOT_APPS else name


def engine_in_use():
    """The engine ibus engine names, or empty when the command failed or printed something else."""
    code, out = _run(["ibus", "engine"])
    words = out.split()
    if code != 0 or len(words) != 1 or not re.fullmatch(r"[\w:.@+-]+", words[0]):
        return ""
    return words[0]


def switch_key_names(accelerators, xkb_options):
    """GNOME's switch-input-source keys and xkb layout toggles, written as the user reads them."""
    # XF86 keys are special keys most keyboards do not have.
    chords = [keys.accelerator(a) for a in accelerators if "XF86" not in a]
    chords += [keys.xkb_toggle(option) for option in xkb_options]
    names = []
    for chord in chords:
        name = chord and keys.label(keys.value(chord))
        if name and name not in names:
            names.append(name)
    return names


def extension_state(text):
    """The State line of gnome-extensions info, which prints nothing for an unknown extension."""
    match = re.search(r"^\s*State:\s*(.+?)\s*$", text, re.M)
    return match.group(1) if match else ""


def has_gnome_portal(env):
    """Whether xdg-desktop-portal-gnome is installed, which D-Bus starts when asked."""
    home = env.get("XDG_DATA_HOME") or os.path.join(env.get("HOME", ""), ".local", "share")
    dirs = [home] + (env.get("XDG_DATA_DIRS") or "/usr/local/share").split(":") + ["/usr/share"]
    name = "dbus-1/services/org.freedesktop.impl.portal.desktop.gnome.service"
    return any(os.path.exists(os.path.join(d, name)) for d in dirs if d)


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
    return _run(cmd)[1]


def _run(cmd):
    """(exit status, stdout); a command that could not run counts as failed."""
    env = {**os.environ, "LC_ALL": "C"}
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=3, env=env)
    except (OSError, subprocess.SubprocessError):
        return -1, ""
    return done.returncode, done.stdout


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


def session_owner(env, proc="/proc", machine_id=None):
    """Which of ibus or fcitx5 wrote its running pid into this session's IBus address file.

    fcitx5 writes its own pid there when it takes the session. Empty when neither does.
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
        return "ibus" if _pids_named("ibus-daemon", proc) else ""
    except OSError:
        return ""
    if match is None:
        return ""
    try:
        with open(
            os.path.join(proc, match.group(1), "comm"), encoding="utf-8", errors="replace"
        ) as f:
            name = f.read().strip()
    except OSError:
        return ""
    return {"ibus-daemon": "ibus", "fcitx5": "fcitx5"}.get(name, "")


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
