#!/usr/bin/env node
// List Rainy75 V2 USB HID interfaces to diagnose "device not found" errors.
//
//   node tools/hid_list.mjs          # only vendor 0x36b0 devices
//   node tools/hid_list.mjs --all    # every HID device (short list)
//
// Exit code: 0 when at least one 0x36b0 device is present, 1 otherwise.
// SPDX-License-Identifier: MIT.
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const HID = require('node-hid');
const VID = 0x36b0;
const all = process.argv.includes('--all');

function row(d) {
  return [
    'PID=0x' + (d.productId ?? 0).toString(16).padStart(4, '0'),
    'usagePage=0x' + (d.usagePage ?? 0).toString(16),
    'usage=0x' + (d.usage ?? 0).toString(16),
    'iface=' + (d.interface ?? '?'),
    'product=' + (d.product || '?'),
  ].join('  ');
}

const devices = await HID.devicesAsync();
const vendor = devices.filter((d) => d.vendorId === VID);
if (!vendor.length) {
  console.log('没有找到厂商 0x36b0 的 HID 接口（Rainy75 V2 键盘/屏幕）。');
  if (all) {
    console.log('全部 HID 设备：');
    for (const d of devices) console.log(' ', row(d), 'VID=0x' + (d.vendorId ?? 0).toString(16));
  } else {
    console.log('加 --all 可以列出所有 HID 设备。');
  }
  console.log('\n常见原因：');
  console.log('  1. 键盘不在 USB 有线模式（蓝牙/2.4G 模式下不提供厂商 HID 接口）');
  console.log('  2. 数据线只充电、或接在无数据口的 Hub 上');
  console.log('  3. 屏幕还停在 IAP 模式（只剩 PID 0x3078），需要重新插拔/恢复');
  console.log('  4. 其他程序（WOBHub、厂商驱动页、烧录页）占用了接口');
  process.exitCode = 1;
} else {
  console.log('找到 ' + vendor.length + ' 个厂商 0x36b0 接口：');
  for (const d of vendor) console.log(' ', row(d));
  const pids = new Set(vendor.map((d) => d.productId));
  const hints = [];
  if (pids.has(0x3075)) hints.push('APP 接口在（0x3075）：可以上传素材/发命令');
  if (pids.has(0x3078)) hints.push('IAP 接口在（0x3078）：屏幕处于升级模式，刷完请重新插拔');
  if (pids.has(0x3079)) hints.push('主控 IAP（0x3079）：主控处于升级模式');
  if (hints.length) console.log(hints.join('\n'));
  process.exitCode = 0;
}
