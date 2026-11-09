# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlparse

from ngosen_settings import system_check as sc

from tests.test_window import FakeSources

GNOME_X11 = {"XDG_CURRENT_DESKTOP": "ubuntu:GNOME", "XDG_SESSION_TYPE": "x11"}
READY = {**GNOME_X11, "XMODIFIERS": "@im=ibus"}


def facts(env=READY, **kwargs):
    defaults = {"ibus_running": True, "in_gnome_sources": True, "has_gnome_portal": True}
    return sc.Facts(env=dict(env), **{**defaults, **kwargs})


def titles(found, level=None):
    return [f.title for f in found if level is None or f.level == level]


class StepsTest(unittest.TestCase):
    def test_ready_machine_has_nothing_to_fix(self):
        found = sc.steps(facts())
        self.assertEqual([f.level for f in found], [sc.OK] * len(found))
        self.assertEqual(sc.summary(found)[0], "This machine is ready")

    def test_ibus_not_running_is_the_only_step(self):
        found = sc.steps(facts(ibus_running=False))
        self.assertEqual([(f.level, f.action) for f in found], [(sc.FAIL, sc.START_IBUS)])

    def test_fcitx5_holding_the_session_is_the_only_step(self):
        found = sc.steps(facts(ibus_running=False, fcitx_owns_session=True))
        self.assertEqual([(f.level, f.action) for f in found], [(sc.FAIL, "")])
        self.assertEqual(found[0].title, "fcitx5 holds the input method")

    def test_engine_in_use_is_only_information(self):
        other = facts(current_engine="xkb:us::eng", switch_keys=["Super+Space", "Alt+Shift"])
        found = sc.steps(other)
        (step,) = [f for f in found if f.level == sc.INFO]
        self.assertIn("Super+Space or Alt+Shift", step.fix)
        self.assertEqual(sc.summary(found)[0], "This machine is ready")
        self.assertEqual(titles(sc.steps(facts(current_engine="ngosen")), sc.INFO), [])
        self.assertEqual(titles(sc.steps(facts(current_engine="")), sc.INFO), [])
        xfce = {"XDG_CURRENT_DESKTOP": "XFCE", "XDG_SESSION_TYPE": "x11"}
        found = sc.steps(facts(xfce, in_gnome_sources=None, current_engine="Unikey"))
        (step,) = [f for f in found if f.level == sc.INFO]
        self.assertNotIn("top bar", step.fix)

    def test_engine_unknown_or_replaced_asks_for_a_restart(self):
        for kwargs in ({"engine_known": False}, {"engine_replaced": True}):
            found = sc.steps(facts(**kwargs))
            self.assertIn(sc.RESTART_IBUS, [f.action for f in found], kwargs)

    def test_missing_source_is_added_on_gnome_only(self):
        found = sc.steps(facts(in_gnome_sources=False))
        self.assertIn(sc.ADD_SOURCE, [f.action for f in found])
        found = sc.steps(facts({"XDG_SESSION_TYPE": "x11"}, in_gnome_sources=None))
        self.assertNotIn(sc.ADD_SOURCE, [f.action for f in found])

    def test_another_module_in_the_variables_fails(self):
        found = sc.steps(facts({**READY, "GTK_IM_MODULE": "fcitx", "QT_IM_MODULE": "ibus"}))
        failed = [f for f in found if f.level == sc.FAIL]
        self.assertEqual(len(failed), 1)
        self.assertIn("fcitx", failed[0].title)
        self.assertIn("Remove GTK_IM_MODULE", failed[0].fix)
        xfce = {"XDG_CURRENT_DESKTOP": "XFCE", "XDG_SESSION_TYPE": "x11", "QT_IM_MODULE": "fcitx"}
        failed = [f for f in sc.steps(facts(xfce, in_gnome_sources=None)) if f.level == sc.FAIL]
        self.assertIn("QT_IM_MODULE=ibus", failed[0].fix)

    def test_fcitx5_gtk_module_warns_on_x11_without_a_choice(self):
        warned = titles(sc.steps(facts(fcitx_gtk_module=True)), sc.WARN)
        self.assertIn("GTK apps may pick fcitx5, which is not running", warned)
        chosen = facts({**READY, "GTK_IM_MODULE": "ibus"}, fcitx_gtk_module=True)
        self.assertEqual(titles(sc.steps(chosen), sc.WARN), [])
        wayland = facts({**READY, "XDG_SESSION_TYPE": "wayland"}, fcitx_gtk_module=True)
        self.assertEqual(titles(sc.steps(wayland), sc.WARN), [])

    def test_gtk_module_ibus_warns_on_gnome_wayland_only(self):
        title = "GTK apps keep the underline: GNOME Wayland does not need GTK_IM_MODULE"
        wayland = {**READY, "XDG_SESSION_TYPE": "wayland", "GTK_IM_MODULE": "ibus"}
        self.assertEqual(titles(sc.steps(facts(wayland)), sc.WARN), [title])
        x11 = {**READY, "GTK_IM_MODULE": "ibus"}
        self.assertEqual(titles(sc.steps(facts(x11)), sc.WARN), [])

    def test_wayland_module_is_fine_on_wayland(self):
        wayland = {**READY, "XDG_SESSION_TYPE": "wayland"}
        both = {**wayland, "GTK_IM_MODULE": "wayland", "QT_IM_MODULE": "wayland"}
        self.assertEqual(titles(sc.steps(facts(both)), sc.FAIL), [])
        x11 = {**READY, "GTK_IM_MODULE": "wayland"}
        self.assertEqual(len(titles(sc.steps(facts(x11)), sc.FAIL)), 1)

    def test_xim_through_fcitx5_is_named(self):
        warned = titles(sc.steps(facts({**GNOME_X11, "XMODIFIERS": "@im=fcitx"})), sc.WARN)
        self.assertEqual(warned, ["Older X11 apps use fcitx5"])

    def test_xim_and_fcitx5_warnings(self):
        warned = titles(sc.steps(facts(GNOME_X11, fcitx_running=True)), sc.WARN)
        self.assertEqual(len(warned), 2)


