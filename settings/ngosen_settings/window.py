# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import subprocess
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Adw, GLib, Gtk  # noqa: E402,F401

from . import brand, i18n, options, pages  # noqa: E402
from .i18n import _  # noqa: E402
from .store import Engine, Store  # noqa: E402

APP_ID = "io.github.ngosen.IBusNgoSen"


class Window(Adw.ApplicationWindow):
    def __init__(self, app, store, names, version):
        super().__init__(application=app, title="Ngó Sen", default_width=800, default_height=720)
        self.store = store
        self.toast = None
        self.rows = pages.SettingRows(store, names, self.save)
        self.macros = pages.MacroPage(store, self.rows, self.save_macros)
        self.dictionary = pages.DictionaryPage(store, self.rows, self.save_words)

        stack = Adw.ViewStack()
        typing = pages.typing_page(self.rows)
        typing.add(pages.fcitx5_group(self._show))
        for page in (
            typing,
            self.macros.page,
            self.dictionary.page,
            pages.about_page(version),
        ):
            stack.add_titled_with_icon(page, None, page.get_title(), page.get_icon_name())
        switcher = Adw.ViewSwitcher(stack=stack, policy=Adw.ViewSwitcherPolicy.WIDE)
        header = Adw.HeaderBar(title_widget=switcher)
        header.pack_start(brand_mark())
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
        store, names, error = load(Engine(os.environ.get("NGOSEN_IBUS_ENGINE", engine_path)))
        window = error_window(app, error) if error else Window(app, store, names, version)
        window.present()

    app.connect("activate", activate)
    return app.run(sys.argv[:1])
