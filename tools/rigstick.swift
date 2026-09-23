// Copyright (c) 2026 Joost Yervante Damad
// SPDX-License-Identifier: 0BSD
//
// rigstick -- the host joystick openMSX does not have (ruling 4's rig).
//
// D-RIGBLOCK measured why `STICK`, `STRIG` and `PAD` are stuck: openMSX 21.0
// carries NO key-joystick pluggable at all (the string `keyjoystick` occurs 0
// times in its binary), and `joystick1` is created from SDL's HOST
// enumeration -- the binary ships SDL's `##joystick-table` controller
// database. So no amount of Tcl reaches a joystick; the only route is a device
// the HOST reports. Joost, 2026-09-23: "write some kind of osx tool that can
// be used as device/interface to test stick trig pad".
//
// This publishes a virtual HID joystick through CoreHID and drives it from
// stdin, one command per line, answering `OK` to each so a probe can
// synchronise instead of sleeping. SDL reads joystick state from the HID layer
// rather than from window events, which is what makes it usable by a HEADLESS
// openMSX -- the reason key injection could never have worked.
//
//     make rigstick                    # build
//     ./build/rigstick --selftest      # pure-logic arms, no device needed
//     ./build/rigstick --probe         # can this machine create the device?
//     ./build/rigstick                 # serve commands on stdin
//
// 🔴 INERT UNTIL AN ENTITLEMENT EXISTS, AND IT SAYS SO RATHER THAN FAILING
// QUIETLY. `com.apple.developer.hid.virtual.device` is a RESTRICTED
// entitlement: unsigned, `HIDVirtualDevice(properties:)` returns nil with
// nothing in the log; ad-hoc signed while CLAIMING it, AMFI SIGKILLs the
// process before `main` (measured 2026-09-23, both directions). It takes an
// Apple-issued provisioning profile carrying the HID-virtual-device
// capability. `--probe` names which of those two happened.
import CoreHID
import Foundation

// --- the report descriptor ---------------------------------------------------
// A plain 2-axis, 4-button joystick. Usage(Joystick) rather than
// Usage(Gamepad) ON PURPOSE: a gamepad gets remapped through SDL's controller
// database, and an MSX stick wants the RAW axes and buttons openMSX's
// JoystickDevice reads. Axes are signed 8-bit so -127/+127 are unambiguously
// past any deadzone.
// Report layout, 3 bytes: [X][Y][buttons:4 + padding:4].
enum Descriptor {
    static let bytes: [UInt8] = [
        0x05, 0x01,             // Usage Page (Generic Desktop)
        0x09, 0x04,             // Usage (Joystick)
        0xA1, 0x01,             // Collection (Application)
        0xA1, 0x00,             //   Collection (Physical)
        0x09, 0x30,             //     Usage (X)
        0x09, 0x31,             //     Usage (Y)
        0x15, 0x81,             //     Logical Minimum (-127)
        0x25, 0x7F,             //     Logical Maximum (127)
        0x75, 0x08,             //     Report Size (8)
        0x95, 0x02,             //     Report Count (2)
        0x81, 0x02,             //     Input (Data,Var,Abs)
        0xC0,                   //   End Collection
        0x05, 0x09,             //   Usage Page (Button)
        0x19, 0x01,             //   Usage Minimum (Button 1)
        0x29, 0x04,             //   Usage Maximum (Button 4)
        0x15, 0x00,             //   Logical Minimum (0)
        0x25, 0x01,             //   Logical Maximum (1)
        0x75, 0x01,             //   Report Size (1)
        0x95, 0x04,             //   Report Count (4)
        0x81, 0x02,             //   Input (Data,Var,Abs)
        0x75, 0x04,             //   Report Size (4)
        0x95, 0x01,             //   Report Count (1)
        0x81, 0x03,             //   Input (Cnst,Var,Abs)  -- padding
        0xC0,                   // End Collection
    ]
}

// --- the stick's state -------------------------------------------------------
struct Stick: Equatable {
    var x: Int8 = 0
    var y: Int8 = 0
    var buttons: UInt8 = 0      // bit 0 = trigger 1, bit 1 = trigger 2

    var report: Data { Data([UInt8(bitPattern: x), UInt8(bitPattern: y),
                             buttons & 0x0F]) }
}

// --- the command language ----------------------------------------------------
// Deliberately tiny and line-oriented: a probe writes a word and reads `OK`.
// ⚠️ A DIRECTION REPLACES THE AXES AND A TRIGGER DOES NOT. `up` then `trig1 on`
// must leave the stick UP and FIRING, which is the whole point of a rig for
// `STICK`+`STRIG`; `up` then `left` is a fresh direction, not a diagonal, and
// `upleft` is how a diagonal is asked for.
enum Command: Equatable {
    case set(Stick)             // a fully-resolved state
    case direction(Int8, Int8)  // axes only, buttons untouched
    case trigger(Int, Bool)     // one button, axes untouched
    case quit
}

