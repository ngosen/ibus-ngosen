/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-primary.h"
#include "ngosen-log.h"

#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <poll.h>

namespace ngosen {

    namespace {

        // libxcb is loaded at run time, as the core loads it for XTEST, so the engine runs without it.
        struct XcbConnection;
        struct XcbCookie {
            unsigned int sequence;
        };
        struct XcbScreenIterator {
            const uint32_t* data; // xcb_screen_t starts with the root window id
            int             rem;
            int             index;
        };

        constexpr uint32_t PrimaryAtom     = 1; // XCB_ATOM_PRIMARY
        constexpr uint32_t AnyPropertyType = 0;
        constexpr uint8_t  SelectionNotify = 31;
        constexpr uint16_t InputOnly       = 2;
        constexpr uint32_t ReadAll         = 0x1fffffff; // in 4-byte units

        struct Xcb {
            void* lib = dlopen("libxcb.so.1", RTLD_NOW | RTLD_LOCAL);

            template <typename T>
            T get(const char* name) const {
                return lib ? reinterpret_cast<T>(dlsym(lib, name)) : nullptr;
            }

            XcbConnection* (*connect)(const char*, int*)                                                        = get<decltype(connect)>("xcb_connect");
            void (*disconnect)(XcbConnection*)                                                                  = get<decltype(disconnect)>("xcb_disconnect");
            int (*hasError)(XcbConnection*)                                                                     = get<decltype(hasError)>("xcb_connection_has_error");
            uint32_t (*generateId)(XcbConnection*)                                                              = get<decltype(generateId)>("xcb_generate_id");
            const void* (*getSetup)(XcbConnection*)                                                             = get<decltype(getSetup)>("xcb_get_setup");
            XcbScreenIterator (*roots)(const void*)                                                             = get<decltype(roots)>("xcb_setup_roots_iterator");
            XcbCookie (*createWindow)(XcbConnection*, uint8_t, uint32_t, uint32_t, int16_t, int16_t, uint16_t, uint16_t, uint16_t, uint16_t, uint32_t, uint32_t,
                                      const void*)                                                              = get<decltype(createWindow)>("xcb_create_window");
            XcbCookie (*internAtom)(XcbConnection*, uint8_t, uint16_t, const char*)                             = get<decltype(internAtom)>("xcb_intern_atom");
            uint8_t* (*internAtomReply)(XcbConnection*, XcbCookie, void**)                                      = get<decltype(internAtomReply)>("xcb_intern_atom_reply");
            XcbCookie (*convertSelection)(XcbConnection*, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t)     = get<decltype(convertSelection)>("xcb_convert_selection");
            int (*flush)(XcbConnection*)                                                                        = get<decltype(flush)>("xcb_flush");
            int (*fileDescriptor)(XcbConnection*)                                                               = get<decltype(fileDescriptor)>("xcb_get_file_descriptor");
            uint8_t* (*pollForEvent)(XcbConnection*)                                                            = get<decltype(pollForEvent)>("xcb_poll_for_event");
            XcbCookie (*getProperty)(XcbConnection*, uint8_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t) = get<decltype(getProperty)>("xcb_get_property");
            uint8_t* (*getPropertyReply)(XcbConnection*, XcbCookie, void**)                                     = get<decltype(getPropertyReply)>("xcb_get_property_reply");
            void* (*propertyValue)(const uint8_t*)                                                              = get<decltype(propertyValue)>("xcb_get_property_value");
            int (*propertyLength)(const uint8_t*)                                                               = get<decltype(propertyLength)>("xcb_get_property_value_length");

            bool usable() const {
                return connect && disconnect && hasError && generateId && getSetup && roots && createWindow && internAtom && internAtomReply && convertSelection && flush &&
                    fileDescriptor && pollForEvent && getProperty && getPropertyReply && propertyValue && propertyLength;
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

        uint32_t atom(const Xcb& x, XcbConnection* conn, const char* name) {
            uint8_t*       reply = x.internAtomReply(conn, x.internAtom(conn, 0, static_cast<uint16_t>(std::strlen(name)), name), nullptr);
            const uint32_t value = reply ? readU32(reply, 8) : 0;
            std::free(reply);
            return value;
        }

        // The property the owner wrote, or nothing when it refused or the time ran out.
        uint32_t waitForSelection(const Xcb& x, XcbConnection* conn, int timeoutMs) {
            const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeoutMs);
            pollfd     fd{x.fileDescriptor(conn), POLLIN, 0};
            while (true) {
                while (uint8_t* event = x.pollForEvent(conn)) {
                    const bool     notify   = (event[0] & 0x7f) == SelectionNotify;
                    const uint32_t property = notify ? readU32(event, 20) : 0;
                    std::free(event);
                    if (notify)
                        return property;
                }
                const auto left = std::chrono::duration_cast<std::chrono::milliseconds>(deadline - std::chrono::steady_clock::now()).count();
                if (left <= 0 || x.hasError(conn) != 0 || poll(&fd, 1, static_cast<int>(left)) <= 0)
                    return 0;
            }
        }

        std::string convertPrimary(const Xcb& x, XcbConnection* conn, int timeoutMs) {
            const XcbScreenIterator screen = x.roots(x.getSetup(conn));
            if (screen.rem == 0 || screen.data == nullptr)
                return {};
            const uint32_t window = x.generateId(conn);
            x.createWindow(conn, 0, window, screen.data[0], 0, 0, 1, 1, 0, InputOnly, 0, 0, nullptr);
            const uint32_t utf8     = atom(x, conn, "UTF8_STRING");
            const uint32_t property = atom(x, conn, "NGOSEN_PRIMARY");
            if (utf8 == 0 || property == 0)
                return {};
            x.convertSelection(conn, window, PrimaryAtom, utf8, property, 0);
            x.flush(conn);
            if (waitForSelection(x, conn, timeoutMs) != property)
                return {};
            uint8_t* reply = x.getPropertyReply(conn, x.getProperty(conn, 1, window, property, AnyPropertyType, 0, ReadAll), nullptr);
            // A large selection comes in parts (INCR), which converting a selection never needs.
            std::string text;
            if (reply != nullptr && readU32(reply, 8) == utf8)
                text.assign(static_cast<const char*>(x.propertyValue(reply)), static_cast<size_t>(x.propertyLength(reply)));
            std::free(reply);
            return text;
        }

    } // namespace

    std::string readPrimarySelection(int timeoutMs) {
        const Xcb& x = xcb();
        if (!x.usable() || std::getenv("DISPLAY") == nullptr)
            return {};
        XcbConnection* conn = x.connect(nullptr, nullptr);
        std::string    text;
        if (conn != nullptr && x.hasError(conn) == 0)
            text = convertPrimary(x, conn, timeoutMs);
        else
            NGOSEN_INFO("Cannot open the X display to read the primary selection");
        if (conn != nullptr)
            x.disconnect(conn);
        return text;
    }

} // namespace ngosen