class FixesTest(unittest.TestCase):
    def test_add_source_appends_and_undoes(self):
        sources = FakeSources([("xkb", "us")])
        fixes = sc.Fixes(sources)
        done, undos, settle = fixes.run([sc.ADD_SOURCE])
        self.assertEqual(done, [sc.ADD_SOURCE])
        self.assertEqual(settle, 0)
        self.assertEqual(sources.get(), [("xkb", "us"), ("ibus", "ngosen")])
        message, undo = fixes.finish(done, undos, [])
        self.assertEqual(message, "Added Ngó Sen to the input sources.")
        self.assertTrue(undo())
        self.assertEqual(sources.get(), [("xkb", "us")])

    def test_undo_keeps_later_source_changes(self):
        sources = FakeSources([("xkb", "us")])
        fixes = sc.Fixes(sources)
        done, undos, _settle = fixes.run([sc.ADD_SOURCE])
        sources.set(sources.get() + [("xkb", "fr")])
        _message, undo = fixes.finish(done, undos, [])
        self.assertTrue(undo())
        self.assertEqual(sources.get(), [("xkb", "us"), ("xkb", "fr")])

    def test_restart_that_left_ibus_stopped_failed(self):
        fixes = sc.Fixes(FakeSources([]))
        stopped = sc.Finding(sc.FAIL, "x", action=sc.START_IBUS)
        message, _undo = fixes.finish([sc.RESTART_IBUS], {}, [stopped])
        self.assertEqual(message, "")
        self.assertIn(sc.RESTART_IBUS, fixes.failed)

    def test_add_source_fails_without_gnome_settings(self):
        fixes = sc.Fixes(FakeSources(None))
        done, _undos, _settle = fixes.run([sc.ADD_SOURCE])
        self.assertEqual(done, [])
        self.assertEqual(fixes.failed, {sc.ADD_SOURCE})

    def test_a_fix_that_left_its_step_failed(self):
        fixes = sc.Fixes(FakeSources([]))
        step = sc.Finding(sc.FAIL, "x", action=sc.ADD_SOURCE)
        message, undo = fixes.finish([sc.ADD_SOURCE], {}, [step])
        self.assertEqual((message, undo), ("", None))
        self.assertEqual(fixes.failed, {sc.ADD_SOURCE})


