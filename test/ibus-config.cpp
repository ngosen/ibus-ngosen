/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "bamboo-core.h"
#include "ngosen-ibus-config.h"
#include "ngosen-ibus-keys.h"
#include "ngosen-ibus-menu.h"
#include "ngosen-ibus-mode-menu.h"

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
                                      "VietnameseOn=True\n# W2U=Non-Start\nW2U=Everywhere\nRetoneSelection=False\nRetypeAfterSwitch=True\n";
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
        IBusSettings expected           = defaults;
        expected.options                = fcitxDefaults;
        check(sameOptions(defaults, expected), "the defaults are the fcitx5 edition's");
        check(defaults.options.retoneSelection, "RetoneSelection is on by default, as in fcitx5");

        const IBusSettings read = readSettings(parseIni(FcitxSettings));
        check(read.options.inputMethod == "VNI", "InputMethod is read");
        check(read.options.w2u == 2, "W2U is read by name");
        check(!read.options.doubleSpaceToPeriod, "DoubleSpaceToPeriod stays off");
        check(!read.options.retypeAfterSwitch, "RetypeAfterSwitch stays off");
        check(!read.options.retoneSelection, "RetoneSelection is read");

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
        changed.options.retoneSelection  = false;
        changed.enableDictionary         = true;
        changed.enableCustomKeymap       = true;
        changed.directTyping             = true;
        const std::string text           = settingsText(changed);
        check(sameOptions(readSettings(parseIni(text)), changed), "settings round trip");
        check(!readSettings(parseIni(text)).options.retoneSelection, "RetoneSelection round trip");
        check(parseIni(text).top.size() == 26, "the file has every key");
        // fcitx5 reads SettingsVersion as the version of its own upgrades.
        check(parseIni(text).top.count("SettingsVersion") == 0, "no SettingsVersion");
    }

    void testOneSetting() {
        const std::string mine = "# my note\nInputMethod=Telex\nSpellCheck=True\n";
        check(withSetting(mine, "SpellCheck", "False") == "# my note\nInputMethod=Telex\nSpellCheck=False\n", "one key changes, the rest stays");
        check(withSetting(mine, "EnableMacro", "True") == mine + "EnableMacro=True\n", "a missing key is added");
        check(withSetting("#SpellCheck=True\n", "SpellCheck", "False") == "#SpellCheck=True\nSpellCheck=False\n", "a commented key is left alone");
        check(readSettings(parseIni(withSetting("SpellCheck=True\nSpellCheck=True\n", "SpellCheck", "False"))).options.spellCheck == false, "every copy of the key changes");
        check(withSetting("A=1\n[Macro/0]\nKey=x\n", "SpellCheck", "False") == "A=1\nSpellCheck=False\n[Macro/0]\nKey=x\n", "a new key goes before the first section");
        check(withSetting("[S]\nSpellCheck=True\n", "SpellCheck", "False") == "SpellCheck=False\n[S]\nSpellCheck=True\n", "a key inside a section is not the setting");
        check(parseIni(withSetting("", "OutputCharset", "TCVN3 (ABC)")).top.at("OutputCharset") == "TCVN3 (ABC)", "a value with spaces is quoted");
    }

    void testToggleKeys() {
        check(readSettings(parseIni("")).toggleKeys == defaultToggleKeys(), "no toggle key reads as Ctrl+Shift");
        check(readSettings(parseIni("ToggleKey=\n")).toggleKeys.empty(), "an empty toggle key turns the key off");
        check(readSettings(parseIni("ToggleKey=Alt+z Control+space\n")).toggleKeys == std::vector<std::string>{"Alt+z", "Control+space"}, "toggle keys are read");
        // fcitx5 allows these; here a bare Shift would switch on every capital.
        check(readSettings(parseIni("ToggleKey=Shift_L Zenkaku_Hankaku\n")).toggleKeys == defaultToggleKeys(), "single keys fall back to the default");
        check(readSettings(parseIni("ToggleKey=Shift_L Alt+z Nope+x\n")).toggleKeys == std::vector<std::string>{"Alt+z"}, "single and unknown keys are dropped");
        const std::vector<std::string> shiftAlt{"Shift+Alt_L", "Shift+Alt_R", "Alt+Shift_L", "Alt+Shift_R"};
        check(readSettings(parseIni("ToggleKey=Shift+Alt_L Shift+Alt_R Alt+Shift_L Alt+Shift_R\n")).toggleKeys == shiftAlt, "the Shift+Alt choice is read whole");

        IBusSettings changed = defaultSettings();
        changed.toggleKeys   = {"Alt+z", "Control+space"};
        check(readSettings(parseIni(settingsText(changed))).toggleKeys == changed.toggleKeys, "toggle keys round trip");
        changed.toggleKeys = {};
        check(readSettings(parseIni(settingsText(changed))).toggleKeys.empty(), "a key turned off stays off");
        check(parseIni(settingsText(defaultSettings()) + "SpellCheck=False\n").top.at("SpellCheck") == "False", "a key appended to the file is still a setting");

        const char* const fcitxKeys = "[ToggleKey]\n0=Alt+z\n2=Control+space\n";
        check(readSettings(parseIni(std::string(FcitxSettings) + fcitxKeys)).toggleKeys == std::vector<std::string>{"Alt+z"},
              "the fcitx5 edition's key list is imported, up to its first missing index");
        check(readSettings(parseIni(std::string(FcitxSettings) + "[ToggleKey]\n")).toggleKeys.empty(), "a key turned off in the fcitx5 edition stays off");
    }

    void testModeMenuSettings() {
        const IBusSettings defaults = readSettings(parseIni(""));
        check(defaults.modeMenuKeys == std::vector<std::string>{"grave"}, "the mode menu opens with ` by default, as in fcitx5");
        check(defaults.shortcutSen == "1" && defaults.shortcutPreedit == "q" && defaults.shortcutOff == "e", "menu shortcuts default to fcitx5's");
        check(readSettings(parseIni("ModeMenuKey=Shift+asciitilde\n")).modeMenuKeys == std::vector<std::string>{"Shift+asciitilde"}, "Shift+~ opens the menu");
        check(readSettings(parseIni("ModeMenuKey=\n")).modeMenuKeys.empty(), "an empty menu key turns the menu off");
        check(readSettings(parseIni("ModeMenuKey=Shift_L Nope\n")).modeMenuKeys == std::vector<std::string>{"grave"}, "a lone modifier falls back to `");
        check(readSettings(parseIni(std::string(FcitxSettings) + "[ModeMenuKey]\n0=apostrophe\n")).modeMenuKeys == std::vector<std::string>{"apostrophe"},
              "the fcitx5 edition's menu key list is imported");
        const IBusSettings shortcuts = readSettings(parseIni("ShortcutSen=a\nShortcutPreedit=semicolon\nShortcutOff=\n"));
        check(shortcuts.shortcutSen == "a" && shortcuts.shortcutPreedit == "q" && shortcuts.shortcutOff == "e", "a shortcut is one letter or digit");
        check(readSettings(parseIni("ShortcutOff=X\n")).shortcutOff == "x", "a shortcut written in capitals is read in lowercase");
        IBusSettings changed  = defaults;
        changed.modeMenuKeys  = {};
        changed.shortcutOff   = "x";
        const IBusSettings rt = readSettings(parseIni(settingsText(changed)));
        check(rt.modeMenuKeys.empty() && rt.shortcutOff == "x", "menu settings round trip");
    }

    void testModeMenuKeys() {
        IBusSettings settings = defaultSettings();
        check(opensModeMenu(settings, {}, IBUS_KEY_grave, 0), "` opens the menu");
        check(!opensModeMenu(settings, {}, IBUS_KEY_grave, IBUS_RELEASE_MASK), "its release does not");
        check(!opensModeMenu(settings, {}, IBUS_KEY_asciitilde, IBUS_SHIFT_MASK), "~ does not open the default menu");
        check(menuKey(settings, IBUS_KEY_q, 0).kind == MenuKey::Pick && menuKey(settings, IBUS_KEY_q, 0).mode == MenuMode::Preedit, "q picks underlined typing");
        check(menuKey(settings, IBUS_KEY_e, 0).mode == MenuMode::English && menuKey(settings, IBUS_KEY_1, 0).mode == MenuMode::Sen, "e and 1 pick their modes");
        check(menuKey(settings, IBUS_KEY_q, IBUS_CONTROL_MASK).kind == MenuKey::Swallow, "Ctrl+q picks nothing");
        check(menuKey(settings, IBUS_KEY_grave, 0).kind == MenuKey::TypeMenuKey, "` again types itself");
        check(menuKey(settings, IBUS_KEY_Escape, 0).kind == MenuKey::Close && menuKey(settings, IBUS_KEY_Return, 0).kind == MenuKey::PickCursor, "Esc closes, Enter picks");
        settings.modeMenuKeys = {"Shift+asciitilde"};
        settings.shortcutOff  = "x";
        check(opensModeMenu(settings, {}, IBUS_KEY_asciitilde, IBUS_SHIFT_MASK) && !opensModeMenu(settings, {}, IBUS_KEY_grave, 0), "Shift+~ opens the menu instead of `");
        check(menuKey(settings, IBUS_KEY_x, 0).mode == MenuMode::English && menuKey(settings, IBUS_KEY_e, 0).kind == MenuKey::Swallow, "a changed shortcut picks its mode");
        check(menuKey(settings, IBUS_KEY_asciitilde, IBUS_SHIFT_MASK).kind == MenuKey::TypeMenuKey, "Shift+~ again types ~");
        settings.options.inputMethod = "VIQR";
        check(!opensModeMenu(settings, {}, IBUS_KEY_asciitilde, IBUS_SHIFT_MASK), "VIQR keeps ~ for its tone");
        settings.options.inputMethod = "Telex";
        check(!opensModeMenu(settings, {{"~", "DauNga"}}, IBUS_KEY_asciitilde, IBUS_SHIFT_MASK), "a custom keymap keeps its keys");
        check(opensModeMenu(settings, {{"s", "DauSac"}}, IBUS_KEY_asciitilde, IBUS_SHIFT_MASK), "other keymap keys leave the menu alone");
    }

    bool matches(const std::string& key, guint keyval, guint state) {
        const auto chord = parseToggleKey(key);
        return chord && matchesKey(*chord, keyval, state);
    }

    void testKeyMatching() {
        check(!parseToggleKey("Shift_L") && !parseToggleKey("Shift+Shift_L") && !parseToggleKey("space") && !parseToggleKey("Nope+x"), "single and unknown keys");
        check(matches("Control+Shift_L", IBUS_KEY_Shift_L, IBUS_CONTROL_MASK), "Ctrl held, Shift pressed");
        check(matches("Control+Shift_L", IBUS_KEY_Shift_L, IBUS_CONTROL_MASK | IBUS_SHIFT_MASK | IBUS_RELEASE_MASK), "Shift released with Ctrl held");
        check(matches("Control+Shift_L", IBUS_KEY_Shift_L, IBUS_CONTROL_MASK | IBUS_MOD2_MASK | IBUS_LOCK_MASK), "NumLock and Caps Lock do not count");
        check(!matches("Control+Shift_L", IBUS_KEY_Shift_R, IBUS_CONTROL_MASK), "the other Shift is another entry");
        check(!matches("Control+Shift_L", IBUS_KEY_Shift_L, IBUS_CONTROL_MASK | IBUS_MOD1_MASK), "Ctrl+Alt+Shift is not Ctrl+Shift");
        check(matches("Alt+Z", IBUS_KEY_z, IBUS_MOD1_MASK) && matches("Alt+z", IBUS_KEY_z, IBUS_MOD1_MASK), "letters match whatever their case");
        check(!matches("Alt+z", IBUS_KEY_Z, IBUS_MOD1_MASK | IBUS_SHIFT_MASK), "Alt+Shift+z is not Alt+z");
        check(matches("Super+space", IBUS_KEY_space, IBUS_MOD4_MASK), "GNOME reports Super as Mod4");
        check(matches("Shift+asciitilde", IBUS_KEY_asciitilde, IBUS_SHIFT_MASK), "keysym names as fcitx5 stores them");
        // The US layout puts Meta on the second level of Alt, so Shift then Alt arrives as Meta.
        check(matches("Shift+Alt_L", IBUS_KEY_Meta_L, IBUS_SHIFT_MASK), "Alt pressed with Shift held reads as Meta");
        check(matches("Shift+Alt_L", IBUS_KEY_Meta_L, IBUS_SHIFT_MASK | IBUS_MOD1_MASK | IBUS_RELEASE_MASK), "Meta released with Shift held");
        check(!otherModifierHeld(IBUS_KEY_Meta_R, IBUS_MOD1_MASK | IBUS_RELEASE_MASK), "Meta released alone holds nothing else");
        // GTK 4 can report the Meta bit beside Mod1 while Alt is held.
        check(matches("Alt+Shift_L", IBUS_KEY_Shift_L, IBUS_SHIFT_MASK | IBUS_MOD1_MASK | IBUS_META_MASK | IBUS_RELEASE_MASK), "Shift released with Alt and its Meta bit held");
        check(!otherModifierHeld(IBUS_KEY_Alt_L, IBUS_MOD1_MASK | IBUS_META_MASK | IBUS_RELEASE_MASK), "Alt released with its Meta bit holds nothing else");
        check(matches("Meta+space", IBUS_KEY_space, IBUS_MOD1_MASK), "a Meta chord reads as Alt");
    }

    IBusProperty* findItem(IBusPropList* list, const std::string& key) {
        for (guint i = 0; IBusProperty* item = ibus_prop_list_get(list, i); ++i) {
            if (key == ibus_property_get_key(item))
                return item;
            if (IBusProperty* inner = findItem(ibus_property_get_sub_props(item), key))
                return inner;
        }
        return nullptr;
    }

    bool isChecked(IBusPropList* menu, const std::string& key) {
        IBusProperty* item = findItem(menu, key);
        return item != nullptr && ibus_property_get_state(item) == PROP_STATE_CHECKED;
    }

    void testMenu() {
        IBusSettings settings                           = defaultSettings();
        settings.options.inputMethod                    = "VNI";
        settings.options.spellCheck                     = false;
        settings.options.capitalizeStartOfText          = true;
        settings.options.autoCapitalizeAfterPunctuation = false;
        IBusPropList* menu                              = newSettingsMenu(settings);
        g_object_ref_sink(menu);
        check(isChecked(menu, "InputMethod/VNI") && !isChecked(menu, "InputMethod/Telex"), "the menu checks the input method in use");
        check(isChecked(menu, "OutputCharset/Unicode"), "the menu checks the charset in use");
        check(!isChecked(menu, "SpellCheck") && findItem(menu, "SpellCheck") != nullptr, "the menu shows spell check off");
        check(isChecked(menu, "CapitalizeStartOfText") && !isChecked(menu, "AutoCapitalizeAfterPunctuation"), "the capitalize items show their own settings");
        check(findItem(menu, SettingsWindowItem) != nullptr, "the menu opens the settings window");
        g_object_unref(menu);

        std::string key;
        std::string value;
        check(settingForClick("InputMethod/Telex", true, key, value) && key == "InputMethod" && value == "Telex", "choosing Telex");
        check(!settingForClick("InputMethod/Telex", false, key, value), "a radio item being unchecked changes nothing");
        check(!settingForClick("InputMethod/Custom", true, key, value), "a method the menu does not offer");
        check(settingForClick("OutputCharset/TCVN3 (ABC)", true, key, value) && key == "OutputCharset" && value == "TCVN3 (ABC)", "choosing a charset");
        check(!settingForClick("OutputCharset/Nope", true, key, value), "an unknown charset");
        check(settingForClick("SpellCheck", false, key, value) && key == "SpellCheck" && value == "False", "turning spell check off");
        check(settingForClick("EnableDictionary", true, key, value) && value == "True", "turning the dictionary on");
        check(settingForClick("DirectTyping", true, key, value) && key == "DirectTyping" && value == "True", "turning Sen on");
        check(!settingForClick("Mode", true, key, value) && !settingForClick(SettingsWindowItem, true, key, value), "items that are not settings");
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
    testOneSetting();
    testToggleKeys();
    testModeMenuSettings();
    testModeMenuKeys();
    testKeyMatching();
    testMenu();
    testImport(root / "import");
    testNoOverwrite(root / "keep");
    testDefaults(root / "defaults");
    testKilledHalfway(root / "killed");
    fs::remove_all(root);
    if (failures == 0)
        std::cout << "all settings checks passed\n";
    return failures == 0 ? 0 : 1;
}
