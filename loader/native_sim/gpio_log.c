/*
 * Copyright (c) Arduino s.r.l. and/or its affiliated companies
 *
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Print the level of emulated GPIO outputs when they are written or
 * configured, so that tests can follow what a sketch does with its pins.
 * gpio_emul also calls the registered callbacks on input events and on
 * pin configuration: only pins currently configured as outputs are
 * printed.
 */

#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/gpio/gpio_emul.h>
#include <zephyr/init.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/util.h>

#define GPIO_EMUL_DEV(node_id) DEVICE_DT_GET(node_id),

static const struct device *const gpio_emul_devs[] = {
	DT_FOREACH_STATUS_OKAY(zephyr_gpio_emul, GPIO_EMUL_DEV)
};

static struct gpio_callback gpio_log_cbs[ARRAY_SIZE(gpio_emul_devs)];

static void gpio_log_handler(const struct device *port, struct gpio_callback *cb,
			     gpio_port_pins_t pins)
{
	gpio_port_pins_t outputs = 0;
	gpio_port_value_t values = 0;

	ARG_UNUSED(cb);

	if (gpio_port_get_direction(port, pins, NULL, &outputs) != 0) {
		return;
	}
	pins &= outputs;

	if (gpio_emul_output_get_masked(port, pins, &values) != 0) {
		return;
	}

	for (gpio_pin_t pin = 0; pins != 0U; pin++, pins >>= 1) {
		if ((pins & 1U) != 0U) {
			printk("[gpio] %s pin %u = %u\n", port->name, pin,
			       (unsigned int)((values >> pin) & 1U));
		}
	}
}

static int gpio_log_init(void)
{
	for (size_t i = 0; i < ARRAY_SIZE(gpio_emul_devs); i++) {
		if (!device_is_ready(gpio_emul_devs[i])) {
			continue;
		}
		gpio_init_callback(&gpio_log_cbs[i], gpio_log_handler, UINT32_MAX);
		(void)gpio_add_callback(gpio_emul_devs[i], &gpio_log_cbs[i]);
	}

	return 0;
}

SYS_INIT(gpio_log_init, APPLICATION, 99);
