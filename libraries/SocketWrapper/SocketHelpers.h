#pragma once

#include "zephyr/net/dhcpv4.h"
#include <zephyr/kernel.h>
#include <zephyr/linker/sections.h>
#include <errno.h>
#include <stdio.h>

#include <zephyr/net/net_if.h>
#include <zephyr/net/net_core.h>
#include <zephyr/net/net_context.h>
#include <zephyr/net/net_mgmt.h>

#include <api/IPAddress.h>

#define DHCP_OPTION_NTP (42)

#define LOG_INF(...)

#ifdef SPECIALIZE_FOR_ETHERNET
enum EthernetLinkStatus {
  Unknown,
  LinkON,
  LinkOFF
};

enum EthernetHardwareStatus {
  EthernetNoHardware,
  EthernetOk
};
#endif

class NetworkInterface {
private:
    int iface_index = -1;

    uint8_t ntp_server[4];
    static struct net_mgmt_event_callback mgmt_cb;
    static struct net_dhcpv4_option_callback dhcp_cb;

    static void link_handler(struct net_mgmt_event_callback *cb,
                uint32_t mgmt_event,
                struct net_if *iface)
    {
        if (mgmt_event == NET_EVENT_IF_UP) {
            //printk("Interface %p is up\n", iface);
        } else {
            //printk("Interface %p is down\n", iface);
        }
    }

    static void addr_handler(struct net_mgmt_event_callback *cb,
                uint32_t mgmt_event,
                struct net_if *iface)
    {
        int i = 0;

        if (mgmt_event != NET_EVENT_IPV4_ADDR_ADD) {
            return;
        }

        //printk("Interface %p has IP\n", iface);

        for (i = 0; i < NET_IF_MAX_IPV4_ADDR; i++) {
            char buf[NET_IPV4_ADDR_LEN];

            if (iface->config.ip.ipv4->unicast[i].ipv4.addr_type !=
                                NET_ADDR_DHCP) {
                continue;
            }

            LOG_INF("   Address[%d]: %s", net_if_get_by_iface(iface),
                net_addr_ntop(AF_INET,
                    &iface->config.ip.ipv4->unicast[i].ipv4.address.in_addr,
                            buf, sizeof(buf)));
            LOG_INF("    Subnet[%d]: %s", net_if_get_by_iface(iface),
                net_addr_ntop(AF_INET,
                        &iface->config.ip.ipv4->unicast[i].netmask,
                        buf, sizeof(buf)));
            LOG_INF("    Router[%d]: %s", net_if_get_by_iface(iface),
                net_addr_ntop(AF_INET,
                            &iface->config.ip.ipv4->gw,
                            buf, sizeof(buf)));
            LOG_INF("Lease time[%d]: %u seconds", net_if_get_by_iface(iface),
                iface->config.dhcpv4.lease_time);
        }
    }

    static void option_handler(struct net_dhcpv4_option_callback *cb,
                size_t length,
                enum net_dhcpv4_msg_type msg_type,
                struct net_if *iface)
    {
        char buf[NET_IPV4_ADDR_LEN];

        LOG_INF("DHCP Option %d: %s", cb->option,
            net_addr_ntop(AF_INET, cb->data, buf, sizeof(buf)));
    }

    int dhcp()
    {
        net_mgmt_init_event_callback(&mgmt_cb, addr_handler, NET_EVENT_IPV4_ADDR_ADD);
        net_mgmt_add_event_callback(&mgmt_cb);

        net_mgmt_init_event_callback(&mgmt_cb, link_handler, NET_EVENT_IF_UP | NET_EVENT_IF_DOWN);
        net_mgmt_add_event_callback(&mgmt_cb);

        net_dhcpv4_init_option_callback(&dhcp_cb, option_handler,
                        DHCP_OPTION_NTP, ntp_server,
                        sizeof(ntp_server));

        net_dhcpv4_add_option_callback(&dhcp_cb);

        net_dhcpv4_start(net_if_get_by_index(iface_index));

        return 0;
    }

public:
    NetworkInterface(int iface_index) : iface_index(iface_index) {
    }
    ~NetworkInterface() {}
    IPAddress localIP() {
        return IPAddress(net_if_get_by_index(iface_index)->config.ip.ipv4->unicast[0].ipv4.address.in_addr.s_addr);
    }

    IPAddress subnetMask() {
        return IPAddress(net_if_get_by_index(iface_index)->config.ip.ipv4->unicast[0].netmask.s_addr);
    }
    IPAddress gatewayIP() {
        return IPAddress(net_if_get_by_index(iface_index)->config.ip.ipv4->gw.s_addr);
    }
    IPAddress dnsServerIP() {
        return arduino::INADDR_NONE;
    }

    IPAddress dnsIP(int n = 0);

    void setMACAddress(const uint8_t* mac);

    bool begin() {
        dhcp();
        // TODO: replace me with semaphore on the callback
        while (net_if_get_by_index(iface_index)->config.ip.ipv4->unicast[0].ipv4.address.in_addr.s_addr == 0) {
            k_sleep(K_MSEC(100));
        }
        return 0;
    }

    // Manual functions
    // net_if_ipv4_set_netmask_by_addr(iface, &addr4, &nm);
    // net_if_ipv4_addr_add(iface, &addr4, NET_ADDR_MANUAL, 0);

#ifdef SPECIALIZE_FOR_ETHERNET
    EthernetLinkStatus linkStatus() {
        if (net_if_is_up(net_if_get_by_index(iface_index))) {
            return LinkON;
        } else {
            return LinkOFF;
        }
    }

    EthernetHardwareStatus hardwareStatus() {
        const struct device *const dev = DEVICE_DT_GET(DT_COMPAT_GET_ANY_STATUS_OKAY(ethernet_phy));
        if (device_is_ready(dev)) {
            return EthernetOk;
        } else {
            return EthernetNoHardware;
        }
    }
#endif
};