class FactsTest(unittest.TestCase):
    def test_engine_names_from_list_engine(self):
        text = "language: vi\n  ngosen - Ngó Sen\n  Unikey - Unikey\nlanguage: en\n  xkb:us::eng - Eng\n"
        self.assertEqual(sc.engine_names(text), ["ngosen", "Unikey", "xkb:us::eng"])

    def test_unread_engine_list_is_not_unknown(self):
        self.assertTrue(sc.engine_listed(""))
        self.assertFalse(sc.engine_listed("language: en\n  xkb:us::eng - Eng\n"))

    def make_proc(self, pid, comm, exe=None):
        os.makedirs(os.path.join(self.proc, pid))
        with open(os.path.join(self.proc, pid, "comm"), "w", encoding="utf-8") as f:
            f.write(comm + "\n")
        if exe:
            os.symlink(exe, os.path.join(self.proc, pid, "exe"))

    def setUp(self):
        self.proc = tempfile.mkdtemp()

    def test_replaced_engine_is_found(self):
        self.make_proc("10", "ibus-engine-ngo", "/usr/libexec/ibus-engine-ngosen")
        self.assertFalse(sc.runs_replaced_engine(self.proc))
        self.make_proc("11", "ibus-engine-ngo", "/usr/libexec/ibus-engine-ngosen (deleted)")
        self.assertTrue(sc.runs_replaced_engine(self.proc))

    def test_ibus_owns_session_reads_the_address_file(self):
        self.make_proc("20", "ibus-daemon")
        self.make_proc("21", "fcitx5")
        address = os.path.join(self.proc, "address")
        env = {"IBUS_ADDRESS_FILE": address}
        for pid, expected in (("20", True), ("21", False), ("99", False)):
            with open(address, "w", encoding="utf-8") as f:
                f.write(f"IBUS_ADDRESS=unix:path=/x\nIBUS_DAEMON_PID={pid}\n")
            self.assertEqual(sc.session_owner(env, self.proc) == "ibus", expected, pid)

    def test_session_owner_from_the_address_file(self):
        self.make_proc("20", "ibus-daemon")
        self.make_proc("21", "fcitx5")
        address = os.path.join(self.proc, "address")
        env = {"IBUS_ADDRESS_FILE": address}
        for pid, expected in (("20", "ibus"), ("21", "fcitx5"), ("99", "")):
            with open(address, "w", encoding="utf-8") as f:
                f.write(f"IBUS_ADDRESS=unix:path=/x\nIBUS_DAEMON_PID={pid}\n")
            self.assertEqual(sc.session_owner(env, self.proc), expected, pid)
        # A running fcitx5 that wrote no address file of this session does not hold it.
        env = {"IBUS_ADDRESS_FILE": os.path.join(self.proc, "missing")}
        self.assertNotEqual(sc.session_owner(env, self.proc), "fcitx5")

    def test_engine_in_use_needs_a_clean_answer(self):
        for answer, expected in (
            ((0, "xkb:us::eng\n"), "xkb:us::eng"),
            ((1, "xkb:us::eng\n"), ""),
            ((0, "a\nb\n"), ""),
            ((0, "no engine is set.\n"), ""),
            ((0, ""), ""),
        ):
            with mock.patch.object(sc, "_run", return_value=answer):
                self.assertEqual(sc.engine_in_use(), expected, answer)

    def test_switch_key_names(self):
        names = sc.switch_key_names(
            ["<Super>space", "<Shift><Super>space", "", "<Primary>period", "XF86Keyboard"],
            ["grp:lalt_lshift_toggle", "grp:ctrl_alt_toggle_bidir", "caps:none"],
        )
        self.assertEqual(
            names, ["Super+Space", "Shift+Super+Space", "Ctrl+.", "Shift+Alt", "Ctrl+Alt"]
        )

    def test_ibus_running_without_an_address_file(self):
        env = {"IBUS_ADDRESS_FILE": os.path.join(self.proc, "missing")}
        self.make_proc(str(os.getpid()), "fcitx5")
        self.assertEqual(sc.session_owner(env, self.proc), "")
        self.make_proc("1" + str(os.getpid()), "ibus-daemon")
        self.assertEqual(sc.session_owner(env, self.proc), "ibus")


