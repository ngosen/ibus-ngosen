# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Labels and hints, worded as in the fcitx5 edition so a setting has one name in both."""

from .i18n import N_

POSITIONS = [
    ("Disabled", N_("Disabled")),
    ("Non-Start", N_("Non-Start")),
    ("Everywhere", N_("Everywhere")),
]
# Stored as the fcitx5 edition stores key lists: both keys in either order, with either key.
TOGGLE_KEYS = [
    ("Control+Shift_L Control+Shift_R Shift+Control_L Shift+Control_R", "Ctrl+Shift"),
    ("Shift+Alt_L Shift+Alt_R Alt+Shift_L Alt+Shift_R", "Shift+Alt"),
    ("", N_("Disabled")),
]
# The fcitx5 edition's default, and Shift+~ as ibus-unikey uses.
MODE_MENU_KEYS = [
    ("grave", "`"),
    ("Shift+asciitilde", "Shift+~"),
    ("", N_("Disabled")),
]
# The keys that pick a mode in the menu, each one letter or digit.
SHORTCUTS = ["ShortcutSen", "ShortcutPreedit", "ShortcutOff"]
LOCK_KEYS = [("Disabled", N_("Disabled")), ("Shift", "Shift"), ("Ctrl", "Ctrl"), ("Alt", "Alt")]
TIME_FORMATS = [
    ("%H:%M", "15:04 (24h)"),
    ("%H:%M:%S", "15:04:05 (24h)"),
    ("%I:%M %p", "03:04 PM"),
    ("%I:%M:%S %p", "03:04:05 PM"),
    ("", N_("None")),
]
DATE_FORMATS = [
    ("%d/%m/%Y", "dd/MM/yyyy"),
    ("%d/%m/%y", "dd/MM/yy"),
    ("%m/%d/%Y", "MM/dd/yyyy"),
    ("%Y-%m-%d", "yyyy-MM-dd"),
    ("%y-%m-%d", "yy-MM-dd"),
    ("", N_("None")),
]

LABELS = {
    "InputMethod": N_("Input Method"),
    "ToggleKey": N_("Switch Between English and Vietnamese"),
    "ModeMenuKey": N_("Mode Menu Hotkey"),
    "ShortcutSen": N_("Shortcut for Sen"),
    "ShortcutPreedit": N_("Shortcut for Preedit"),
    "ShortcutOff": N_("Shortcut for English"),
    "DirectTyping": N_("Type with Sen where the app allows (experimental)"),
    "OutputCharset": N_("Output Charset"),
    "EnableCustomKeymap": N_("Custom Keymap"),
    "SpellCheck": N_("Enable Spell Check Using Dictionary"),
    "EnableDictionary": N_("Custom Dictionary"),
    "AutoNonVnRestore": N_("Auto Restore Invalid Words"),
    "LockWordModifier": N_("Key to Keep the Word as Typed"),
    "DdFreeStyle": N_("Allow dd To Produce đ When Auto Restore Invalid Words Is On"),
    "ModernStyle": N_("Use oà, uý (Instead Of òa, úy)"),
    "FreeMarking": N_("Allow Type With More Freedom"),
    "BackspaceRemovesTone": N_("Backspace Removes the Tone Mark"),
    "RetoneSelection": N_("Change the tone of a typed word"),
    "W2U": N_("Type w to Produce ư"),
    "BracketTransform": N_("Type [ -> ơ, ] -> ư, { -> Ơ, } -> Ư"),
    "AutoCapitalizeAfterPunctuation": N_(
        "Auto capitalize after sentence-ending punctuation (. ! ? Enter)"
    ),
    "CapitalizeStartOfText": N_("Capitalize the first letter of the text or of a line"),
    "EnableMacro": N_("Enable Macro"),
    "CapitalizeMacro": N_("Capitalize Macro"),
    "TimeFormat": N_("Time Format ($TIME in macro)"),
    "DateFormat": N_("Date Format ($DATE in macro)"),
}

