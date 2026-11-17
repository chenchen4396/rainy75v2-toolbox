#!/usr/bin/env node
// Read-only screen/keyboard status probe: answers "is the screen firmware alive?"
// without writing anything to the device.
//
//   node tools/screen_status.mjs
//
// Prints main/IPS capability IDs, screen state, battery, connection mode, last key and
// screen time. A working IPS answers 0x5536 (L6) or 0x5537 (pixel/interactive).
// SPDX-License-Identifier: MIT.
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const HID = require('node-hid');
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const web = (name) => new URL('file://' + path.join(ROOT, 'web', name).replace(/\\/g, '/'));
const { AppClient, HidIO } = await import(web('hid.mjs'));

const VID = 0x36b0;
const APP_PIDS = [0x3075, 0x3071];
const LABELS = {0x3075: 'USB 有线', 0x3071: '2.4G 接收器'};
const hex = (v) => '0x' + (v >>> 0).toString(16).padStart(4, '0');

async function openApp(pid) {
  const devices = (await HID.devicesAsync()).filter(
    (d) => d.vendorId === VID && d.productId === pid
      && d.usagePage === 0xff60 && d.usage === 0x61);
  if (devices.length !== 1) return null;
  const handle = await HID.HIDAsync.open(devices[0].path);
  const listeners = new Set();
  const size = 256;
  const report = { reportId: 0, items: [{ reportSize: 8, reportCount: size }] };
  const device = {
    vendorId: VID, productId: pid, opened: true, closed: false,
    collections: [{ usagePage: 0xff60, usage: 0x61, inputReports: [report], outputReports: [report] }],
    sendReport: async (id, payload) => {
      if (!device.opened) throw Error('设备已关闭');
      if (id !== 0 || payload.length !== size) throw Error('报文长度错误');
      const written = await handle.write([0, ...payload]);
      if (written !== size + 1) throw Error('USB HID 写入不完整');
    },
    addEventListener: (e, fn) => { if (e === 'inputreport') listeners.add(fn); },
    removeEventListener: (e, fn) => { if (e === 'inputreport') listeners.delete(fn); },
    close: async () => { device.opened = false; device.closed = true; listeners.clear(); await handle.close(); },
  };
  handle.on('error', () => { device.opened = false; });
  handle.on('data', (raw) => {
    let buf = Buffer.from(raw);
    if (buf.length === size + 1 && buf[0] === 0) buf = buf.subarray(1);
    if (buf.length !== size || !device.opened) return;
    const payload = new Uint8Array(buf);
    for (const fn of listeners) fn({ reportId: 0, data: new DataView(payload.buffer) });
  });
  return new AppClient(new HidIO(device, size));
}

async function tryRead(label, fn) {
  try {
    const value = await fn();
    console.log(`  ${label}: ${hex(value)}`);
    return value;
  } catch (err) {
    console.log(`  ${label}: 读取失败（${err && err.message ? err.message : err}）`);
    return null;
  }
}

let app = null, pid = null;
for (const candidate of APP_PIDS) {
  try {
    const client = await openApp(candidate);
    if (!client) continue;
    await client.queryMain(9);
    app = client; pid = candidate;
    console.log('键盘 APP 已连接（' + LABELS[candidate] + '，0x' + candidate.toString(16)
      + '），查询有应答。以下全部为只读查询：');
    break;
  } catch (err) {
    console.log('（' + LABELS[candidate] + ' 0x' + candidate.toString(16) + ' 查询无应答：'
      + (err && err.message ? err.message : err) + '）');
  }
}
if (!app) {
  console.log('两个厂商接口都打开/查询失败：请确认键盘在 USB 有线模式、关闭 WOBHub 网页与官方驱动，'
    + '并只保留一个连接（拔掉 2.4G 接收器后更稳）。');
  process.exitCode = 1;
} else try {
  const mainCap = await tryRead('主控能力 queryMain(9)', () => app.queryMain(9));
  const ipsCap = await tryRead('屏幕能力 queryIps(0)', () => app.queryIps(0));
  await tryRead('最近按键 queryIps(1)', () => app.queryIps(1));
  await tryRead('电量 queryIps(2)', () => app.queryIps(2));
  await tryRead('连接模式 queryIps(3)', () => app.queryIps(3));
  await tryRead('屏幕状态 queryIps(4)', () => app.queryIps(4));
  await tryRead('屏幕时间低 queryIps(5)', () => app.queryIps(5));
  await tryRead('屏幕时间高 queryIps(6)', () => app.queryIps(6));
  await tryRead('主控时间有效 queryMain(8)', () => app.queryMain(8));

  console.log('\n判断：');
  if (ipsCap === 0x5536 || ipsCap === 0x5537) {
    console.log('  屏幕 MCU 与 APP 有应答（屏幕活着）。若仍全黑且无背光，'
      + '问题在显示/背光/排线，属于硬件路径。');
  } else if (ipsCap === 0xffff || ipsCap === null) {
    console.log('  屏幕没有有效应答：屏幕 APP 可能未启动，或屏幕不在应用模式。'
      + '需要官方烧录工具/售后，CLI 只能写已进入 IAP 的屏幕。');
  } else {
    console.log('  屏幕有应答但能力号不匹配（' + hex(ipsCap) + '）：可能是其他版本固件。');
  }
  if (mainCap !== 0x4350) console.log('  注意：主控能力号不是 V7.1 的 0x4350（' + hex(mainCap) + '）。');
} finally {
  await app.close().catch(() => {});
}

