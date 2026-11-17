/* SPDX-License-Identifier: MIT
 * Stub RTC used by the pixel/typing builds: the animated character screens do not show
 * a clock, so the whole time-keeping module is dropped to save flash space.
 */
#include "native_ui.h"

void rtc_tick(u32 now) { (void)now; }
unsigned rtc_schedule(const u8 *p, u16 seq, u32 now) { (void)p; (void)now; return seq & 1u; }
u32 rtc_value(void) { return 0; }
unsigned rtc_state(void) { return 0; }
int rtc_receive(const u8 *p, u16 n, u32 now) { (void)p; (void)n; (void)now; return 0; }