class AppModesTest(unittest.TestCase):
    def test_only_a_newline_ends_a_line(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "ngosen-app-rules.conf")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write("firefox=2\rcode=2\ngedit=2\r\n")
            self.assertEqual(sc.app_modes(sc._read(path)), {"gedit": sc.SEN})

    def test_read_as_the_engine_reads_them(self):
        text = "\n".join(
            [
                "# The typing mode picked for each app",
                "firefox=1",
                "code.desktop=2",
                "gtk3-im:gedit=5",
                "kate=2",
                "kate=5",
                "term=5",
                "term=7",
                "gnome-shell=2",
                "#hidden=2",
                "bad=x",
                "=2",
                "  spaced =  8 ",
                "long=123",
                "org.app_org.app=3",
            ]
        )
        self.assertEqual(
            sc.app_modes(text),
            {
                "firefox": sc.SEN,
                "code": sc.SEN,
                "gedit": sc.PREEDIT,
                "kate": sc.PREEDIT,
                "term": sc.PREEDIT,
                "spaced": sc.SEN,
                "org.app": sc.SEN,
            },
        )


GNOME_WAYLAND = {**READY, "XDG_SESSION_TYPE": "wayland"}


class ShellStepsTest(unittest.TestCase):
    def forward_keys(self, version, state, **kwargs):
        args = {"direct_typing": True, **kwargs}
        f = facts(gnome_shell_version=version, forward_keys_state=state, **args)
        return [x for x in sc.steps(f) if "GNOME" in x.title and version in x.title]

    def test_forward_keys_step_on_gnome_50_0_to_50_3_with_sen(self):
        (step,) = self.forward_keys("50.1", "INACTIVE")
        self.assertEqual((step.level, step.action), (sc.WARN, sc.ENABLE_FORWARD_KEYS))
        self.assertEqual(step.command, "gnome-extensions enable " + sc.FORWARD_KEYS)
        (step,) = self.forward_keys("50.3", "")
        self.assertEqual((step.level, step.action), (sc.WARN, ""))
        (step,) = self.forward_keys("50.0", "ACTIVE")
        self.assertEqual(step.level, sc.OK)

    def test_no_forward_keys_step_elsewhere(self):
        for version in ("50.4", "49.2", "46.0", "51.0"):
            self.assertEqual(self.forward_keys(version, "INACTIVE"), [], version)
        # The underlined mode sends no keys on to the app.
        self.assertEqual(self.forward_keys("50.1", "INACTIVE", direct_typing=False), [])

    def test_forward_keys_step_for_an_app_that_picked_sen(self):
        (step,) = self.forward_keys("50.2", "INACTIVE", direct_typing=False, sen_apps=1)
        self.assertEqual(step.action, sc.ENABLE_FORWARD_KEYS)

    def test_missing_portal_warns_on_gnome_wayland(self):
        title = "Ngó Sen cannot tell which app is in use"
        missing = facts(GNOME_WAYLAND, has_gnome_portal=False)
        self.assertEqual(titles(sc.steps(missing), sc.WARN), [title])
        self.assertEqual(titles(sc.steps(facts(GNOME_WAYLAND)), sc.WARN), [])
        # On X11 apps reach IBus themselves, not through GNOME Shell.
        self.assertEqual(titles(sc.steps(facts(has_gnome_portal=False)), sc.WARN), [])

    def test_enable_forward_keys_and_undo(self):
        with mock.patch.object(sc, "_succeeds", return_value=True) as run:
            done, undo = sc.run_fix(sc.ENABLE_FORWARD_KEYS, FakeSources())
            self.assertTrue(done)
            self.assertTrue(undo())
        self.assertEqual(
            [c.args[0] for c in run.call_args_list],
            [["gnome-extensions", verb, sc.FORWARD_KEYS] for verb in ("enable", "disable")],
        )
        with mock.patch.object(sc, "_succeeds", return_value=False):
            self.assertEqual(sc.run_fix(sc.ENABLE_FORWARD_KEYS, FakeSources()), (False, None))

    def test_extension_state(self):
        text = "forward-keys@ngosen.github.io\n  Name: Forward keys\n  State: ACTIVE\n"
        self.assertEqual(sc.extension_state(text), "ACTIVE")
        self.assertEqual(sc.extension_state(""), "")

    def test_gnome_portal_found_in_the_data_dirs(self):
        exists = os.path.exists
        with tempfile.TemporaryDirectory() as data:
            env = {"XDG_DATA_DIRS": data, "XDG_DATA_HOME": os.path.join(data, "home")}
            # Only the test's folder counts, whatever this machine has installed.
            only_data = mock.patch.object(
                os.path, "exists", side_effect=lambda p: p.startswith(data) and exists(p)
            )
            with only_data:
                self.assertFalse(sc.has_gnome_portal(env))
                services = os.path.join(data, "dbus-1", "services")
                os.makedirs(services)
                name = "org.freedesktop.impl.portal.desktop.gnome.service"
                open(os.path.join(services, name), "w").close()
                self.assertTrue(sc.has_gnome_portal(env))


