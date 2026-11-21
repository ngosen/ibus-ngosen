/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-data-control.h"
#include "ngosen-ibus-primary.h"
#include "ngosen-log.h"

#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <fcntl.h>
#include <future>
#include <memory>
#include <poll.h>
#include <system_error>
#include <thread>
#include <unistd.h>
#include <vector>

namespace ngosen {
    namespace {

        using wayland::Interface;
        namespace op = wayland::op;

        struct Proxy;
        using Clock   = std::chrono::steady_clock;
        using Handler = void (*)();

        constexpr uint32_t DestroyFlag = 1; // WL_MARSHAL_FLAG_DESTROY
        constexpr size_t   MaxBytes    = 16 * 1024 * 1024;

        // libwayland-client is loaded at run time, as libxcb is, so the engine runs without it.
        struct Wl {
            void* lib = dlopen("libwayland-client.so.0", RTLD_NOW | RTLD_LOCAL);

            template <typename T>
            T get(const char* name) const {
                return lib ? reinterpret_cast<T>(dlsym(lib, name)) : nullptr;
            }

            Proxy* (*connect)(const char*)                                            = get<decltype(connect)>("wl_display_connect");
            void (*disconnect)(Proxy*)                                                = get<decltype(disconnect)>("wl_display_disconnect");
            int (*fileDescriptor)(Proxy*)                                             = get<decltype(fileDescriptor)>("wl_display_get_fd");
            int (*dispatchPending)(Proxy*)                                            = get<decltype(dispatchPending)>("wl_display_dispatch_pending");
            int (*prepareRead)(Proxy*)                                                = get<decltype(prepareRead)>("wl_display_prepare_read");
            void (*cancelRead)(Proxy*)                                                = get<decltype(cancelRead)>("wl_display_cancel_read");
            int (*readEvents)(Proxy*)                                                 = get<decltype(readEvents)>("wl_display_read_events");
            int (*flush)(Proxy*)                                                      = get<decltype(flush)>("wl_display_flush");
            Proxy* (*marshal)(Proxy*, uint32_t, const void*, uint32_t, uint32_t, ...) = get<decltype(marshal)>("wl_proxy_marshal_flags");
            int (*addListener)(Proxy*, const Handler*, void*)                         = get<decltype(addListener)>("wl_proxy_add_listener");
            void (*destroy)(Proxy*)                                                   = get<decltype(destroy)>("wl_proxy_destroy");
            uint32_t (*version)(Proxy*)                                               = get<decltype(version)>("wl_proxy_get_version");
            const Interface* registryInterface                                        = get<const Interface*>("wl_registry_interface");
            const Interface* seatInterface                                            = get<const Interface*>("wl_seat_interface");
            const Interface* callbackInterface                                        = get<const Interface*>("wl_callback_interface");

            bool             usable() const {
                return connect && disconnect && fileDescriptor && dispatchPending && prepareRead && cancelRead && readEvents && flush && marshal && addListener && destroy &&
                    version && registryInterface && seatInterface && callbackInterface;
            }
        };

        const Wl& wl() {
            static const Wl loaded;
            return loaded;
        }

        struct Offer {
            Proxy*                   proxy = nullptr;
            std::vector<std::string> mimeTypes;
        };

        // What the registry and the data device tell one read.
        struct Session {
            const Wl&                           w;
            Proxy*                              display;
            const wayland::DataControl*         protocol       = nullptr;
            uint32_t                            managerName    = 0;
            uint32_t                            managerVersion = 0;
            uint32_t                            seatName       = 0;
            std::vector<std::unique_ptr<Offer>> offers;
            Offer*                              primary         = nullptr;
            bool                                primaryAnswered = false;
            bool                                synced          = false;
        };

        void onGlobal(void* data, Proxy*, uint32_t name, const char* interface, uint32_t version) {
            auto& s = *static_cast<Session*>(data);
            // The newer protocol wins; the older one has a primary selection from its version 2.
            if (std::strcmp(interface, wayland::extDataControl.manager->name) == 0) {
                s.protocol       = &wayland::extDataControl;
                s.managerName    = name;
                s.managerVersion = 1;
            } else if (std::strcmp(interface, wayland::wlrDataControl.manager->name) == 0 && version >= 2 && s.protocol != &wayland::extDataControl) {
                s.protocol       = &wayland::wlrDataControl;
                s.managerName    = name;
                s.managerVersion = 2;
            } else if (std::strcmp(interface, "wl_seat") == 0 && s.seatName == 0) {
                s.seatName = name;
            }
        }

