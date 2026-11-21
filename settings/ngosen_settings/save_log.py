# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Saves the typing log from a terminal, as the menu item does, and prints where it went."""

import os
import sys
import time

from . import i18n, system_check
from .i18n import _
from .toggle import ibus_running, state_dir

REQUEST_PREFIX = "save-log-"
REPLY_PREFIX = "saved-log-"
WAIT_SECONDS = 5


def save(
    folder=None,
    engine_in_use=system_check.engine_in_use,
    running=ibus_running,
    wait=WAIT_SECONDS,
):
    """Returns (exit code, message)."""
    if not running():
        return 1, _("IBus is not running.")
    engine = engine_in_use()
    if engine and engine != system_check.ENGINE:
        return 1, _("Ngó Sen is not the input source in use. Switch to it once, then try again.")
    folder = folder or state_dir()
    suffix = f"{time.monotonic_ns()}-{os.getpid()}"
    request = os.path.join(folder, REQUEST_PREFIX + suffix)
    reply = os.path.join(folder, REPLY_PREFIX + suffix)
    try:
        os.makedirs(folder, mode=0o700, exist_ok=True)
        with open(request, "x", encoding="utf-8"):
            pass
    except OSError as e:
        return 1, str(e)
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        try:
            with open(reply, encoding="utf-8") as f:
                path = f.read().strip()
        except FileNotFoundError:
            time.sleep(0.05)
            continue
        os.remove(reply)
        if not path:
            return 1, _("Could not save the typing log to ") + folder
        return 0, _("Typing log saved: ") + path
    # The engine has not started in this session yet, or another input method has the field.
    if os.path.exists(request):
        os.remove(request)
    return 1, _("Ngó Sen did not answer. Type a few letters with it in any app, then try again.")


def main(localedir):
    i18n.setup(localedir)
    code, message = save()
    print(message, file=sys.stdout if code == 0 else sys.stderr)
    return code
