# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Ngó Sen marks: larger text for the wordmark and for typed text, in the system font."""

from gi.repository import Gdk, Gtk

# Some monospace fallbacks misplace stacked tone marks, so the system font is used as it is.
CSS = """
.wordmark { font-size: 26px; }
.typed text { font-size: 17px; }
"""


def install_css():
    provider = Gtk.CssProvider()
    provider.load_from_string(CSS)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