enum Parser {
    static let directions: [String: (Int8, Int8)] = [
        "centre": (0, 0), "center": (0, 0), "none": (0, 0),
        "up": (0, -127), "down": (0, 127),
        "left": (-127, 0), "right": (127, 0),
        "upleft": (-127, -127), "upright": (127, -127),
        "downleft": (-127, 127), "downright": (127, 127),
    ]

    /// nil = not a command this tool understands. The caller reports that as
    /// an error rather than ignoring it: a rig that silently drops a line
    /// would let a probe score a direction it never set.
    static func parse(_ line: String) -> Command? {
        let f = line.lowercased().split(separator: " ").map(String.init)
        guard let head = f.first else { return nil }
        if head == "quit" || head == "exit" { return f.count == 1 ? .quit : nil }
        if let d = directions[head] {
            return f.count == 1 ? .direction(d.0, d.1) : nil
        }
        if head == "trig1" || head == "trig2" {
            guard f.count == 2, let on = onOff(f[1]) else { return nil }
            return .trigger(head == "trig1" ? 0 : 1, on)
        }
        if head == "state" {
            guard f.count == 4, let x = Int(f[1]), let y = Int(f[2]),
                  let b = Int(f[3]), (-127...127).contains(x),
                  (-127...127).contains(y), (0...15).contains(b)
            else { return nil }
            return .set(Stick(x: Int8(x), y: Int8(y), buttons: UInt8(b)))
        }
        return nil
    }

    static func onOff(_ s: String) -> Bool? {
        switch s {
        case "on", "1", "true", "down": return true
        case "off", "0", "false", "up": return false
        default: return nil
        }
    }

    static func apply(_ c: Command, to s: Stick) -> Stick {
        var out = s
        switch c {
        case .set(let n): out = n
        case .direction(let x, let y): out.x = x; out.y = y
        case .trigger(let i, let on):
            if on { out.buttons |= UInt8(1 << i) }
            else { out.buttons &= ~UInt8(1 << i) }
        case .quit: break
        }
        return out
    }
}

// --- the device --------------------------------------------------------------
final class Silent: HIDVirtualDeviceDelegate {
    func hidVirtualDevice(_ d: HIDVirtualDevice,
                          receivedSetReportRequestOfType t: HIDReportType,
                          id: HIDReportID?, data: Data) async throws {}
    func hidVirtualDevice(_ d: HIDVirtualDevice,
                          receivedGetReportRequestOfType t: HIDReportType,
                          id: HIDReportID?, maxSize: Int) async throws -> Data {
        Data()
    }
}

func makeDevice() -> HIDVirtualDevice? {
    HIDVirtualDevice(properties: .init(
        descriptor: Data(Descriptor.bytes), vendorID: 0x5A5A, productID: 0x0001,
        transport: .virtual, product: "zerobas rig stick",
        manufacturer: "zerobas", uniqueID: "zerobas-rig-0"))
}

