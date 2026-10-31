/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-keys.h"

#include <ibus.h>

namespace ngosen {

    namespace {

        constexpr guint HeldModifiers = IBUS_SHIFT_MASK | IBUS_CONTROL_MASK | IBUS_MOD1_MASK | IBUS_SUPER_MASK | IBUS_HYPER_MASK;

        // The US layout puts Meta on the second level of Alt, so Shift then Alt arrives as Meta.
        guint canonicalKey(guint keyval) {
            switch (keyval) {
                case IBUS_KEY_Meta_L: return IBUS_KEY_Alt_L;
                case IBUS_KEY_Meta_R: return IBUS_KEY_Alt_R;
                default: return ibus_keyval_to_lower(keyval);
            }
        }

        // The modifier a key itself sets, so releasing Shift_L is not read as Shift held.
        guint ownModifier(guint keyval) {
            switch (canonicalKey(keyval)) {
                case IBUS_KEY_Shift_L:
                case IBUS_KEY_Shift_R: return IBUS_SHIFT_MASK;
                case IBUS_KEY_Control_L:
                case IBUS_KEY_Control_R: return IBUS_CONTROL_MASK;
                case IBUS_KEY_Alt_L:
                case IBUS_KEY_Alt_R: return IBUS_MOD1_MASK;
                case IBUS_KEY_Super_L:
                case IBUS_KEY_Super_R: return IBUS_SUPER_MASK;
                default: return 0;
            }
        }

        // GNOME reports Super as Mod4, while "Super+space" parses to the Super bit. GTK 4 reports
        // the Meta bit beside the Mod1 of Alt.
        guint heldModifiers(guint state) {
            if ((state & IBUS_MOD4_MASK) != 0)
                state |= IBUS_SUPER_MASK;
            if ((state & IBUS_META_MASK) != 0)
                state |= IBUS_MOD1_MASK;
            return state & HeldModifiers;
        }

    } // namespace

    const std::vector<std::string>& defaultToggleKeys() {
        static const std::vector<std::string> keys = {"Control+Shift_L", "Control+Shift_R", "Shift+Control_L", "Shift+Control_R"};
        return keys;
    }

    const std::vector<std::string>& defaultModeMenuKeys() {
        static const std::vector<std::string> keys = {"grave"};
        return keys;
    }

    std::optional<KeyChord> parseToggleKey(const std::string& text) {
        KeyChord chord;
        if (!ibus_key_event_from_string(text.c_str(), &chord.keyval, &chord.modifiers) || chord.keyval == IBUS_KEY_VoidSymbol)
            return std::nullopt;
        chord.modifiers = heldModifiers(chord.modifiers) & ~ownModifier(chord.keyval);
        if (chord.modifiers == 0)
            return std::nullopt;
        // fcitx5 matches letters whatever their case, so "Alt+Z" is Alt with the z key.
        chord.keyval = canonicalKey(chord.keyval);
        return chord;
    }

    std::optional<KeyChord> parseMenuKey(const std::string& text) {
        KeyChord chord;
        if (!ibus_key_event_from_string(text.c_str(), &chord.keyval, &chord.modifiers) || chord.keyval == IBUS_KEY_VoidSymbol || ownModifier(chord.keyval) != 0)
            return std::nullopt;
        chord.modifiers = heldModifiers(chord.modifiers);
        chord.keyval    = canonicalKey(chord.keyval);
        return chord;
    }

    bool otherModifierHeld(guint keyval, guint state) {
        return (heldModifiers(state) & ~ownModifier(keyval)) != 0;
    }

    bool matchesKey(const KeyChord& chord, guint keyval, guint state) {
        return canonicalKey(keyval) == chord.keyval && (heldModifiers(state) & ~ownModifier(keyval)) == chord.modifiers;
    }

} // namespace ngosen
