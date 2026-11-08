/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-app-modes.h"

#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <string>

namespace fs = std::filesystem;
using namespace ngosen;

namespace {

    int  failures = 0;

    void check(bool ok, const std::string& what) {
        if (!ok) {
            ++failures;
            std::cout << "FAIL " << what << '\n';
        }
    }

    void testNames() {
        check(modeAppName("gtk3-im:firefox") == "firefox", "an IBus client is named by its program");
        check(modeAppName("firefox_firefox") == "firefox", "a snap is named once");
        check(modeAppName("org.gnome.TextEditor.desktop") == "org.gnome.TextEditor", "a GNOME app is named without .desktop");
        check(modeAppName("org.gnome.Ptyxis") == "org.gnome.Ptyxis", "a name stays as it is");
        for (const char* shared : {"", "gnome-shell", "QIBusInputContext", "xim"})
            check(modeAppName(shared).empty(), std::string("no single app: ") + shared);
    }

    void testFormat() {
        const AppModeMap modes = parseAppModes("# comment\nfirefox=5\nkate = 2\nlegacy=1\ncode=0\nemoji=6\nwide=99\nword=abc\nno equals\ngnome-shell=5\n");
        check(modes.size() == 3, "only Sen and Preedit for a named app are kept");
        check(modes.count("firefox") && modes.at("firefox") == AppMode::Preedit, "5 is Preedit");
        check(modes.count("kate") && modes.at("kate") == AppMode::Sen, "2 is Sen, spaces trimmed");
        check(modes.count("legacy") && modes.at("legacy") == AppMode::Sen, "a former Sen number is Sen");
        check(parseAppModes(appModesText(modes)) == modes, "app modes round trip");
        check(appModesText({{"firefox", AppMode::Preedit}}).find("\nfirefox=5\n") != std::string::npos, "written as fcitx5 writes it");
    }

    void testFile(const fs::path& root) {
        const std::string path = (root / "ngosen-app-rules.conf").string();
        AppModes          modes(path);
        check(!modes.find("firefox"), "no file, no modes");
        check(modes.set("firefox", AppMode::Preedit), "a mode is saved");
        check(modes.find("firefox") == AppMode::Preedit, "the saved mode applies");
        check(!modes.find("kate"), "another app keeps the shared mode");
        check(AppModes(path).find("firefox") == AppMode::Preedit, "the mode is kept after a restart");

        writeFileAtomically(path, "firefox=2\nkate=5\n");
        fs::last_write_time(path, fs::last_write_time(path) + std::chrono::seconds(2));
        check(modes.find("firefox") == AppMode::Sen && modes.find("kate") == AppMode::Preedit, "an edit by hand applies without a restart");

        check(modes.set("firefox", std::nullopt) && !modes.find("firefox"), "Default forgets the app");
        check(modes.find("kate") == AppMode::Preedit, "forgetting one app keeps the others");

        check(!modes.set("", AppMode::Sen) && !modes.find(""), "an app without a name keeps nothing");

        writeFileAtomically(path, "# mine\ncode=0\nfirefox.desktop=5\nkate=2\n");
        fs::last_write_time(path, fs::last_write_time(path) + std::chrono::seconds(4));
        check(modes.set("firefox", AppMode::Sen), "a pick over a file written elsewhere");
        std::string text;
        readFile(path, text);
        check(text == "# mine\ncode=0\nkate=2\nfirefox=2\n", "a pick changes only the app's own lines: " + text);

        AppModes failing(path, [](const std::string&, const std::string&) { return false; });
        check(!failing.set("kate", AppMode::Sen), "a failed write is reported");
        check(failing.find("kate") == AppMode::Sen, "a failed write changes nothing");
    }

} // namespace

int main() {
    char        pattern[] = "/tmp/ngosen-app-modes-XXXXXX";
    const char* dir       = mkdtemp(pattern);
    if (dir == nullptr)
        return 2;
    const fs::path root(dir);
    testNames();
    testFormat();
    testFile(root);
    fs::remove_all(root);
    if (failures == 0)
        std::cout << "all app mode checks passed\n";
    return failures == 0 ? 0 : 1;
}