// --- selftest ----------------------------------------------------------------
// 🔴 EVERY ARM HERE RUNS WITHOUT THE ENTITLEMENT, on purpose: the parser and
// the report encoder are the parts a probe's verdict rests on, and they must
// be checkable on a machine that cannot create the device at all. What the
// selftest CANNOT cover is said out loud at the end rather than implied.
func selftest() -> Int32 {
    var fails = 0
    func arm(_ label: String, _ ok: Bool) {
        if !ok { print("  selftest: FAIL \(label)"); fails += 1 }
    }

    arm("the descriptor is a closed pair of collections",
        Descriptor.bytes.first == 0x05 && Descriptor.bytes.last == 0xC0)
    arm("the report is exactly 3 bytes", Stick().report.count == 3)
    arm("centre encodes as all zero", Array(Stick().report) == [0, 0, 0])
    // A NEGATIVE axis must survive the trip through UInt8 unchanged -- this is
    // the one place a sign error would turn `left` into `right` and still look
    // like a working rig.
    arm("left encodes as 0x81, not 0x7F",
        Array(Stick(x: -127, y: 0, buttons: 0).report)[0] == 0x81)
    arm("up encodes as 0x81 on the Y axis",
        Array(Stick(x: 0, y: -127, buttons: 0).report)[1] == 0x81)
    arm("the button nibble is masked to 4 bits",
        Array(Stick(x: 0, y: 0, buttons: 0xF0).report)[2] == 0x00)

    arm("a direction parses", Parser.parse("up") == .direction(0, -127))
    arm("a diagonal is its own word",
        Parser.parse("downright") == .direction(127, 127))
    arm("a trigger parses", Parser.parse("trig2 on") == .trigger(1, true))
    arm("a raw state parses",
        Parser.parse("state -127 0 3") == .set(Stick(x: -127, y: 0, buttons: 3)))
    arm("quit parses", Parser.parse("quit") == .quit)

    // NEGATIVE CONTROLS. Without these the parser could return a command for
    // anything at all and every arm above would still pass.
    arm("NEGATIVE: an unknown word is refused", Parser.parse("wiggle") == nil)
    arm("NEGATIVE: an empty line is refused", Parser.parse("") == nil)
    arm("NEGATIVE: a direction with an argument is refused",
        Parser.parse("up 1") == nil)
    arm("NEGATIVE: a trigger with no on/off is refused",
        Parser.parse("trig1") == nil)
    arm("NEGATIVE: a trigger with a junk argument is refused",
        Parser.parse("trig1 maybe") == nil)
    arm("NEGATIVE: an out-of-range axis is refused",
        Parser.parse("state -128 0 0") == nil)
    arm("NEGATIVE: an out-of-range button mask is refused",
        Parser.parse("state 0 0 16") == nil)
    arm("NEGATIVE: a short state is refused", Parser.parse("state 0 0") == nil)

    // 🔴 A TRIGGER MUST NOT MOVE THE STICK AND A DIRECTION MUST NOT DROP THE
    // TRIGGER -- the composite `STICK`+`STRIG` reading depends on exactly this,
    // and it is the arm that would have caught the obvious implementation
    // (rebuild the whole state per command).
    let firing = Parser.apply(.trigger(0, true), to: Stick())
    let upFiring = Parser.apply(.direction(0, -127), to: firing)
    arm("a direction keeps the trigger held", upFiring.buttons == 1)
    arm("...and sets the axis", upFiring.y == -127)
    let released = Parser.apply(.trigger(0, false), to: upFiring)
    arm("releasing a trigger keeps the direction",
        released.y == -127 && released.buttons == 0)
    arm("NEGATIVE: trigger 2 does not release trigger 1",
        Parser.apply(.trigger(1, true), to: firing).buttons == 3)

    print(fails == 0 ? "  selftest: PASS"
                     : "  selftest: \(fails) FAILURE(S)")
    print("  ⚠️  NOT COVERED, named rather than implied: that macOS accepts the "
          + "descriptor, that SDL enumerates the device, and that openMSX then "
          + "offers `joystick1`. None of those can be reached without the "
          + "entitlement -- run `--probe` to see where this machine stands.")
    return fails == 0 ? 0 : 1
}

// --- entry point -------------------------------------------------------------
@main
struct Rigstick {
    static func main() async {
        let args = Array(CommandLine.arguments.dropFirst())
        if args.contains("--selftest") { exit(selftest()) }

        guard let dev = makeDevice() else {
            // The OTHER refusal -- an ad-hoc signature CLAIMING the entitlement
            // -- never reaches this line at all: AMFI kills the process before
            // `main`. So "nil here" specifically means the entitlement is
            // ABSENT, not that it was rejected.
            print("REFUSED: HIDVirtualDevice(properties:) returned nil "
                  + "(uid=\(getuid())). The entitlement "
                  + "com.apple.developer.hid.virtual.device is absent. It is "
                  + "RESTRICTED: it needs an Apple-issued provisioning profile "
                  + "carrying the HID-virtual-device capability. A self-signed "
                  + "claim is worse than none -- AMFI SIGKILLs it.")
            exit(1)
        }
        await dev.activate(delegate: Silent())
        var state = Stick()
        try? await dev.dispatchInputReport(data: state.report, timestamp: .now)
        print("READY: zerobas rig stick is live (uid=\(getuid()))")
        if args.contains("--probe") { exit(0) }

        while let line = readLine(strippingNewline: true) {
            let t = line.trimmingCharacters(in: .whitespaces)
            if t.isEmpty { continue }
            guard let cmd = Parser.parse(t) else {
                // Refuse rather than ignore: a dropped line would let a probe
                // score a direction the stick never took.
                print("ERR: \(t)")
                continue
            }
            if cmd == .quit { print("OK"); break }
            state = Parser.apply(cmd, to: state)
            do {
                try await dev.dispatchInputReport(data: state.report,
                                                  timestamp: .now)
                print("OK")
            } catch {
                print("ERR: dispatch failed: \(error)")
            }
        }
    }
}
