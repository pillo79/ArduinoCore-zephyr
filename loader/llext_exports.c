#include <string.h>
#include <strings.h>
#include <zephyr/llext/symbol.h>
#include <zephyr/usb/usb_device.h>
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <zephyr/kernel.h>

#define FORCE_EXPORT_SYM(name) \
       extern void name(void); \
       EXPORT_SYMBOL(name);

EXPORT_SYMBOL(strrchr);
EXPORT_SYMBOL(strstr);
EXPORT_SYMBOL(strncmp);
EXPORT_SYMBOL(strncpy);
EXPORT_SYMBOL(strcasecmp);
EXPORT_SYMBOL(strtoul);
EXPORT_SYMBOL(strcmp);
EXPORT_SYMBOL(strlen);
EXPORT_SYMBOL(strchr);
EXPORT_SYMBOL(strcat);
EXPORT_SYMBOL(memmove);

EXPORT_SYMBOL(k_malloc);
EXPORT_SYMBOL(malloc);
EXPORT_SYMBOL(realloc);
EXPORT_SYMBOL(calloc);
EXPORT_SYMBOL(free);
EXPORT_SYMBOL(rand);
EXPORT_SYMBOL(srand);

EXPORT_SYMBOL(atoi);
EXPORT_SYMBOL(atof);
EXPORT_SYMBOL(atol);
EXPORT_SYMBOL(isspace);
EXPORT_SYMBOL(isalnum);
EXPORT_SYMBOL(tolower);
EXPORT_SYMBOL(toupper);
EXPORT_SYMBOL(isalpha);
EXPORT_SYMBOL(iscntrl);
EXPORT_SYMBOL(isdigit);
EXPORT_SYMBOL(isgraph);
EXPORT_SYMBOL(isprint);
EXPORT_SYMBOL(isupper);
EXPORT_SYMBOL(islower);
EXPORT_SYMBOL(isxdigit);

EXPORT_SYMBOL(atan2);
EXPORT_SYMBOL(atan2f);
EXPORT_SYMBOL(atanf);
EXPORT_SYMBOL(asinf);
EXPORT_SYMBOL(acosf);
EXPORT_SYMBOL(sqrt);
EXPORT_SYMBOL(sqrtf);

EXPORT_SYMBOL(k_sched_lock);
EXPORT_SYMBOL(k_sched_unlock);

#if defined(CONFIG_USB_DEVICE_STACK)
EXPORT_SYMBOL(usb_enable);
EXPORT_SYMBOL(usb_disable);
#endif

EXPORT_SYMBOL(z_log_msg_runtime_vcreate);

#if defined(CONFIG_NETWORKING)
FORCE_EXPORT_SYM(net_if_foreach);
FORCE_EXPORT_SYM(net_if_down);
FORCE_EXPORT_SYM(net_if_get_by_iface);
FORCE_EXPORT_SYM(net_if_ipv4_maddr_add);
FORCE_EXPORT_SYM(net_if_ipv4_maddr_join);
FORCE_EXPORT_SYM(net_if_ipv4_set_gw);
FORCE_EXPORT_SYM(net_if_ipv4_addr_add);
FORCE_EXPORT_SYM(net_if_ipv4_set_netmask_by_addr);
FORCE_EXPORT_SYM(net_if_lookup_by_dev);
#endif

#if defined(CONFIG_NET_L2_ETHERNET)
FORCE_EXPORT_SYM(_net_l2_ETHERNET);
#endif

#if defined(CONFIG_NET_DHCPV4)
FORCE_EXPORT_SYM(net_dhcpv4_start);
#if defined(CONFIG_NET_DHCPV4_OPTION_CALLBACKS)
FORCE_EXPORT_SYM(net_dhcpv4_add_option_callback);
#endif
#endif

#if defined(CONFIG_NET_DHCPV4_SERVER)
FORCE_EXPORT_SYM(net_dhcpv4_server_start);
#endif

#if defined(CONFIG_NET_MGMT_EVENT)
FORCE_EXPORT_SYM(net_mgmt_add_event_callback);
FORCE_EXPORT_SYM(net_mgmt_event_wait_on_iface);
#endif

#if defined(CONFIG_MBEDTLS)
FORCE_EXPORT_SYM(tls_credential_add);
#endif

#if defined(CONFIG_WIFI)
FORCE_EXPORT_SYM(net_if_get_wifi_sta);
FORCE_EXPORT_SYM(net_if_get_wifi_sap);
FORCE_EXPORT_SYM(net_mgmt_NET_REQUEST_WIFI_CONNECT);
FORCE_EXPORT_SYM(net_mgmt_NET_REQUEST_WIFI_IFACE_STATUS);
FORCE_EXPORT_SYM(net_mgmt_NET_REQUEST_WIFI_AP_ENABLE);
#endif

#if defined(CONFIG_BT)
FORCE_EXPORT_SYM(bt_enable_raw);
FORCE_EXPORT_SYM(bt_send);
FORCE_EXPORT_SYM(bt_buf_get_tx);
FORCE_EXPORT_SYM(net_buf_simple_pull);
FORCE_EXPORT_SYM(net_buf_simple_add_mem);
FORCE_EXPORT_SYM(net_buf_simple_pull_mem);
FORCE_EXPORT_SYM(net_buf_unref);
#endif

#if defined(CONFIG_STACK_CANARIES)
FORCE_EXPORT_SYM(__stack_chk_guard);
FORCE_EXPORT_SYM(__stack_chk_fail);
#endif

