/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-mode-menu.h"
#include "ngosen-ibus-i18n.h"

#include "ngosen-ibus-keys.h"

#include <ibus.h>
#include <algorithm>
#include <sstream>
#include <string_view>

namespace ngosen {

    namespace {

        constexpr guint CommandModifiers = IBUS_CONTROL_MASK | IBUS_MOD1_MASK | IBUS_MOD4_MASK | IBUS_SUPER_MASK | IBUS_META_MASK;

        bool            matchesAny(const std::vector<std::string>& keys, guint keyval, guint state) {
            for (const auto& key : keys) {
                if (const auto chord = parseMenuKey(key); chord && matchesKey(*chord, keyval, state))
                    return true;
            }
            return false;
        }

        // VIQR puts tones on ` and ~, so a menu on those keys would take them from every word.
        bool typesWithKey(const IBusSettings& settings, const std::vector<KeymapEntry>& keymap, guint keyval) {
            const gunichar ch = ibus_keyval_to_unicode(keyval);
            if (ch == 0 || ch > 0x7f)
                return false;
            const std::string text(1, static_cast<char>(ch));
            if (settings.options.inputMethod.find("VIQR") != std::string::npos && std::string_view("0'`?~.^+*(d").find(text) != std::string_view::npos)
                return true;
            for (const auto& entry : keymap) {
                if (entry.key == text)
                    return true;
            }
            return false;
        }

        std::vector<MenuItem> shownModes(const IBusSettings& settings, bool withUnlisted, bool vimOn) {
            struct Known {
                const char* name;
                MenuItem    item;
                bool        shown;
            };
            const auto  key     = [](const std::string& name) { return ibus_keyval_from_name(name.c_str()); };
            const Known known[] = {
                {"Sen", {MenuMode::Sen, _("Sen"), key(settings.shortcutSen)}, settings.showModeSen},
                {"Preedit", {MenuMode::Preedit, _("Preedit"), key(settings.shortcutPreedit)}, settings.showModePreedit},
                {"Off", {MenuMode::Off, _("OFF"), key(settings.shortcutOff)}, settings.showModeOff},
                {"Vim", {MenuMode::Vim, vimOn ? _("Vim mode: on") : _("Vim mode: off"), key(settings.shortcutVim)}, settings.showModeVim},
            };
            std::vector<const Known*> ordered;
            const auto                add = [&ordered](const Known& entry) {
                if (std::find(ordered.begin(), ordered.end(), &entry) == ordered.end())
                    ordered.push_back(&entry);
            };
            std::istringstream names(settings.modeOrder);
            for (std::string name; std::getline(names, name, ',');) {
                for (const auto& entry : known) {
                    if (trimIni(name) == entry.name)
                        add(entry);
                }
            }
            if (withUnlisted) {
                for (const auto& entry : known)
                    add(entry);
            }
            std::vector<MenuItem> items;
            for (const Known* entry : ordered) {
                if (entry->shown)
                    items.push_back(entry->item);
            }
            return items;
        }

    } // namespace

    std::vector<MenuItem> modeMenuItems(const IBusSettings& settings, bool vimOn) {
        std::vector<MenuItem> items = shownModes(settings, true, vimOn);
        for (auto item = items.begin(); item != items.end(); ++item) {
            if (std::any_of(items.begin(), item, [&](const MenuItem& other) { return other.key == item->key; }))
                item->key = IBUS_KEY_VoidSymbol;
        }
        return items;
    }

    std::vector<MenuMode> cycleMenuModes(const IBusSettings& settings) {
        std::vector<MenuMode> modes;
        for (const auto& item : shownModes(settings, false, false)) {
            if (item.mode != MenuMode::Vim)
                modes.push_back(item.mode);
        }
        return modes;
    }

    bool cyclesMode(const IBusSettings& settings, guint keyval, guint state) {
        return (state & IBUS_RELEASE_MASK) == 0 && matchesAny(settings.cycleModeKeys, keyval, state);
    }

    bool opensModeMenu(const IBusSettings& settings, const std::vector<KeymapEntry>& keymap, guint keyval, guint state) {
        return (state & IBUS_RELEASE_MASK) == 0 && matchesAny(settings.modeMenuKeys, keyval, state) && !typesWithKey(settings, keymap, keyval);
    }

    MenuKey menuKey(const IBusSettings& settings, guint keyval, guint state) {
        switch (keyval) {
            case IBUS_KEY_Escape: return {MenuKey::Close};
            case IBUS_KEY_Up:
            case IBUS_KEY_ISO_Left_Tab: return {MenuKey::Up};
            case IBUS_KEY_Down:
            case IBUS_KEY_Tab: return {MenuKey::Down};
            case IBUS_KEY_space:
            case IBUS_KEY_Return:
            case IBUS_KEY_KP_Enter: return {MenuKey::PickCursor};
            default: break;
        }
        if ((state & CommandModifiers) == 0) {
            for (const auto& item : modeMenuItems(settings)) {
                if (item.key != IBUS_KEY_VoidSymbol && ibus_keyval_to_lower(keyval) == item.key)
                    return {MenuKey::Pick, item.mode};
            }
        }
        // As in the fcitx5 edition: the menu key again types itself, since ` is common in code.
        if (matchesAny(settings.modeMenuKeys, keyval, state))
            return {MenuKey::TypeMenuKey};
        return {MenuKey::Swallow};
    }

    IBusLookupTable* newModeMenuTable(const std::vector<MenuItem>& items, guint cursor) {
        IBusLookupTable* table = ibus_lookup_table_new(static_cast<guint>(items.size()), cursor, TRUE, TRUE);
        ibus_lookup_table_set_orientation(table, IBUS_ORIENTATION_VERTICAL);
        for (guint i = 0; i < items.size(); ++i) {
            ibus_lookup_table_append_candidate(table, ibus_text_new_from_string(items[i].label.c_str()));
            // A key an earlier item took shows no label, as in fcitx5.
            gchar* label = items[i].key == IBUS_KEY_VoidSymbol ? g_strdup("") : g_strdup_printf("%s.", ibus_keyval_name(items[i].key));
            ibus_lookup_table_set_label(table, i, ibus_text_new_from_string(label));
            g_free(label);
        }
        return table;
    }

} // namespace ngosen
