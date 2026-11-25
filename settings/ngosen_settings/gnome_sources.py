# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""GNOME's input sources and shortcuts, read without GTK so a terminal command can use them too."""

from gi.repository import Gio, GLib

from . import system_check

# Where GNOME keeps its shortcuts; a toggle key on one of them would take it from GNOME or lose to it.
KEYBINDINGS = [
    "org.gnome.desktop.wm.keybindings",
    "org.gnome.shell.keybindings",
    "org.gnome.mutter.keybindings",
    "org.gnome.mutter.wayland.keybindings",
    "org.gnome.settings-daemon.plugins.media-keys",
]


class GnomeSources:
    """The GNOME input sources, or None where GNOME's settings are not installed."""

    def __init__(self):
        schemas = Gio.SettingsSchemaSource.get_default()
        has_schema = schemas is not None and schemas.lookup(system_check.GNOME_SOURCES, True)
        self.settings = Gio.Settings.new(system_check.GNOME_SOURCES) if has_schema else None
        has_ibus = schemas is not None and schemas.lookup(system_check.IBUS_GENERAL, True)
        self.ibus = Gio.Settings.new(system_check.IBUS_GENERAL) if has_ibus else None

    def ibus_engines(self):
        """IBus's own list of input methods, which it uses where GNOME Shell does not set one."""
        return self.ibus.get_strv("preload-engines") if self.ibus is not None else None

    def set_ibus_engines(self, engines):
        if self.ibus is None:
            return False
        ok = self.ibus.set_strv("preload-engines", engines)
        Gio.Settings.sync()
        return ok

    def get(self):
        if self.settings is None:
            return None
        return [tuple(source) for source in self.settings.get_value("sources").unpack()]

    def gnome_keys(self):
        """GNOME's shortcuts as accelerators, and the xkb options that may switch layouts."""
        schemas = Gio.SettingsSchemaSource.get_default()
        accelerators = []
        for schema_id in KEYBINDINGS:
            schema = schemas.lookup(schema_id, True) if schemas is not None else None
            if schema is None:
                continue
            bindings = Gio.Settings.new(schema_id)
            for name in schema.list_keys():
                value = bindings.get_value(name)
                if name == "custom-keybindings":
                    accelerators += [custom_binding(path) for path in value.unpack()]
                elif value.get_type_string() == "as":
                    accelerators += value.unpack()
        return accelerators, self._xkb_options()

    def switch_keys(self):
        """The shortcuts that switch input sources, and the xkb options that may switch layouts."""
        schemas = Gio.SettingsSchemaSource.get_default()
        schema = schemas.lookup(KEYBINDINGS[0], True) if schemas is not None else None
        accelerators = []
        if schema is not None and schema.has_key("switch-input-source"):
            accelerators = Gio.Settings.new(KEYBINDINGS[0]).get_strv("switch-input-source")
        return accelerators, self._xkb_options()

    def _xkb_options(self):
        return self.settings.get_strv("xkb-options") if self.settings is not None else []

    def set(self, sources):
        if self.settings is None:
            return False
        ok = self.settings.set_value("sources", GLib.Variant("a(ss)", sources))
        Gio.Settings.sync()
        return ok


def custom_binding(path):
    """A shortcut the user added in GNOME Settings; GSettings aborts on a missing schema or bad path."""
    schema_id = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
    schemas = Gio.SettingsSchemaSource.get_default()
    found = schemas.lookup(schema_id, True) if schemas is not None else None
    if found is None or not (path.startswith("/") and path.endswith("/")) or "//" in path:
        return ""
    return Gio.Settings.new_with_path(schema_id, path).get_string("binding")