#if defined(CONFIG_VIDEO)
FORCE_EXPORT_SYM(video_buffer_aligned_alloc);
FORCE_EXPORT_SYM(video_buffer_alloc);
FORCE_EXPORT_SYM(video_buffer_release);
#endif

#if defined(CONFIG_SHARED_MULTI_HEAP)
FORCE_EXPORT_SYM(shared_multi_heap_aligned_alloc);
FORCE_EXPORT_SYM(shared_multi_heap_free);
#endif

#if defined(CONFIG_NET_SOCKETS)
FORCE_EXPORT_SYM(getaddrinfo);
FORCE_EXPORT_SYM(socket);
FORCE_EXPORT_SYM(connect);
FORCE_EXPORT_SYM(send);
FORCE_EXPORT_SYM(recv);
FORCE_EXPORT_SYM(open);
FORCE_EXPORT_SYM(close);
FORCE_EXPORT_SYM(accept);
FORCE_EXPORT_SYM(bind);
FORCE_EXPORT_SYM(listen);
EXPORT_SYMBOL(exit);
FORCE_EXPORT_SYM(inet_pton);
FORCE_EXPORT_SYM(sendto);
FORCE_EXPORT_SYM(recvfrom);
FORCE_EXPORT_SYM(setsockopt);
#endif

#if defined(CONFIG_CDC_ACM_DTE_RATE_CALLBACK_SUPPORT)
FORCE_EXPORT_SYM(cdc_acm_dte_rate_callback_set);
#endif

#if defined(CONFIG_USB_DEVICE_STACK_NEXT)
FORCE_EXPORT_SYM(usbd_init);
FORCE_EXPORT_SYM(usbd_add_descriptor);
FORCE_EXPORT_SYM(usbd_device_set_bcd_usb);
FORCE_EXPORT_SYM(usbd_msg_register_cb);
FORCE_EXPORT_SYM(usbd_device_set_code_triple);
FORCE_EXPORT_SYM(usbd_register_all_classes);
FORCE_EXPORT_SYM(usbd_add_configuration);
FORCE_EXPORT_SYM(usbd_caps_speed);
FORCE_EXPORT_SYM(usbd_can_detect_vbus);
FORCE_EXPORT_SYM(usbd_enable);
FORCE_EXPORT_SYM(usbd_disable);
#endif

#if defined(CONFIG_SHARED_MULTI_HEAP)
FORCE_EXPORT_SYM(shared_multi_heap_alloc);
#endif

EXPORT_SYMBOL(k_timer_init);
EXPORT_SYMBOL(k_fatal_halt);
EXPORT_SYMBOL(k_work_schedule);
//FORCE_EXPORT_SYM(k_timer_user_data_set);
//FORCE_EXPORT_SYM(k_timer_start);

EXPORT_SYMBOL(sin);
EXPORT_SYMBOL(cos);
EXPORT_SYMBOL(tan);
EXPORT_SYMBOL(atan);
EXPORT_SYMBOL(pow);

EXPORT_SYMBOL(puts);
EXPORT_SYMBOL(putchar);
EXPORT_SYMBOL(printf);
EXPORT_SYMBOL(sprintf);
EXPORT_SYMBOL(snprintf);
EXPORT_SYMBOL(cbvprintf);
;
FORCE_EXPORT_SYM(abort);
#if defined(CONFIG_RING_BUFFER)
EXPORT_SYMBOL(ring_buf_get);
EXPORT_SYMBOL(ring_buf_peek);
EXPORT_SYMBOL(ring_buf_put);
#endif
EXPORT_SYMBOL(sys_clock_cycle_get_32);
FORCE_EXPORT_SYM(__aeabi_dcmpun);
FORCE_EXPORT_SYM(__aeabi_dcmple);
FORCE_EXPORT_SYM(__aeabi_d2lz);
FORCE_EXPORT_SYM(__aeabi_uldivmod);
FORCE_EXPORT_SYM(__aeabi_ui2d);
FORCE_EXPORT_SYM(__aeabi_dcmplt);
FORCE_EXPORT_SYM(__aeabi_ddiv);
FORCE_EXPORT_SYM(__aeabi_dmul);
FORCE_EXPORT_SYM(__aeabi_d2f);
FORCE_EXPORT_SYM(__aeabi_fcmpun);
FORCE_EXPORT_SYM(__aeabi_dadd);
FORCE_EXPORT_SYM(__aeabi_fcmple);
FORCE_EXPORT_SYM(__aeabi_idiv);
FORCE_EXPORT_SYM(__aeabi_dcmpgt);
FORCE_EXPORT_SYM(__aeabi_dsub);
FORCE_EXPORT_SYM(__aeabi_i2d);
FORCE_EXPORT_SYM(__aeabi_uidiv);
FORCE_EXPORT_SYM(__aeabi_l2d);
FORCE_EXPORT_SYM(__aeabi_d2uiz);
FORCE_EXPORT_SYM(__aeabi_uidivmod);
FORCE_EXPORT_SYM(__aeabi_dcmpeq);
FORCE_EXPORT_SYM(__aeabi_d2iz);
FORCE_EXPORT_SYM(__aeabi_f2d);
FORCE_EXPORT_SYM(__aeabi_idivmod);
FORCE_EXPORT_SYM(__aeabi_ldivmod);
FORCE_EXPORT_SYM(__aeabi_ul2f);
FORCE_EXPORT_SYM(__aeabi_dcmpge);
FORCE_EXPORT_SYM(__cxa_pure_virtual);
