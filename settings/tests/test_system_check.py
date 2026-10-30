# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

from ngosen_settings import system_check as sc

from tests.test_window import FakeSources

GNOME_X11 = {"XDG_CURRENT_DESKTOP": "ubuntu:GNOME", "XDG_SESSION_TYPE": "x11"}
READY = {**GNOME_X11, "XMODIFIERS": "@im=ibus"}


def facts(env=READY, **kwargs):
    defaults = {"ibus_running": True, "in_gnome_sources": True}
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
            self.assertEqual(sc.ibus_owns_session(env, self.proc), expected, pid)


class ReportTest(unittest.TestCase):
    def test_report_and_issue_link(self):
        f = facts(GNOME_X11, ngosen_version="1.2.0", distro="Ubuntu 24.04", ibus_version="1.5.29")
        findings = [x for x in sc.steps(f) if x.level != sc.OK]
        text = sc.report(f, findings)
        self.assertTrue(
            text.startswith("Ngó Sen 1.2.0, IBus 1.5.29\nUbuntu 24.04, UBUNTU:GNOME, x11")
        )
        self.assertIn("XMODIFIERS=(unset)", text)
        query = parse_qs(urlparse(sc.issue_url(f, text)).query)
        self.assertEqual(query["setup"], [text])
        self.assertEqual(query["template"], ["bug_report.yml"])


if __name__ == "__main__":
    unittest.main()
