# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from ngosen_settings import fcitx5_leftovers as lo
from ngosen_settings import system_check as sc

from tests.test_window import FakeSources

INSTALL_SH = os.path.join(os.path.dirname(__file__), "..", "..", "ngosen", "install.sh")


class SameAsInstallerTest(unittest.TestCase):
    """install.sh --uninstall compares files with its own text, so the copies here must match it."""

    def installer(self, function, *args, env=None):
        cmd = f'eval "$(sed -n "/^{function}() {{/,/^}}/p" "$0")"; {function} "$@"'
        return subprocess.run(
            ["bash", "-c", cmd, INSTALL_SH, *args],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        ).stdout

    def test_gnome_variables(self):
        self.assertEqual(self.installer("im_environment_entry"), lo.GNOME_ENV)

    def test_kde_variable(self):
        with open(INSTALL_SH, encoding="utf-8") as f:
            self.assertIn(f"echo '{lo.KDE_ENV.strip()}'", f.read())

    def test_autostart_mask(self):
        self.assertEqual(self.installer("fcitx5_autostart_mask"), lo.AUTOSTART_MASK)

    def test_hidden_launcher(self):
        for launcher in lo.LAUNCHERS:
            entry = self.installer("hidden_launcher_entry", launcher)
            self.assertEqual(entry, lo.hidden_launcher_entry(launcher))

    def test_launcher_list(self):
        with open(INSTALL_SH, encoding="utf-8") as f:
            self.assertIn(f"FCITX5_LAUNCHERS=({' '.join(lo.LAUNCHERS)})", f.read())

    def test_paths_follow_xdg(self):
        env = {
            "HOME": "/home/u",
            "XDG_STATE_HOME": "/s",
            "XDG_DATA_HOME": "/d",
            "XDG_CONFIG_HOME": "/c",
            "PATH": os.defpath,
        }
        self.assertEqual(self.installer("changes_file", env=env), lo.changes_file(env))
        self.assertEqual(self.installer("applications_dir", env=env), lo.applications_dir(env))
        self.assertEqual(self.installer("config_home", env=env), lo.config_home(env))
        del env["XDG_STATE_HOME"], env["XDG_DATA_HOME"], env["XDG_CONFIG_HOME"]
        self.assertEqual(self.installer("changes_file", env=env), lo.changes_file(env))
        self.assertEqual(self.installer("applications_dir", env=env), lo.applications_dir(env))
        self.assertEqual(self.installer("config_home", env=env), lo.config_home(env))


