// Copyright (c) 2026 Joost Yervante Damad
// SPDX-License-Identifier: 0BSD
//
// rigfw -- the host joystick openMSX does not have, as a REAL USB device.
//
// tools/rigstick.swift is the same rig as a CoreHID virtual device, and it is
// inert without an Apple-issued entitlement. Joost's fallback ruling
// (2026-09-23): a native-USB board flashed as a HID joystick needs nothing from
// Apple -- macOS sees a genuine joystick and SDL (inside openMSX) enumerates it.
// The board is an RP2040-Zero (bought 2026-09-24).
//
// ONE composite USB device, three interfaces:
//   * HID joystick -- rigstick's descriptor, byte for byte: 2 signed 8-bit axes
//     + 4 buttons. Usage(Joystick), not Gamepad, so SDL hands openMSX the RAW
//     axes rather than remapping them through its controller database.
//   * HID mouse    -- relative motion + 2 buttons, for PAD/PDL (openMSX's
//     touchpad/paddle/arkanoidpad take HOST mouse motion).
//   * CDC serial   -- the command channel.
//
// THE COMMAND LANGUAGE IS rigstick's, so a probe does not care which rig it
// drives: one command per line, answered `OK` once the report is queued (or
// `ERR: <line>`), so a probe synchronises instead of sleeping.
//   centre|up|down|left|right|upleft|upright|downleft|downright
//   trig1 on|off   trig2 on|off       -- a trigger keeps the direction
//   state X Y B                        -- X,Y in -127..127, B in 0..15
//   move DX DY                         -- relative mouse motion, -127..127
//   mbtn1 on|off   mbtn2 on|off        -- mouse buttons
//   id                                 -- answers `rigfw 1` then `OK`
//   quit|exit                          -- answers `OK` (the board keeps running)
// ⚠️ A DIRECTION REPLACES THE AXES AND A TRIGGER DOES NOT (rigstick's load-
// bearing rule): `up` then `trig1 on` is UP and FIRING; `upleft` is a diagonal.
//
// Build/flash (arduino-pico core, Adafruit TinyUSB stack):
//   arduino-cli compile -b rp2040:rp2040:waveshare_rp2040_zero:usbstack=tinyusb tools/rigfw
//   arduino-cli upload  -b rp2040:rp2040:waveshare_rp2040_zero:usbstack=tinyusb -p /dev/cu.usbmodemXXXX tools/rigfw
#include <Adafruit_TinyUSB.h>

static const uint8_t joy_desc[] = {
  0x05, 0x01,  // Usage Page (Generic Desktop)
  0x09, 0x04,  // Usage (Joystick)
  0xA1, 0x01,  // Collection (Application)
  0xA1, 0x00,  //   Collection (Physical)
  0x09, 0x30,  //     Usage (X)
  0x09, 0x31,  //     Usage (Y)
  0x15, 0x81,  //     Logical Minimum (-127)
  0x25, 0x7F,  //     Logical Maximum (127)
  0x75, 0x08,  //     Report Size (8)
  0x95, 0x02,  //     Report Count (2)
  0x81, 0x02,  //     Input (Data,Var,Abs)
  0xC0,        //   End Collection
  0x05, 0x09,  //   Usage Page (Button)
  0x19, 0x01,  //   Usage Minimum (Button 1)
  0x29, 0x04,  //   Usage Maximum (Button 4)
  0x15, 0x00,  //   Logical Minimum (0)
  0x25, 0x01,  //   Logical Maximum (1)
  0x75, 0x01,  //   Report Size (1)
  0x95, 0x04,  //   Report Count (4)
  0x81, 0x02,  //   Input (Data,Var,Abs)
  0x75, 0x04,  //   Report Size (4)
  0x95, 0x01,  //   Report Count (1)
  0x81, 0x03,  //   Input (Cnst,Var,Abs)  -- padding
  0xC0,        // End Collection
};
static const uint8_t mouse_desc[] = { TUD_HID_REPORT_DESC_MOUSE() };

Adafruit_USBD_HID joy(joy_desc, sizeof joy_desc, HID_ITF_PROTOCOL_NONE, 2, false);
Adafruit_USBD_HID mouse(mouse_desc, sizeof mouse_desc, HID_ITF_PROTOCOL_MOUSE, 2, false);

static int8_t stick_x = 0, stick_y = 0;
static uint8_t stick_b = 0;   // bit 0 = trigger 1, bit 1 = trigger 2
static uint8_t mouse_b = 0;

struct Dir { const char *name; int8_t x, y; };
static const Dir dirs[] = {
  {"centre", 0, 0}, {"center", 0, 0}, {"none", 0, 0},
  {"up", 0, -127}, {"down", 0, 127}, {"left", -127, 0}, {"right", 127, 0},
  {"upleft", -127, -127}, {"upright", 127, -127},
  {"downleft", -127, 127}, {"downright", 127, 127},
};

