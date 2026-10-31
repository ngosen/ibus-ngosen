/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-engine.h"

#include "ngosen-globals.h"
#include "ngosen-ibus-host.h"
#include "ngosen-ibus-keys.h"
#include "ngosen-ibus-menu.h"
#include "ngosen-ibus-resources.h"
#include "ngosen-ibus-typing-log.h"
#include "ngosen-log.h"
#include "ngosen-pointer.h"
#include "ngosen-state.h"

#include <glib/gi18n-lib.h>
#include <algorithm>
#include <atomic>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <string>

namespace {

    ngosen::IBusResources& resources() {
        static ngosen::IBusResources instance(ngosen::SettingsPaths::fromEnvironment());
        return instance;
    }

    // What the toggle key last chose, shared by every field as in the fcitx5 edition.
    bool englishOn = false;

    // Off, every word goes into the preedit; on, the core picks for each word whether it goes
    // straight into the field or into the preedit.
    ngosen::Mode typingMode() {
        if (englishOn)
            return ngosen::Mode::Off;
        return resources().settings().directTyping ? ngosen::Mode::Sen : ngosen::Mode::Preedit;
    }

    const std::vector<ngosen::KeyChord>& toggleChords() {
        static std::vector<ngosen::KeyChord> chords;
        static unsigned                      generation = ~0U;
        if (generation != resources().generation()) {
            chords.clear();
            for (const auto& key : resources().settings().toggleKeys) {
                if (const auto chord = ngosen::parseToggleKey(key))
                    chords.push_back(*chord);
            }
            generation = resources().generation();
        }
        return chords;
    }

    bool isToggleKey(guint keyval, guint state) {
        const auto& chords = toggleChords();
        return std::any_of(chords.begin(), chords.end(), [&](const ngosen::KeyChord& chord) { return ngosen::matchesKey(chord, keyval, state); });
    }

    // A tap of a modifier-only key such as Ctrl+Shift toggles once every modifier is up, as in the
    // fcitx5 edition, so Ctrl+Shift+T or Ctrl+Shift then Ctrl+V does not. A key with a letter such as
    // Alt+Z toggles on its first press, and the app sees neither its press nor its release.
    struct ToggleTap {
        bool     armed        = false;
        bool     pending      = false;
        gint64   since        = 0;
        unsigned clicks       = 0;
        guint    swallowedKey = 0;
    };

    // Longer than this is a hold, such as Ctrl+Shift with a click.
    constexpr gint64 TapMicroseconds = 500000;

    // Counted by the X11 click watcher, so a click between the keys of a tap cancels it.
    std::atomic<unsigned> clicksSeen{0};

    struct Session {
        ngosen::IBusHost*                    host = nullptr;
        std::unique_ptr<ngosen::TypingState> state;
        unsigned                             generation = 0;
        ToggleTap                            tap;
        bool                                 showsLanguage = false;

        // Only between words: a new engine would drop the word being typed.
        void applyNewSettings() {
            if (host->hasPreedit())
                return;
            resources().reloadIfChanged();
            if (generation == resources().generation())
                return;
            realMode = typingMode();
            host->setDirectTyping(realMode == ngosen::Mode::Sen);
            state->setEngine();
            generation = resources().generation();
        }
    };

} // namespace

struct NgoSenEngine {
    IBusEngine parent;
    Session*   session;
};

struct NgoSenEngineClass {
    IBusEngineClass parent;
};

G_DEFINE_TYPE(NgoSenEngine, ngosen_engine, IBUS_TYPE_ENGINE)

namespace {

    Session* sessionOf(IBusEngine* engine) {
        return reinterpret_cast<NgoSenEngine*>(engine)->session;
    }

    void showLanguage(IBusEngine* engine) {
        IBusText* text = ibus_text_new_from_string(englishOn ? _("English") : _("Vietnamese"));
        ibus_engine_update_auxiliary_text(engine, text, TRUE);
    }

