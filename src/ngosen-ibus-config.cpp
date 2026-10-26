/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-config.h"

#include "bamboo-core.h"
#include "ngosen-log.h"

#include <algorithm>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <filesystem>
#include <fstream>
#include <glib.h>
#include <sstream>
#include <unistd.h>

namespace ngosen {

    namespace {

        std::string trim(const std::string& text) {
            const auto begin = text.find_first_not_of(" \t\r\f\v");
            if (begin == std::string::npos)
                return "";
            const auto end = text.find_last_not_of(" \t\r\f\v");
            return text.substr(begin, end - begin + 1);
        }

        constexpr char EscapedChars[]  = "\\\"\n\f\r\t\v";
        constexpr char EscapeLetters[] = "\\\"nfrtv";

        // As fcitx5 reads a value: only a quoted one has escapes, and a bad escape drops it.
        bool unescapeIniValue(const std::string& value, std::string& out) {
            if (value.size() < 2 || value.front() != '"' || value.back() != '"') {
                out = value;
                return true;
            }
            out.clear();
            for (size_t i = 1; i + 1 < value.size(); ++i) {
                if (value[i] == '"')
                    return false;
                if (value[i] != '\\') {
                    out += value[i];
                    continue;
                }
                const char* letter = ++i + 1 < value.size() ? std::strchr(EscapeLetters, value[i]) : nullptr;
                if (letter == nullptr || *letter == '\0')
                    return false;
                out += EscapedChars[letter - EscapeLetters];
            }
            return true;
        }

        std::vector<std::string> takeNames(char** names) {
            std::vector<std::string> result;
            if (names == nullptr)
                return result;
            for (size_t i = 0; names[i] != nullptr; ++i) { //NOLINT
                result.emplace_back(names[i]);             //NOLINT
                free(names[i]);                            //NOLINT
            }
            free(names); //NOLINT
            return result;
        }

        bool contains(const std::vector<std::string>& list, const std::string& value) {
            return std::find(list.begin(), list.end(), value) != list.end();
        }

        const char* const ModeNames[]        = {"Disabled", "Non-Start", "Everywhere"};
        const char* const LockWordKeyNames[] = {"Disabled", "Shift", "Ctrl", "Alt"};

        struct Reader {
            const std::map<std::string, std::string>& values;

            const std::string*                        find(const char* key) const {
                const auto it = values.find(key);
                return it == values.end() ? nullptr : &it->second;
            }
            void boolean(const char* key, bool& out) const {
                if (const auto* value = find(key); value != nullptr && (*value == "True" || *value == "False"))
                    out = *value == "True";
            }
            void text(const char* key, std::string& out) const {
                if (const auto* value = find(key))
                    out = *value;
            }
            void choice(const char* key, std::string& out, const std::vector<std::string>& allowed) const {
                if (const auto* value = find(key); value != nullptr && contains(allowed, *value))
                    out = *value;
            }
            template <size_t N>
            void index(const char* key, int& out, const char* const (&names)[N]) const {
                if (const auto* value = find(key)) {
                    for (size_t i = 0; i < N; ++i) {
                        if (*value == names[i])
                            out = static_cast<int>(i);
                    }
                }
            }
        };

        const char* boolText(bool value) {
            return value ? "True" : "False";
        }

        bool fileExists(const std::string& path) {
            std::error_code error;
            return std::filesystem::exists(path, error);
        }

    } // namespace

    const std::vector<std::string>& inputMethodNames() {
        static const std::vector<std::string> names = [] {
            auto list = takeNames(GetInputMethodNames());
            list.emplace_back("Custom");
            return list;
        }();
        return names;
    }

    const std::vector<std::string>& charsetNames() {
        static const std::vector<std::string> names = takeNames(GetCharsetNames());
        return names;
    }

    IniFile parseIni(const std::string& text) {
        IniFile                             ini;
        std::map<std::string, std::string>* current = &ini.top;
        std::istringstream                  lines(text);
        std::string                         line;
        while (std::getline(lines, line)) {
            line = trim(line);
            if (line.empty() || line[0] == '#')
                continue;
            if (line.front() == '[' && line.back() == ']') {
                current = &ini.sections[line.substr(1, line.size() - 2)];
                continue;
            }
            const auto equal = line.find('=');
            if (equal == std::string::npos)
                continue;
            std::string value;
            if (unescapeIniValue(line.substr(equal + 1), value))
                (*current)[line.substr(0, equal)] = value;
        }
        return ini;
    }

