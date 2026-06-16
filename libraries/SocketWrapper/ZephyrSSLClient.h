/*
 * Copyright (c) Arduino s.r.l. and/or its affiliated companies
 *
 * SPDX-License-Identifier: LGPL-2.1-or-later
 */

#pragma once

#include "SocketWrapper.h"
#include "api/Client.h"
#include "unistd.h"
#include "zephyr/sys/printk.h"
#include "ZephyrClient.h"

#if defined(CONFIG_MBEDTLS) && !defined(CONFIG_MBEDTLS_INIT)
#define ARDUINO_MANAGES_MBEDTLS
#endif

#if defined(CONFIG_NET_SOCKETS_SOCKOPT_TLS)
class ZephyrSSLClient : public ZephyrClient {

private:
#if defined(ARDUINO_MANAGES_MBEDTLS)
	bool mbedtls_is_ready = false;
#endif
public:
	ZephyrSSLClient();

	int connect(const char *host, uint16_t port) override {
#if defined(ARDUINO_MANAGES_MBEDTLS)
		if (!mbedtls_is_ready) {
			return 0;
		}
#endif
		return connectSSL(host, port, nullptr);
	}

	int connect(const char *host, uint16_t port, const char *cert) {
#if defined(ARDUINO_MANAGES_MBEDTLS)
		if (!mbedtls_is_ready) {
			return 0;
		}
#endif
		return connectSSL(host, port, cert);
	}
};
#endif