    void showMenu(IBusEngine* engine, const ngosen::IBusSettings& settings, bool clicked = false);
    void showLanguageItem(IBusEngine* engine);

    void toggleLanguage(IBusEngine* engine, Session& session) {
        // The word ends in the mode it was typed in, and the core drops what it held for it.
        session.state->commitBuffer();
        session.state->resetAfterAppCommit(false);
        englishOn = !englishOn;
        ngosen::saveEnglishOn(resources().paths(), englishOn);
        realMode = typingMode();
        session.host->setDirectTyping(realMode == ngosen::Mode::Sen);
        // As on focus-in: the per-field checks of Sen start over.
        if (realMode == ngosen::Mode::Sen)
            session.state->activate(ngosen::Mode::Sen, true);
        NGOSEN_INFO("Toggle key: " << (englishOn ? "English" : "Vietnamese"));
        showLanguageItem(engine);
        showLanguage(engine);
        session.showsLanguage = true;
    }

    // True when the app must not see this key.
    bool handleToggleKey(IBusEngine* engine, Session& session, guint keyval, guint state) {
        ToggleTap& tap      = session.tap;
        const bool release  = (state & IBUS_RELEASE_MASK) != 0;
        const bool modifier = ngosen::IBusKeyPress(keyval, 0, state).isModifier();
        if (release && tap.swallowedKey != 0 && ibus_keyval_to_lower(keyval) == tap.swallowedKey) {
            tap.swallowedKey = 0;
            return true;
        }
        if (!release && !modifier) {
            tap.armed = tap.pending = false;
            if (!isToggleKey(keyval, state))
                return false;
            // A held chord repeats; only its first press switches.
            if (tap.swallowedKey != ibus_keyval_to_lower(keyval))
                toggleLanguage(engine, session);
            tap.swallowedKey = ibus_keyval_to_lower(keyval);
            return true;
        }
        if (!modifier)
            return false;
        if (!release) {
            // Nothing else held means every key went up, even if a grab ate the last release.
            if (tap.pending && ngosen::otherModifierHeld(keyval, state))
                return false;
            tap.pending = false;
            // A held key repeats; the hold counts from the first press.
            const bool matched = isToggleKey(keyval, state);
            if (matched && !tap.armed) {
                tap.since  = g_get_monotonic_time();
                tap.clicks = clicksSeen.load(std::memory_order_acquire);
            }
            tap.armed = matched;
            return false;
        }
        // The hold ends at the toggle key itself; the other modifier may come up later.
        if (tap.armed && isToggleKey(keyval, state)) {
            tap.armed   = false;
            tap.pending = g_get_monotonic_time() - tap.since <= TapMicroseconds;
        }
        if (tap.pending && !ngosen::otherModifierHeld(keyval, state)) {
            tap.pending = false;
            if (clicksSeen.load(std::memory_order_acquire) == tap.clicks)
                toggleLanguage(engine, session);
        }
        return false;
    }

    bool isPlainEnter(guint keyval, guint state) {
        constexpr guint modifiers = IBUS_SHIFT_MASK | IBUS_CONTROL_MASK | IBUS_MOD1_MASK | IBUS_MOD4_MASK | IBUS_SUPER_MASK | IBUS_RELEASE_MASK;
        return (keyval == IBUS_KEY_Return || keyval == IBUS_KEY_KP_Enter) && (state & modifiers) == 0;
    }