// Wait (bounded) until an interface can take a report. false = the host is
// not polling it, which the caller reports rather than claiming `OK`.
static bool wait_ready(Adafruit_USBD_HID &h) {
  for (int i = 0; i < 200; i++) {
    if (h.ready()) return true;
    delay(1);
  }
  return false;
}

static bool send_stick() {
  if (!wait_ready(joy)) return false;
  uint8_t r[3] = { (uint8_t)stick_x, (uint8_t)stick_y, (uint8_t)(stick_b & 0x0F) };
  return joy.sendReport(0, r, sizeof r);
}

static bool send_mouse(int8_t dx, int8_t dy) {
  if (!wait_ready(mouse)) return false;
  return mouse.mouseReport(0, mouse_b, dx, dy, 0, 0);
}

// "on"/"off" and rigstick's synonyms. -1 = neither.
static int on_off(const char *s) {
  if (!strcmp(s, "on") || !strcmp(s, "1") || !strcmp(s, "true") || !strcmp(s, "down")) return 1;
  if (!strcmp(s, "off") || !strcmp(s, "0") || !strcmp(s, "false") || !strcmp(s, "up")) return 0;
  return -1;
}

// Strict integer parse in [lo, hi]; false on anything else.
static bool to_int(const char *s, long lo, long hi, long *out) {
  if (!s || !*s) return false;
  char *end;
  long v = strtol(s, &end, 10);
  if (*end || v < lo || v > hi) return false;
  *out = v;
  return true;
}

// 1 = OK, 0 = not a command (ERR), -1 = a command the host did not take.
static int run(char *line) {
  char *f[5];
  int n = 0;
  for (char *t = strtok(line, " \t"); t && n < 5; t = strtok(nullptr, " \t")) {
    for (char *p = t; *p; p++) *p = tolower(*p);
    f[n++] = t;
  }
  if (n == 0 || strtok(nullptr, " \t")) return 0;
  const char *h = f[0];

  if (!strcmp(h, "quit") || !strcmp(h, "exit")) return n == 1;
  if (!strcmp(h, "id")) {
    if (n != 1) return 0;
    Serial.println("rigfw 1");
    return 1;
  }
  for (const Dir &d : dirs) {
    if (!strcmp(h, d.name)) {
      if (n != 1) return 0;
      stick_x = d.x;
      stick_y = d.y;
      return send_stick() ? 1 : -1;
    }
  }
  if (!strcmp(h, "trig1") || !strcmp(h, "trig2")) {
    int on = n == 2 ? on_off(f[1]) : -1;
    if (on < 0) return 0;
    uint8_t bit = h[4] == '1' ? 1 : 2;
    stick_b = on ? (stick_b | bit) : (stick_b & ~bit);
    return send_stick() ? 1 : -1;
  }
  if (!strcmp(h, "state")) {
    long x, y, b;
    if (n != 4 || !to_int(f[1], -127, 127, &x) || !to_int(f[2], -127, 127, &y)
        || !to_int(f[3], 0, 15, &b)) return 0;
    stick_x = x;
    stick_y = y;
    stick_b = b;
    return send_stick() ? 1 : -1;
  }
  if (!strcmp(h, "move")) {
    long dx, dy;
    if (n != 3 || !to_int(f[1], -127, 127, &dx) || !to_int(f[2], -127, 127, &dy)) return 0;
    return send_mouse(dx, dy) ? 1 : -1;
  }
  if (!strcmp(h, "mbtn1") || !strcmp(h, "mbtn2")) {
    int on = n == 2 ? on_off(f[1]) : -1;
    if (on < 0) return 0;
    uint8_t bit = h[4] == '1' ? MOUSE_BUTTON_LEFT : MOUSE_BUTTON_RIGHT;
    mouse_b = on ? (mouse_b | bit) : (mouse_b & ~bit);
    return send_mouse(0, 0) ? 1 : -1;
  }
  return 0;
}

void setup() {
  TinyUSBDevice.setManufacturerDescriptor("zerobas");
  TinyUSBDevice.setProductDescriptor("zerobas rig stick");
  joy.begin();
  mouse.begin();
  Serial.begin(115200);
  // arduino-pico starts USB before setup(): re-enumerate so the host sees the
  // HID interfaces added above.
  if (TinyUSBDevice.mounted()) {
    TinyUSBDevice.detach();
    delay(10);
    TinyUSBDevice.attach();
  }
}

void loop() {
  static char buf[64];
  static size_t len = 0;
  static bool overflow = false;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c != '\n') {
      if (len < sizeof buf - 1) buf[len++] = c;
      else overflow = true;
      continue;
    }
    buf[len] = 0;
    if (overflow) {
      Serial.println("ERR: line too long");
    } else {
      char copy[sizeof buf];
      strcpy(copy, buf);
      int r = run(buf);
      if (r > 0) Serial.println("OK");
      else if (r < 0) Serial.println("ERR: host not polling");
      else { Serial.print("ERR: "); Serial.println(copy); }
    }
    len = 0;
    overflow = false;
  }
}
