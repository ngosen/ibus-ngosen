/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-engine.h"

#include "ngosen-globals.h"
#include "ngosen-ibus-host.h"
#include "ngosen-ibus-resources.h"
#include "ngosen-log.h"
#include "ngosen-state.h"

#include <memory>

namespace {

    struct Session {
        ngosen::IBusHost*                    host = nullptr;
        std::unique_ptr<ngosen::TypingState> state;
    };

    ngosen::IBusResources& resources() {
        static ngosen::IBusResources instance;
        return instance;
    }

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
        // The word goes out before Enter, so the core has nothing to commit and lets Enter through
        // instead of holding it back and forwarding it, which GNOME 50.0-50.3 drop.
        if (isPlainEnter(keyval, state))
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

    void focusIn(IBusEngine* engine) {
        if (Session* session = sessionOf(engine))
            session->host->setFocus(true);
    }

    void focusOut(IBusEngine* engine) {
        Session* session = sessionOf(engine);
        if (session == nullptr)
            return;
        session->state->resetAfterAppCommit(true);
        session->host->setFocus(false);
    }

#if IBUS_CHECK_VERSION(1, 5, 27)
    void focusInId(IBusEngine* engine, const gchar* /*objectPath*/, const gchar* client) {
        if (Session* session = sessionOf(engine))
            session->host->setClient(client != nullptr ? client : "");
        NGOSEN_INFO("Focus in: " << (client != nullptr ? client : ""));
        focusIn(engine);
    }

    void focusOutId(IBusEngine* engine, const gchar* /*objectPath*/) {
        focusOut(engine);
    }
#endif

    // A click in the field or a change the app made itself; the app has committed the preedit. A
    // sentence begun with Enter, which also resets GTK fields, still capitalizes.
    void reset(IBusEngine* engine) {
        if (Session* session = sessionOf(engine))
            session->state->resetAfterAppCommit(false);
    }

    void disable(IBusEngine* engine) {
        focusOut(engine);
    }

    void setSurroundingText(IBusEngine* engine, IBusText* text, guint cursor, guint anchor) {
        IBUS_ENGINE_CLASS(ngosen_engine_parent_class)->set_surrounding_text(engine, text, cursor, anchor);
        if (Session* session = sessionOf(engine))
            session->state->surroundingUpdated();
    }

    void setContentType(IBusEngine* engine, guint purpose, guint hints) {
        IBUS_ENGINE_CLASS(ngosen_engine_parent_class)->set_content_type(engine, purpose, hints);
        NGOSEN_DEBUG("Content type: purpose " << purpose << ", hints " << hints);
        if (Session* session = sessionOf(engine))
            session->host->setContentType(purpose, hints);
    }

    void destroy(IBusObject* object) {
        auto* self = reinterpret_cast<NgoSenEngine*>(object);
        delete self->session;
        self->session = nullptr;
        IBUS_OBJECT_CLASS(ngosen_engine_parent_class)->destroy(object);
    }

#if IBUS_CHECK_VERSION(1, 5, 27)
    // The factory's own engines never get focus_in_id, which names the app.
    IBusEngine* createEngine(IBusFactory* factory, const gchar* name, gpointer /*data*/) {
        static guint id     = 0;
        gchar*       path   = g_strdup_printf("/org/freedesktop/IBus/Engine/NgoSen/%u", ++id);
        auto*        engine = IBUS_ENGINE(g_object_new(ngosen_engine_get_type(), "engine-name", name, "object-path", path, "connection",
                                                       ibus_service_get_connection(IBUS_SERVICE(factory)), "has-focus-id", TRUE, nullptr));
        g_free(path);
        return engine;
    }
#endif

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
#if IBUS_CHECK_VERSION(1, 5, 27)
    engineClass->focus_in_id  = focusInId;
    engineClass->focus_out_id = focusOutId;
#endif
    IBUS_OBJECT_CLASS(klass)->destroy = destroy;
}

static void ngosen_engine_init(NgoSenEngine* self) {
    auto  host     = std::make_unique<ngosen::IBusHost>(IBUS_ENGINE(self));
    auto* session  = new Session;
    session->host  = host.get();
    session->state = std::make_unique<ngosen::TypingState>(&resources(), std::move(host));
    session->host->setOnCommit([state = session->state.get()](const std::string& text) { state->noteCommit(text); });
    self->session = session;
}

namespace ngosen {

    void addEngine(IBusFactory* factory) {
        // The IBus edition only types into the preedit, which the app commits itself.
        realMode = Mode::Preedit;
        ibus_factory_add_engine(factory, "ngosen", ngosen_engine_get_type());
#if IBUS_CHECK_VERSION(1, 5, 27)
        g_signal_connect(factory, "create-engine", G_CALLBACK(createEngine), nullptr);
#endif
    }

} // namespace ngosen
