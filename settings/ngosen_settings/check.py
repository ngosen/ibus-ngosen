# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prints the Check page as text, for a terminal or an AI assistant. It changes nothing."""

import argparse
import os
import subprocess

from . import i18n, ini, system_check
from .store import Engine, config_dir, read_text


def saved_settings(engine_path, folder=None):
    """The engine's defaults with the saved file on top, as the settings window reads them."""
    try:
        values = Engine(engine_path).settings()
    except (OSError, subprocess.SubprocessError):
        values = {}
    folder = folder or config_dir()
    values.update(ini.parse(read_text(os.path.join(folder, "ngosen.conf")) or "")[0])
    return values, folder


NOT_RUNNING, NOT_LOADED = 2, 3


def exit_code(facts):
    """Codes as in the fcitx5 edition's ngosen-check; the report is printed either way."""
    if not facts.ibus_running:
        return NOT_RUNNING
    if not facts.engine_known:
        return NOT_LOADED
    return 0


def check(engine_path, version, sources=None, folder=None):
    """Returns the report and the exit code."""
    if sources is None:
        # Needs gi, which a package build can lack; the tests pass their own sources.
        from .gnome_sources import GnomeSources

        sources = GnomeSources()
    values, folder = saved_settings(engine_path, folder)
    facts = system_check.collect(
        sources,
        version,
        direct_typing=values.get("DirectTyping") == "True",
        app_modes_file=os.path.join(folder, "ngosen-app-rules.conf"),
        toggle_key=bool(values.get("ToggleKey", "").strip()),
        output_charset=values.get("OutputCharset", "Unicode"),
    )
    return system_check.terminal_report(facts, system_check.steps(facts)), exit_code(facts)


def main(engine_path, localedir, version, argv=None):
    i18n.setup(localedir)
    parser = argparse.ArgumentParser(prog="ngosen-check", description=__doc__)
    parser.parse_args(argv)
    report, code = check(os.environ.get("NGOSEN_IBUS_ENGINE", engine_path), version)
    print(report)
    return code
