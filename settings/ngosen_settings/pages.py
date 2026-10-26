# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""The pages of the window. Each control saves as soon as it changes."""

from gi.repository import Adw, GLib, Gtk

from . import options
from .i18n import N_, _


class SettingRows:
    """Builds a row for each setting and puts the saved values back into them."""

    def __init__(self, store, names, on_change):
        self.store = store
        self.names = names  # Values the engine accepts for InputMethod and OutputCharset.
        self.on_change = on_change
        self.loading = False
        self.rows = {}
        self.pairs = {}  # What each combo row lists, as (value, label).

    def build(self, key):
        if options.is_switch(key):
            row = Adw.SwitchRow()
            row.connect(
                "notify::active",
                lambda r, _p: self._changed(key, "True" if r.get_active() else "False"),
            )
        else:
            row = Adw.ComboRow()
            row.connect("notify::selected", lambda r, _p: self._changed(key, self._choice(key, r)))
        row.set_title(_(options.LABELS[key]))
        if key in options.HINTS:
            row.set_subtitle(_(options.HINTS[key]))
        self.rows[key] = row
        return row

    def choices(self, key):
        """(value, label) pairs; a value saved by hand that is not in the list stays offered."""
        if key in options.CHOICES:
            pairs = [(value, _(label)) for value, label in options.CHOICES[key]]
        else:
            pairs = [(value, value) for value in self.names[key]]
        current = self.store.values.get(key, "")
        if current not in (value for value, _label in pairs):
            pairs.append((current, current))
        return pairs

    def _choice(self, key, row):
        index = row.get_selected()
        pairs = self.pairs.get(key, [])
        return pairs[index][0] if index < len(pairs) else None

    def _changed(self, key, value):
        if key == "InputMethod":
            self._show_example()
        if not self.loading and value is not None:
            self.on_change(key, value)

    def _show_example(self):
        row = self.rows.get("InputMethod")
        if row is not None:
            row.set_subtitle(options.TYPING_EXAMPLES.get(self._choice("InputMethod", row), ""))

    def refresh(self):
        self.loading = True
        try:
            for key, row in self.rows.items():
                value = self.store.values.get(key, "")
                if isinstance(row, Adw.SwitchRow):
                    row.set_active(value == "True")
                    continue
                pairs = self.pairs[key] = self.choices(key)
                row.set_model(Gtk.StringList.new([label for _value, label in pairs]))
                row.set_selected([v for v, _label in pairs].index(value))
            self._show_example()
        finally:
            self.loading = False


def preferences_group(title=None, description=None):
    group = Adw.PreferencesGroup()
    if title:
        group.set_title(_(title))
    if description:
        group.set_description(description)
    return group


def typing_page(rows):
    page = Adw.PreferencesPage(title=_("Typing"), icon_name="input-keyboard-symbolic")
    for title, keys in options.TYPING_GROUPS:
        group = preferences_group(title)
        for key in keys:
            group.add(rows.build(key))
        if title is None:
            try_it = Adw.EntryRow(title=_("Try it"))
            try_it.add_css_class("typed")
            group.add(try_it)
        page.add(group)
    return page


