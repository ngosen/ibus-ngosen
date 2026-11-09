# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""What the fcitx5 edition's installer left for this account, and how to take it back.

A file goes only while it holds exactly what the installer wrote, as with install.sh --uninstall,
so the texts below have to stay the same as in ngosen/install.sh.
"""

import functools
import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field

AUTOSTART_NAME = "org.fcitx.Fcitx5.desktop"
AUTOSTART_SOURCE = f"/usr/share/applications/{AUTOSTART_NAME}"
SYSTEM_AUTOSTART = f"/etc/xdg/autostart/{AUTOSTART_NAME}"
AUTOSTART_MASK = "[Desktop Entry]\nType=Application\nName=Fcitx 5\nHidden=true\n"
ENV_FILE = "90-ngosen.conf"
GNOME_ENV = "GTK_IM_MODULE=fcitx\nQT_IM_MODULE=fcitx\nXMODIFIERS=@im=fcitx\nSDL_IM_MODULE=fcitx\n"
KDE_ENV = "XMODIFIERS=@im=fcitx\n"
LAUNCHERS = (
    "org.fcitx.Fcitx5.desktop",
    "org.fcitx.fcitx5-migrator.desktop",
    "fcitx5-configtool.desktop",
)
IM_CONFIG_CHANGE = "im-config"
KIMPANEL = "kimpanel@kde.org"
# Kinds of note: what only the user can decide about.
EDITED_ENVIRONMENT, EDITED_AUTOSTART, SYSTEM_STARTS_FCITX5 = "environment", "autostart", "system"
IM_CONFIG_PICK, KIMPANEL_INSTALLED = "im-config", "kimpanel"
# The variables that send apps to fcitx5.
_TO_FCITX = re.compile(r"^\s*(?:(?:GTK|QT|SDL)_IM_MODULE=\s*fcitx|XMODIFIERS=@im=fcitx)", re.M)


def hidden_launcher_entry(launcher_id):
    name = launcher_id.removesuffix(".desktop")
    return f"[Desktop Entry]\nType=Application\nName={name}\nNoDisplay=true\n"


def _home(env):
    return env.get("HOME") or os.path.expanduser("~")


def config_home(env):
    return env.get("XDG_CONFIG_HOME") or os.path.join(_home(env), ".config")


def applications_dir(env):
    data = env.get("XDG_DATA_HOME") or os.path.join(_home(env), ".local", "share")
    return os.path.join(data, "applications")


def changes_file(env):
    state = env.get("XDG_STATE_HOME") or os.path.join(_home(env), ".local", "state")
    return os.path.join(state, "ngosen", "install-changes")


def env_file(env):
    return os.path.join(config_home(env), "environment.d", ENV_FILE)


def xinputrc(env):
    return os.path.join(_home(env), ".xinputrc")


def _read(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


def _holds(data, text):
    # install.sh compares $(cat file) with $(printf ...), and both drop trailing newlines.
    return data is not None and data.rstrip(b"\n") == text.encode("utf-8").rstrip(b"\n")


@dataclass
class Leftovers:
    # Files that still hold exactly what the installer wrote.
    files: list = field(default_factory=list)
    # The installer picked fcitx5 in im-config, and that is still the pick.
    im_config: bool = False
    # Whether removing them changes the session environment, which needs a reload.
    environment: bool = False
    # What only the user can decide about, as (kind, path, command to copy or "").
    notes: list = field(default_factory=list)

    @property
    def fixable(self):
        return bool(self.files or self.im_config)


def find(env, has_im_config=None):
    """What the fcitx5 installer left behind for this account."""
    if has_im_config is None:
        has_im_config = shutil.which("im-config") is not None
    found = Leftovers()
    data = _read(changes_file(env))
    changes = (data or b"").decode("utf-8", "replace").splitlines()
    _find_environment(env, found)
    _find_autostart(env, found, installer_ran=data is not None)
    _find_im_config(env, found, has_im_config, changes)
    kimpanel = os.path.join(
        os.path.dirname(applications_dir(env)), "gnome-shell", "extensions", KIMPANEL
    )
    if f"installed {KIMPANEL}" in changes and os.path.isdir(kimpanel):
        found.notes.append((KIMPANEL_INSTALLED, kimpanel, f"gnome-extensions uninstall {KIMPANEL}"))
    if found.files or found.im_config:
        # Hidden launchers matter only next to the rest, so they go along with it.
        for launcher in LAUNCHERS:
            path = os.path.join(applications_dir(env), launcher)
            if _holds(_read(path), hidden_launcher_entry(launcher)):
                found.files.append(path)
    return found


def _find_environment(env, found):
    path = env_file(env)
    data = _read(path)
    if _holds(data, GNOME_ENV):
        found.files.append(path)
        found.environment = True
    elif data is not None and _TO_FCITX.search(data.decode("utf-8", "replace")):
        # KDE keeps fcitx5 after install.sh --uninstall too, and kwinrc still starts it.
        found.notes.append((EDITED_ENVIRONMENT, path, ""))


def _find_autostart(env, found, installer_ran):
    path = os.path.join(config_home(env), "autostart", AUTOSTART_NAME)
    data = _read(path)
    source = _read(AUTOSTART_SOURCE)
    if data is not None and _holds(data, AUTOSTART_MASK):
        return
    if data is not None and source is not None and data == source:
        found.files.append(path)
    elif data is not None and source is not None and b"Hidden=true" not in data:
        found.notes.append((EDITED_AUTOSTART, path, ""))
    if data is None and installer_ran and os.path.exists(SYSTEM_AUTOSTART):
        # The fcitx5 package starts it for every account; only a mask of this account's stops it.
        found.notes.append((SYSTEM_STARTS_FCITX5, SYSTEM_AUTOSTART, _mask_command(env)))


def _mask_command(env):
    folder = os.path.join(config_home(env), "autostart")
    home = _home(env)
    if folder.startswith(home + "/"):
        folder = "~/" + shlex.quote(folder[len(home) + 1 :])
    else:
        folder = shlex.quote(folder)
    text = AUTOSTART_MASK.replace("\n", "\\n")
    return f"mkdir -p {folder} && printf '{text}' > {folder}/{AUTOSTART_NAME}"


def _find_im_config(env, found, has_im_config, changes):
    runs_fcitx5 = re.search(rb"^run_im fcitx5$", _read(xinputrc(env)) or b"", re.M) is not None
    if not runs_fcitx5:
        return
    if IM_CONFIG_CHANGE in changes and has_im_config:
        found.im_config = True
    else:
        # Nothing tells whether the installer or the user picked fcitx5 there.
        command = _im_config_command() if has_im_config else ""
        found.notes.append((IM_CONFIG_PICK, xinputrc(env), command))


# The check page runs on the main loop, and the installed im-config does not change under it.
@functools.cache
def _im_config_is_1_1():
    try:
        out = subprocess.run(["im-config", "-h"], capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return False
    return "-w <name>" in out.stdout + out.stderr


def _im_config_command():
    return "im-config -w auto" if _im_config_is_1_1() else "im-config -n REMOVE"


def _succeeds(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _reload_user_environment():
    # The systemd user manager reads environment.d only when it starts, and can outlive a logout.
    _succeeds(["systemctl", "--user", "daemon-reload"])


def _write(path, data):
    if data is None:
        if os.path.lexists(path):
            os.remove(path)
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def _restore(before):
    ok = True
    for path, data in before.items():
        try:
            if _read(path) != data:
                _write(path, data)
        except OSError:
            ok = False
    return ok


def _without_im_config(data):
    lines = (data or b"").decode("utf-8", "replace").splitlines()
    kept = [line for line in lines if line != IM_CONFIG_CHANGE]
    return "".join(line + "\n" for line in kept).encode("utf-8")


def clean(env, has_im_config=None):
    """Takes back what find() reports, all or nothing.

    Returns (done, undo, what went): the paths removed, and IM_CONFIG_CHANGE if im-config was reset.
    Undo puts every byte back while nothing changed since.
    """
    found = find(env, has_im_config)
    if not found.fixable:
        return False, None, []
    changes = changes_file(env)
    watched = list(found.files) + ([xinputrc(env), changes] if found.im_config else [])
    before = {path: _read(path) for path in watched}
    try:
        for path in found.files:
            os.remove(path)
        if found.im_config:
            command = _im_config_command().split()
            if not _succeeds(command):
                raise OSError(f"{' '.join(command)} failed")
            _write(changes, _without_im_config(before[changes]))
    except OSError:
        _restore(before)
        if found.environment:
            _reload_user_environment()
        return False, None, []
    if found.environment:
        _reload_user_environment()
    after = {path: _read(path) for path in watched}

    def undo():
        if any(_read(path) != data for path, data in after.items()):
            return False
        ok = _restore(before)
        if found.environment:
            _reload_user_environment()
        return ok

    return True, undo, list(found.files) + ([IM_CONFIG_CHANGE] if found.im_config else [])
