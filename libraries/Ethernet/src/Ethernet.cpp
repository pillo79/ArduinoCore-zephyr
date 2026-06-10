/*
 * Copyright (c) Arduino s.r.l. and/or its affiliated companies
 *
 * SPDX-License-Identifier: LGPL-2.1-or-later
 */

#include "Ethernet.h"
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/pwm.h>
#include <zephyrClockInit.hpp>
#include <zephyrPinctrl.h>

#if DT_HAS_COMPAT_STATUS_OKAY(ethernet_phy)
#define ETH_PHY_NODE DT_INST(0, ethernet_phy)
static const struct device *eth_phy_dev = DEVICE_DT_GET(ETH_PHY_NODE);

#if DT_HAS_CHOSEN(arduino_eth_clock)
#define CLOCK_NODE DT_CHOSEN(arduino_eth_clock)
static const struct pwm_dt_spec CLOCK_PWM = PWM_DT_SPEC_GET(CLOCK_NODE);
#define INIT_ETH_CLOCK() zephyr::arduino::init_pwm_ref_clock(DEVICE_DT_GET(CLOCK_NODE), CLOCK_PWM)
#else
/* Some boards provide ETH ref clock on a dedicated pin, not via a PWM alias. */
#define INIT_ETH_CLOCK() 0
#endif

int EthernetClass::begin(uint8_t *mac, unsigned long timeout, unsigned long responseTimeout) {
	(void)timeout;
	(void)responseTimeout;
	if (hardwareStatus() != EthernetOk) {
		return 0;
	}
	setMACAddress(mac);
	return NetworkInterface::begin();
}

int EthernetClass::maintain() {
	return 0; // DHCP_CHECK_NONE
}

int EthernetClass::begin(uint8_t *mac, IPAddress ip) {
	IPAddress dns = ip;
	dns[3] = 1;

	auto ret = begin(mac, ip, dns);
	return ret;
}

int EthernetClass::begin(uint8_t *mac, IPAddress ip, IPAddress dns) {
	IPAddress gateway = ip;
	gateway[3] = 1;

	auto ret = begin(mac, ip, dns, gateway);
	return ret;
}

int EthernetClass::begin(uint8_t *mac, IPAddress ip, IPAddress dns, IPAddress gateway) {
	IPAddress subnet(255, 255, 255, 0);
	auto ret = begin(mac, ip, dns, gateway, subnet);
	return ret;
}

int EthernetClass::begin(uint8_t *mac, IPAddress ip, IPAddress dns, IPAddress gateway,
						 IPAddress subnet, unsigned long timeout, unsigned long responseTimeout) {
	(void)timeout;
	(void)responseTimeout;
	if (hardwareStatus() != EthernetOk) {
		return 0;
	}
	setMACAddress(mac);
	config(ip, dns, gateway, subnet);
	if (!net_if_is_up(netif)) {
		net_if_up(netif);
	}
	return 1;
}

EthernetLinkStatus EthernetClass::linkStatus() {
	if (hardwareStatus() == EthernetOk) {
		if (net_if_is_up(netif)) {
			return LinkON;
		} else {
			return LinkOFF;
		}
	}

	return LinkOFF;
}

EthernetHardwareStatus EthernetClass::hardwareStatus() {
	if (netif == nullptr) {
		netif = net_if_get_first_ethernet();
	}

	if (netif == nullptr) {
		return EthernetNoHardware;
	}

	if (!net_if_is_up(netif)) {
		/* since we don't perform hardware setup only once in begin() but here, avoid doing it again
		 * every time we call this function if network is already up */
		int ret = INIT_ETH_CLOCK();
		if (ret < 0) {
			return EthernetNoHardware;
		}

		ret = zephyr::arduino::init_dev_apply_pinctrl(eth_phy_dev);
		if (ret < 0) {
			return EthernetNoHardware;
		}
	}
	return EthernetOk;
}

void EthernetClass::setRetransmissionTimeout(uint16_t milliseconds) {
	(void)milliseconds;
}

void EthernetClass::setRetransmissionCount(uint8_t num) {
	(void)num;
}

EthernetClass Ethernet;
#endif
