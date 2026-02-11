/*
 * Copyright (c) 2025 Arduino SA
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <Arduino.h>

extern "C" {
    int analog_reference(uint8_t mode);
};

void analogReference(uint8_t mode)
{
  analog_reference(mode);
}