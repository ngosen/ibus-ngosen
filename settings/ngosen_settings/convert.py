# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Convert page, as in fcitx5: the key that converts selected text, its charsets, and a box to
convert here."""

from gi.repository import Adw, Gdk, GLib, Gtk

from . import options
from .i18n import _

SETTING_KEYS = ("ConvertFrom", "ConvertTo", "ConvertCase", "ConvertStripDiacritics")
# Long enough to skip the runs in the middle of a fast paste or typing burst.
DELAY_MS = 150
BOX_HEIGHT = 110
COPIED_MS = 1500


def case_index(value):
    """The core's letter case: the place of value among the ConvertCase choices."""
    names = [name for name, _label in options.CONVERT_CASES]
    return names.index(value) if value in names else 0


def _text_view(editable=True):
    view = Gtk.TextView(
        wrap_mode=Gtk.WrapMode.WORD_CHAR,
        editable=editable,
        cursor_visible=editable,
        accepts_tab=False,
        top_margin=10,
        bottom_margin=10,
        left_margin=12,
        right_margin=12,
        css_classes=["typed"],
    )
    scroll = Gtk.ScrolledWindow(
        child=view,
        min_content_height=BOX_HEIGHT,
        hscrollbar_policy=Gtk.PolicyType.NEVER,
        css_classes=["card"],
    )
    return view, scroll


def _text(view):
    buffer = view.get_buffer()
    return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)


class ConvertPage:
    """convert(text) gives (converted text, None), or (None, a line saying why it could not)."""

    def __init__(self, rows, convert, on_swap):
        self.rows = rows
        self.convert = convert
        self.on_swap = on_swap
        self._pending = 0
        self.page = Adw.PreferencesPage(title=_("Convert"), icon_name="edit-find-replace-symbolic")
        for title, keys in options.CONVERT_GROUPS:
            group = Adw.PreferencesGroup(title=_(title))
            for key in keys:
                group.add(rows.build(key))
            if title == options.CONVERT_CHARSETS:
                swap = Gtk.Button(
                    label=_("S_wap"),
                    use_underline=True,
                    tooltip_text=_("Swap the charsets"),
                    css_classes=["flat"],
                )
                swap.connect("clicked", lambda _b: self.swap())
                group.set_header_suffix(swap)
            self.page.add(group)
        self.page.add(self._convert_here())

    def swap(self):
        values = self.rows.store.values
        self.on_swap(
            {"ConvertFrom": values.get("ConvertTo", ""), "ConvertTo": values.get("ConvertFrom", "")}
        )

    def _convert_here(self):
        group = Adw.PreferencesGroup(
            title=_("Convert here"),
            description=_("Paste text in the first box; the second shows it converted."),
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.source, source_box = _text_view()
        self.source.update_property(
            [Gtk.AccessibleProperty.LABEL], [_("Paste the text to convert")]
        )
        self.result, result_box = _text_view(editable=False)
        self.result.update_property(
            [Gtk.AccessibleProperty.LABEL], [_("The converted text shows here")]
        )
        self.source.get_buffer().connect("changed", lambda _b: self._later())
        box.append(source_box)
        box.append(result_box)
        bottom = Gtk.Box(spacing=8)
        self.error = Gtk.Label(wrap=True, xalign=0, use_markup=False)
        self.error_icon = Gtk.Image(icon_name="dialog-warning-symbolic", valign=Gtk.Align.START)
        self.copy = Gtk.Button(
            label=_("_Copy result"), use_underline=True, halign=Gtk.Align.END, hexpand=True
        )
        self.copy.connect("clicked", lambda _b: self._copy())
        bottom.append(self.error_icon)
        bottom.append(self.error)
        bottom.append(self.copy)
        box.append(bottom)
        group.add(box)
        self._show("", None)
        return group

    def _later(self):
        if self._pending:
            GLib.source_remove(self._pending)
        self._pending = GLib.timeout_add(DELAY_MS, self._on_time)

    def _on_time(self):
        self._pending = 0
        self.refresh()
        return GLib.SOURCE_REMOVE

    def refresh(self):
        """Converts the box again, after it or one of the settings changed."""
        text = _text(self.source)
        self._show(*(self.convert(text) if text else ("", None)))

    def _show(self, text, error):
        self.result.get_buffer().set_text(text or "")
        self.error.set_text(error or "")
        self.error.set_visible(bool(error))
        self.error_icon.set_visible(bool(error))
        self.copy.set_sensitive(bool(text))

    def _copy(self):
        Gdk.Display.get_default().get_clipboard().set(_text(self.result))
        self.copy.set_label(_("Copied"))
        GLib.timeout_add(COPIED_MS, self._copied_done)

    def _copied_done(self):
        self.copy.set_label(_("_Copy result"))
        return GLib.SOURCE_REMOVE
