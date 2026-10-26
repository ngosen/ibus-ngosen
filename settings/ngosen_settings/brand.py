# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Ngó Sen marks: Xanh Mono for the wordmark and for typed text."""

import ctypes
import ctypes.util
import os

from gi.repository import Gdk, Gtk, PangoCairo

CSS = """
.wordmark { font-family: "Xanh Mono", monospace; font-size: 26px; }
.typed text { font-family: "Xanh Mono", monospace; font-size: 17px; }
"""


def load_font(path):
    """Makes Xanh Mono available to this process only; the system monospace font stands in if not."""
    if not os.path.exists(path):
        return
    font_map = PangoCairo.FontMap.get_default()
    if hasattr(font_map, "add_font_file"):  # Pango 1.56
        try:
            font_map.add_font_file(path)
            return
        except Exception:
            pass
    library = ctypes.util.find_library("fontconfig")
    if library:
        ctypes.CDLL(library).FcConfigAppFontAddFile(None, path.encode())


def install_css():
    provider = Gtk.CssProvider()
    provider.load_from_string(CSS)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
