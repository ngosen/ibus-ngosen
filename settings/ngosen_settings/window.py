# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import subprocess
import sys
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402,F401

from . import backup, brand, check_page, i18n, keys, options, pages  # noqa: E402
from .i18n import _  # noqa: E402
from .store import Engine, Store  # noqa: E402

APP_ID = "io.github.ngosen.IBusNgoSen"
# A file dialog the user closed; older GTK has no CANCELLED.
CLOSED_DIALOG = [
    getattr(Gtk.DialogError, name)
    for name in ("DISMISSED", "CANCELLED")
    if hasattr(Gtk.DialogError, name)
]


class Window(Adw.ApplicationWindow):
    def __init__(self, app, store, names, version, sources=None, engine=None):
        super().__init__(application=app, title="Ngó Sen", default_width=800, default_height=720)
        self.store = store
        self.engine = engine
        self.toast = None
        self.check_tab = None
        sources = sources or check_page.GnomeSources()
        self.rows = pages.SettingRows(
            store, names, self.save, lambda: keys.gnome_chords(*sources.gnome_keys())
        )
        self.macros = pages.MacroPage(store, self.rows, self.save_macros)
        self.dictionary = pages.DictionaryPage(store, self.rows, self.save_words)
        self.check = check_page.CheckPage(sources, version, self.notify, self._count)

        stack = Adw.ViewStack()
        typing = pages.typing_page(self.rows)
        typing.add(pages.fcitx5_group(self._show))
        for page in (
            typing,
            self.macros.page,
            self.dictionary.page,
            self.check.page,
            pages.about_page(version),
        ):
            tab = stack.add_titled_with_icon(page, None, page.get_title(), page.get_icon_name())
            if page is self.check.page:
                self.check_tab = tab
        self._count(len(self.check.findings))
        switcher = Adw.ViewSwitcher(stack=stack, policy=Adw.ViewSwitcherPolicy.WIDE)
        header = Adw.HeaderBar(title_widget=switcher)
        header.pack_start(brand_mark())
        header.pack_end(self._backup_menu())
        switcher_bar = Adw.ViewSwitcherBar(stack=stack)

        view = Adw.ToolbarView(content=stack)
        view.add_top_bar(header)
        view.add_bottom_bar(switcher_bar)
        self.toasts = Adw.ToastOverlay(child=view)
        self.set_content(self.toasts)

        narrow = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 550sp"))
        narrow.add_setter(switcher, "visible", False)
        narrow.add_setter(switcher_bar, "reveal", True)
        self.add_breakpoint(narrow)
        self.refresh()

    def refresh(self):
        self.rows.refresh()
        self.macros.refresh()
        self.dictionary.refresh()

    def save(self, key, value):
        self._write(lambda: self.store.set(key, value), _(options.LABELS[key]))

    def save_macros(self, macros, _key):
        saved = self._write(lambda: self.store.set_macros(macros) or True, _("Macro"))
        self.macros.refresh()
        return saved

    def save_words(self, words):
        saved = self._write(lambda: self.store.set_words(words) or True, _("Dictionary"))
        self.dictionary.refresh()
        return saved

    def _write(self, write, label):
        try:
            if not write():
                return True
        except OSError as error:
            self._show(Adw.Toast(title=_("Cannot save: {}").format(error.strerror), timeout=0))
            self.refresh()
            return False
        toast = Adw.Toast(title=_("Saved “{}”.").format(label), button_label=_("_Undo"))
        toast.connect("button-clicked", lambda _t: self.undo())
        self._show(toast)
        return True

    def _count(self, left):
        if self.check_tab is not None:
            self.check_tab.set_badge_number(left)
            self.check_tab.set_needs_attention(left > 0)

    def notify(self, text, undo):
        toast = Adw.Toast(title=text)
        if undo is not None:
            toast.set_button_label(_("_Undo"))
            toast.connect("button-clicked", lambda _t: undo())
        self._show(toast)

    def _show(self, toast):
        if self.toast is not None:
            self.toast.dismiss()
        self.toast = toast
        toast.set_use_markup(False)
        self.toasts.add_toast(toast)

    def undo(self):
        if not self.store.can_undo():
            return
        try:
            self.store.undo()
        except OSError as error:
            self._show(Adw.Toast(title=_("Cannot save: {}").format(error.strerror), timeout=0))
        self.refresh()

    def _backup_menu(self):
        menu = Gio.Menu()
        for label, name, run in (
            (_("Back _Up…"), "backup", self.choose_backup_file),
            (_("_Restore…"), "restore-backup", self.choose_restore_file),
        ):
            menu.append(label, f"win.{name}")
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda *_args, run=run: run())
            self.add_action(action)
        return Gtk.MenuButton(
            icon_name="open-menu-symbolic", menu_model=menu, tooltip_text=_("Menu")
        )

    def choose_backup_file(self):
        dialog = self._file_dialog(_("Back Up Settings"))
        dialog.set_initial_name(f"ngosen-backup-{datetime.now():%Y%m%d-%H%M%S}.json")
        dialog.save(self, None, self._on_file, dialog.save_finish, self.export_backup)

    def choose_restore_file(self):
        dialog = self._file_dialog(_("Restore Settings"))
        dialog.open(self, None, self._on_file, dialog.open_finish, self.restore_backup)

    def _file_dialog(self, title):
        json_files = Gtk.FileFilter(name=_("Ngó Sen backup"))
        json_files.add_suffix("json")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(json_files)
        return Gtk.FileDialog(title=title, modal=True, filters=filters, default_filter=json_files)

    def _on_file(self, _dialog, result, finish, use):
        try:
            file = finish(result)
        except GLib.Error as error:
            if not any(error.matches(Gtk.dialog_error_quark(), code) for code in CLOSED_DIALOG):
                text = _("Cannot open the file dialog: {}").format(error.message)
                self._show(Adw.Toast(title=text, timeout=0))
            return
        if file is not None and file.get_path():
            use(file.get_path())

    def export_backup(self, path):
        try:
            backup.export(self.engine, backup.Paths(self.store), path)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            self._show(Adw.Toast(title=_("Cannot back up: {}").format(reason(error)), timeout=0))
            return
        self._show(Adw.Toast(title=_("Backed up to {}.").format(path)))

    def restore_backup(self, path):
        """Checks the whole file before writing; what the user would lose is asked about first."""
        try:
            data = backup.load(path)
            _changes, notes = backup.plan(
                data, backup.Paths(self.store), self.engine, self.rows.taken_keys()
            )
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            self._cannot_restore(error)
            return None
        name = os.path.basename(path)
        if not notes:
            self.apply_backup(data, name)
            return None
        dialog = Adw.AlertDialog(heading=_("Restore {}?").format(name), body="\n\n".join(notes))
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("restore", _("Restore"))
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect(
            "response", lambda _d, answer: answer == "restore" and self.apply_backup(data, name)
        )
        dialog.present(self)
        return dialog

    def apply_backup(self, data, name):
        try:
            # Planned again, so a change made while the dialog was open is not written over.
            changes, _notes = backup.plan(
                data, backup.Paths(self.store), self.engine, self.rows.taken_keys()
            )
            before = backup.replace(changes)
        except backup.RestoreError as error:
            self._show(Adw.Toast(title=str(error), timeout=0))
            self._reload()
            return
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            self._cannot_restore(error)
            return
        self._reload()
        toast = Adw.Toast(title=_("Restored from {}.").format(name), button_label=_("_Undo"))
        toast.connect("button-clicked", lambda _t: self.undo_restore(before, changes))
        self._show(toast)

    def undo_restore(self, before, restored):
        try:
            if not backup.undo(before, restored):
                text = _("The settings changed after the restore, so nothing was undone.")
                self._show(Adw.Toast(title=text, timeout=0))
        except OSError as error:
            self._show(Adw.Toast(title=_("Cannot save: {}").format(reason(error)), timeout=0))
        self._reload()

    def _cannot_restore(self, error):
        text = _("Cannot restore: {}. Nothing was changed.").format(reason(error).rstrip("."))
        self._show(Adw.Toast(title=text, timeout=0))

    def _reload(self):
        try:
            self.store.reload(self.engine)
        except (OSError, subprocess.SubprocessError) as error:
            self._show(Adw.Toast(title=_("Cannot read the settings: {}").format(reason(error))))
        self.refresh()