class MacroPage:
    """The macro switches and the list, which saves on every add, edit and removal."""

    def __init__(self, store, rows, on_list_change):
        self.store = store
        self.on_list_change = on_list_change
        self.page = Adw.PreferencesPage(title=_("Macro"), icon_name="document-edit-symbolic")
        group = preferences_group()
        for key in options.MACRO_SWITCHES + ["TimeFormat", "DateFormat"]:
            group.add(rows.build(key))
        self.page.add(group)
        self.page.add(self._editor())
        self.page.add(self._list())

    def _editor(self):
        group = preferences_group()
        self.key_row = Adw.EntryRow(title=_("Abbreviation (e.g. kg)"))
        self.value_row = Adw.EntryRow(title=_("Full text (e.g. khô gà)"))
        self.value_row.add_css_class("typed")
        self.add_button = Gtk.Button(label=_("Add"), valign=Gtk.Align.CENTER)
        self.add_button.add_css_class("suggested-action")
        self.add_button.connect("clicked", lambda _b: self._add())
        self.value_row.add_suffix(self.add_button)
        for row in (self.key_row, self.value_row):
            row.connect("changed", lambda _r: self._check())
            row.connect("entry-activated", lambda _r: self._add())
            group.add(row)
        self._check()
        return group

    def _list(self):
        group = preferences_group()
        self.search = Gtk.SearchEntry(placeholder_text=_("Search macros..."))
        self.search.connect("search-changed", lambda _s: self.list.invalidate_filter())
        group.set_header_suffix(self.search)
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.list.add_css_class("boxed-list")
        self.list.set_placeholder(
            Gtk.Label(label=_("No macros yet."), margin_top=12, margin_bottom=12)
        )
        self.list.set_filter_func(self._matches)
        group.add(self.list)
        return group

    def _check(self):
        key = self.key_row.get_text()
        bad = bool(key) and not options.valid_macro_key(key)
        if bad:
            self.key_row.add_css_class("error")
        else:
            self.key_row.remove_css_class("error")
        self.key_row.set_tooltip_text(
            _("Macro keys cannot contain spaces or special characters.") if bad else None
        )
        exists = any(k == key for k, _v in self.store.macros)
        self.add_button.set_label(_("Update") if exists else _("Add"))
        self.add_button.set_sensitive(bool(key) and not bad and bool(self.value_row.get_text()))

    def _add(self):
        if not self.add_button.get_sensitive():
            return
        key, value = self.key_row.get_text(), self.value_row.get_text()
        macros = list(self.store.macros)
        index = next((i for i, (k, _v) in enumerate(macros) if k == key), None)
        if index is None:
            macros.append((key, value))
        else:
            macros[index] = (key, value)
        if self.on_list_change(macros, key):
            self.key_row.set_text("")
            self.value_row.set_text("")
            self.key_row.grab_focus()

    def _remove(self, key):
        self.on_list_change([(k, v) for k, v in self.store.macros if k != key], key)

    def _edit(self, key, value):
        self.key_row.set_text(key)
        self.value_row.set_text(value)
        self.value_row.grab_focus()

    def _matches(self, row):
        needle = self.search.get_text().casefold()
        return not needle or needle in row.macro[0].casefold() or needle in row.macro[1].casefold()

    def refresh(self):
        self.list.remove_all()
        for key, value in self.store.macros:
            self.list.append(self._macro_row(key, value))
        self._check()

    def _macro_row(self, key, value):
        row = Adw.ActionRow(use_markup=False, activatable=True)
        row.set_title(key)
        row.set_subtitle(value)
        row.macro = (key, value)
        row.connect("activated", lambda _r: self._edit(key, value))
        remove = Gtk.Button(
            icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER, tooltip_text=_("Remove")
        )
        remove.add_css_class("flat")
        remove.connect("clicked", lambda _b: self._remove(key))
        row.add_suffix(remove)
        return row


class DictionaryPage:
    """The custom dictionary switch and its word list, saved on every add and removal."""

    # Thousands of rows make GTK slow, so the list shows search results only.
    SHOWN = 100

    def __init__(self, store, rows, on_list_change):
        self.store = store
        self.on_list_change = on_list_change
        self.page = Adw.PreferencesPage(
            title=_("Dictionary"), icon_name="accessories-dictionary-symbolic"
        )
        group = preferences_group()
        self.switch = rows.build("EnableDictionary")
        group.add(self.switch)
        self.page.add(group)
        self.editor = preferences_group()
        self.word_row = Adw.EntryRow(title=_("Word (e.g. ngoãy)"))
        self.word_row.add_css_class("typed")
        self.add_button = Gtk.Button(label=_("Add"), valign=Gtk.Align.CENTER)
        self.add_button.add_css_class("suggested-action")
        self.add_button.connect("clicked", lambda _b: self._add())
        self.word_row.add_suffix(self.add_button)
        self.word_row.connect("changed", lambda _r: self._check())
        self.word_row.connect("entry-activated", lambda _r: self._add())
        self.editor.add(self.word_row)
        self.page.add(self.editor)
        self.page.add(self._list())
        self.switch.connect("notify::active", lambda _r, _p: self._enable())

    def _list(self):
        self.list_group = preferences_group()
        self.search = Gtk.SearchEntry(placeholder_text=_("Search words..."))
        self.search.connect("search-changed", lambda _s: self._show())
        self.list_group.set_header_suffix(self.search)
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.list.add_css_class("boxed-list")
        self.list_group.add(self.list)
        return self.list_group

    def _check(self):
        word = self.word_row.get_text().strip()
        bad = any(c.isspace() for c in word)
        if bad:
            self.word_row.add_css_class("error")
        else:
            self.word_row.remove_css_class("error")
        self.word_row.set_tooltip_text(_("One word, without spaces.") if bad else None)
        self.add_button.set_sensitive(bool(word) and not bad and word not in self.store.words)

    def _add(self):
        if not self.add_button.get_sensitive():
            return
        word = self.word_row.get_text().strip()
        if self.on_list_change(self.store.words + [word]):
            self.word_row.set_text("")
            self.search.set_text(word)
            self._show()  # The search entry reports the change only after a delay.

    def _remove(self, word):
        self.on_list_change([w for w in self.store.words if w != word])

    def _enable(self):
        on = self.switch.get_active()
        self.editor.set_sensitive(on)
        self.list_group.set_sensitive(on)

    def _show(self):
        self.list.remove_all()
        needle = self.search.get_text().strip().casefold()
        if not needle:
            count = len(self.store.words)
            self.list_group.set_description(_("{} words. Search to see them.").format(count))
            return
        found = [w for w in self.store.words if needle in w.casefold()]
        for word in found[: self.SHOWN]:
            self.list.append(self._word_row(word))
        if not found:
            text = _("No words found.")
        elif len(found) > self.SHOWN:
            text = _("Showing {} of {} words found.").format(self.SHOWN, len(found))
        else:
            text = None
        self.list_group.set_description(text)

    def refresh(self):
        self._show()
        self._check()
        self._enable()

    def _word_row(self, word):
        row = Adw.ActionRow(use_markup=False, title=word)
        remove = Gtk.Button(
            icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER, tooltip_text=_("Remove")
        )
        remove.add_css_class("flat")
        remove.connect("clicked", lambda _b: self._remove(word))
        row.add_suffix(remove)
        return row


