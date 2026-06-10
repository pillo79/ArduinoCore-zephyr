/*
 * Copyright (c) Arduino s.r.l. and/or its affiliated companies
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

#include <zephyr/drivers/clock_control.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/drivers/pinctrl.h>
#include <zephyrPinctrl.h>

namespace zephyr {
namespace arduino {

inline int init_pwm_ref_clock(const struct device *clock_dev, const struct pwm_dt_spec &clock_pwm,
							  size_t state_pin_idx = PINCTRL_STATE_DEFAULT) {

	int ret = init_dev_apply_channel_pinctrl(clock_pwm.dev, state_pin_idx);
	if (ret < 0) {
		return ret;
	}

	if (clock_control_get_status(clock_dev, (clock_control_subsys_t)0) != CLOCK_CONTROL_STATUS_ON) {
		return clock_control_on(clock_dev, (clock_control_subsys_t)0);
	}

	return 0;
}

} // namespace arduino
} // namespace zephyr
