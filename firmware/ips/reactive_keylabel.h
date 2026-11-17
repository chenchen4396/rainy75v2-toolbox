/* SPDX-License-Identifier: MIT
 * Pure key-code → panel label mapping for the interactive pixel UI.
 *
 * Codes follow the native profile in profiles/keys.json (not raw HID for
 * modifiers):
 *   - normal keys: USB HID usage IDs (A=4, Enter=40, arrows 79..82, ...)
 *   - modifiers: negative 8-bit codes 0xF8..0xFF = -8..-1
 *       F8 CtrlL, F9 ShiftL, FA AltL, FB MetaL, FC CtrlR, FD ShiftR, FE AltR, FF MetaR
 *   - Fn keys: vendor codes 401..405
 *   - Win: 227
 * Anything unknown renders as "K<hex>" so it can be reported and mapped.
 *
 * Kept in its own header so tests/test_keylabel.py can compile it on the host.
 */
#ifndef REACTIVE_KEYLABEL_H
#define REACTIVE_KEYLABEL_H

static const char rk_basic[5][6] = {"ENTER", "ESC", "DEL", "TAB", "SPACE"};
static const char rk_mod[4][6] = {"CTRL", "SHIFT", "ALT", "WIN"};
static const char rk_caps[5] = "CAPS";
static const char rk_fn[3][4] = {"PRT", "SCR", "PAU"};
static const char rk_hexd[17] = "0123456789ABCDEF";
/* 0x2D..0x37 printable punctuation, shifted legends where the key is usually used. */
static const char rk_punct[] = "-+[]\\;'~,./";

/* k: native key code, buf: caller-provided 4-byte scratch for generated labels. */
static const char *rk_key_label(unsigned k, char *buf)
{
    unsigned n;
    /* Right/left modifiers can arrive sign-extended from a signed byte
     * (e.g. -7 -> 0xFFF9); normalise back to the native 0xF8..0xFF byte. */
    if (k >= 0xFFF8u && k <= 0xFFFFu) k &= 0xFFu;
    if (k >= 0x04u && k <= 0x1Du) { buf[0] = (char)('A' + (k - 0x04u)); buf[1] = 0; return buf; }
    if (k >= 0x1Eu && k <= 0x26u) { buf[0] = (char)('1' + (k - 0x1Eu)); buf[1] = 0; return buf; }
    if (k == 0x27u) { buf[0] = '0'; buf[1] = 0; return buf; }
    if (k >= 0x3Au && k <= 0x45u) {
        n = k - 0x3Au + 1u;
        buf[0] = 'F';
        if (n < 10u) { buf[1] = (char)('0' + n); buf[2] = 0; }
        else { buf[1] = '1'; buf[2] = (char)('0' + (n - 10u)); buf[3] = 0; }
        return buf;
    }
    if (k == 57u) return rk_caps;
    if (k >= 0x28u && k <= 0x2Cu) return rk_basic[k - 0x28u];
    if (k >= 0x2Du && k <= 0x37u) {                        /* printable punctuation */
        buf[0] = rk_punct[k - 0x2Du]; buf[1] = 0; return buf;
    }
    if (k >= 0x46u && k <= 0x48u) return rk_fn[k - 0x46u];
    if (k == 227u) return rk_mod[3];                       /* Windows key */
    if (k == 73u) return "INS";
    if (k == 76u) return "DEL";
    if (k == 0x4Bu) return "PGU";
    if (k == 0x4Eu) return "PGD";
    /* native modifier encoding: -8..-1 as unsigned bytes */
    if (k >= 0xF8u && k <= 0xFFu) {
        if (k == 0xF8u || k == 0xFCu) return rk_mod[0];    /* Ctrl L/R */
        if (k == 0xF9u || k == 0xFDu) return rk_mod[1];    /* Shift L/R */
        if (k == 0xFAu || k == 0xFEu) return rk_mod[2];    /* Alt L/R */
        return rk_mod[3];                                  /* Meta L/R */
    }
    if (k >= 401u && k <= 405u) {                          /* Fn layer keys */
        buf[0] = 'F'; buf[1] = 'N'; buf[2] = (char)('1' + (k - 401u)); buf[3] = 0;
        return buf;
    }
    if (k >= 0xE0u && k <= 0xE7u) return rk_mod[k & 3u];   /* HID-style fallback */
    if (k == 0x53u) return "NUM";
    if (k >= 0x54u && k <= 0x57u) return "KP";
    if (k == 0x58u) return "KPE";
    if (k >= 0x59u && k <= 0x63u) {
        buf[0] = 'K'; buf[1] = 'P';
        buf[2] = (k == 0x62u) ? '0' : (k == 0x63u) ? '.' : (char)('1' + (k - 0x59u));
        buf[3] = 0;
        return buf;
    }
    buf[0] = 'K';
    buf[1] = rk_hexd[(k >> 4) & 15u];
    buf[2] = rk_hexd[k & 15u];
    buf[3] = 0;
    return buf;
}

#endif /* REACTIVE_KEYLABEL_H */