    gboolean processKeyEvent(IBusEngine* engine, guint keyval, guint keycode, guint state) {
        Session* session = sessionOf(engine);
        if (session == nullptr)
            return FALSE;
        session->applyNewSettings();
        // Shown until the next key typed, not the release of the toggle key itself.
        if (session->showsLanguage && (state & IBUS_RELEASE_MASK) == 0 && !ngosen::IBusKeyPress(keyval, keycode, state).isModifier()) {
            ibus_engine_hide_auxiliary_text(engine);
            session->showsLanguage = false;
        }
        // A password is sent as typed, the way fcitx5 turns input methods off in password fields.
        if (session->host->takesPassword()) {
            session->tap = {};
            return FALSE;
        }
        if (handleToggleKey(engine, *session, keyval, state))
            return TRUE;
        // The word goes out before Enter, so the core has nothing to commit and lets Enter through
        // instead of holding it back and forwarding it, which GNOME 50.0-50.3 drop.
        if (isPlainEnter(keyval, state) && session->host->hasPreedit())
            session->state->commitBuffer();
        // Apps that send no reset on a click (XIM clients) still show the preedit, which the core would drop.
        else if (session->host->hasPreedit() && g_mouse_clicked.load(std::memory_order_acquire))
            session->state->commitBuffer();
        ngosen::IBusKeyPress key(keyval, keycode, state);
        session->state->keyEvent(key);
        if (key.accepted())
            return TRUE;
        // IBus cannot change a key it lets through, so the changed key goes out on its own.
        if (const uint32_t sym = key.replacedSym()) {
            ibus_engine_forward_key_event(engine, sym, keycode, state);
            return TRUE;
        }
        return FALSE;
    }

    void updateItems(IBusEngine* engine, IBusPropList* items) {
        for (guint i = 0; IBusProperty* item = ibus_prop_list_get(items, i); ++i) {
            ibus_engine_update_property(engine, item);
            updateItems(engine, ibus_property_get_sub_props(item));
        }
    }

    std::string itemStates(IBusPropList* items) {
        std::string states;
        for (guint i = 0; IBusProperty* item = ibus_prop_list_get(items, i); ++i) {
            states += ibus_property_get_key(item);
            states += ibus_property_get_state(item) == PROP_STATE_CHECKED ? "+" : "-";
            states += itemStates(ibus_property_get_sub_props(item));
        }
        return states;
    }

    // What the panel was last told, the same for every engine since the settings are shared.
    std::string shownStates;

    // clicked: the panel already flipped the item itself, so its state goes out even when unchanged.
    void showMenu(IBusEngine* engine, const ngosen::IBusSettings& settings, bool clicked) {
        IBusPropList* menu = ngosen::newSettingsMenu(settings, englishOn);
        g_object_ref_sink(menu);
        ibus_engine_register_properties(engine, menu);
        // GNOME Shell takes the whole menu only once after the engine is chosen, then single items.
        // It rebuilds the menu on each item, so resending them on every focus change stalls it (#28).
        std::string states = itemStates(menu);
        if (clicked || states != shownStates) {
            updateItems(engine, menu);
            shownStates = std::move(states);
        }
        g_object_unref(menu);
    }

    // Only the language item changed; the whole menu would stall GNOME Shell for a second, and the
    // keys typed meanwhile reach the core in one burst.
    void showLanguageItem(IBusEngine* engine) {
        IBusPropList* menu = ngosen::newSettingsMenu(resources().settings(), englishOn);
        g_object_ref_sink(menu);
        ibus_engine_register_properties(engine, menu);
        for (guint i = 0; IBusProperty* item = ibus_prop_list_get(menu, i); ++i) {
            if (g_strcmp0(ibus_property_get_key(item), ngosen::InputModeItem) == 0)
                ibus_engine_update_property(engine, item);
        }
        shownStates = itemStates(menu);
        g_object_unref(menu);
    }

    // The panel shows this engine's menu, which a change from the settings window updates at once.
    IBusEngine* focusedEngine = nullptr;

    void        showNewSettings() {
        if (focusedEngine == nullptr)
            return;
        if (Session* session = sessionOf(focusedEngine))
            session->applyNewSettings();
        showMenu(focusedEngine, resources().settings());
    }

    void focusIn(IBusEngine* engine) {
        static bool watching = false;
        if (!watching) {
            resources().onChange(showNewSettings);
            watching = true;
        }
        focusedEngine = engine;
        if (Session* session = sessionOf(engine)) {
            session->host->setFocus(true);
            session->applyNewSettings();
            // With use-global-engine off each field has its own engine, and the toggle key may have switched elsewhere.
            session->host->setDirectTyping(realMode == ngosen::Mode::Sen);
            // The per-field checks of Sen start over, as the fcitx5 frontend does on focus-in.
            if (realMode == ngosen::Mode::Sen)
                session->state->activate(ngosen::Mode::Sen, true);
        }
        showMenu(engine, resources().settings());
    }

