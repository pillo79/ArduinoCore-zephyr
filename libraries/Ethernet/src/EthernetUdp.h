/*
 * Copyright (c) Arduino s.r.l. and/or its affiliated companies
 *
 * SPDX-License-Identifier: LGPL-2.1-or-later
 */

#pragma once
#include <ZephyrUDP.h>

#if DT_HAS_COMPAT_STATUS_OKAY(ethernet_phy)
using EthernetUDP = ZephyrUDP;
#endif
