/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-announce.h"
#include "ngosen-ibus-i18n.h"

#include "ngosen-log.h"

#include <gio/gio.h>

namespace ngosen {

    namespace {
        const char* const Service   = "org.freedesktop.Notifications";
        const char* const Path      = "/org/freedesktop/Notifications";
        const char* const Interface = "org.freedesktop.Notifications";

        struct Notice {
            GDBusConnection*      bus     = nullptr;
            guint32               id      = 0;
            guint                 actions = 0;
            guint                 closed  = 0;
            std::function<void()> open;
        };

        void forget(Notice* notice) {
            g_dbus_connection_signal_unsubscribe(notice->bus, notice->actions);
            g_dbus_connection_signal_unsubscribe(notice->bus, notice->closed);
            g_object_unref(notice->bus);
            delete notice;
        }

        void onSignal(GDBusConnection*, const gchar*, const gchar*, const gchar*, const gchar* signal, GVariant* parameters, gpointer data) {
            auto*   notice = static_cast<Notice*>(data);
            guint32 id     = 0;
            g_variant_get_child(parameters, 0, "u", &id);
            if (id != notice->id)
                return;
            // Clicking a button closes the notice too, so it is forgotten on the close that follows.
            if (g_strcmp0(signal, "ActionInvoked") == 0)
                notice->open();
            else
                forget(notice);
        }

        void onSent(GObject* source, GAsyncResult* result, gpointer data) {
            auto*     notice = static_cast<Notice*>(data);
            GError*   error  = nullptr;
            GVariant* reply  = g_dbus_connection_call_finish(G_DBUS_CONNECTION(source), result, &error);
            if (reply == nullptr) {
                NGOSEN_WARN(std::string("Cannot show what is new: ") + error->message);
                g_error_free(error);
                forget(notice);
                return;
            }
            g_variant_get(reply, "(u)", &notice->id);
            g_variant_unref(reply);
        }

        gboolean send(gpointer data) {
            auto*       notice = static_cast<Notice*>(data);
            const char* show   = _("Show");
            const char* title  = _("What's new in Ngó Sen?");
            // Names the release, so it changes with each feature release.
            const char* body      = _("Version 1.3: Ctrl+Shift and OFF switch the app in use only, the ` menu can be set up your way, and settings can be "
                                      "searched. See also typing tips.");
            const char* actions[] = {"default", show, "show", show, nullptr};
            // It is shown once, so it stays until the user closes it.
            const gint32 neverExpire = 0;
            g_dbus_connection_call(notice->bus, Service, Path, Interface, "Notify",
                                   g_variant_new("(susss^asa{sv}i)", "Ngó Sen", 0U, "ibus-ngosen", title, body, actions, nullptr, neverExpire), G_VARIANT_TYPE("(u)"),
                                   G_DBUS_CALL_FLAGS_NONE, -1, nullptr, onSent, notice);
            return G_SOURCE_REMOVE;
        }
    } // namespace

    void openWhatsNew() {
        gchar*  argv[] = {const_cast<gchar*>(NGOSEN_SETUP_EXEC), const_cast<gchar*>("--page"), const_cast<gchar*>("whats-new"), nullptr}; //NOLINT
        GError* error  = nullptr;
        if (!g_spawn_async(nullptr, argv, nullptr, G_SPAWN_DEFAULT, nullptr, nullptr, nullptr, &error)) {
            NGOSEN_WARN(std::string("Cannot open the settings window: ") + error->message);
            g_error_free(error);
        }
    }

    void announceRelease(const std::string& release, unsigned delaySeconds, std::function<void()> open) {
        if (release.empty())
            return;
        GError*          error = nullptr;
        GDBusConnection* bus   = g_bus_get_sync(G_BUS_TYPE_SESSION, nullptr, &error);
        if (bus == nullptr) {
            NGOSEN_WARN(std::string("Cannot show what is new: ") + error->message);
            g_error_free(error);
            return;
        }
        NGOSEN_INFO("Announcing release " + release);
        auto* notice    = new Notice;
        notice->bus     = bus;
        notice->open    = std::move(open);
        notice->actions = g_dbus_connection_signal_subscribe(bus, Service, Interface, "ActionInvoked", Path, nullptr, G_DBUS_SIGNAL_FLAGS_NONE, onSignal, notice, nullptr);
        notice->closed  = g_dbus_connection_signal_subscribe(bus, Service, Interface, "NotificationClosed", Path, nullptr, G_DBUS_SIGNAL_FLAGS_NONE, onSignal, notice, nullptr);
        g_timeout_add_seconds(delaySeconds, send, notice);
    }

} // namespace ngosen
