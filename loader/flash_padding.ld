/*
 * Copyright (c) Arduino s.r.l. and/or its affiliated companies
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <zephyr/devicetree.h>

#if CONFIG_FLASH_BINARY_PADDING < 0

    /* Get the erase-block-size of the flash device chosen in Devicetree */

    #if !DT_HAS_CHOSEN(zephyr_flash)
        #error "Padding failed: No 'zephyr,flash' chosen node defined in Devicetree!"
    #endif

    #if !DT_NODE_HAS_PROP(DT_CHOSEN(zephyr_flash), erase_block_size)
        #error "Padding failed: The chosen flash node is missing 'erase-block-size'!"
    #endif

    #define PADDING_DIM DT_PROP(DT_CHOSEN(zephyr_flash), erase_block_size)

#elif CONFIG_FLASH_BINARY_PADDING > 0

    /* Use the user-defined padding size */
    #define PADDING_DIM CONFIG_FLASH_BINARY_PADDING

#endif

/* Pad the final image to an exact multiple of the requested size.
 *
 * zephyr_linker_sources(SECTIONS SORT_KEY zzz_flash_padding ...) (see
 * loader/CMakeLists.txt) places this section last among all
 * SECTIONS-injected snippets, and CONFIG_LINKER_LAST_SECTION_ID=n guarantees
 * that Zephyr's own mandatory ".last_section", which always follows, stays
 * empty. That makes this section the true end of the image.
 *
 * BYTE(0xFF) forces the section to contain real data (PROGBITS); a section
 * made up solely of a location-counter advance would be emitted as NOBITS
 * and silently dropped from the final .bin/.hex. FILL(0xFF) then pads
 * everything up to the next FLASH_BLOCK_SIZE boundary with 0xFF.
 */
SECTION_PROLOGUE(.flash_padding,,)
{
    FILL(0xFF);
    BYTE(0xFF);
    . = ALIGN(PADDING_DIM);
} GROUP_LINK_IN(ROMABLE_REGION)