MISSING = [
    N_("Sen, which types straight into the app, and its fixes for each app"),
    N_("Cứu chữ and Cứu dấu"),
    N_("Two spaces to a period, -- to —"),
    N_("The emoji picker and rules for each app"),
]
FULL_EDITION_URL = "https://github.com/ngosen/ngosen"
PROJECT_URL = "https://github.com/ngosen/ibus-ngosen"


def about_page(version):
    page = Adw.PreferencesPage(title=_("About"), icon_name="help-about-symbolic")
    page.add(_about_header(version))
    missing = preferences_group(N_("Not in the GNOME edition"))
    for text in MISSING:
        missing.add(Adw.ActionRow(title=_(text), use_markup=False))
    missing.add(
        _link_row(
            _("Ngó Sen full edition"), _("Runs on fcitx5 and has all of these."), FULL_EDITION_URL
        )
    )
    page.add(missing)
    links = preferences_group()
    links.add(_link_row(_("Report Bug"), None, PROJECT_URL + "/issues/new"))
    links.add(_link_row(_("Source code"), None, PROJECT_URL))
    page.add(links)
    page.add(_credit())
    return page


def _about_header(version):
    group = Adw.PreferencesGroup()
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, halign=Gtk.Align.CENTER)
    box.append(Gtk.Image(icon_name="io.github.ngosen.IBusNgoSen", pixel_size=96))
    wordmark = Gtk.Label(label="Ngó Sen")
    wordmark.add_css_class("wordmark")
    box.append(wordmark)
    box.append(Gtk.Label(label=_("Vietnamese input method for GNOME")))
    version_label = Gtk.Label(label=_("Version {}").format(version))
    version_label.add_css_class("dim-label")
    box.append(version_label)
    group.add(box)
    return group


def _link_row(title, subtitle, url):
    row = Adw.ActionRow(title=title, activatable=True)
    if subtitle:
        row.set_subtitle(subtitle)
    row.add_suffix(Gtk.Image(icon_name="adw-external-link-symbolic"))
    row.connect(
        "activated", lambda r: Gtk.UriLauncher(uri=url).launch(r.get_root(), None, None, None)
    )
    return row


def _credit():
    group = Adw.PreferencesGroup()
    credit = _("Based on the code of {fork} and {vmk}.").format(
        fork='<a href="https://github.com/LotusInputMethod/fcitx5-lotus">fcitx5-lotus</a>',
        vmk='<a href="https://github.com/thanhpy2009/VMK">VMK</a>',
    )
    licence = GLib.markup_escape_text(_("Licensed under the GNU General Public License v3.0"))
    label = Gtk.Label(
        label=f"{credit}\n{licence}", use_markup=True, justify=Gtk.Justification.CENTER, wrap=True
    )
    label.add_css_class("dim-label")
    group.add(label)
    return group
