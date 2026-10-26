# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reads and writes ~/.config/ngosen; the engine sees each write and reloads."""

import os
import subprocess
import tempfile

from . import ini

MACRO_LIST = "Macro"


def config_dir():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "ngosen")


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="surrogateescape", newline="") as f:
            return f.read()
    except FileNotFoundError:
        return None


def write_text(path, text):
    """Writes through a temporary file, so the engine never reads half a file."""
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=folder, prefix=os.path.basename(path) + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    except BaseException:
        os.unlink(temp)
        raise


def restore_text(path, text):
    if text is not None:
        write_text(path, text)
    elif os.path.exists(path):
        os.unlink(path)


class Engine:
    """Asks the engine, so the window shows the defaults and names the engine types with."""

    def __init__(self, program):
        self.program = program

    def _run(self, command):
        result = subprocess.run(
            [self.program, command], capture_output=True, text=True, check=True, timeout=10
        )
        return result.stdout

    def settings(self):
        return ini.parse(self._run("--print-settings"))[0]

    def input_methods(self):
        return self._run("--list-input-methods").splitlines()

    def charsets(self):
        return self._run("--list-charsets").splitlines()


class Store:
    """The settings and the macro list, with one step of undo."""

    def __init__(self, engine, folder=None):
        self.folder = folder or config_dir()
        self.settings_file = os.path.join(self.folder, "ngosen.conf")
        self.macro_file = os.path.join(self.folder, "ngosen-macro-table.conf")
        self.values = engine.settings()
        self.macros = ini.read_list(ini.parse(read_text(self.macro_file) or "")[1], MACRO_LIST)
        self._undo = None

    def set(self, key, value):
        if self.values.get(key) == value:
            return False
        before = read_text(self.settings_file)
        write_text(self.settings_file, ini.set_value(before or "", key, value))
        self._undo = (self.settings_file, before, "values", dict(self.values))
        self.values[key] = value
        return True

    def set_macros(self, macros):
        before = read_text(self.macro_file)
        _, sections = ini.parse(before or "")
        # Sections other than the list are not ours; keep them.
        kept = "".join(
            f"[{name}]\n" + "".join(f"{k}={ini.escape(v)}\n" for k, v in keys.items()) + "\n"
            for name, keys in sections.items()
            if not name.startswith(MACRO_LIST + "/")
        )
        write_text(self.macro_file, kept + ini.list_text(MACRO_LIST, macros))
        self._undo = (self.macro_file, before, "macros", list(self.macros))
        self.macros = list(macros)

    def can_undo(self):
        return self._undo is not None

    def undo(self):
        path, text, field, value = self._undo
        restore_text(path, text)
        setattr(self, field, value)
        self._undo = None
