/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-program-name.h"

#include "ngosen-flatpak-names.h"
#include "ngosen-ibus-config.h"
#include "ngosen-ibus-i18n.h"

#include <glib.h>

namespace ngosen {

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

    // Read as fcitx5 reads it, which skips a line it cannot read where GKeyFile gives up.
    std::optional<std::string> readStartupWmClass(const std::string& path) {
        gchar* contents = nullptr;
        if (!g_file_get_contents(path.c_str(), &contents, nullptr, nullptr))
            return std::nullopt;
        const IniFile ini = parseIni(contents);
        g_free(contents);
        const auto entry = ini.sections.find("Desktop Entry");
        if (entry == ini.sections.end())
            return std::string();
        const auto wmClass = entry->second.find("StartupWMClass");
        return wmClass == entry->second.end() ? std::string() : trimIni(wmClass->second);
    }

    namespace {

        std::string readName(const std::string& path) {
            GKeyFile*   file = g_key_file_new();
            std::string name;
            if (g_key_file_load_from_file(file, path.c_str(), G_KEY_FILE_NONE, nullptr)) {
                // The engine's text may stay English while the desktop's language is not.
                const char* locale = uiEnglish() ? "en" : nullptr;
                if (gchar* text = g_key_file_get_locale_string(file, G_KEY_FILE_DESKTOP_GROUP, G_KEY_FILE_DESKTOP_KEY_NAME, locale, nullptr)) {
                    name = text;
                    g_free(text);
                }
            }
            g_key_file_free(file);
            return name;
        }

        bool sameName(const std::string& a, const std::string& b) {
            return g_ascii_strcasecmp(a.c_str(), b.c_str()) == 0;
        }

        // X11 apps are known by their WM_CLASS, which a desktop file named after something else declares.
        std::string nameByWmClass(const std::string& program) {
            std::vector<std::string> dirs = {g_get_user_data_dir()};
            for (const gchar* const* dir = g_get_system_data_dirs(); *dir != nullptr; ++dir)
                dirs.emplace_back(*dir);
            for (const auto& dir : dirs) {
                gchar* folder = g_build_filename(dir.c_str(), "applications", nullptr);
                GDir*  list   = g_dir_open(folder, 0, nullptr);
                for (const gchar* entry = list != nullptr ? g_dir_read_name(list) : nullptr; entry != nullptr; entry = g_dir_read_name(list)) {
                    if (!g_str_has_suffix(entry, ".desktop"))
                        continue;
                    gchar*            path = g_build_filename(folder, entry, nullptr);
                    const std::string file = path;
                    g_free(path);
                    const auto wmClass = readStartupWmClass(file);
                    if (wmClass && sameName(*wmClass, program)) {
                        if (std::string name = readName(file); !name.empty()) {
                            g_dir_close(list);
                            g_free(folder);
                            return name;
                        }
                    }
                }
                if (list != nullptr)
                    g_dir_close(list);
                g_free(folder);
            }
            return {};
        }

    } // namespace

    // Not cached, so an app installed during the session shows its name; it runs only when the menu opens.
    std::string appDisplayName(const std::string& program) {
        if (program.empty())
            return {};
        for (const auto& file : desktopFiles(program)) {
            if (std::string name = readName(file); !name.empty())
                return name;
        }
        if (std::string name = nameByWmClass(program); !name.empty())
            return name;
        return program;
    }

    // Not cached, so an app installed during the session is named; this runs once per app switch.
    std::string gnomeProgramName(const std::string& appId) {
        return flatpakProgramName(appId, desktopFiles, readStartupWmClass);
    }

} // namespace ngosen
