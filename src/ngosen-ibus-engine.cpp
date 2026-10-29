/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-engine.h"

#include "ngosen-globals.h"
#include "ngosen-ibus-host.h"
#include "ngosen-ibus-menu.h"
#include "ngosen-ibus-resources.h"
#include "ngosen-ibus-typing-log.h"
#include "ngosen-log.h"
#include "ngosen-state.h"

#include <memory>

namespace {

    ngosen::IBusResources& resources() {
        static ngosen::IBusResources instance(ngosen::SettingsPaths::fromEnvironment());
        return instance;
    }

    struct Session {
        ngosen::IBusHost*                    host = nullptr;
        std::unique_ptr<ngosen::TypingState> state;
        unsigned                             generation = 0;

        // Only between words: a new engine would drop the word being typed.
        void applyNewSettings() {
            if (host->hasPreedit())
                return;
            resources().reloadIfChanged();
            host->setDirectTyping(resources().settings().directTyping);
            if (generation == resources().generation())
                return;
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

    bool isPlainEnter(guint keyval, guint state) {
        constexpr guint modifiers = IBUS_SHIFT_MASK | IBUS_CONTROL_MASK | IBUS_MOD1_MASK | IBUS_MOD4_MASK | IBUS_SUPER_MASK | IBUS_RELEASE_MASK;
        return (keyval == IBUS_KEY_Return || keyval == IBUS_KEY_KP_Enter) && (state & modifiers) == 0;
    }

    gboolean processKeyEvent(IBusEngine* engine, guint keyval, guint keycode, guint state) {
        Session* session = sessionOf(engine);
        if (session == nullptr)
            return FALSE;
        session->applyNewSettings();
        // A password is sent as typed, the way fcitx5 turns input methods off in password fields.
        if (session->host->takesPassword())
            return FALSE;
        // The word goes out before Enter, so the core has nothing to commit and lets Enter through
        // instead of holding it back and forwarding it, which GNOME 50.0-50.3 drop.
        if (isPlainEnter(keyval, state) && session->host->hasPreedit())
            session->state->commitBuffer();
        // The core saw the cursor leave the word, so the word in the app is no longer ours to change.
        if (g_mouse_clicked.load(std::memory_order_acquire))
            session->host->forgetTypedWord();
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

    void showMenu(IBusEngine* engine, const ngosen::IBusSettings& settings) {
        IBusPropList* menu = ngosen::newSettingsMenu(settings);
        g_object_ref_sink(menu);
        ibus_engine_register_properties(engine, menu);
        // GNOME Shell takes the whole menu only once after the engine is chosen, then single items.
        updateItems(engine, menu);
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
        std::string key;
        std::string value;
        if (name == nullptr || !ngosen::settingForClick(name, state == PROP_STATE_CHECKED, key, value))
            return;
        ngosen::IBusSettings saved;
        // A failed write shows the old state again, so the menu never claims a setting that is not saved.
        showMenu(engine, resources().saveSetting(key, value, saved) ? saved : resources().settings());
    }

    void focusOut(IBusEngine* engine) {
        if (focusedEngine == engine)
            focusedEngine = nullptr;
        Session* session = sessionOf(engine);
        if (session == nullptr)
            return;
        session->host->forgetTypedWord();
        session->state->resetAfterAppCommit(true);
        session->host->setFocus(false);
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
        if (Session* session = sessionOf(engine)) {
            session->host->forgetTypedWord();
            session->state->resetAfterAppCommit(false);
        }
    }

    void disable(IBusEngine* engine) {
        focusOut(engine);
    }

    void setSurroundingText(IBusEngine* engine, IBusText* text, guint cursor, guint anchor) {
        IBUS_ENGINE_CLASS(ngosen_engine_parent_class)->set_surrounding_text(engine, text, cursor, anchor);
        if (Session* session = sessionOf(engine)) {
            session->host->setReportedText(ibus_text_get_text(text), cursor);
            const bool clicked = g_mouse_clicked.load(std::memory_order_acquire);
            const bool reset   = needEngineReset.load(std::memory_order_acquire);
            session->state->surroundingUpdated();
            // VS Code reports the cursor at the start of the field and then back after the word.
            if (!clicked && session->host->backAfterTypedWord() && g_mouse_clicked.load(std::memory_order_acquire)) {
                g_mouse_clicked.store(false, std::memory_order_release);
                needEngineReset.store(reset, std::memory_order_release);
            }
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

    // The factory's own engines never get focus_in_id, which names the app.
    IBusEngine* createEngine(IBusFactory* factory, const gchar* name, gpointer /*data*/) {
        static guint id     = 0;
        gchar*       path   = g_strdup_printf("/org/freedesktop/IBus/Engine/NgoSen/%u", ++id);
        auto*        engine = IBUS_ENGINE(g_object_new(ngosen_engine_get_type(), "engine-name", name, "object-path", path, "connection",
                                                       ibus_service_get_connection(IBUS_SERVICE(factory)), "has-focus-id", TRUE, nullptr));
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
    session->host->setDirectTyping(resources().settings().directTyping);
    self->session = session;
}

namespace ngosen {

    void addEngine(IBusFactory* factory) {
        // The IBus edition only types into the preedit, which the app commits itself.
        realMode = Mode::Preedit;
        ibus_factory_add_engine(factory, "ngosen", ngosen_engine_get_type());
        g_signal_connect(factory, "create-engine", G_CALLBACK(createEngine), nullptr);
    }

} // namespace ngosen
