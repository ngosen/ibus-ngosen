# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import gettext

DOMAIN = "ibus-ngosen"

_translation = gettext.NullTranslations()


def setup(localedir):
    """Vietnamese whatever the desktop language is, as in the fcitx5 edition."""
    global _translation
    _translation = gettext.translation(DOMAIN, localedir, languages=["vi"], fallback=True)


def _(text):
    return _translation.gettext(text)


def N_(text):
    return text