    std::string escapeIniValue(const std::string& value) {
        if (value.find_first_of(" \f\r\t\v\"\\\n") == std::string::npos)
            return value;
        std::string out = "\"";
        for (const char c : value) {
            if (const char* escaped = c != '\0' ? std::strchr(EscapedChars, c) : nullptr) {
                out += '\\';
                out += EscapeLetters[escaped - EscapedChars];
            } else {
                out += c;
            }
        }
        return out + "\"";
    }

    std::vector<KeymapEntry> iniList(const IniFile& ini, const std::string& name) {
        // fcitx5 stops at the first missing index too.
        std::vector<KeymapEntry> entries;
        for (size_t i = 0;; ++i) {
            const auto it = ini.sections.find(name + "/" + std::to_string(i));
            if (it == ini.sections.end())
                return entries;
            const auto key   = it->second.find("Key");
            const auto value = it->second.find("Value");
            entries.push_back({key != it->second.end() ? key->second : "", value != it->second.end() ? value->second : ""});
        }
    }

    IBusSettings defaultSettings() {
        IBusSettings settings;
        auto&        o         = settings.options;
        o.retypeAfterSwitch    = false;
        o.retoneSelection      = false;
        o.enableMacroInOffMode = false;
        o.doubleSpaceToPeriod  = false;
        o.doubleHyphenToEmDash = false;
        return settings;
    }

    IBusSettings readSettings(const IniFile& ini) {
        IBusSettings settings = defaultSettings();
        auto&        o        = settings.options;
        const Reader read{ini.top};
        read.choice("InputMethod", o.inputMethod, inputMethodNames());
        read.choice("OutputCharset", o.outputCharset, charsetNames());
        read.boolean("SpellCheck", o.spellCheck);
        read.boolean("ModernStyle", o.modernStyle);
        read.boolean("FreeMarking", o.freeMarking);
        read.index("W2U", o.w2u, ModeNames);
        read.index("BracketTransform", o.bracketTransform, ModeNames);
        read.boolean("AutoNonVnRestore", o.autoNonVnRestore);
        read.boolean("DdFreeStyle", o.ddFreeStyle);
        read.boolean("BackspaceRemovesTone", o.backspaceRemovesTone);
        read.boolean("EnableMacro", o.enableMacro);
        read.boolean("CapitalizeMacro", o.capitalizeMacro);
        int lockWordKey = static_cast<int>(o.lockWordKey);
        read.index("LockWordModifier", lockWordKey, LockWordKeyNames);
        o.lockWordKey = static_cast<LockWordKey>(lockWordKey);
        read.boolean("AutoCapitalizeAfterPunctuation", o.autoCapitalizeAfterPunctuation);
        read.boolean("CapitalizeStartOfText", o.capitalizeStartOfText);
        read.text("TimeFormat", o.timeFormat);
        read.text("DateFormat", o.dateFormat);
        read.boolean("EnableDictionary", settings.enableDictionary);
        read.boolean("EnableCustomKeymap", settings.enableCustomKeymap);
        return settings;
    }

    std::string settingsText(const IBusSettings& settings) {
        const auto&        o = settings.options;
        std::ostringstream out;
        const auto         line = [&out](const char* key, const std::string& value) { out << key << '=' << escapeIniValue(value) << '\n'; };
        line("InputMethod", o.inputMethod);
        line("OutputCharset", o.outputCharset);
        line("SpellCheck", boolText(o.spellCheck));
        line("ModernStyle", boolText(o.modernStyle));
        line("FreeMarking", boolText(o.freeMarking));
        line("W2U", ModeNames[o.w2u]);
        line("BracketTransform", ModeNames[o.bracketTransform]);
        line("AutoNonVnRestore", boolText(o.autoNonVnRestore));
        line("DdFreeStyle", boolText(o.ddFreeStyle));
        line("BackspaceRemovesTone", boolText(o.backspaceRemovesTone));
        line("EnableMacro", boolText(o.enableMacro));
        line("CapitalizeMacro", boolText(o.capitalizeMacro));
        line("LockWordModifier", LockWordKeyNames[static_cast<int>(o.lockWordKey)]);
        line("AutoCapitalizeAfterPunctuation", boolText(o.autoCapitalizeAfterPunctuation));
        line("CapitalizeStartOfText", boolText(o.capitalizeStartOfText));
        line("TimeFormat", o.timeFormat);
        line("DateFormat", o.dateFormat);
        line("EnableDictionary", boolText(settings.enableDictionary));
        line("EnableCustomKeymap", boolText(settings.enableCustomKeymap));
        return out.str();
    }

