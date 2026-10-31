# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Toggle keys in the fcitx5 list format the engine reads, such as "Control+Shift_L Shift+Control_L"."""

import re

from .i18n import N_

# The modifier each key sets, in the order labels show them. GTK 4 reports Alt pressed after Shift as Meta.
MODIFIER_KEYS = {
    "Control_L": "Control",
    "Control_R": "Control",
    "Shift_L": "Shift",
    "Shift_R": "Shift",
    "Alt_L": "Alt",
    "Alt_R": "Alt",
    "Meta_L": "Alt",
    "Meta_R": "Alt",
    "Super_L": "Super",
    "Super_R": "Super",
}
ORDER = ["Control", "Shift", "Alt", "Super"]
SHOWN = {"Control": "Ctrl"}
# GTK accelerator names and xkb option words for the same modifiers.
ACCELERATOR_MODIFIERS = {
    "control": "Control",
    "ctrl": "Control",
    "primary": "Control",
    "shift": "Shift",
    "alt": "Alt",
    "mod1": "Alt",
    "meta": "Alt",
    "super": "Super",
    "mod4": "Super",
}
XKB_WORDS = {"ctrl": "Control", "shift": "Shift", "alt": "Alt", "win": "Super"}
XKB_KEYS = {"space": "space", "caps": "Caps_Lock", "menu": "Menu", "tab": "Tab"}

NEEDS_TWO = N_("Press at least two keys together.")
TYPES_TEXT = N_("Shift with a key types a capital letter or a symbol.")
GNOME_USES = N_("GNOME already uses these keys to switch input sources.")
ALT_MENU = N_("Firefox and some other apps open their menu bar when Alt is let go.")


def _key_name(name):
    return name.lower() if len(name) == 1 else name


def _sorted(modifiers):
    return [m for m in ORDER if m in modifiers]


def chord(modifiers, key):
    """(modifiers, key) as a set and a key name; key is None when the chord is modifiers only."""
    modifiers = set(modifiers)
    if key in MODIFIER_KEYS:
        modifiers.add(MODIFIER_KEYS[key])
        key = None
    return frozenset(modifiers), (None if key is None else _key_name(key))


def from_pressed(names):
    """The chord for keys held together, by their GDK key names."""
    modifiers = {MODIFIER_KEYS[n] for n in names if n in MODIFIER_KEYS}
    others = [n for n in names if n not in MODIFIER_KEYS]
    if len(others) > 1:
        return None
    return chord(modifiers, others[0] if others else None)


def value(keys):
    """The stored value: a modifier-only chord in every order and with either key, as fcitx5 does."""
    modifiers, key = keys
    if key is not None:
        return "+".join(_sorted(modifiers) + [key])
    entries = []
    for last in reversed(_sorted(modifiers)):
        held = "+".join(m for m in _sorted(modifiers) if m != last)
        entries += [f"{held}+{last}_L", f"{held}+{last}_R"]
    return " ".join(entries)


def parse(text):
    """The chord a stored value stands for, or None when its entries disagree."""
    found = set()
    for entry in text.split():
        *held, key = entry.split("+")
        found.add(chord({ACCELERATOR_MODIFIERS.get(m.lower(), m) for m in held}, key))
    return found.pop() if len(found) == 1 else None


def label(text):
    keys = parse(text)
    if keys is None:
        return text
    modifiers, key = keys
    shown = [SHOWN.get(m, m) for m in _sorted(modifiers)]
    if key is not None:
        shown.append(key.upper() if len(key) == 1 else key[:1].upper() + key[1:])
    return "+".join(shown)


def accelerator(text):
    """A GTK accelerator such as <Shift><Super>space as a chord."""
    held = re.findall(r"<(\w+)>", text)
    key = re.sub(r"<\w+>", "", text)
    if not key:
        return None
    return chord({ACCELERATOR_MODIFIERS.get(m.lower(), m) for m in held}, key)


def xkb_toggle(option):
    """An xkb option such as grp:alt_shift_toggle as a chord, if it is a two-key toggle."""
    match = re.fullmatch(r"grp:(\w+)_toggle", option)
    if not match:
        return None
    modifiers, key = set(), None
    for word in match.group(1).split("_"):
        word = word[1:] if word[:1] in "lr" and word[1:] in XKB_WORDS else word
        if word in XKB_WORDS:
            modifiers.add(XKB_WORDS[word])
        elif word in XKB_KEYS and key is None:
            key = XKB_KEYS[word]
        else:
            return None
    if len(modifiers) + (key is not None) < 2:
        return None
    return frozenset(modifiers), key


def gnome_chords(accelerators, xkb_options):
    found = [accelerator(a) for a in accelerators] + [xkb_toggle(o) for o in xkb_options]
    return {c for c in found if c is not None}


def problem(keys, taken):
    """(error, warning) for a chord: an error keeps it from being saved."""
    if keys is None:
        return NEEDS_TWO, None
    modifiers, key = keys
    if len(modifiers) + (key is not None) < 2:
        return NEEDS_TWO, None
    if key is not None and modifiers == {"Shift"}:
        return TYPES_TEXT, None
    if keys in taken:
        return GNOME_USES, None
    if key is not None and modifiers == {"Alt"}:
        return None, ALT_MENU
    return None, None
