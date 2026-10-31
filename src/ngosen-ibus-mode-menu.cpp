/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-mode-menu.h"

#include "ngosen-ibus-keys.h"

#include <glib/gi18n-lib.h>
#include <ibus.h>

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

    } // namespace

    std::vector<MenuItem> modeMenuItems(const IBusSettings& settings) {
        return {
            {MenuMode::Sen, _("Sen"), ibus_keyval_from_name(settings.shortcutSen.c_str())},
            {MenuMode::Preedit, _("Preedit"), ibus_keyval_from_name(settings.shortcutPreedit.c_str())},
            {MenuMode::English, _("English"), ibus_keyval_from_name(settings.shortcutOff.c_str())},
        };
    }

    bool opensModeMenu(const IBusSettings& settings, guint keyval, guint state) {
        return (state & IBUS_RELEASE_MASK) == 0 && matchesAny(settings.modeMenuKeys, keyval, state);
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
            gchar* label = g_strdup_printf("%s.", ibus_keyval_name(items[i].key));
            ibus_lookup_table_set_label(table, i, ibus_text_new_from_string(label));
            g_free(label);
        }
        return table;
    }

} // namespace ngosen
