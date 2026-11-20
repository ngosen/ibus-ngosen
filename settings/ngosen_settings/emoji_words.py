# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Emoji page's lists: which words offer which emoji, and the apps that offer none.

Only the user's changes to the default words are kept, as in fcitx5, so words added to a later
version still reach the user.
"""

import json
import unicodedata

from . import ini
from .emoji_table import EMOJI, GROUPS

WORDS = "Words"
# The engine writes the same line when it switches an app from its menu.
OFF_APPS_HEADER = "# Apps where Ngó Sen offers no emoji, one per line"
_BY_EMOJI = {row[0]: row for row in EMOJI}
# The fcitx5 edition's file of shared words, so either edition imports the other's.
SHARE_KIND = "ngosen-emoji-words"
MOST_SHARED = 5000
LONGEST_WORD = 40


def clean(word):
    """A word as the engine compares it: lower case, composed, single spaces."""
    return " ".join(unicodedata.normalize("NFC", word).lower().split())


def export_words(edits, path):
    """Writes the words the user turned on to path, for others to import. Returns how many."""
    items = [{"Keyword": w, "Emoji": e} for (e, w), on in sorted(edits.items()) if on]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"meta": {"kind": SHARE_KIND, "version": 1}, "emoji_words": items},
            f,
            indent=2,
            ensure_ascii=False,
        )
    return len(items)


def read_shared(path):
    """The (emoji, word) pairs in a shared file; raises OSError or ValueError when it is not one."""
    # i18n reads the settings through the store, which loads this module.
    from .i18n import _

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    meta = data.get("meta") if isinstance(data, dict) else None
    if not isinstance(meta, dict) or meta.get("kind") != SHARE_KIND:
        raise ValueError(_("This is not a file of emoji words exported from Ngó Sen."))
    items = data.get("emoji_words")
    if not isinstance(items, list) or len(items) > MOST_SHARED:
        raise ValueError(_("The emoji words in the file are damaged."))
    pairs = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(_("The emoji words in the file are damaged."))
        emoji, word = item.get("Emoji"), clean(str(item.get("Keyword", "")))
        # An emoji this version does not list, a long text or one the settings file cannot hold is
        # skipped rather than refused.
        if isinstance(emoji, str) and emoji in _BY_EMOJI and _fits(word):
            pairs.append((emoji, word))
    return pairs


def _fits(word):
    try:
        word.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return 0 < len(word) <= LONGEST_WORD


def parse_edits(text):
    """The user's word changes, as the engine reads them: {(emoji, word): on}."""
    _top, sections = ini.parse(text or "")
    edits = {}
    index = 0
    # The engine stops at the first missing index and skips entries without both fields.
    while (section := sections.get(f"{WORDS}/{index}")) is not None:
        # Kept as written: the engine compares keywords literally, so cleaning could merge two.
        key = (section.get("Emoji", ""), section.get("Keyword", ""))
        if all(key):
            add_edit(edits, key, section.get("On", "True") != "False")
        index += 1
    return edits


def add_edit(edits, key, on):
    """The engine offers the emoji for any entry that turns it on, whatever comes after."""
    edits[key] = edits.get(key, False) or on


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

    @property
    def english(self):
        """Off hides the English words, as the engine skips them."""
        return self.store.values.get("EnglishEmojiKeywords", "True") != "False"

    # The words of an emoji, as (word, on): its defaults, the user's own, English, then its name's.
    def chips(self, emoji):
        row = _BY_EMOJI.get(emoji, (emoji, 0, "", (), (), ()))
        defaults, others, english = row[3], row[4], self._english(emoji)
        known = (*defaults, *english, *others)
        added = [w for (e, w) in self.edits if e == emoji and w not in known]
        return [(w, self.is_on(emoji, w)) for w in (*defaults, *added, *english, *others)]

    def _english(self, emoji):
        return _BY_EMOJI[emoji][5] if self.english and emoji in _BY_EMOJI else ()

    def is_on(self, emoji, word):
        return self.edits.get((emoji, word), word in self._defaults(emoji))

    def _defaults(self, emoji):
        return (*_BY_EMOJI[emoji][3], *self._english(emoji)) if emoji in _BY_EMOJI else ()

    def toggled(self, emoji, word):
        """The edits with word switched for emoji."""
        edits = dict(self.edits)
        on = not self.is_on(emoji, word)
        row = _BY_EMOJI.get(emoji)
        known = row is not None and word in (*row[3], *row[4], *row[5])
        # A word of the user's own keeps its entry, so it stays on the page when turned off.
        if known and on == (word in self._defaults(emoji)):
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

    def merged(self, pairs):
        """The edits with the words in pairs turned on, except ones the user turned off, and how many."""
        edits = dict(self.edits)
        added = 0
        for emoji, word in pairs:
            if (emoji, word) in edits or self.is_on(emoji, word):
                continue
            edits[(emoji, word)] = True
            added += 1
        return edits, added

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
