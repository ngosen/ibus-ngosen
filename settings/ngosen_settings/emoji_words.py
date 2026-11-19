# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Emoji page's lists: which words offer which emoji, and the apps that offer none.

Only the user's changes to the default words are kept, as in fcitx5, so words added to a later
version still reach the user.
"""

import unicodedata

from . import ini
from .emoji_table import EMOJI, GROUPS

WORDS = "Words"
# The engine writes the same line when it switches an app from its menu.
OFF_APPS_HEADER = "# Apps where Ngó Sen offers no emoji, one per line"
_BY_EMOJI = {row[0]: row for row in EMOJI}


def clean(word):
    """A word as the engine compares it: lower case, composed, single spaces."""
    return " ".join(unicodedata.normalize("NFC", word).lower().split())


def parse_edits(text):
    """The user's word changes, as the engine reads them: {(emoji, word): on}."""
    _top, sections = ini.parse(text or "")
    edits = {}
    index = 0
    # The engine stops at the first missing index and skips entries without both fields.
    while (section := sections.get(f"{WORDS}/{index}")) is not None:
        # Kept as written: the engine compares keywords literally, so cleaning could merge two.
        key = (section.get("Emoji", "").strip(), section.get("Keyword", "").strip())
        if all(key):
            edits[key] = section.get("On", "True") != "False"
        index += 1
    return edits


def edits_text(edits):
    return "".join(
        f"[{WORDS}/{i}]\nKeyword={ini.escape(word)}\nEmoji={ini.escape(emoji)}\n"
        f"On={'True' if on else 'False'}\n\n"
        for i, ((emoji, word), on) in enumerate(edits.items())
    )


def app_name(name):
    """An app as the engine names it, so names fcitx5 saved for the same app count as one."""
    name = name.strip()
    if len(name) > len(".desktop") and name.endswith(".desktop"):
        name = name[: -len(".desktop")]
    head, colon, rest = name.partition(":")
    if colon and head.endswith("-im"):
        name = rest
    head, underscore, rest = name.partition("_")
    if underscore and head == rest:
        name = head
    return "" if name in ("gnome-shell", "QIBusInputContext", "xim", "wayland") else name


def parse_apps(text):
    apps = []
    for line in ini.lines(text or ""):
        if line.startswith("#"):
            continue
        app = app_name(line)
        if app and app not in apps:
            apps.append(app)
    return apps


def apps_text(apps):
    return OFF_APPS_HEADER + "\n" + "".join(app + "\n" for app in apps)


class EmojiWords:
    """The words of every emoji, over the edits the store keeps."""

    def __init__(self, store):
        self.store = store

    @property
    def edits(self):
        return self.store.emoji_edits

    @property
    def off_apps(self):
        return self.store.emoji_off_apps

    # The words of an emoji, as (word, on): its defaults, then the user's own, then its name's.
    def chips(self, emoji):
        _e, _group, _name, defaults, others = _BY_EMOJI.get(emoji, (emoji, 0, "", (), ()))
        known = (*defaults, *others)
        added = [w for (e, w) in self.edits if e == emoji and w not in known]
        return [(w, self.is_on(emoji, w)) for w in (*defaults, *added, *others)]

    def is_on(self, emoji, word):
        return self.edits.get((emoji, word), word in self._defaults(emoji))

    def _defaults(self, emoji):
        return _BY_EMOJI[emoji][3] if emoji in _BY_EMOJI else ()

    def toggled(self, emoji, word):
        """The edits with word switched for emoji."""
        edits = dict(self.edits)
        on = not self.is_on(emoji, word)
        row = _BY_EMOJI.get(emoji)
        known = row is not None and word in (*row[3], *row[4])
        # A word of the user's own keeps its entry, so it stays on the page when turned off.
        if known and on == (word in row[3]):
            edits.pop((emoji, word), None)
        else:
            edits[(emoji, word)] = on
        return edits

    def added(self, emoji, word):
        """The edits with word turned on for emoji; None when it is empty or already there."""
        word = clean(word)
        if not word or any(w == word for w, _on in self.chips(emoji)):
            return None
        return {**self.edits, (emoji, word): True}

    def changed(self, emoji):
        return any(e == emoji for e, _w in self.edits)

    def reset(self, emoji):
        """The edits without any change to emoji."""
        return {key: on for key, on in self.edits.items() if key[0] != emoji}

    def rows(self, query="", group=None, only_on=False):
        """The table's rows that match, as in EMOJI."""
        needle = clean(query)
        shown = []
        for row in EMOJI:
            if group and GROUPS[row[1]] != group:
                continue
            chips = self.chips(row[0])
            if only_on and not any(on for _w, on in chips):
                continue
            if needle and needle != row[0] and not any(needle in w for w, _on in chips):
                continue
            shown.append(row)
        return shown
