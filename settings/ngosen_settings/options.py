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
# The fcitx5 edition's default, and Shift+~ as ibus-unikey uses. A lone ` is too small to see in a combo.
MODE_MENU_KEYS = [
    ("grave", N_("` (key above Tab)")),
    ("Shift+asciitilde", "Shift+~"),
    ("", N_("Disabled")),
]
# Off by default, as in fcitx5; the menu key stays on ` without Ctrl.
CYCLE_MODE_KEYS = [
    ("", N_("Disabled")),
    ("Control+grave", "Ctrl+`"),
]
# Off by default, as in fcitx5; a key saved there stays offered.
CONVERT_KEYS = [
    ("", N_("Disabled")),
    ("Control+Shift+F6", "Ctrl+Shift+F6"),
]
# Stored by their English labels, in the order of the core's letter case.
CONVERT_CASES = [
    ("Keep", N_("Keep")),
    ("UPPER CASE", N_("UPPER CASE")),
    ("lower case", N_("lower case")),
    ("Sentence case", N_("Sentence case")),
    ("Title Case", N_("Title Case")),
]
# Settings that offer the charsets the engine knows.
CHARSET_KEYS = ("OutputCharset", "ConvertFrom", "ConvertTo")
# fcitx5 drags the modes into any order; these are the common ones, and a saved order stays offered.
MODE_ORDERS = [
    ("Sen,Preedit,Emoji,Teencode,Off,Vim", N_("Sen, Preedit, OFF")),
    ("Preedit,Sen,Emoji,Teencode,Off,Vim", N_("Preedit, Sen, OFF")),
    ("Off,Sen,Preedit,Emoji,Teencode,Vim", N_("OFF, Sen, Preedit")),
]
# The labels above name only these, the order of the switches around them aside.
ORDERED_MODES = ("Sen", "Preedit", "Off")
# Named in their own language, as in fcitx5.
UI_LANGUAGES = [("Vietnamese", "Tiếng Việt"), ("English", "English")]
SHOW_MODES = [
    "ShowModeSen",
    "ShowModePreedit",
    "ShowModeEmoji",
    "ShowModeTeencode",
    "ShowModeOff",
    "ShowModeVim",
]
SHOW_MENUS = [
    "ShowMenuInputMethod",
    "ShowMenuCharset",
    "ShowMenuMacro",
    "ShowMenuCapitalizeMacro",
    "ShowMenuAutoCapitalize",
    "ShowMenuAutoRestore",
    "ShowMenuDictionary",
]
# The keys that pick a mode in the menu, each one letter or digit.
SHORTCUTS = [
    "ShortcutSen",
    "ShortcutPreedit",
    "ShortcutEmoji",
    "ShortcutTeencode",
    "ShortcutOff",
    "ShortcutVim",
]
# Stored by their English labels, as fcitx5 stores the enum.
TOGGLE_SCOPES = [("All apps", N_("All apps")), ("Each app", N_("Each app"))]
EMOJI_OFFER_AT = [
    ("At the end of a sentence", N_("At the end of a sentence")),
    ("After each word", N_("After each word")),
]
EMOJI_PLACEMENTS = [
    ("After the word", N_("After the word")),
    ("Instead of the word", N_("Instead of the word")),
]
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
    "ToggleScope": N_("Switch Applies To"),
    "ModeMenuKey": N_("Mode Menu Hotkey"),
    "CycleModeKey": N_("Cycle Mode Hotkey"),
    "ModeOrder": N_("Mode Order"),
    "ShowModeSen": N_("Show Sen"),
    "ShowModePreedit": N_("Show Preedit"),
    "ShowModeOff": N_("Show OFF"),
    "ShowModeVim": N_("Show Vim mode"),
    "ShowModeEmoji": N_("Show emoji suggestions"),
    "ShowModeTeencode": N_("Show teencode"),
    "UiLanguage": N_("Interface Language"),
    # Under a group title that says where they show, so each is named as in the menu.
    "ShowMenuInputMethod": N_("Input Method"),
    "ShowMenuCharset": N_("Charset"),
    "ShowMenuMacro": N_("Macro"),
    "ShowMenuCapitalizeMacro": N_("Capitalize Macro"),
    "ShowMenuAutoCapitalize": N_("Auto Capitalize"),
    "ShowMenuAutoRestore": N_("Auto Restore Invalid Words"),
    "ShowMenuDictionary": N_("Custom Dictionary"),
    "ShortcutSen": N_("Shortcut for Sen"),
    "ShortcutPreedit": N_("Shortcut for Preedit"),
    "ShortcutOff": N_("Shortcut for OFF"),
    "ShortcutVim": N_("Shortcut for Vim mode"),
    "ShortcutEmoji": N_("Shortcut for emoji suggestions"),
    "ShortcutTeencode": N_("Shortcut for teencode"),
    "EmojiSuggestions": N_("Suggest emoji while typing"),
    "EmojiPlacement": N_("Put a picked emoji"),
    "EmojiOfferAt": N_("Offer emoji"),
    "EnglishEmojiKeywords": N_("English keywords"),
    "ConvertKey": N_("Convert Selected Text Hotkey"),
    "ConvertFrom": N_("Convert From"),
    "ConvertTo": N_("Convert To"),
    "ConvertCase": N_("Letter Case"),
    "ConvertStripDiacritics": N_("Remove Diacritics"),
    "YahooEmoticons": N_("Yahoo Messenger emoticons"),
    "DirectTyping": N_("Mode"),
    "OutputCharset": N_("Output Charset"),
    "EnableCustomKeymap": N_("Custom Keymap"),
    "EnableDictionary": N_("Custom Dictionary"),
    "AutoNonVnRestore": N_("Auto Restore Invalid Words"),
    "LockWordModifier": N_("Key to Keep the Word as Typed"),
    "DdFreeStyle": N_("Allow dd To Produce đ When Auto Restore Invalid Words Is On"),
    "ModernStyle": N_("Use oà, uý (Instead Of òa, úy)"),
    "FreeMarking": N_("Allow Type With More Freedom"),
    "BackspaceRemovesTone": N_("Backspace Removes the Tone Mark"),
    "RetoneSelection": N_("Change the tone of a typed word"),
    "RawWordAfterSlash": N_("Type a word that starts with / as is"),
    "RetypeAfterSwitch": N_("Retype text typed before switching on"),
    "W2U": N_("Type w to Produce ư"),
    "BracketTransform": N_("Type [ -> ơ, ] -> ư, { -> Ơ, } -> Ư"),
    "AutoCapitalizeAfterPunctuation": N_(
        "Auto capitalize after sentence-ending punctuation (. ! ? Enter)"
    ),
    "CapitalizeStartOfText": N_("Capitalize the first letter of the text or of a line"),
    "DoubleSpaceToPeriod": N_("Double Space to Period"),
    "DoubleHyphenToEmDash": N_("Double Hyphen to Em-Dash (--)"),
    "EnableMacro": N_("Enable Macro"),
    "CapitalizeMacro": N_("Capitalize Macro"),
    "EnableMacroInOffMode": N_("Macros while typing English"),
    "TimeFormat": N_("Time Format ($TIME in macro)"),
    "DateFormat": N_("Date Format ($DATE in macro)"),
}

