/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-data-control.h"

// Transcribed from ext-data-control-v1.xml (wayland-protocols) and wlr-data-control-unstable-v1.xml
// (wlr-protocols). Object arguments of other interfaces (the seat, a source) have no type here:
// libwayland checks types only on events, and the engine never sends a source.

namespace ngosen::wayland {
    namespace {

        extern const Interface extSource;
        extern const Interface extOffer;
        extern const Interface extDevice;
        extern const Interface extManager;
        extern const Interface wlrSource;
        extern const Interface wlrOffer;
        extern const Interface wlrDevice;
        extern const Interface wlrManager;

        const Interface*       none[]         = {nullptr, nullptr};
        const Interface*       extNewSource[] = {&extSource};
        const Interface*       extNewDevice[] = {&extDevice, nullptr};
        const Interface*       extOfferArg[]  = {&extOffer};
        const Interface*       wlrNewSource[] = {&wlrSource};
        const Interface*       wlrNewDevice[] = {&wlrDevice, nullptr};
        const Interface*       wlrOfferArg[]  = {&wlrOffer};

        const Message          extManagerRequests[] = {
            {"create_data_source", "n", extNewSource},
            {"get_data_device", "no", extNewDevice},
            {"destroy", "", none},
        };
        const Message extDeviceRequests[] = {
            {"set_selection", "?o", none},
            {"destroy", "", none},
            {"set_primary_selection", "?o", none},
        };
        const Message extDeviceEvents[] = {
            {"data_offer", "n", extOfferArg},
            {"selection", "?o", extOfferArg},
            {"finished", "", none},
            {"primary_selection", "?o", extOfferArg},
        };
        const Message offerRequests[] = {
            {"receive", "sh", none},
            {"destroy", "", none},
        };
        const Message offerEvents[] = {
            {"offer", "s", none},
        };
        const Message sourceRequests[] = {
            {"offer", "s", none},
            {"destroy", "", none},
        };
        const Message sourceEvents[] = {
            {"send", "sh", none},
            {"cancelled", "", none},
        };

        const Message wlrManagerRequests[] = {
            {"create_data_source", "n", wlrNewSource},
            {"get_data_device", "no", wlrNewDevice},
            {"destroy", "2", none},
        };
        const Message wlrDeviceRequests[] = {
            {"set_selection", "?o", none},
            {"destroy", "", none},
            {"set_primary_selection", "2?o", none},
        };
        const Message wlrDeviceEvents[] = {
            {"data_offer", "n", wlrOfferArg},
            {"selection", "?o", wlrOfferArg},
            {"finished", "", none},
            {"primary_selection", "2?o", wlrOfferArg},
        };

        const Interface extSource  = {"ext_data_control_source_v1", 1, 2, sourceRequests, 2, sourceEvents};
        const Interface extOffer   = {"ext_data_control_offer_v1", 1, 2, offerRequests, 1, offerEvents};
        const Interface extDevice  = {"ext_data_control_device_v1", 1, 3, extDeviceRequests, 4, extDeviceEvents};
        const Interface extManager = {"ext_data_control_manager_v1", 1, 3, extManagerRequests, 0, nullptr};
        const Interface wlrSource  = {"zwlr_data_control_source_v1", 2, 2, sourceRequests, 2, sourceEvents};
        const Interface wlrOffer   = {"zwlr_data_control_offer_v1", 2, 2, offerRequests, 1, offerEvents};
        const Interface wlrDevice  = {"zwlr_data_control_device_v1", 2, 3, wlrDeviceRequests, 4, wlrDeviceEvents};
        const Interface wlrManager = {"zwlr_data_control_manager_v1", 2, 3, wlrManagerRequests, 0, nullptr};

    } // namespace

    const DataControl extDataControl = {&extManager, &extDevice, &extOffer, 1};
    const DataControl wlrDataControl = {&wlrManager, &wlrDevice, &wlrOffer, 2};

} // namespace ngosen::wayland