        void onGlobalRemove(void*, Proxy*, uint32_t) {}

        void onDone(void* data, Proxy*, uint32_t) {
            static_cast<Session*>(data)->synced = true;
        }

        void onMimeType(void* data, Proxy*, const char* mimeType) {
            static_cast<Offer*>(data)->mimeTypes.emplace_back(mimeType);
        }

        const Handler offerEvents[] = {reinterpret_cast<Handler>(onMimeType)};

        void          onDataOffer(void* data, Proxy*, Proxy* proxy) {
            auto& s      = *static_cast<Session*>(data);
            auto  offer  = std::make_unique<Offer>();
            offer->proxy = proxy;
            s.w.addListener(proxy, offerEvents, offer.get());
            s.offers.push_back(std::move(offer));
        }

        Offer* findOffer(Session& s, Proxy* proxy) {
            for (const auto& offer : s.offers) {
                if (offer->proxy == proxy)
                    return offer.get();
            }
            return nullptr;
        }

        void onSelection(void*, Proxy*, Proxy*) {}

        void onFinished(void*, Proxy*) {}

        void onPrimarySelection(void* data, Proxy*, Proxy* proxy) {
            auto& s           = *static_cast<Session*>(data);
            s.primary         = proxy ? findOffer(s, proxy) : nullptr;
            s.primaryAnswered = true;
        }

        const Handler registryEvents[] = {reinterpret_cast<Handler>(onGlobal), reinterpret_cast<Handler>(onGlobalRemove)};
        const Handler callbackEvents[] = {reinterpret_cast<Handler>(onDone)};
        const Handler deviceEvents[]   = {reinterpret_cast<Handler>(onDataOffer), reinterpret_cast<Handler>(onSelection), reinterpret_cast<Handler>(onFinished),
                                          reinterpret_cast<Handler>(onPrimarySelection)};

        int           remainingMs(Clock::time_point deadline) {
            const auto left = std::chrono::duration_cast<std::chrono::milliseconds>(deadline - Clock::now()).count();
            return left > 0 ? static_cast<int>(left) : 0;
        }

        // A round trip bounded by the deadline: wl_display_roundtrip would wait forever on a stalled compositor.
        bool sync(Session& s, Clock::time_point deadline) {
            const Wl& w     = s.w;
            s.synced        = false;
            Proxy* callback = w.marshal(s.display, 0, w.callbackInterface, w.version(s.display), 0, nullptr);
            w.addListener(callback, callbackEvents, &s);
            while (!s.synced) {
                // After a protocol error dispatching fails without emptying the queue, so stop instead of spinning.
                bool broken = false;
                while (!broken && w.prepareRead(s.display) != 0)
                    broken = w.dispatchPending(s.display) < 0;
                if (broken || s.synced) {
                    if (!broken)
                        w.cancelRead(s.display);
                    break;
                }
                w.flush(s.display);
                pollfd fd = {w.fileDescriptor(s.display), POLLIN, 0};
                if (poll(&fd, 1, remainingMs(deadline)) <= 0) {
                    w.cancelRead(s.display);
                    break;
                }
                if (w.readEvents(s.display) < 0)
                    break;
                w.dispatchPending(s.display);
            }
            w.destroy(callback);
            return s.synced;
        }

        std::string pickMimeType(const Offer& offer) {
            for (const char* wanted : {"text/plain;charset=utf-8", "UTF8_STRING", "text/plain", "TEXT", "STRING"}) {
                for (const auto& mimeType : offer.mimeTypes) {
                    if (mimeType == wanted)
                        return mimeType;
                }
            }
            return {};
        }

