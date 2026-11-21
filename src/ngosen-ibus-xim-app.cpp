/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-xim-app.h"
#include "ngosen-log.h"

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>

namespace ngosen {

    namespace {

        // libxcb is loaded at run time, as for the primary selection, so the engine runs without it.
        struct XcbConnection;
        struct XcbCookie {
            unsigned int sequence;
        };

        constexpr uint32_t WmClassAtom = 67; // XCB_ATOM_WM_CLASS
        constexpr uint32_t StringAtom  = 31; // XCB_ATOM_STRING
        constexpr int      MaxParents  = 8;

        struct Xcb {
            void* lib = dlopen("libxcb.so.1", RTLD_NOW | RTLD_LOCAL);

            template <typename T>
            T get(const char* name) const {
                return lib ? reinterpret_cast<T>(dlsym(lib, name)) : nullptr;
            }

            XcbConnection* (*connect)(const char*, int*)                                                        = get<decltype(connect)>("xcb_connect");
            void (*disconnect)(XcbConnection*)                                                                  = get<decltype(disconnect)>("xcb_disconnect");
            int (*hasError)(XcbConnection*)                                                                     = get<decltype(hasError)>("xcb_connection_has_error");
            XcbCookie (*getInputFocus)(XcbConnection*)                                                          = get<decltype(getInputFocus)>("xcb_get_input_focus");
            uint8_t* (*getInputFocusReply)(XcbConnection*, XcbCookie, void**)                                   = get<decltype(getInputFocusReply)>("xcb_get_input_focus_reply");
            XcbCookie (*queryTree)(XcbConnection*, uint32_t)                                                    = get<decltype(queryTree)>("xcb_query_tree");
            uint8_t* (*queryTreeReply)(XcbConnection*, XcbCookie, void**)                                       = get<decltype(queryTreeReply)>("xcb_query_tree_reply");
            XcbCookie (*getProperty)(XcbConnection*, uint8_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t) = get<decltype(getProperty)>("xcb_get_property");
            uint8_t* (*getPropertyReply)(XcbConnection*, XcbCookie, void**)                                     = get<decltype(getPropertyReply)>("xcb_get_property_reply");
            void* (*propertyValue)(const uint8_t*)                                                              = get<decltype(propertyValue)>("xcb_get_property_value");
            int (*propertyLength)(const uint8_t*)                                                               = get<decltype(propertyLength)>("xcb_get_property_value_length");

            bool usable() const {
                return connect && disconnect && hasError && getInputFocus && getInputFocusReply && queryTree && queryTreeReply && getProperty && getPropertyReply &&
                    propertyValue && propertyLength;
            }
        };

        uint32_t readU32(const uint8_t* bytes, size_t offset) {
            uint32_t value;
            std::memcpy(&value, bytes + offset, sizeof value);
            return value;
        }

        struct XimApp {
            Xcb            x;
            XcbConnection* conn = nullptr;
            std::string    program;
            bool           forTest = false;

            // One connection for the session; a broken one is opened again on the next focus.
            bool connected() {
                if (conn != nullptr && x.hasError(conn) == 0)
                    return true;
                if (conn != nullptr)
                    x.disconnect(conn);
                conn = x.connect(nullptr, nullptr);
                return conn != nullptr && x.hasError(conn) == 0;
            }

            // The instance part of WM_CLASS, which is the name fcitx5 gives an XIM client.
            std::string instanceName(uint32_t window) {
                uint8_t*    reply = x.getPropertyReply(conn, x.getProperty(conn, 0, window, WmClassAtom, StringAtom, 0, 64), nullptr);
                std::string name;
                if (reply != nullptr) {
                    const char* value = static_cast<const char*>(x.propertyValue(reply));
                    name.assign(value, strnlen(value, static_cast<size_t>(x.propertyLength(reply))));
                }
                std::free(reply);
                return name;
            }

            uint32_t parentOf(uint32_t window) {
                uint8_t*       reply  = x.queryTreeReply(conn, x.queryTree(conn, window), nullptr);
                const uint32_t root   = reply ? readU32(reply, 8) : 0;
                const uint32_t parent = reply ? readU32(reply, 12) : 0;
                std::free(reply);
                return parent == root ? 0 : parent;
            }

            // The focus can sit on a child of the window that carries WM_CLASS.
            std::string focusedName() {
                uint8_t* reply  = x.getInputFocusReply(conn, x.getInputFocus(conn), nullptr);
                uint32_t window = reply ? readU32(reply, 8) : 0;
                std::free(reply);
                for (int i = 0; window > 1 && i < MaxParents; ++i, window = parentOf(window)) {
                    if (std::string name = instanceName(window); !name.empty())
                        return name;
                }
                return {};
            }
        };

        XimApp& ximApp() {
            static XimApp app;
            return app;
        }

    } // namespace

    // An XIM client asks for focus after its window got the X input focus, so that window is the client's.
    void noteXimFocus() {
        XimApp& app = ximApp();
        if (app.forTest)
            return;
        const std::string old = app.program;
        app.program           = app.x.usable() && app.connected() ? app.focusedName() : std::string();
        if (app.program != old)
            NGOSEN_INFO("XIM focused app: " + (app.program.empty() ? std::string("unknown") : app.program));
    }

    const std::string& ximFocusedApp() {
        return ximApp().program;
    }

    void setXimFocusedAppForTest(std::string program) {
        ximApp().forTest = true;
        ximApp().program = std::move(program);
    }

} // namespace ngosen
