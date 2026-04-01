/*
 * Copyright (c) Arduino s.r.l. and/or its affiliated companies
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * This file provides long-call trampolines for the LLEXT extension.
 * Precompiled toolchain libraries emit R_ARM_THM_JUMP24 / R_ARM_THM_CALL
 * relocations for the export libc functions. These have a +/-16 MB range
 * limit which is exceeded when the LLEXT is loaded in a different memory
 * region than the kernel.
 *
 * Each trampoline is a naked function that loads the full 32-bit target
 * address into ip (r12) and branches to it. This preserves all argument
 * registers (r0-r3, s0-s15/d0-d7) and lr, so the callee returns directly to
 * the original call site. Even though the return types are not declared here,
 * the caller and callee agree on the calling convention, so the return value
 * is passed back correctly in r0/s0/d0 as appropriate.
 */

#ifndef CONFIG_ARM
#error "LLEXT trampolines are only supported on ARM"
#endif

/*
 * TRAMPOLINE — emit a register-preserving veneer for __real_<name>.
 *
 * Uses ip (r12), the intra-procedure-call scratch register (AAPCS),
 * with an inline literal pool so every trampoline is self-contained.
 * BX (not BLX) leaves lr untouched: the callee returns to the
 * original caller.
 */
#define TRAMPOLINE(name)                                                                           \
	__attribute__((naked)) void name(void) {                                                       \
		__asm__("ldr ip, 1f\n\t"                                                                   \
				"bx  ip\n\t"                                                                       \
				".align 2\n"                                                                       \
				"1: .word __real_" #name "\n");                                                    \
	}

/* ARM EABI functions */
TRAMPOLINE(__aeabi_read_tp);

/* string.h */
TRAMPOLINE(memcpy);
TRAMPOLINE(memmove);
TRAMPOLINE(strlen);
TRAMPOLINE(strnlen);
TRAMPOLINE(strchr);
TRAMPOLINE(strrchr);
TRAMPOLINE(strstr);
TRAMPOLINE(strcmp);
TRAMPOLINE(strncmp);
TRAMPOLINE(strcasecmp);
TRAMPOLINE(strncpy);
TRAMPOLINE(strcat);
TRAMPOLINE(strcpy);
TRAMPOLINE(memcmp);
TRAMPOLINE(memset);
TRAMPOLINE(strtok);

/* stdlib.h - conversion */
TRAMPOLINE(strtod);
TRAMPOLINE(strtol);
TRAMPOLINE(strtoul);
TRAMPOLINE(atoi);
TRAMPOLINE(atof);
TRAMPOLINE(atol);

/* stdlib.h - memory */
TRAMPOLINE(malloc);
TRAMPOLINE(realloc);
TRAMPOLINE(calloc);
TRAMPOLINE(free);

/* stdlib.h - random */
TRAMPOLINE(rand);
TRAMPOLINE(srand);

/* ctype.h */
TRAMPOLINE(isspace);
TRAMPOLINE(isalnum);
TRAMPOLINE(tolower);
TRAMPOLINE(toupper);
TRAMPOLINE(isalpha);
TRAMPOLINE(iscntrl);
TRAMPOLINE(isdigit);
TRAMPOLINE(isgraph);
TRAMPOLINE(isprint);
TRAMPOLINE(isupper);
TRAMPOLINE(islower);
TRAMPOLINE(isxdigit);

/* math.h - double */
TRAMPOLINE(acos);
TRAMPOLINE(asin);
TRAMPOLINE(atan);
TRAMPOLINE(atan2);
TRAMPOLINE(cos);
TRAMPOLINE(exp);
TRAMPOLINE(exp2);
TRAMPOLINE(ldexp);
TRAMPOLINE(log10);
TRAMPOLINE(log2);
TRAMPOLINE(log);
TRAMPOLINE(pow);
TRAMPOLINE(sin);
TRAMPOLINE(sqrt);
TRAMPOLINE(tan);

/* math.h - float */
TRAMPOLINE(acosf);
TRAMPOLINE(asinf);
TRAMPOLINE(atanf);
TRAMPOLINE(atan2f);
TRAMPOLINE(cosf);
TRAMPOLINE(logf);
TRAMPOLINE(sinf);
TRAMPOLINE(sqrtf);
TRAMPOLINE(tanf);

/* stdio.h */
TRAMPOLINE(puts);
TRAMPOLINE(putchar);
TRAMPOLINE(vsnprintf);

/* stdlib.h - atexit */
TRAMPOLINE(atexit);

/* process control - noreturn */
__attribute__((noreturn)) TRAMPOLINE(abort);
__attribute__((noreturn)) TRAMPOLINE(exit);
__attribute__((noreturn)) TRAMPOLINE(_exit);
