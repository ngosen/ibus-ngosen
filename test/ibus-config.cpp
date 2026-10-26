/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "bamboo-core.h"
#include "ngosen-ibus-config.h"

#include <cstdio>
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

    std::string read(const std::string& path) {
        std::string text;
        return readFile(path, text) ? text : "<missing>";
    }

    void write(const std::string& path, const std::string& text) {
        fs::create_directories(fs::path(path).parent_path());
        check(writeFileAtomically(path, text), "write " + path);
    }

    bool sameOptions(const IBusSettings& a, const IBusSettings& b) {
        return settingsText(a) == settingsText(b);
    }

    SettingsPaths pathsIn(const fs::path& root) {
        return {root / "config/ngosen", root / "data/ngosen", root / "config/fcitx5/conf", root / "data/fcitx5/ngosen"};
    }

    // As the fcitx5 edition writes them: defaults are commented out.
    const char* const FcitxSettings = "# Mode\n# Mode=Sen\nMode=Preedit\nInputMethod=VNI\nSettingsVersion=3\nDoubleSpaceToPeriod=True\n"
                                      "VietnameseOn=True\n# W2U=Non-Start\nW2U=Everywhere\n";
    const char* const FcitxMacros   = "[Macro]\n[Macro/0]\nKey=ko\nValue=không\n[Macro/1]\nKey=vn\nValue=\"Việt Nam\"\n";

    void              testValues() {
        for (const std::string value : {"không", "a b", "x\"y", "back\\slash", "line\nbreak", "", "  lead", "tab\tin", "100%"}) {
            const IniFile ini = parseIni("Key=" + escapeIniValue(value) + "\n");
            const auto    it  = ini.top.find("Key");
            check(it != ini.top.end() && it->second == value, "value round trip: " + value);
        }
        check(parseIni("Key=\"a\\qb\"\n").top.count("Key") == 0, "an unknown escape drops the value, as in fcitx5");
        check(parseIni("Key=a\\nb\n").top.at("Key") == "a\\nb", "an unquoted value has no escapes, as in fcitx5");
        check(parseIni("Key=  spaced  \n").top.at("Key") == "  spaced", "spaces at the ends of a line are dropped");
    }

    void testLists() {
        const auto macros = iniList(parseIni(FcitxMacros), "Macro");
        check(macros.size() == 2 && macros[0].key == "ko" && macros[0].value == "không" && macros[1].value == "Việt Nam", "macro list");
        const auto gap = iniList(parseIni("[Macro/0]\nKey=a\nValue=b\n[Macro/2]\nKey=c\nValue=d\n"), "Macro");
        check(gap.size() == 1, "a list stops at the first missing index, as in fcitx5");
    }

    void testSettings() {
        const IBusSettings defaults = defaultSettings();
        check(sameOptions(readSettings(parseIni("")), defaults), "an empty file reads as the defaults");
        Options fcitxDefaults           = defaultOptions;
        fcitxDefaults.retypeAfterSwitch = false;
        fcitxDefaults.retoneSelection   = false;
        IBusSettings expected           = defaults;
        expected.options                = fcitxDefaults;
        check(sameOptions(defaults, expected), "the defaults are the fcitx5 edition's");

        const IBusSettings read = readSettings(parseIni(FcitxSettings));
        check(read.options.inputMethod == "VNI", "InputMethod is read");
        check(read.options.w2u == 2, "W2U is read by name");
        check(!read.options.doubleSpaceToPeriod, "DoubleSpaceToPeriod stays off");
        check(!read.options.retypeAfterSwitch && !read.options.retoneSelection, "retyping stays off");

        const IBusSettings odd = readSettings(parseIni("InputMethod=Nope\nSpellCheck=yes\nOutputCharset=Nope\nLockWordModifier=Disabled\n"));
        check(odd.options.inputMethod == "Telex" && odd.options.spellCheck && odd.options.outputCharset == "Unicode", "unknown values keep the defaults");
        check(odd.options.lockWordKey == LockWordKey::None, "LockWordModifier is read by name");

        IBusSettings changed             = defaults;
        changed.options.inputMethod      = "VNI";
        changed.options.outputCharset    = "TCVN3 (ABC)";
        changed.options.bracketTransform = 1;
        changed.options.lockWordKey      = LockWordKey::Alt;
        changed.options.timeFormat       = "%H giờ %M";
        changed.options.spellCheck       = false;
        changed.enableDictionary         = true;
        changed.enableCustomKeymap       = true;
        const std::string text           = settingsText(changed);
        check(sameOptions(readSettings(parseIni(text)), changed), "settings round trip");
        check(parseIni(text).top.size() == 19, "the file has every key");
        // fcitx5 reads SettingsVersion as the version of its own upgrades.
        check(parseIni(text).top.count("SettingsVersion") == 0, "no SettingsVersion");
    }

    void testImport(const fs::path& root) {
        const SettingsPaths paths = pathsIn(root);
        write(paths.fcitxConfigDir + "/ngosen.conf", FcitxSettings);
        write(paths.fcitxConfigDir + "/ngosen-macro-table.conf", FcitxMacros);
        write(paths.fcitxDataDir + "/vietnamese.cm.dict", "người dùng\n");
        check(prepareSettings(paths), "import succeeds");
        const IniFile settings = parseIni(read(paths.settingsFile()));
        check(settings.top.count("InputMethod") == 1 && settings.top.at("InputMethod") == "VNI", "InputMethod imported");
        check(settings.top.count("Mode") == 0, "Mode not imported");
        check(settings.top.count("SettingsVersion") == 0, "the fcitx5 SettingsVersion not imported");
        check(read(paths.macroFile()) == FcitxMacros, "macros copied as they are");
        check(read(paths.dictionaryFile()) == "người dùng\n", "the user's dictionary copied");
        check(!fs::exists(paths.keymapFile()), "no keymap file without one to copy");

        write(paths.fcitxConfigDir + "/ngosen.conf", "InputMethod=Telex\n");
        check(prepareSettings(paths) && parseIni(read(paths.settingsFile())).top.at("InputMethod") == "VNI", "a later run imports nothing");

        write(paths.fcitxConfigDir + "/ngosen.conf", FcitxSettings);
        fs::remove(paths.settingsFile());
        check(prepareSettings(paths) && read(paths.settingsFile()) == settingsText(defaultSettings()), "a deleted ngosen.conf comes back as the defaults");
    }

    void testNoOverwrite(const fs::path& root) {
        const SettingsPaths paths = pathsIn(root);
        write(paths.fcitxConfigDir + "/ngosen-macro-table.conf", FcitxMacros);
        write(paths.macroFile(), "[Macro/0]\nKey=a\nValue=b\n");
        check(prepareSettings(paths), "prepare with a macro file already there");
        check(read(paths.macroFile()) == "[Macro/0]\nKey=a\nValue=b\n", "an existing file is kept");
    }

    void testDefaults(const fs::path& root) {
        const SettingsPaths paths = pathsIn(root);
        check(prepareSettings(paths), "defaults written");
        check(read(paths.settingsFile()) == settingsText(defaultSettings()), "nothing to import writes the defaults");
    }

    // A run killed after any write leaves files the next run finishes into the same result.
    void testKilledHalfway(const fs::path& root) {
        const auto fill = [](const SettingsPaths& paths) {
            write(paths.fcitxConfigDir + "/ngosen.conf", FcitxSettings);
            write(paths.fcitxConfigDir + "/ngosen-macro-table.conf", FcitxMacros);
            write(paths.fcitxConfigDir + "/ngosen-custom-keymap.conf", "[CustomKeymap/0]\nKey=z\nValue=XoaDauThanh\n");
            write(paths.fcitxDataDir + "/vietnamese.cm.dict", "từ\n");
        };
        const auto result = [](const SettingsPaths& paths) {
            return read(paths.settingsFile()) + read(paths.macroFile()) + read(paths.keymapFile()) + read(paths.dictionaryFile()) + read(paths.importedMark());
        };
        const SettingsPaths clean = pathsIn(root / "clean");
        fill(clean);
        prepareSettings(clean);
        for (int stopAt = 0; stopAt < 5; ++stopAt) {
            const SettingsPaths paths = pathsIn(root / std::to_string(stopAt));
            fill(paths);
            int        writes = 0;
            const bool done = prepareSettings(paths, [&](const std::string& path, const std::string& content) { return writes++ < stopAt && writeFileAtomically(path, content); });
            check(!done && !fs::exists(paths.importedMark()), "stopped after " + std::to_string(stopAt) + " writes");
            prepareSettings(paths);
            check(result(paths) == result(clean), "finished after stopping at write " + std::to_string(stopAt));
        }
    }

} // namespace

int main() {
    Init();
    char        pattern[] = "/tmp/ngosen-config-XXXXXX";
    const char* dir       = mkdtemp(pattern);
    if (dir == nullptr)
        return 2;
    const fs::path root(dir);
    testValues();
    testLists();
    testSettings();
    testImport(root / "import");
    testNoOverwrite(root / "keep");
    testDefaults(root / "defaults");
    testKilledHalfway(root / "killed");
    fs::remove_all(root);
    if (failures == 0)
        std::cout << "all settings checks passed\n";
    return failures == 0 ? 0 : 1;
}