        // Text cut short would replace the whole selection, so anything but a complete transfer gives nothing.
        std::string receive(Session& s, const Offer& offer, const std::string& mimeType, Clock::time_point deadline) {
            int ends[2];
            if (pipe2(ends, O_CLOEXEC) != 0)
                return {};
            s.w.marshal(offer.proxy, op::OfferReceive, nullptr, s.w.version(offer.proxy), 0, mimeType.c_str(), ends[1]);
            s.w.flush(s.display);
            close(ends[1]);
            std::string text;
            char        buffer[4096];
            bool        complete = false;
            for (;;) {
                pollfd fd = {ends[0], POLLIN, 0};
                if (poll(&fd, 1, remainingMs(deadline)) <= 0)
                    break;
                const ssize_t got = read(ends[0], buffer, sizeof buffer);
                complete          = got == 0;
                if (got <= 0 || text.size() + static_cast<size_t>(got) > MaxBytes)
                    break;
                text.append(buffer, static_cast<size_t>(got));
            }
            close(ends[0]);
            return complete ? text : std::string();
        }

        std::optional<std::string> readFromCompositor(Session& s, Proxy* registry, Clock::time_point deadline) {
            const Wl& w = s.w;
            w.addListener(registry, registryEvents, &s);
            // Only a compositor that answered without data-control hands the read to X11; a stalled one has used the time.
            if (!sync(s, deadline))
                return std::string();
            if (!s.protocol || s.seatName == 0)
                return std::nullopt;
            const auto bind = [&](uint32_t name, const Interface* interface, uint32_t version) {
                return w.marshal(registry, op::RegistryBind, interface, version, 0, name, interface->name, version, nullptr);
            };
            Proxy*                     seat    = bind(s.seatName, w.seatInterface, 1);
            Proxy*                     manager = bind(s.managerName, s.protocol->manager, s.managerVersion);
            Proxy*                     device  = w.marshal(manager, op::ManagerGetDataDevice, s.protocol->device, s.managerVersion, 0, nullptr, seat);
            std::optional<std::string> text    = std::string();
            w.addListener(device, deviceEvents, &s);
            if (sync(s, deadline)) {
                // A compositor without a primary selection never sends the event; Xwayland may still have one.
                if (!s.primaryAnswered)
                    text = std::nullopt;
                else if (const std::string mimeType = s.primary ? pickMimeType(*s.primary) : std::string(); !mimeType.empty())
                    text = receive(s, *s.primary, mimeType, deadline);
            }
            for (const auto& offer : s.offers)
                w.marshal(offer->proxy, op::OfferDestroy, nullptr, w.version(offer->proxy), DestroyFlag);
            w.marshal(device, op::DeviceDestroy, nullptr, w.version(device), DestroyFlag);
            w.marshal(manager, op::ManagerDestroy, nullptr, w.version(manager), DestroyFlag);
            w.destroy(seat);
            return text;
        }

        // No logging here: this runs off the main thread.
        std::optional<std::string> readPrimary(Clock::time_point deadline) {
            const Wl& w       = wl();
            Proxy*    display = w.connect(nullptr);
            if (display == nullptr)
                return std::nullopt;
            Session s{w, display};
            Proxy*  registry = w.marshal(display, op::DisplayGetRegistry, w.registryInterface, w.version(display), 0, nullptr);
            auto    text     = readFromCompositor(s, registry, deadline);
            w.destroy(registry);
            w.flush(display);
            w.disconnect(display);
            return text;
        }

        // Set while a read runs; a read stuck on a stalled compositor must not gain company at every key press.
        std::atomic<bool> reading{false};

    } // namespace

    std::optional<std::string> readWaylandPrimarySelection(int timeoutMs) {
        if (!wl().usable() || std::getenv("WAYLAND_DISPLAY") == nullptr)
            return std::nullopt;
        if (reading.exchange(true)) {
            NGOSEN_INFO("The compositor has not answered the last read of the primary selection");
            return std::string();
        }
        const auto deadline = Clock::now() + std::chrono::milliseconds(timeoutMs);
        auto       result   = std::make_shared<std::promise<std::optional<std::string>>>();
        auto       text     = result->get_future();
        try {
            std::thread([result, deadline] {
                result->set_value(readPrimary(deadline));
                reading = false;
            }).detach();
        } catch (const std::system_error&) {
            reading = false;
            return std::nullopt;
        }
        if (text.wait_until(deadline + std::chrono::milliseconds(50)) != std::future_status::ready) {
            NGOSEN_INFO("The compositor did not answer in time for the primary selection");
            return std::string();
        }
        return text.get();
    }

} // namespace ngosen