    void propertyActivate(IBusEngine* engine, const gchar* name, guint state) {
        if (g_strcmp0(name, ngosen::SettingsWindowItem) == 0) {
            gchar*  argv[] = {const_cast<gchar*>(NGOSEN_SETUP_EXEC), nullptr}; //NOLINT
            GError* error  = nullptr;
            if (!g_spawn_async(nullptr, argv, nullptr, G_SPAWN_DEFAULT, nullptr, nullptr, nullptr, &error)) {
                NGOSEN_WARN("Cannot open the settings window: " << error->message);
                g_error_free(error);
            }
            return;
        }
        if (g_strcmp0(name, ngosen::SaveTypingLogItem) == 0) {
            ngosen::saveTypingLog(resources().recorder());
            return;
        }
        if (g_strcmp0(name, ngosen::InputModeItem) == 0) {
            // Checked means Vietnamese; a click that asks for the language in use changes nothing.
            if (Session* session = sessionOf(engine); session != nullptr && (state == PROP_STATE_CHECKED) == englishOn)
                toggleLanguage(engine, *session);
            return;
        }
        std::string key;
        std::string value;
        if (name == nullptr || !ngosen::settingForClick(name, state == PROP_STATE_CHECKED, key, value))
            return;
        ngosen::IBusSettings saved;
        // A failed write shows the old state again, so the menu never claims a setting that is not saved.
        showMenu(engine, resources().saveSetting(key, value, saved) ? saved : resources().settings(), true);
    }

    void focusOut(IBusEngine* engine) {
        if (focusedEngine == engine)
            focusedEngine = nullptr;
        Session* session = sessionOf(engine);
        if (session == nullptr)
            return;
        session->tap = {};
        session->state->resetAfterAppCommit(true);
        session->host->setFocus(false);
        session->host->forgetReportedText();
    }

    void focusInId(IBusEngine* engine, const gchar* /*objectPath*/, const gchar* client) {
        if (Session* session = sessionOf(engine))
            session->host->setClient(client != nullptr ? client : "");
        NGOSEN_INFO("Focus in: " << (client != nullptr ? client : ""));
        focusIn(engine);
    }

    void focusOutId(IBusEngine* engine, const gchar* /*objectPath*/) {
        focusOut(engine);
    }

    // A click in the field or a change the app made itself; the app has committed the preedit. A
    // sentence begun with Enter, which also resets GTK fields, still capitalizes.
    void reset(IBusEngine* engine) {
        Session* session = sessionOf(engine);
        if (session == nullptr)
            return;
        // Firefox on X11 resets after every key it is let through. As in the fcitx5 edition, a word typed
        // straight in survives that while the engine sees clicks itself.
        const ngosen::IBusHost& host = *session->host;
        // Where the engine watches clicks, a reset during a tap is the app's own and the tap goes on.
        if (!ngosen::clicksWatched.load(std::memory_order_acquire))
            session->tap = {};
        if (ngosen::clicksWatched.load(std::memory_order_acquire) && host.typesWithKeysBesideText() && !host.hasPreedit() && !session->state->isEmptyHistory())
            return;
        session->state->resetAfterAppCommit(false);
    }

    void disable(IBusEngine* engine) {
        focusOut(engine);
    }

    void setSurroundingText(IBusEngine* engine, IBusText* text, guint cursor, guint anchor) {
        IBUS_ENGINE_CLASS(ngosen_engine_parent_class)->set_surrounding_text(engine, text, cursor, anchor);
        if (Session* session = sessionOf(engine)) {
            session->host->setReportedText(ibus_text_get_text(text), cursor, anchor);
            session->state->surroundingUpdated();
        }
    }