HINTS = {
    "ToggleKey": N_(
        "Tap the keys together and let go; the top bar shows V or E. Super+Space still switches input sources."
    ),
    "ModeMenuKey": N_(
        "Opens a menu to switch every app to Sen, underlined typing or English. Press it twice to type the key itself; in English it types as usual."
    ),
    "DirectTyping": N_(
        "Text goes straight into fields that report the text around the cursor, without an underline. Elsewhere words keep the underline."
    ),
    "OutputCharset": N_(
        "Keep Unicode unless an old document or app needs another one, such as TCVN3 (ABC)."
    ),
    "EnableCustomKeymap": N_("The keys below, used when the input method is Custom."),
    "SpellCheck": N_("Words that are not Vietnamese get no tone marks."),
    "EnableDictionary": N_(
        "Check spelling against the list below. Off: the list that comes with Ngó Sen."
    ),
    "AutoNonVnRestore": N_("Typing windows still gives windows."),
    "LockWordModifier": N_(
        "Tap the key alone to keep the word as shown: tunx, Ctrl → tũn, with no restore or macro. Alt also shows the menu bar in some apps."
    ),
    "DdFreeStyle": N_("dd and Space stays đ instead of going back to dd."),
    "ModernStyle": N_("hoà, khoẻ, thuý, tuỳ. Off: hòa, khỏe, thúy, tùy."),
    "FreeMarking": N_("Tone marks can also go at the end of the word."),
    "BackspaceRemovesTone": N_(
        "z in Telex (0 in VNI) removes the tone mark even with this off. On a word without one, Backspace deletes as usual."
    ),
    "RetoneSelection": N_(
        "Click right after chao, or select it in an X11 app, and type f to get chào. Only when typing with Sen; Tab or Esc puts the key back."
    ),
    "W2U": N_(
        "Non-Start: nhw → như, but w alone stays w. Everywhere: w alone gives ư too. uw always gives ư."
    ),
    "BracketTransform": N_("ch]a → chưa, m[f → mờ. Type a bracket twice to get it back: [[ → [."),
    "AutoCapitalizeAfterPunctuation": N_("ban. tooi → ban. Tôi. The same after Enter."),
    "CapitalizeStartOfText": N_(
        "xin → Xin in an empty field or on a new line. Not in address bars or some apps; on GNOME 47 and later, Chrome and similar apps skip an empty field."
    ),
    "TimeFormat": N_("Macros support dynamic placeholders: $TIME and $DATE."),
}

# What a word looks like while typing it, shown under the input method.
TYPING_EXAMPLES = {
    "Telex": "vieetj → việt",
    "VNI": "vie65t → việt",
    "VIQR": "vie^.t → việt",
    "Telex + VNI": "vieetj → việt",
    "Telex + VNI + VIQR": "vieetj → việt",
}

# Pages and their groups, in the order they show.
TYPING_GROUPS = [
    (None, ["InputMethod", "ToggleKey", "ModeMenuKey", "DirectTyping", "OutputCharset"]),
    (
        N_("Tone marks"),
        [
            "SpellCheck",
            "AutoNonVnRestore",
            "LockWordModifier",
            "DdFreeStyle",
            "ModernStyle",
            "FreeMarking",
            "BackspaceRemovesTone",
            "RetoneSelection",
            "W2U",
            "BracketTransform",
        ],
    ),
    (N_("Quick typing"), ["AutoCapitalizeAfterPunctuation", "CapitalizeStartOfText"]),
    (N_("Mode menu"), SHORTCUTS),
]
MACRO_SWITCHES = ["EnableMacro", "CapitalizeMacro"]

CHOICES = {
    "ToggleKey": TOGGLE_KEYS,
    "ModeMenuKey": MODE_MENU_KEYS,
    "W2U": POSITIONS,
    "BracketTransform": POSITIONS,
    "LockWordModifier": LOCK_KEYS,
    "TimeFormat": TIME_FORMATS,
    "DateFormat": DATE_FORMATS,
}


def is_switch(key):
    return (
        key not in CHOICES and key not in SHORTCUTS and key not in ("InputMethod", "OutputCharset")
    )


def shortcut_problem(key, value, values):
    """Why value cannot pick the mode of key, given the saved values of the other shortcuts."""
    if len(value) != 1 or not value.isascii() or not value.isalnum():
        return N_("One letter or digit.")
    if any(values.get(other, "").lower() == value.lower() for other in SHORTCUTS if other != key):
        return N_("Another mode already uses this key.")
    return None


def valid_macro_key(key):
    """Letters and digits only, as the fcitx5 edition allows."""
    return key.isalnum()
