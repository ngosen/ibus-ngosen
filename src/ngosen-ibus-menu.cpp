/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-menu.h"

#include <algorithm>
#include <glib/gi18n-lib.h>
#include <iterator>
#include <vector>

namespace ngosen {

    namespace {

        struct Toggle {
            const char* key;
            const char* label;
            bool (*isOn)(const IBusSettings&);
        };

        const Toggle        DirectTyping     = {"DirectTyping", N_("Type with Sen where the app allows (experimental)"), [](const IBusSettings& s) { return s.directTyping; }};
        const Toggle        SpellCheck       = {"SpellCheck", N_("Spell Check"), [](const IBusSettings& s) { return s.options.spellCheck; }};
        const Toggle        Macro            = {"EnableMacro", N_("Macro"), [](const IBusSettings& s) { return s.options.enableMacro; }};
        const Toggle        CapitalizeMacro  = {"CapitalizeMacro", N_("Capitalize Macro"), [](const IBusSettings& s) { return s.options.capitalizeMacro; }};
        const Toggle        AfterPunctuation = {"AutoCapitalizeAfterPunctuation", N_("After . ! ? and Enter"),
                                                [](const IBusSettings& s) { return s.options.autoCapitalizeAfterPunctuation; }};
        const Toggle        StartOfText      = {"CapitalizeStartOfText", N_("Start of text or line"), [](const IBusSettings& s) { return s.options.capitalizeStartOfText; }};
        const Toggle        Restore          = {"AutoNonVnRestore", N_("Auto Restore Invalid Words"), [](const IBusSettings& s) { return s.options.autoNonVnRestore; }};
        const Toggle        Dictionary       = {"EnableDictionary", N_("Custom Dictionary"), [](const IBusSettings& s) { return s.enableDictionary; }};

        const Toggle* const Toggles[] = {&DirectTyping, &SpellCheck, &Macro, &CapitalizeMacro, &AfterPunctuation, &StartOfText, &Restore, &Dictionary};

        // The two methods most people switch between, as in the fcitx5 edition; the rest stay in
        // the settings window.
        const std::vector<std::string> MenuInputMethods = {"Telex", "VNI"};

        IBusProperty*                  newItem(const std::string& key, IBusPropType type, const char* label, bool checked = false, IBusPropList* items = nullptr) {
            return ibus_property_new(key.c_str(), type, ibus_text_new_from_string(label), nullptr, nullptr, TRUE, TRUE, checked ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, items);
        }

        IBusProperty* newToggle(const Toggle& toggle, const IBusSettings& settings) {
            return newItem(toggle.key, PROP_TYPE_TOGGLE, _(toggle.label), toggle.isOn(settings));
        }

        IBusProperty* newChoice(const std::string& key, const char* label, const std::vector<std::string>& names, const std::string& current) {
            IBusPropList* items = ibus_prop_list_new();
            for (const auto& name : names)
                ibus_prop_list_append(items, newItem(key + '/' + name, PROP_TYPE_RADIO, name.c_str(), name == current));
            return newItem(key, PROP_TYPE_MENU, label, false, items);
        }

        bool contains(const std::vector<std::string>& list, const std::string& value) {
            return std::find(list.begin(), list.end(), value) != list.end();
        }

    } // namespace

    IBusPropList* newSettingsMenu(const IBusSettings& settings) {
        IBusPropList* menu = ibus_prop_list_new();
        ibus_prop_list_append(menu, newChoice("InputMethod", _("Input Method"), MenuInputMethods, settings.options.inputMethod));
        ibus_prop_list_append(menu, newToggle(DirectTyping, settings));
        ibus_prop_list_append(menu, newChoice("OutputCharset", _("Charset"), charsetNames(), settings.options.outputCharset));
        ibus_prop_list_append(menu, newToggle(SpellCheck, settings));
        ibus_prop_list_append(menu, newToggle(Macro, settings));
        ibus_prop_list_append(menu, newToggle(CapitalizeMacro, settings));
        IBusPropList* capitalize = ibus_prop_list_new();
        ibus_prop_list_append(capitalize, newToggle(AfterPunctuation, settings));
        ibus_prop_list_append(capitalize, newToggle(StartOfText, settings));
        ibus_prop_list_append(menu, newItem("AutoCapitalize", PROP_TYPE_MENU, _("Auto Capitalize"), false, capitalize));
        ibus_prop_list_append(menu, newToggle(Restore, settings));
        ibus_prop_list_append(menu, newToggle(Dictionary, settings));
        ibus_prop_list_append(menu, newItem(SettingsWindowItem, PROP_TYPE_NORMAL, _("Settings")));
        return menu;
    }

    bool settingForClick(const std::string& name, bool checked, std::string& key, std::string& value) {
        if (const auto slash = name.find('/'); slash != std::string::npos) {
            key   = name.substr(0, slash);
            value = name.substr(slash + 1);
            if (key == "InputMethod")
                return checked && contains(MenuInputMethods, value);
            return key == "OutputCharset" && checked && contains(charsetNames(), value);
        }
        const auto toggle = std::find_if(std::begin(Toggles), std::end(Toggles), [&name](const Toggle* t) { return name == t->key; });
        if (toggle == std::end(Toggles))
            return false;
        key   = name;
        value = checked ? "True" : "False";
        return true;
    }

} // namespace ngosen
