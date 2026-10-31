# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Backups in the JSON of the fcitx5 edition, so either edition restores the other's."""

import json
import os
import tempfile
from datetime import datetime

from . import ini, keys
from .i18n import _
from .store import MACRO_LIST

COMPONENTS = ("config", "macros", "keymaps", "rules", "dictionary")
KEYMAP_FILE = "ngosen-custom-keymap.conf"
KEYMAP_LIST = "CustomKeymap"
# The fcitx5 edition keeps these as Mode, VietnameseOn and an indexed ToggleKey list.
IBUS_ONLY = ("DirectTyping", "ToggleKey")
# fcitx5 names its modes OFF, Sen, Preedit and Emoji Picker; OFF types with Sen when Vietnamese is on.
DIRECT_TYPING = {"off": "True", "sen": "True", "preedit": "False", "emoji picker": "False"}


class RestoreError(OSError):
    """A restore failed and some files could not be put back."""

    def __init__(self, paths):
        super().__init__(_("These files could not be put back: {}").format(", ".join(paths)))
        self.paths = paths


def english_mark():
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.path.join(base, "ngosen", "english")


class Paths:
    """Every file a restore writes. The marker is there while typing English."""

    def __init__(self, store):
        self.settings = store.settings_file
        self.macros = store.macro_file
        self.keymaps = os.path.join(store.folder, KEYMAP_FILE)
        self.dictionary = store.dictionary_file
        self.english = english_mark()


def read_bytes(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None


def put(path, data):
    """Writes data through a temporary file, or removes the file when data is None."""
    if data is None:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
        return
    folder = os.path.dirname(path)
    # The state folder also holds typing logs, which only the user may read.
    os.makedirs(folder, mode=0o700, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=folder, prefix=os.path.basename(path) + ".")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    except BaseException:
        os.unlink(temp)
        raise


def replace(changes, write=put):
    """Writes changes ({path: bytes or None}) and returns what the files held before.

    A failure puts back the files already written before it raises. Each file is replaced whole, but
    a crash between two files leaves some old and some new.
    """
    before = {path: read_bytes(path) for path in changes}
    written = []
    try:
        for path, data in changes.items():
            if data == before[path]:
                continue
            written.append(path)
            write(path, data)
    except Exception as error:
        failed = []
        for path in written:
            try:
                write(path, before[path])
            except OSError:
                failed.append(path)
        if failed:
            raise RestoreError(failed) from error
        raise
    return before


def _entries(path, name):
    text = read_bytes(path)
    entries = ini.read_list(ini.parse((text or b"").decode("utf-8"))[1], name)
    return [{"Key": key, "Value": value} for key, value in entries]


def export(engine, paths, target):
    """Writes the backup to target; raises OSError or ValueError."""
    values = engine.settings()
    config = {key: value for key, value in values.items() if key not in IBUS_ONLY}
    config["Mode"] = "Sen" if values.get("DirectTyping") == "True" else "Preedit"
    config["ToggleKey"] = {str(i): key for i, key in enumerate(values.get("ToggleKey", "").split())}
    config["VietnameseOn"] = "False" if os.path.exists(paths.english) else "True"
    backup = {
        "config": config,
        "macros": _entries(paths.macros, MACRO_LIST),
        "keymaps": _entries(paths.keymaps, KEYMAP_LIST),
    }
    dictionary = read_bytes(paths.dictionary)
    if dictionary is not None:
        backup["dictionary"] = dictionary.decode("utf-8")
    backup["meta"] = {
        "version": 1,
        "timestamp": datetime.now().isoformat(),
        "components": [k for k in COMPONENTS if k in backup],
    }
    put(target, json.dumps(backup, indent=2, ensure_ascii=False).encode("utf-8"))


def load(path):
    """The backup in path; raises OSError or ValueError when it is not one."""
    with open(path, encoding="utf-8") as f:
        backup = json.load(f)
    if not isinstance(backup, dict) or not any(k in backup for k in COMPONENTS):
        raise ValueError(_("No settings found in the file."))
    if not isinstance(backup.get("config", {}), dict):
        raise ValueError(_("The settings in the file are damaged."))
    for name in ("macros", "keymaps", "rules"):
        items = backup.get(name, [])
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise ValueError(_("The lists in the file are damaged."))
    for name in ("macros", "keymaps"):
        for item in backup.get(name, []):
            if not all(isinstance(item.get(k, ""), str) for k in ("Key", "Value")):
                raise ValueError(_("The lists in the file are damaged."))
    if not isinstance(backup.get("dictionary", ""), str):
        raise ValueError(_("The dictionary in the file is damaged."))
    try:
        # JSON can hold half of a surrogate pair, which no UTF-8 file can.
        json.dumps(backup, ensure_ascii=False).encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError(_("The file holds text that is not valid Unicode.")) from None
    return backup


def _text(value):
    """A value as the settings file holds it; fcitx5 gives strings, a hand-made file may not."""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, str):
        return value
    raise ValueError(_("The settings in the file are damaged."))