    void setContentType(IBusEngine* engine, guint purpose, guint hints) {
        IBUS_ENGINE_CLASS(ngosen_engine_parent_class)->set_content_type(engine, purpose, hints);
        NGOSEN_DEBUG("Content type: purpose " << purpose << ", hints " << hints);
        if (Session* session = sessionOf(engine))
            session->host->setContentType(purpose, hints);
    }

    void destroy(IBusObject* object) {
        auto* self = reinterpret_cast<NgoSenEngine*>(object);
        if (focusedEngine == &self->parent)
            focusedEngine = nullptr;
        delete self->session;
        self->session = nullptr;
        IBUS_OBJECT_CLASS(ngosen_engine_parent_class)->destroy(object);
    }

    // The factory's own engines never get focus_in_id, which names the app. GNOME Shell sends the text
    // around the cursor only after a request, which active-surrounding-text makes IBus send on each focus-in.
    IBusEngine* createEngine(IBusFactory* factory, const gchar* name, gpointer /*data*/) {
        static guint id     = 0;
        gchar*       path   = g_strdup_printf("/org/freedesktop/IBus/Engine/NgoSen/%u", ++id);
        auto*        engine = IBUS_ENGINE(g_object_new(ngosen_engine_get_type(), "engine-name", name, "object-path", path, "connection",
                                                       ibus_service_get_connection(IBUS_SERVICE(factory)), "has-focus-id", TRUE, "active-surrounding-text", TRUE, nullptr));
        g_free(path);
        return engine;
    }

} // namespace

static void ngosen_engine_class_init(NgoSenEngineClass* klass) {
    auto* engineClass                 = IBUS_ENGINE_CLASS(klass);
    engineClass->process_key_event    = processKeyEvent;
    engineClass->focus_in             = focusIn;
    engineClass->focus_out            = focusOut;
    engineClass->reset                = reset;
    engineClass->disable              = disable;
    engineClass->set_surrounding_text = setSurroundingText;
    engineClass->set_content_type     = setContentType;
    engineClass->focus_in_id          = focusInId;
    engineClass->focus_out_id         = focusOutId;
    engineClass->property_activate    = propertyActivate;
    IBUS_OBJECT_CLASS(klass)->destroy = destroy;
}

static void ngosen_engine_init(NgoSenEngine* self) {
    auto  host          = std::make_unique<ngosen::IBusHost>(IBUS_ENGINE(self));
    auto* session       = new Session;
    session->host       = host.get();
    session->state      = std::make_unique<ngosen::TypingState>(&resources(), std::move(host));
    session->generation = resources().generation();
    // A settings change seen by no engine yet still reaches the new one.
    realMode = typingMode();
    session->host->setDirectTyping(realMode == ngosen::Mode::Sen);
    self->session = session;
}

namespace ngosen {

    void addEngine(IBusFactory* factory) {
        englishOn = readEnglishOn(resources().paths());
        realMode  = typingMode();
        ibus_factory_add_engine(factory, "ngosen", ngosen_engine_get_type());
        g_signal_connect(factory, "create-engine", G_CALLBACK(createEngine), nullptr);
    }

    std::thread watchClicks(const std::atomic<bool>& stop) {
        // On Wayland the X server sees clicks on X11 windows only, and a missed click would let a
        // reset be ignored after the cursor moved.
        const char* wayland = std::getenv("WAYLAND_DISPLAY");
        const char* session = std::getenv("XDG_SESSION_TYPE");
        if ((wayland != nullptr && *wayland != 0) || (session != nullptr && std::strcmp(session, "wayland") == 0))
            return {};
        return std::thread([&stop] {
            clicksWatched.store(true, std::memory_order_release);
            watchX11PointerClicks(stop, [] {
                needEngineReset.store(true, std::memory_order_release);
                g_mouse_clicked.store(true, std::memory_order_release);
                clicksSeen.fetch_add(1, std::memory_order_acq_rel);
            });
            clicksWatched.store(false, std::memory_order_release);
        });
    }

} // namespace ngosen
