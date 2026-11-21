/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-xim-app.h"
#include "ngosen-log.h"

#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <future>
#include <memory>
#include <system_error>
#include <thread>

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
        // Runs on focus-in, before the first key reaches the new field.
        constexpr auto LookupTime = std::chrono::milliseconds(50);

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

        const Xcb& xcb() {
            static const Xcb loaded;
            return loaded;
        }

        uint32_t readU32(const uint8_t* bytes, size_t offset) {
            uint32_t value;
            std::memcpy(&value, bytes + offset, sizeof value);
            return value;
        }

        // The instance part of WM_CLASS, which is the name fcitx5 gives an XIM client.
        std::string instanceName(const Xcb& x, XcbConnection* conn, uint32_t window) {
            uint8_t*    reply = x.getPropertyReply(conn, x.getProperty(conn, 0, window, WmClassAtom, StringAtom, 0, 64), nullptr);
            std::string name;
            if (reply != nullptr) {
                const char* value = static_cast<const char*>(x.propertyValue(reply));
                name.assign(value, strnlen(value, static_cast<size_t>(x.propertyLength(reply))));
            }
            std::free(reply);
            return name;
        }

        uint32_t parentOf(const Xcb& x, XcbConnection* conn, uint32_t window) {
            uint8_t*       reply  = x.queryTreeReply(conn, x.queryTree(conn, window), nullptr);
            const uint32_t root   = reply ? readU32(reply, 8) : 0;
            const uint32_t parent = reply ? readU32(reply, 12) : 0;
            std::free(reply);
            return parent == root ? 0 : parent;
        }

        // The focus can sit on a child of the window that carries WM_CLASS.
        std::string focusedName() {
            const Xcb&     x    = xcb();
            XcbConnection* conn = x.connect(nullptr, nullptr);
            std::string    name;
            if (conn != nullptr && x.hasError(conn) == 0) {
                uint8_t* reply  = x.getInputFocusReply(conn, x.getInputFocus(conn), nullptr);
                uint32_t window = reply ? readU32(reply, 8) : 0;
                std::free(reply);
                for (int i = 0; window > 1 && i < MaxParents && name.empty(); ++i) {
                    name = instanceName(x, conn, window);
                    if (name.empty())
                        window = parentOf(x, conn, window);
                }
            }
            if (conn != nullptr)
                x.disconnect(conn);
            return name;
        }

        std::atomic<bool> looking{false};
        std::string       program;
        bool              forTest = false;

        // Connecting and every reply can stall on a busy X server, so a thread asks and the engine waits
        // only until the deadline; a late thread finishes on its own.
        std::string askForFocusedName() {
            if (!xcb().usable() || std::getenv("DISPLAY") == nullptr)
                return {};
            if (looking.exchange(true))
                return {};
            auto result = std::make_shared<std::promise<std::string>>();
            auto name   = result->get_future();
            try {
                std::thread([result] {
                    result->set_value(focusedName());
                    looking = false;
                }).detach();
            } catch (const std::system_error&) {
                looking = false;
                return {};
            }
            if (name.wait_for(LookupTime) != std::future_status::ready) {
                NGOSEN_INFO("The X server did not name the focused window in time");
                return {};
            }
            return name.get();
        }

    } // namespace

    // An XIM client asks for focus after its window got the X input focus, so that window is the client's.
    void noteXimFocus() {
        if (forTest)
            return;
        const std::string old = program;
        program               = askForFocusedName();
        if (program != old)
            NGOSEN_INFO("XIM focused app: " + (program.empty() ? std::string("unknown") : program));
    }

    const std::string& ximFocusedApp() {
        return program;
    }

    void setXimFocusedAppForTest(std::string name) {
        forTest = true;
        program = std::move(name);
    }

} // namespace ngosen