def reason(error):
    return getattr(error, "strerror", None) or str(error)


def brand_mark():
    box = Gtk.Box(spacing=8)
    box.append(Gtk.Image(icon_name=APP_ID, pixel_size=24))
    label = Gtk.Label(label="Ngó Sen")
    label.add_css_class("wordmark")
    box.append(label)
    return box


def error_window(app, message):
    window = Adw.ApplicationWindow(
        application=app, title="Ngó Sen", default_width=520, default_height=360
    )
    page = Adw.StatusPage(
        icon_name="dialog-error-symbolic", title=_("Cannot read the settings"), description=message
    )
    view = Adw.ToolbarView(content=page)
    view.add_top_bar(Adw.HeaderBar())
    window.set_content(view)
    return window


def load(engine):
    """The store and the names to offer, or a message saying why the engine did not answer."""
    try:
        names = {"InputMethod": engine.input_methods(), "OutputCharset": engine.charsets()}
        return Store(engine), names, None
    except (OSError, subprocess.SubprocessError) as error:
        return None, None, str(error)


def main(engine_path, localedir, font_path, version):
    i18n.setup(localedir)
    app = Adw.Application(application_id=APP_ID)

    def activate(app):
        if app.get_active_window() is not None:
            app.get_active_window().present()
            return
        brand.load_font(font_path)
        brand.install_css()
        engine = Engine(os.environ.get("NGOSEN_IBUS_ENGINE", engine_path))
        store, names, error = load(engine)
        window = (
            error_window(app, error) if error else Window(app, store, names, version, engine=engine)
        )
        window.present()

    app.connect("activate", activate)
    return app.run(sys.argv[:1])