def _key_list(value):
    """fcitx5 gives a key list as {"0": …, "1": …}; fcitx5 stops at the first gap."""
    if value == "":
        return []
    if isinstance(value, str):
        return value.split()
    if isinstance(value, list):
        found = value
    elif isinstance(value, dict):
        found = []
        while str(len(found)) in value:
            found.append(value[str(len(found))])
    else:
        raise ValueError(_("The settings in the file are damaged."))
    if not all(isinstance(key, str) for key in found):
        raise ValueError(_("The settings in the file are damaged."))
    return found


def _shown(names):
    return ", ".join(keys.label(name) or name for name in names)


def _toggle_key(value, engine, notes):
    """The ToggleKey line to write, or None to keep the current one."""
    wanted = _key_list(value)
    if not wanted:
        return ""
    # The setting is one line split at spaces, so a key with a space cannot be kept.
    candidates = [key for key in wanted if key and not any(c.isspace() for c in key)]
    usable = engine.usable_toggle_keys(candidates) if candidates else set()
    kept = [key for key in wanted if key in usable]
    dropped = [key for key in wanted if key not in usable]
    if not kept:
        notes.append(
            _(
                "The switch key in the backup ({}) does not work in this edition, so the current one"
                " stays. It needs Ctrl, Alt, Shift or Super with another key."
            ).format(_shown(dropped))
        )
        return None
    if dropped:
        notes.append(
            _(
                "These switch keys in the backup do not work in this edition and are left out: {}."
                " They need Ctrl, Alt, Shift or Super with another key."
            ).format(_shown(dropped))
        )
    return " ".join(kept)


def _direct_typing(mode, notes):
    name = _text(mode)
    value = DIRECT_TYPING.get(name.lower())
    if value is None:
        notes.append(
            _(
                "The backup types in a mode this edition does not know ({}), so the current one stays."
            ).format(name)
        )
    elif name.lower() == "emoji picker":
        notes.append(_("This edition has no emoji picker, so words are underlined instead."))
    return value


def _settings(config, text, known, engine, notes):
    for key in known:
        if key not in IBUS_ONLY and key in config:
            text = ini.set_value(text, key, _text(config[key]))
    if "Mode" in config:
        direct = _direct_typing(config["Mode"], notes)
        if direct is not None:
            text = ini.set_value(text, "DirectTyping", direct)
    if "ToggleKey" in config:
        toggle = _toggle_key(config["ToggleKey"], engine, notes)
        if toggle is not None:
            text = ini.set_value(text, "ToggleKey", toggle)
    return text.encode("utf-8", "surrogateescape")


def _english(config, paths, notes):
    """The marker's new content: b"" for English, None for Vietnamese."""
    value = _text(config["VietnameseOn"])
    if value not in ("True", "False"):
        raise ValueError(_("The settings in the file are damaged."))
    if value == "False" and not os.path.exists(paths.english):
        notes.append(_("The backup was made while typing English, so typing switches to English."))
    return None if value == "True" else b""


def _list_file(text, name, items):
    """text with the list replaced and every other section kept, as Store.set_macros does."""
    _top, sections = ini.parse(text)
    kept = "".join(
        f"[{section}]\n" + "".join(f"{k}={ini.escape(v)}\n" for k, v in values.items()) + "\n"
        for section, values in sections.items()
        if not section.startswith(name + "/")
    )
    entries = [(item.get("Key", ""), item.get("Value", "")) for item in items]
    return (kept + ini.list_text(name, entries)).encode("utf-8", "surrogateescape")


def _current(path):
    data = read_bytes(path)
    return None if data is None else data.decode("utf-8", "surrogateescape")


def plan(backup, paths, engine):
    """The files to write for backup and what the user should know first. Writes nothing.

    Raises ValueError for a damaged backup, and OSError or SubprocessError when a file or the
    engine cannot be read.
    """
    notes = []
    changes = {}
    config = backup.get("config", {})
    if "config" in backup:
        known = list(engine.settings())
        changes[paths.settings] = _settings(
            config, _current(paths.settings) or "", known, engine, notes
        )
    for name, path, section in (
        ("macros", paths.macros, MACRO_LIST),
        ("keymaps", paths.keymaps, KEYMAP_LIST),
    ):
        if name in backup:
            current = _current(path)
            data = _list_file(current or "", section, backup[name])
            # An empty list needs no new file.
            changes[path] = None if current is None and not data else data
    if "dictionary" in backup:
        changes[paths.dictionary] = backup["dictionary"].encode("utf-8")
    # Last, so the running engine switches language only once the rest is written.
    if "VietnameseOn" in config:
        changes[paths.english] = _english(config, paths, notes)
    if backup.get("rules"):
        notes.append(_("Rules for each app are left out: this edition has none."))
    return changes, notes
