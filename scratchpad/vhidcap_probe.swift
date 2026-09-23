// Feasibility probe: can this macOS create a CoreHID virtual gamepad from a
// plain, unsigned, non-root command-line tool?  Prints one line either way.
import CoreHID
import Foundation

let descriptor: [UInt8] = [
  0x05, 0x01, 0x09, 0x05, 0xA1, 0x01,
    0xA1, 0x00,
      0x09, 0x30, 0x09, 0x31,
      0x15, 0x81, 0x25, 0x7F,
      0x75, 0x08, 0x95, 0x02, 0x81, 0x02,
    0xC0,
    0x05, 0x09, 0x19, 0x01, 0x29, 0x04,
    0x15, 0x00, 0x25, 0x01,
    0x75, 0x01, 0x95, 0x04, 0x81, 0x02,
    0x75, 0x04, 0x95, 0x01, 0x81, 0x03,
  0xC0,
]

final class Delegate: HIDVirtualDeviceDelegate {
  func hidVirtualDevice(_ d: HIDVirtualDevice,
                        receivedSetReportRequestOfType t: HIDReportType,
                        id: HIDReportID?, data: Data) async throws {}
  func hidVirtualDevice(_ d: HIDVirtualDevice,
                        receivedGetReportRequestOfType t: HIDReportType,
                        id: HIDReportID?, maxSize: Int) async throws -> Data { Data() }
}

let props = HIDVirtualDevice.Properties(
  descriptor: Data(descriptor), vendorID: 0x5A5A, productID: 0x0001,
  transport: .virtual, product: "zerobas rig stick",
  manufacturer: "zerobas", uniqueID: "zerobas-rig-0")

guard let dev = HIDVirtualDevice(properties: props) else {
  print("RESULT: REFUSED — HIDVirtualDevice(properties:) returned nil "
        + "(uid=\(getuid()))")
  exit(1)
}
await dev.activate(delegate: Delegate())
print("RESULT: CREATED — virtual HID gamepad is live (uid=\(getuid()))")
try? await Task.sleep(for: .seconds(2))
try? await dev.dispatchInputReport(data: Data([0x7F, 0x00, 0x01]),
                                   timestamp: .now)
print("RESULT: REPORT DISPATCHED")
try? await Task.sleep(for: .seconds(1))
