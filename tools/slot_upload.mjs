#!/usr/bin/env node
// Upload a 320x172 GIF to a numbered screen slot (S1..S9) over USB HID.
//
//   node tools/slot_upload.mjs --slot S2 --file local/spongebob/background.gif --dry-run
//   node tools/slot_upload.mjs --slot S2 --file local/spongebob/background.gif --yes
//
// S1 is the slot the stock player normally shows. Other slots are a probe: the screen
// may accept the write (ack ok) yet never play the file. Always verify on the device,
// e.g. by selecting slot 2 in the vendor driver. Reuse of the WebHID protocol code keeps
// the bytes on the wire identical to the tested upload path.
// SPDX-License-Identifier: MIT.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const HID = require('node-hid');
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const web = (name) => new URL('file://' + path.join(ROOT, 'web', name).replace(/\\/g, '/'));
const { AppClient, HidIO } = await import(web('hid.mjs'));
const { validateGif } = await import(web('protocol.mjs'));

const VID = 0x36b0;
const APP_PID = 0x3075;

function args() {
  const out = { slot: 'S2', file: null, yes: false, dryRun: false, remove: false };
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--slot') out.slot = String(argv[++i]).toUpperCase();
    else if (a === '--file') out.file = path.resolve(argv[++i]);
    else if (a === '--yes' || a === '-y') out.yes = true;
    else if (a === '--dry-run') out.dryRun = true;
    else if (a === '--remove' || a === '--delete') out.remove = true;
    else if (a === '--help' || a === '-h') out.help = true;
    else throw Error('unknown argument: ' + a);
  }
  return out;
}

async function openDevice(pid, reportBytes, label) {
  const devices = (await HID.devicesAsync()).filter(
    (d) => d.vendorId === VID && d.productId === pid && d.usagePage === 0xff60 && d.usage === 0x61);
  if (devices.length !== 1) {
    throw Error(`${label}: 需要且只需要一个匹配设备（PID 0x${pid.toString(16)}），当前 ${devices.length} 个`);
  }
  const handle = await HID.HIDAsync.open(devices[0].path);
  const listeners = new Set();
  const report = { reportId: 0, items: [{ reportSize: 8, reportCount: reportBytes }] };
  const device = {
    vendorId: VID, productId: pid, opened: true, closed: false,
    collections: [{ usagePage: 0xff60, usage: 0x61, inputReports: [report], outputReports: [report] }],
    sendReport: async (id, payload) => {
      if (!device.opened) throw Error(label + ': 设备已关闭');
      if (id !== 0 || payload.length !== reportBytes) throw Error(label + ': 报文长度错误');
      const written = await handle.write([0, ...payload]);
      if (written !== reportBytes + 1) throw Error(label + ': USB HID 写入不完整');
    },
    addEventListener: (event, fn) => { if (event === 'inputreport') listeners.add(fn); },
    removeEventListener: (event, fn) => { if (event === 'inputreport') listeners.delete(fn); },
    close: async () => {
      if (!device.opened && device.closed) return;
      device.opened = false; device.closed = true; listeners.clear();
      await handle.close();
    },
  };
  handle.on('error', () => { device.opened = false; });
  handle.on('data', (raw) => {
    let buf = Buffer.from(raw);
    if (buf.length === reportBytes + 1 && buf[0] === 0) buf = buf.subarray(1);
    if (buf.length !== reportBytes || !device.opened) return;
    const payload = new Uint8Array(buf);
    for (const fn of listeners) fn({ reportId: 0, data: new DataView(payload.buffer) });
  });
  return new HidIO(device, reportBytes);
}

async function main() {
  const opts = args();
  if (opts.help || (!opts.file && !opts.remove)) {
    console.log('用法: node tools/slot_upload.mjs --slot S2 --file <320x172.gif> [--dry-run|--yes]');
    console.log('      node tools/slot_upload.mjs --slot S2 --remove --yes   # 删除该槽位素材');
    return;
  }
  if (!/^S[1-4]$/.test(opts.slot)) throw Error('官方协议只支持槽位 S1..S4');
  if (opts.remove) {
    console.log('删除槽位:', opts.slot);
    if (opts.dryRun) { console.log('预演通过：未连接设备，未删除。'); return; }
    if (!opts.yes) { console.log('未加 --yes，未删除。确认后运行：'); 
      console.log(`  node tools/slot_upload.mjs --slot ${opts.slot} --remove --yes`); return; }
    const io = await openDevice(APP_PID, 256, '键盘 APP');
    const app = new AppClient(io);
    try { await app.stock(12, Number(opts.slot.slice(1))); }
    finally { await app.close().catch(() => {}); }
    console.log('删除指令已应答。若屏幕仍在播放旧画面，请切槽位或重新插拔。');
    return;
  }
  if (!fs.existsSync(opts.file)) throw Error('文件不存在: ' + opts.file);
  const bytes = new Uint8Array(fs.readFileSync(opts.file));
  validateGif(bytes);
  console.log('槽位:', opts.slot, ' 文件:', opts.file, ' 大小:', bytes.length, 'bytes');
  if (opts.dryRun) {
    console.log('预演通过：GIF 是 320x172、大小在限制内；未连接设备。');
    return;
  }
  if (!opts.yes) {
    console.log('未加 --yes，未写入。确认后运行：');
    console.log(`  node tools/slot_upload.mjs --slot ${opts.slot} --file "${opts.file}" --yes`);
    return;
  }
  console.log('开始写入槽位 ' + opts.slot + '（应答成功不代表屏幕会播放该槽位）');
  const io = await openDevice(APP_PID, 256, '键盘 APP');
  const app = new AppClient(io);
  try {
    const st = await app.status();
    console.log('屏幕能力 0x' + st.ipsCap.toString(16));
    await app.upload(bytes, { replaceConfirmed: true, slot: opts.slot,
      progress: (p) => { const pct = Math.round(p * 100); if (pct % 20 === 0) console.log('  ', pct + '%'); } });
  } finally {
    await app.close().catch(() => {});
  }
  console.log('写入完成。请用原厂驱动切换到该槽位确认能否播放；若不能，说明屏幕只支持 S1。');
}

main().catch((err) => {
  console.error('\n[停止] ' + (err && err.message ? err.message : err));
  process.exitCode = 1;
});
