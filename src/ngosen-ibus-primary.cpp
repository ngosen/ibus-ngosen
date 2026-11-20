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
#include <atomic>
#include <dlfcn.h>
#include <future>
#include <memory>
#include <poll.h>
#include <system_error>
#include <thread>

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
        constexpr uint8_t  PropertyNotify  = 28;
        constexpr uint8_t  SelectionNotify = 31;
        constexpr uint8_t  NewValue        = 0;
        constexpr uint16_t InputOnly       = 2;
        constexpr uint32_t EventMask       = 0x800;      // XCB_CW_EVENT_MASK
        constexpr uint32_t PropertyChange  = 0x400000;   // XCB_EVENT_MASK_PROPERTY_CHANGE
        constexpr uint32_t ReadAll         = 0x1fffffff; // in 4-byte units
        // Far more than a document anyone converts at once, and a bound on a runaway owner.
        constexpr size_t MaxBytes = 16 * 1024 * 1024;

        using Clock = std::chrono::steady_clock;

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

        // Waits for an event that matches; false when the time ran out or the connection broke.
        template <typename Match>
        bool waitFor(const Xcb& x, XcbConnection* conn, Clock::time_point deadline, Match matches) {
            pollfd fd{x.fileDescriptor(conn), POLLIN, 0};
            while (true) {
                while (uint8_t* event = x.pollForEvent(conn)) {
                    const bool found = matches(event);
                    std::free(event);
                    if (found)
                        return true;
                }
                const auto left = std::chrono::duration_cast<std::chrono::milliseconds>(deadline - Clock::now()).count();
                if (left <= 0 || x.hasError(conn) != 0 || poll(&fd, 1, static_cast<int>(left)) <= 0)
                    return false;
            }
        }

        struct Property {
            uint32_t    type = 0;
            std::string data;
        };

        // Reading deletes the property, which tells an owner sending in parts to send the next one.
        Property takeProperty(const Xcb& x, XcbConnection* conn, uint32_t window, uint32_t property) {
            uint8_t* reply = x.getPropertyReply(conn, x.getProperty(conn, 1, window, property, AnyPropertyType, 0, ReadAll), nullptr);
            Property result;
            if (reply != nullptr) {
                result.type = readU32(reply, 8);
                result.data.assign(static_cast<const char*>(x.propertyValue(reply)), static_cast<size_t>(x.propertyLength(reply)));
            }
            std::free(reply);
            return result;
        }

        // A large selection comes in parts (ICCCM INCR): each part is a new value of the property, and an empty one ends it.
        bool readParts(const Xcb& x, XcbConnection* conn, uint32_t window, uint32_t property, uint32_t utf8, Clock::time_point deadline, std::string& text) {
            const auto newValue = [&](const uint8_t* event) {
                return (event[0] & 0x7f) == PropertyNotify && readU32(event, 4) == window && readU32(event, 8) == property && event[16] == NewValue;
            };
            while (waitFor(x, conn, deadline, newValue)) {
                const Property part = takeProperty(x, conn, window, property);
                if (part.type != utf8 || text.size() + part.data.size() > MaxBytes)
                    return false;
                if (part.data.empty())
                    return true;
                text += part.data;
            }
            return false;
        }

        std::string convertPrimary(const Xcb& x, XcbConnection* conn, Clock::time_point deadline) {
            const XcbScreenIterator screen = x.roots(x.getSetup(conn));
            if (screen.rem == 0 || screen.data == nullptr)
                return {};
            const uint32_t window = x.generateId(conn);
            const uint32_t events = PropertyChange;
            x.createWindow(conn, 0, window, screen.data[0], 0, 0, 1, 1, 0, InputOnly, 0, EventMask, &events);
            const uint32_t utf8     = atom(x, conn, "UTF8_STRING");
            const uint32_t incr     = atom(x, conn, "INCR");
            const uint32_t property = atom(x, conn, "NGOSEN_PRIMARY");
            if (utf8 == 0 || incr == 0 || property == 0)
                return {};
            x.convertSelection(conn, window, PrimaryAtom, utf8, property, 0);
            x.flush(conn);
            const auto notified = [&](const uint8_t* event) { return (event[0] & 0x7f) == SelectionNotify && readU32(event, 20) == property; };
            if (!waitFor(x, conn, deadline, notified))
                return {};
            Property first = takeProperty(x, conn, window, property);
            if (first.type == utf8)
                return first.data;
            std::string text;
            if (first.type == incr && readParts(x, conn, window, property, utf8, deadline, text))
                return text;
            return {};
        }

        // Set while a read runs; a read stuck on a stalled server must not gain company at every key press.
        std::atomic<bool> reading{false};

        std::string       readPrimary(Clock::time_point deadline) {
            const Xcb&     x    = xcb();
            XcbConnection* conn = x.connect(nullptr, nullptr);
            std::string    text;
            // No logging here: this runs off the main thread.
            if (conn != nullptr && x.hasError(conn) == 0)
                text = convertPrimary(x, conn, deadline);
            if (conn != nullptr)
                x.disconnect(conn);
            return text;
        }

    } // namespace

    std::string readPrimarySelection(int timeoutMs) {
        if (!xcb().usable() || std::getenv("DISPLAY") == nullptr)
            return {};
        // Connecting and every reply can stall on a busy X server, so a thread does the reading and the
        // engine waits only until the deadline; a late thread finishes on its own.
        if (reading.exchange(true)) {
            NGOSEN_INFO("The X server has not answered the last read of the primary selection");
            return {};
        }
        const auto deadline = Clock::now() + std::chrono::milliseconds(timeoutMs);
        auto       result   = std::make_shared<std::promise<std::string>>();
        auto       text     = result->get_future();
        try {
            std::thread([result, deadline] {
                result->set_value(readPrimary(deadline));
                reading = false;
            }).detach();
        } catch (const std::system_error&) {
            reading = false;
            return {};
        }
        if (text.wait_until(deadline + std::chrono::milliseconds(50)) != std::future_status::ready) {
            NGOSEN_INFO("The X server did not answer in time for the primary selection");
            return {};
        }
        return text.get();
    }

} // namespace ngosen