class LeftoversCase(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.env = {"HOME": self.home}
        system = os.path.join(self.home, "system")
        os.makedirs(system)
        self.source = os.path.join(system, "org.fcitx.Fcitx5.desktop")
        self.write(self.source, "[Desktop Entry]\nName=Fcitx 5\nExec=fcitx5\n")
        for name, value in (
            ("AUTOSTART_SOURCE", self.source),
            ("SYSTEM_AUTOSTART", os.path.join(system, "xdg-autostart.desktop")),
        ):
            patcher = mock.patch.object(lo, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.reloads = []
        patcher = mock.patch.object(lo, "_succeeds", side_effect=self.run_command)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.commands = []
        self.command_ok = True

    def run_command(self, cmd):
        self.commands.append(cmd)
        return self.command_ok

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def read(self, path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    def path(self, *parts):
        return os.path.join(self.home, *parts)

    def install_gnome(self, im_config=False):
        """What install.sh writes on GNOME."""
        self.env_file = self.path(".config", "environment.d", "90-ngosen.conf")
        self.write(self.env_file, lo.GNOME_ENV)
        self.autostart = self.path(".config", "autostart", "org.fcitx.Fcitx5.desktop")
        self.write(self.autostart, self.read(self.source))
        self.launcher = self.path(".local", "share", "applications", "org.fcitx.Fcitx5.desktop")
        self.write(self.launcher, lo.hidden_launcher_entry("org.fcitx.Fcitx5.desktop"))
        changes = "extension forward-keys@ngosen.github.io\n"
        if im_config:
            self.write(self.path(".xinputrc"), "# im-config\nrun_im fcitx5\n")
            changes += "im-config\n"
        self.write(lo.changes_file(self.env), changes)


class FindTest(LeftoversCase):
    def test_what_the_installer_wrote_is_found(self):
        self.install_gnome()
        found = lo.find(self.env, has_im_config=False)
        self.assertEqual(
            sorted(found.files), sorted([self.env_file, self.autostart, self.launcher])
        )
        self.assertTrue(found.fixable)
        self.assertEqual(found.notes, [])

    def test_xdg_directories_are_followed(self):
        self.env["XDG_CONFIG_HOME"] = self.path("config")
        path = os.path.join(self.env["XDG_CONFIG_HOME"], "environment.d", "90-ngosen.conf")
        self.write(path, lo.GNOME_ENV)
        self.assertEqual(lo.find(self.env, has_im_config=False).files, [path])

    def test_a_mask_is_left_alone(self):
        self.write(self.path(".config", "autostart", "org.fcitx.Fcitx5.desktop"), lo.AUTOSTART_MASK)
        found = lo.find(self.env, has_im_config=False)
        self.assertEqual((found.files, found.notes), ([], []))

    def test_edited_files_are_only_reported(self):
        self.install_gnome()
        self.write(self.env_file, lo.GNOME_ENV + "MY_VAR=1\n")
        self.write(self.autostart, self.read(self.source) + "X-Mine=1\n")
        found = lo.find(self.env, has_im_config=False)
        # The hidden launcher alone does no harm, so it stays with them.
        self.assertEqual(found.files, [])
        kinds = [kind for kind, _path, _command in found.notes]
        self.assertEqual(kinds, [lo.EDITED_ENVIRONMENT, lo.EDITED_AUTOSTART])

    def test_kde_variables_are_only_reported(self):
        path = self.path(".config", "environment.d", "90-ngosen.conf")
        self.write(path, lo.KDE_ENV)
        found = lo.find(self.env, has_im_config=False)
        self.assertEqual(found.files, [])
        self.assertEqual(found.notes, [(lo.EDITED_ENVIRONMENT, path, "")])

    def test_hidden_launchers_alone_are_not_worth_a_step(self):
        launcher = self.path(".local", "share", "applications", "org.fcitx.Fcitx5.desktop")
        self.write(launcher, lo.hidden_launcher_entry("org.fcitx.Fcitx5.desktop"))
        self.assertFalse(lo.find(self.env, has_im_config=False).fixable)

    def test_without_fcitx5_installed_its_autostart_copy_is_harmless(self):
        self.install_gnome()
        os.remove(self.source)
        self.assertNotIn(self.autostart, lo.find(self.env, has_im_config=False).files)

    def test_system_autostart_suggests_a_mask(self):
        self.write(lo.SYSTEM_AUTOSTART, self.read(self.source))
        (note,) = lo.find(self.env, has_im_config=False).notes
        self.assertEqual(note[0], lo.SYSTEM_STARTS_FCITX5)
        self.assertIn("Hidden=true", note[2])

    def test_im_config(self):
        self.install_gnome(im_config=True)
        self.assertTrue(lo.find(self.env, has_im_config=True).im_config)
        with mock.patch.object(lo, "_im_config_is_1_1", return_value=True):
            found = lo.find(self.env, has_im_config=False)
        self.assertFalse(found.im_config)
        self.assertEqual(found.notes, [(lo.IM_CONFIG_PICK, self.path(".xinputrc"), "")])
        # Without the installer's mark, fcitx5 may be the user's own pick.
        self.write(lo.changes_file(self.env), "")
        with mock.patch.object(lo, "_im_config_is_1_1", return_value=True):
            found = lo.find(self.env, has_im_config=True)
        self.assertFalse(found.im_config)
        self.assertEqual(found.notes[0][2], "im-config -w auto")
        self.write(self.path(".xinputrc"), "run_im ibus\n")
        found = lo.find(self.env, has_im_config=True)
        self.assertEqual((found.im_config, found.notes), (False, []))


class CleanTest(LeftoversCase):
    def snapshot(self):
        found = {}
        for folder, _dirs, files in os.walk(self.home):
            for name in files:
                path = os.path.join(folder, name)
                with open(path, "rb") as f:
                    found[path] = f.read()
        return found

    def test_removes_all_and_undo_puts_back_every_byte(self):
        self.install_gnome(im_config=True)
        before = self.snapshot()
        with mock.patch.object(lo, "_im_config_is_1_1", return_value=False):
            done, undo, removed = lo.clean(self.env, has_im_config=True)
        self.assertTrue(done)
        self.assertEqual(sorted(removed), sorted([self.env_file, self.autostart, self.launcher]))
        for path in removed:
            self.assertFalse(os.path.exists(path))
        self.assertIn(["im-config", "-n", "REMOVE"], self.commands)
        self.assertIn(["systemctl", "--user", "daemon-reload"], self.commands)
        changes = self.read(lo.changes_file(self.env))
        self.assertEqual(changes, "extension forward-keys@ngosen.github.io\n")
        self.commands.clear()
        self.assertTrue(undo())
        self.assertEqual(self.snapshot(), before)
        self.assertIn(["systemctl", "--user", "daemon-reload"], self.commands)

    def test_undo_refuses_after_a_later_change(self):
        self.install_gnome()
        _done, undo, _removed = lo.clean(self.env, has_im_config=False)
        self.write(self.env_file, "GTK_IM_MODULE=ibus\n")
        self.assertFalse(undo())
        self.assertEqual(self.read(self.env_file), "GTK_IM_MODULE=ibus\n")

    def test_a_failed_im_config_puts_everything_back(self):
        self.install_gnome(im_config=True)
        before = self.snapshot()
        self.command_ok = False
        with mock.patch.object(lo, "_im_config_is_1_1", return_value=True):
            self.assertEqual(lo.clean(self.env, has_im_config=True), (False, None, []))
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.commands[-1], ["systemctl", "--user", "daemon-reload"])

    def test_a_file_that_cannot_go_puts_the_others_back(self):
        self.install_gnome()
        before = self.snapshot()
        remove = os.remove
        calls = []

        def second_fails(path):
            calls.append(path)
            if len(calls) == 2:
                raise PermissionError(path)
            remove(path)

        with mock.patch.object(lo.os, "remove", side_effect=second_fails):
            self.assertEqual(lo.clean(self.env, has_im_config=False), (False, None, []))
        self.assertEqual(self.snapshot(), before)


class CheckPageTest(LeftoversCase):
    def facts(self, **kwargs):
        env = {"XDG_CURRENT_DESKTOP": "GNOME", "XDG_SESSION_TYPE": "wayland"}
        args = {"ibus_running": True, "in_gnome_sources": True, "has_gnome_portal": True}
        args["leftovers"] = lo.find(self.env, has_im_config=False)
        return sc.Facts(env=env, **{**args, **kwargs})

    def test_shown_even_when_ibus_does_not_hold_the_session(self):
        self.install_gnome()
        for kwargs in (
            {"ibus_running": False},
            {"ibus_running": False, "fcitx_owns_session": True},
        ):
            actions = [f.action for f in sc.steps(self.facts(**kwargs))]
            self.assertIn(sc.CLEAN_FCITX5, actions, kwargs)

    def test_replaces_the_fcitx5_running_warning(self):
        self.install_gnome()
        titles = [f.title for f in sc.steps(self.facts(fcitx_running=True))]
        self.assertNotIn("fcitx5 is running next to IBus", titles)

    def test_never_in_fix_all_but_its_own_button_works(self):
        self.install_gnome()
        os.remove(self.autostart)
        self.write(self.autostart, self.read(self.source) + "X-Mine=1\n")
        found = [f for f in sc.steps(self.facts()) if f.level != sc.OK]
        fixes = sc.Fixes(FakeSources([]), self.env)
        self.assertNotIn(sc.CLEAN_FCITX5, fixes.fixable(found))
        done, undos, _settle = fixes.run([sc.CLEAN_FCITX5])
        self.assertEqual(done, [sc.CLEAN_FCITX5])
        # The edited autostart file stays as a step without a button.
        left = [f for f in sc.steps(self.facts()) if f.level != sc.OK]
        self.assertEqual([f.action for f in left if "fcitx5" in f.title], [""])
        message, undo = fixes.finish(done, undos, left)
        self.assertIn("90-ngosen.conf", message)
        self.assertIsNotNone(undo)
        self.assertNotIn(sc.CLEAN_FCITX5, fixes.failed)


if __name__ == "__main__":
    unittest.main()
