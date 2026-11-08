/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-program-name.h"

#include "ngosen-flatpak-names.h"

#include <glib.h>
#include <sstream>
#include <unordered_map>

namespace ngosen {

    namespace {
        std::string trimmed(const std::string& text) {
            const char*  space = " \t\r";
            const size_t first = text.find_first_not_of(space);
            if (first == std::string::npos)
                return {};
            return text.substr(first, text.find_last_not_of(space) - first + 1);
        }

        // fcitx5 unescapes a value only when it is quoted, and skips the line when that fails.
        std::optional<std::string> iniValue(const std::string& raw) {
            if (raw.size() < 2 || raw.front() != '"' || raw.back() != '"')
                return raw;
            std::string value;
            for (size_t i = 1; i + 1 < raw.size(); ++i) {
                char c = raw[i];
                if (c == '"')
                    return std::nullopt;
                if (c == '\\') {
                    if (i + 2 >= raw.size())
                        return std::nullopt;
                    switch (raw[++i]) {
                        case 'n': c = '\n'; break;
                        case 't': c = '\t'; break;
                        case 'r': c = '\r'; break;
                        case 'f': c = '\f'; break;
                        case 'v': c = '\v'; break;
                        case '\\': c = '\\'; break;
                        case '"': c = '"'; break;
                        default: return std::nullopt;
                    }
                }
                value += c;
            }
            return value;
        }
    } // namespace

    std::vector<std::string> desktopFiles(const std::string& appId) {
        const std::string        file = "applications/" + appId + ".desktop";
        std::vector<std::string> found;
        const auto               add = [&](const char* dir) {
            gchar* path = g_build_filename(dir, file.c_str(), nullptr);
            if (g_file_test(path, G_FILE_TEST_EXISTS))
                found.emplace_back(path);
            g_free(path);
        };
        add(g_get_user_data_dir());
        for (const gchar* const* dir = g_get_system_data_dirs(); *dir != nullptr; ++dir)
            add(*dir);
        return found;
    }

    // Line by line like fcitx5's ini reader, which skips a line it cannot read where GKeyFile gives up.
    std::optional<std::string> readStartupWmClass(const std::string& path) {
        gchar* contents = nullptr;
        if (!g_file_get_contents(path.c_str(), &contents, nullptr, nullptr))
            return std::nullopt;
        std::istringstream lines(contents);
        g_free(contents);
        std::string line;
        std::string group;
        std::string wmClass;
        while (std::getline(lines, line)) {
            line = trimmed(line);
            if (line.empty() || line[0] == '#')
                continue;
            if (line.front() == '[' && line.back() == ']') {
                group = line.substr(1, line.size() - 2);
                continue;
            }
            const size_t equals = line.find('=');
            if (equals == std::string::npos || group != "Desktop Entry" || line.compare(0, equals, "StartupWMClass") != 0)
                continue;
            if (const auto value = iniValue(line.substr(equals + 1)))
                wmClass = trimmed(*value);
        }
        return wmClass;
    }

    std::string gnomeProgramName(const std::string& appId) {
        static std::unordered_map<std::string, std::string> names;
        auto                                                it = names.find(appId);
        if (it == names.end())
            it = names.emplace(appId, flatpakProgramName(appId, desktopFiles, readStartupWmClass)).first;
        return it->second;
    }

} // namespace ngosen
