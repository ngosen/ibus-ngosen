# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Switches between English and Vietnamese from a desktop shortcut, also with no field focused."""

import os
import sys
import time

from . import i18n, system_check
from .i18n import _

# The engine takes any file named so; one per run, so two quick presses are two requests.
REQUEST_PREFIX = "toggle-"


def state_dir():
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.path.join(base, "ngosen")


def ibus_running():
    return system_check.session_owner(os.environ) == "ibus"


def toggle(folder=None, engine_in_use=system_check.engine_in_use, running=ibus_running):
    """Returns (exit code, message); the message is empty when it worked."""
    if not running():
        return 1, _("IBus is not running.")
    # Empty where each field has its own engine; the engine then drops a request it cannot take.
    engine = engine_in_use()
    if engine and engine != system_check.ENGINE:
        return 1, _("Ngó Sen is not the input source in use. Switch to it once, then try again.")
    folder = folder or state_dir()
    try:
        os.makedirs(folder, mode=0o700, exist_ok=True)
        # The engine watches the folder, switches as with the toggle key and removes the file.
        name = f"{REQUEST_PREFIX}{time.monotonic_ns()}-{os.getpid()}"
        with open(os.path.join(folder, name), "x", encoding="utf-8"):
            pass
    except OSError as e:
        return 1, str(e)
    return 0, ""


def notify(message):
    # A shortcut has no terminal to print to.
    try:
        from gi.repository import Gio, GLib

        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        bus.call_sync(
            "org.freedesktop.Notifications",
            "/org/freedesktop/Notifications",
            "org.freedesktop.Notifications",
            "Notify",
            GLib.Variant(
                "(susssasa{sv}i)",
                (
                    "Ngó Sen",
                    0,
                    "ibus-ngosen",
                    _("Could not switch English/Vietnamese"),
                    message,
                    [],
                    {},
                    6000,
                ),
            ),
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )
    except Exception:  # noqa: BLE001 - the message is already on stderr
        pass


def main(localedir):
    i18n.setup(localedir)
    code, message = toggle()
    if code != 0:
        print(message, file=sys.stderr)
        notify(message)
    return code
