# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import gettext
import os

from . import ini, store

DOMAIN = "ibus-ngosen"

_translation = gettext.NullTranslations()


def setup(localedir):
    """Vietnamese whatever the desktop language is unless English was picked, as in fcitx5."""
    global _translation
    text = store.read_text(os.path.join(store.config_dir(), "ngosen.conf")) or ""
    if ini.parse(text)[0].get("UiLanguage") == "English":
        _translation = gettext.NullTranslations()
    else:
        _translation = gettext.translation(DOMAIN, localedir, languages=["vi"], fallback=True)


def _(text):
    return _translation.gettext(text)


def N_(text):
    return text