HINTS = {
    "ConvertKey": N_(
        "Select text in an app, then press this key. The text changes in place; Ctrl+Z brings it back."
    ),
    "ConvertFrom": N_("Old documents are often TCVN3."),
    "ConvertStripDiacritics": N_("Tiếng Việt becomes Tieng Viet."),
    "ToggleKey": N_(
        "Tap the keys together and let go; the top bar shows V or E. Super+Space still switches input sources."
    ),
    "ToggleScope": N_(
        "All apps switches English/Vietnamese everywhere except apps set to OFF; Each app remembers a separate choice for each app."
    ),
    "ModeMenuKey": N_(
        "Opens a menu to pick Sen, underlined typing or Off for the app in use. Press it twice to type the key itself; while typing English it types as usual."
    ),
    "UiLanguage": N_("The top bar menu changes at once, this window the next time it opens."),
    "CycleModeKey": N_(
        "Moves the app in use to the next mode in the list below, and remembers it for that app."
    ),
    "ModeOrder": N_(
        "With the mode menu open, press a mode's key to pick it for the app in use. Pick the app's usual mode again to make it follow the global setting."
    ),
    "OutputCharset": N_(
        "Keep Unicode unless an old document or app needs another one, such as TCVN3 (ABC). "
        "Unicode tổ hợp sends tone marks apart from their letters, which terminals and many apps "
        "handle badly. Cứu dấu works only with Unicode."
    ),
    "EnableCustomKeymap": N_("The keys below, used when the input method is Custom."),
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
    "RawWordAfterSlash": N_(
        "/cost and /usr/share stay as typed, at the start of a line or after a space, so chat commands and file paths work. và/hoặc and @tên still get tones."
    ),
    "RetoneSelection": N_(
        "Click right after chao, or select it in an X11 app, and type f to get chào. Only when typing with Sen; Tab or Esc puts the key back."
    ),
    "RetypeAfterSwitch": N_(
        "Typed vieetj in English? Switch to Vietnamese and it becomes việt; Tab or Esc puts it back. Where a word may be English on purpose, Enter retypes and Tab or Esc keeps it."
    ),
    "W2U": N_(
        "Non-Start: nhw → như, but w alone stays w. Everywhere: w alone gives ư too. uw always gives ư."
    ),
    "BracketTransform": N_("ch]a → chưa, m[f → mờ. Type a bracket twice to get it back: [[ → [."),
    "AutoCapitalizeAfterPunctuation": N_("ban. tooi → ban. Tôi. The same after Enter."),
    "CapitalizeStartOfText": N_(
        "xin → Xin in an empty field or on a new line. Not in address bars or some apps; on GNOME 47 and later, Chrome and similar apps skip an empty field."
    ),
    "DoubleSpaceToPeriod": N_("ban and Space twice gives “ban. ”."),
    "DoubleHyphenToEmDash": N_("a--b → a—b."),
    "EnableMacroInOffMode": N_(
        "With Enable Macro on, a macro such as ko → không expands even in English."
    ),
    "TimeFormat": N_("Macros support dynamic placeholders: $TIME and $DATE."),
    "EmojiSuggestions": N_(
        "cười shows Tab: 😂 … next to the cursor. Tab numbers them: 1–5 picks one, Tab, Space or Enter the first, Esc keeps the word. haha and :) are replaced. Only where the hint is known to show."
    ),
    "YahooEmoticons": N_(
        "=)) and :x offer 🤣 and 😍, like on Yahoo Messenger; Tab swaps the code for the emoji."
    ),
    "EmojiPlacement": N_(
        "After the word: cười 😂. Instead of the word: 😂. haha and :) are always replaced."
    ),
    "EnglishEmojiKeywords": N_(
        "cat and thumbs up also offer 🐈 and 👍, from the Unicode list of English words. Words that"
        " are also Vietnamese, like can, are left out."
    ),
    "EmojiOfferAt": N_(
        "At the end of a sentence: the emoji of the sentence show while you type. After . ! ? or a"
        " short pause, 1–9 picks one, or Tab first where digits type tones, as in VNI; it goes at the"
        " cursor. Esc hides them until the next sentence."
        " After each word: the list shows as soon as a keyword is typed."
    ),
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
    (
        None,
        [
            "InputMethod",
            "ToggleKey",
            "ToggleScope",
            "ModeMenuKey",
            "CycleModeKey",
            "DirectTyping",
            "OutputCharset",
        ],
    ),
    (
        N_("Tone marks"),
        [
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
    (
        N_("Quick typing"),
        [
            "RetypeAfterSwitch",
            "AutoCapitalizeAfterPunctuation",
            "CapitalizeStartOfText",
            "DoubleSpaceToPeriod",
            "DoubleHyphenToEmDash",
            "RawWordAfterSlash",
        ],
    ),
    (N_("Mode menu"), ["ModeOrder", *SHOW_MODES, *SHORTCUTS]),
    (N_("Show in the top bar menu"), SHOW_MENUS),
    (N_("Language"), ["UiLanguage"]),
]
# The Convert page, as in fcitx5.
CONVERT_CHARSETS = N_("Charsets")
CONVERT_GROUPS = [
    (N_("Hotkey"), ["ConvertKey"]),
    (CONVERT_CHARSETS, ["ConvertFrom", "ConvertTo"]),
    (N_("After converting"), ["ConvertStripDiacritics", "ConvertCase"]),
]
# The Emoji page, as in fcitx5.
EMOJI_SETTINGS = [
    "EmojiSuggestions",
    "EmojiOfferAt",
    "EmojiPlacement",
    "YahooEmoticons",
    "EnglishEmojiKeywords",
]
MACRO_SWITCHES = ["EnableMacro", "CapitalizeMacro", "EnableMacroInOffMode"]
# The mode of apps not set on their own, shown as the fcitx5 edition shows its Mode: (saved value, label, hint).
TYPING_MODES = [
    ("True", N_("Sen"), N_("Text goes straight into the app as you type.")),
    (
        "False",
        N_("Preedit"),
        N_(
            "The word is underlined until it is done. Use it in an app that Sen does not work with."
        ),
    ),
]

CHOICES = {
    "ToggleKey": TOGGLE_KEYS,
    "ToggleScope": TOGGLE_SCOPES,
    "ModeMenuKey": MODE_MENU_KEYS,
    "CycleModeKey": CYCLE_MODE_KEYS,
    "ModeOrder": MODE_ORDERS,
    "UiLanguage": UI_LANGUAGES,
    "W2U": POSITIONS,
    "BracketTransform": POSITIONS,
    "LockWordModifier": LOCK_KEYS,
    "TimeFormat": TIME_FORMATS,
    "DateFormat": DATE_FORMATS,
    "EmojiPlacement": EMOJI_PLACEMENTS,
    "EmojiOfferAt": EMOJI_OFFER_AT,
    "ConvertKey": CONVERT_KEYS,
    "ConvertCase": CONVERT_CASES,
}


def is_switch(key):
    return key not in CHOICES and key not in SHORTCUTS and key not in ("InputMethod", *CHARSET_KEYS)


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
