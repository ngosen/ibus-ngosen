# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Check page: each setup step, with a fix where the window can do it."""

from gi.repository import Adw, Gdk, GLib, Gtk

from . import system_check
from .gnome_sources import GnomeSources, custom_binding  # noqa: F401
from .i18n import _

ICONS = {
    system_check.OK: ("object-select-symbolic", "success"),
    system_check.INFO: ("dialog-information-symbolic", "accent"),
    system_check.WARN: ("dialog-warning-symbolic", "warning"),
    system_check.FAIL: ("dialog-error-symbolic", "error"),
}


def _text(css=None):
    label = Gtk.Label(wrap=True, xalign=0)
    if css:
        label.add_css_class(css)
    return label


def _button(label, on_click, *css):
    button = Gtk.Button(label=label, css_classes=list(css), valign=Gtk.Align.CENTER)
    button.connect("clicked", lambda _b: on_click())
    return button


def _copy(text):
    Gdk.Display.get_default().get_clipboard().set(text)


class CheckPage:
    def __init__(
        self,
        sources,
        ngosen_version,
        notify,
        on_count,
        direct_typing=lambda: False,
        app_modes_file=None,
        toggle_key=lambda: False,
        config_dir=None,
        output_charset=lambda: "Unicode",
    ):
        """notify(text, undo) shows a toast; on_count(n) gets the number of steps left."""
        self.sources = sources
        self.app_modes_file = app_modes_file
        self.direct_typing = direct_typing
        self.toggle_key = toggle_key
        self.output_charset = output_charset
        self.ngosen_version = ngosen_version
        self.notify = notify
        self.on_count = on_count
        self.fixes = system_check.Fixes(sources, config_dir=config_dir)
        self.rows = []
        page = Adw.PreferencesPage(title=_("Check"), icon_name="preferences-system-symbolic")
        page.add(self._summary_group())
        self.steps = Adw.PreferencesGroup(title=_("Steps to type Vietnamese"))
        page.add(self.steps)
        page.add(self._try_group())
        page.add(self._send_group())
        self.page = page
        self.run()

    def _summary_group(self):
        group = Adw.PreferencesGroup()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.heading = _text("title-2")
        self.heading.set_accessible_role(Gtk.AccessibleRole.HEADING)
        self.summary = _text("dim-label")
        box.append(self.heading)
        box.append(self.summary)
        buttons = Gtk.Box(spacing=12, margin_top=6)
        self.fix_all_btn = _button("", self.fix_all, "suggested-action", "pill")
        self.again_btn = _button(_("Check again"), self.run, "pill")
        buttons.append(self.fix_all_btn)
        buttons.append(self.again_btn)
        box.append(buttons)
        group.add(box)
        return group

    def _try_group(self):
        group = Adw.PreferencesGroup(
            title=_("Try typing here"),
            description=_("In Telex, vieetj becomes việt."),
        )
        entry = Adw.EntryRow(title=_("Type here to test"))
        entry.add_css_class("typed")
        group.add(entry)
        return group

    def _send_group(self):
        group = Adw.PreferencesGroup(
            title=_("Send the result to Ngó Sen"),
            description=_(
                "The result lists the steps above. Nothing is sent until you press a button below."
            ),
        )
        row = Gtk.Box(spacing=12)
        row.append(_button(_("Message on Facebook…"), self.open_chat, "suggested-action"))
        row.append(_button(_("Report on GitHub…"), self.open_report))
        row.append(_button(_("Copy result"), self.copy_report))
        group.add(row)
        return group

    def run(self):
        self.facts = system_check.collect(
            self.sources,
            self.ngosen_version,
            direct_typing=self.direct_typing(),
            app_modes_file=self.app_modes_file,
            toggle_key=self.toggle_key(),
            output_charset=self.output_charset(),
        )
        self.found = system_check.steps(self.facts)
        self.findings = system_check.steps_left(self.found)
        self._show_steps()

    def _show_steps(self):
        for row in self.rows:
            self.steps.remove(row)
        self.rows = [self._row(finding) for finding in self.found]
        for row in self.rows:
            self.steps.add(row)
        title, text = system_check.summary(self.found, self.fixes.failed)
        if self.fixes.busy:
            title = _("Fixing…")
        self.heading.set_text(title)
        self.summary.set_text(text)
        fixable = self.fixes.fixable(self.findings)
        self.fix_all_btn.set_label(_("Fix all ({})").format(len(fixable)))
        self.fix_all_btn.set_visible(len(fixable) > 1)
        self.fix_all_btn.set_sensitive(not self.fixes.busy)
        self.on_count(len(self.findings))

    def _row(self, finding):
        # A step with a button needs no instructions unless the button fails; a note says why it is there.
        subtitle = finding.fix if finding.level == system_check.INFO or not finding.action else ""
        row = Adw.ActionRow(title=finding.title, subtitle=subtitle, use_markup=False)
        # Some steps give a command to copy.
        row.set_subtitle_selectable(not finding.action)
        icon, css = ICONS[finding.level]
        row.add_prefix(Gtk.Image(icon_name=icon, css_classes=[css]))
        row.level = finding.level
        row.button = None
        if finding.action in self.fixes.busy:
            row.set_subtitle(_("Fixing…"))
            row.add_suffix(Gtk.Spinner(spinning=True, valign=Gtk.Align.CENTER))
        elif finding.action in self.fixes.failed:
            row.set_subtitle(system_check.failed_text(finding))
            if finding.command:
                row.button = _button(_("Copy command"), lambda: self.copy_command(finding.command))
                row.add_suffix(row.button)
        elif finding.action:
            row.button = _button(
                system_check.fix_label(finding.action), lambda: self.fix([finding.action])
            )
            row.add_suffix(row.button)
        return row

    def fix_all(self):
        self.fix(self.fixes.fixable(self.findings))

    def fix(self, actions):
        if self.fixes.busy or not actions:
            return
        self.fixes.busy = set(actions)
        # IBus shows as stopped while it restarts.
        if system_check.RESTART_IBUS in actions:
            self.fixes.busy.add(system_check.START_IBUS)
        self._show_steps()
        # Let the spinner show before the fix holds the main loop.
        GLib.timeout_add(50, self._run_fixes, list(actions))

    def _run_fixes(self, actions):
        done, undos, settle = self.fixes.run(actions)
        GLib.timeout_add(settle, self._fixed, done, undos)
        return GLib.SOURCE_REMOVE

    def _fixed(self, done, undos):
        self.run()
        wait = self.fixes.settle_again(done, self.found)
        if wait:
            GLib.timeout_add(wait, self._fixed, done, undos)
            return GLib.SOURCE_REMOVE
        # Every step with a button, notes included, so a note whose fix failed says so.
        text, undo = self.fixes.finish(done, undos, self.found)
        self._show_steps()
        if text:
            self.notify(text, self._then_check(undo) if undo else None)
        return GLib.SOURCE_REMOVE

    def _then_check(self, undo):
        def undo_and_check():
            ok = undo()
            self.run()
            return ok

        return undo_and_check

    def copy_command(self, command):
        _copy(command)
        self.notify(_("Copied: {}").format(command), None)

    def report_text(self):
        return system_check.report(self.facts, self.found)

    def copy_report(self):
        _copy(self.report_text())
        self.notify(_("Copied the result."), None)

    def open_chat(self):
        # Messenger cannot be handed the text, so it waits on the clipboard.
        _copy(self.report_text())
        self.notify(
            _("Copied the result. Paste it into the message and say what went wrong."), None
        )
        _open(self.page, system_check.MESSENGER_URL)

    def open_report(self):
        _open(self.page, system_check.issue_url(self.facts, self.report_text()))


def _open(widget, uri):
    Gtk.UriLauncher(uri=uri).launch(widget.get_root(), None, None, None)