class ReportTest(unittest.TestCase):
    def test_report_and_issue_link(self):
        f = facts(GNOME_X11, ngosen_version="1.2.0", distro="Ubuntu 24.04", ibus_version="1.5.29")
        findings = [x for x in sc.steps(f) if x.level != sc.OK]
        text = sc.report(f, findings)
        self.assertTrue(
            text.startswith("Ngó Sen 1.2.0, IBus 1.5.29\nUbuntu 24.04, UBUNTU:GNOME, x11")
        )
        self.assertIn("XMODIFIERS=(unset)", text)
        shell = facts(
            GNOME_X11,
            gnome_shell_version="50.1",
            forward_keys_state="ACTIVE",
            has_gnome_portal=False,
        )
        self.assertIn(
            "GNOME Shell 50.1, forward-keys: ACTIVE, portal: not installed, mode: underlined",
            sc.report(shell, []),
        )
        picked = facts(GNOME_X11, gnome_shell_version="50.1", picked_apps=3)
        text = sc.report(picked, [])
        self.assertIn("forward-keys: not found", text)
        self.assertIn("apps with their own mode: 3", text)
        query = parse_qs(urlparse(sc.issue_url(f, text)).query)
        self.assertEqual(query["setup"], [text])
        self.assertEqual(query["template"], ["bug_report.yml"])


if __name__ == "__main__":
    unittest.main()


US, FR, NGOSEN = ("xkb", "us"), ("xkb", "fr"), ("ibus", "ngosen")


class OnlyNgosenTest(unittest.TestCase):
    def test_duplicate_layout_is_a_note_left_out_of_fix_all(self):
        found = sc.steps(facts(duplicate_layout=True))
        (step,) = [f for f in found if f.level == sc.INFO]
        self.assertEqual(step.action, sc.ONLY_NGOSEN)
        self.assertEqual(sc.summary(found)[0], "This machine is ready")
        self.assertNotIn(sc.ONLY_NGOSEN, sc.Fixes(FakeSources()).fixable(found))
        self.assertEqual(titles(sc.steps(facts()), sc.INFO), [])

    def test_removes_us_and_undo_puts_it_back_in_place(self):
        sources = FakeSources([FR, US, NGOSEN])
        fixes = sc.Fixes(sources)
        done, undos, _settle = fixes.run([sc.ONLY_NGOSEN])
        self.assertEqual(sources.get(), [FR, NGOSEN])
        message, undo = fixes.finish(done, undos, [])
        self.assertEqual(message, "Removed English (US) from the input sources.")
        self.assertTrue(undo())
        self.assertEqual(sources.get(), [FR, US, NGOSEN])

    def test_undo_does_not_add_us_twice(self):
        sources = FakeSources([US, NGOSEN])
        _done, undo = sc.run_fix(sc.ONLY_NGOSEN, sources)
        sources.set([NGOSEN, US])
        self.assertTrue(undo())
        self.assertEqual(sources.get(), [NGOSEN, US])

    def test_fails_without_us_or_gnome_settings(self):
        for sources in (FakeSources(None), FakeSources([NGOSEN])):
            self.assertEqual(sc.run_fix(sc.ONLY_NGOSEN, sources), (False, None))

    def test_collect_needs_both_sources_and_a_toggle_key(self):
        cases = [([US, NGOSEN], True, True), ([US, NGOSEN], False, False), ([US], True, False)]
        for current, toggle_key, expected in cases:
            with (
                mock.patch.object(sc, "session_owner", return_value=""),
                mock.patch.object(sc, "_output", return_value=""),
                mock.patch.object(sc, "_pids_named", return_value=[]),
                mock.patch.object(sc, "_fcitx_gtk_modules", return_value=[]),
                mock.patch.object(sc.fcitx5_leftovers, "find", return_value=None),
            ):
                got = sc.collect(FakeSources(current), env=READY, toggle_key=toggle_key)
            self.assertEqual(got.duplicate_layout, expected, (current, toggle_key))