    std::string withSetting(const std::string& text, const std::string& key, const std::string& value) {
        const std::string  setting = key + '=' + escapeIniValue(value);
        std::istringstream lines(text);
        std::ostringstream out;
        std::string        line;
        bool               top = true;
        bool               set = false;
        while (std::getline(lines, line)) {
            const std::string trimmed = trim(line);
            const auto        equal   = trimmed.find('=');
            if (!trimmed.empty() && trimmed.front() == '[' && trimmed.back() == ']') {
                // A key after a section header would belong to that section.
                if (top && !set)
                    out << setting << '\n';
                top = false;
                set = true;
            } else if (top && equal != std::string::npos && trimmed[0] != '#' && trimmed.substr(0, equal) == key) {
                // Every copy, since parseIni() keeps the last one.
                line = setting;
                set  = true;
            }
            out << line << '\n';
        }
        if (!set)
            out << setting << '\n';
        return out.str();
    }

    SettingsPaths SettingsPaths::fromEnvironment() {
        const std::string config = g_get_user_config_dir();
        const std::string data   = g_get_user_data_dir();
        return {config + "/ngosen", data + "/ngosen", config + "/fcitx5/conf", data + "/fcitx5/ngosen"};
    }

    std::string SettingsPaths::settingsFile() const {
        return configDir + "/ngosen.conf";
    }
    std::string SettingsPaths::macroFile() const {
        return configDir + "/ngosen-macro-table.conf";
    }
    std::string SettingsPaths::keymapFile() const {
        return configDir + "/ngosen-custom-keymap.conf";
    }
    std::string SettingsPaths::dictionaryFile() const {
        return dataDir + "/vietnamese.cm.dict";
    }
    std::string SettingsPaths::importedMark() const {
        return configDir + "/.fcitx5-imported";
    }

    bool readFile(const std::string& path, std::string& content) {
        std::ifstream file(path, std::ios::binary);
        if (!file)
            return false;
        std::ostringstream buffer;
        buffer << file.rdbuf();
        content = buffer.str();
        return true;
    }

    bool writeFileAtomically(const std::string& path, const std::string& content) {
        const std::filesystem::path target(path);
        std::error_code             error;
        std::filesystem::create_directories(target.parent_path(), error);
        std::string temp = path + ".XXXXXX";
        const int   fd   = ::mkostemp(temp.data(), O_CLOEXEC);
        if (fd == -1) {
            NGOSEN_WARN("Cannot write " << path << ": " << std::strerror(errno));
            return false;
        }
        size_t written = 0;
        while (written < content.size()) {
            const ssize_t n = ::write(fd, content.data() + written, content.size() - written);
            if (n > 0)
                written += static_cast<size_t>(n);
            else if (n == 0 || errno != EINTR)
                break;
        }
        const bool ok = written == content.size() && ::fsync(fd) == 0;
        ::close(fd);
        if (!ok || ::rename(temp.c_str(), path.c_str()) != 0) {
            NGOSEN_WARN("Cannot write " << path << ": " << std::strerror(errno));
            ::unlink(temp.c_str());
            return false;
        }
        return true;
    }

    bool prepareSettings(const SettingsPaths& paths, const FileWriter& write) {
        const bool  imported = fileExists(paths.importedMark());
        std::string content;
        if (!imported) {
            const std::pair<std::string, std::string> copies[] = {
                {paths.fcitxDataDir + "/vietnamese.cm.dict", paths.dictionaryFile()},
                {paths.fcitxConfigDir + "/ngosen-macro-table.conf", paths.macroFile()},
                {paths.fcitxConfigDir + "/ngosen-custom-keymap.conf", paths.keymapFile()},
            };
            for (const auto& [from, to] : copies) {
                if (!fileExists(to) && readFile(from, content) && !write(to, content))
                    return false;
            }
        }
        if (!fileExists(paths.settingsFile())) {
            IBusSettings settings = defaultSettings();
            if (!imported && readFile(paths.fcitxConfigDir + "/ngosen.conf", content)) {
                NGOSEN_INFO("Importing the settings of the fcitx5 edition");
                settings = readSettings(parseIni(content));
            }
            if (!write(paths.settingsFile(), settingsText(settings)))
                return false;
        }
        return imported || write(paths.importedMark(), "");
    }

} // namespace ngosen
