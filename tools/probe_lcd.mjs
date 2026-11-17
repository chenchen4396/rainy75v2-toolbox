#!/usr/bin/env node
// Low-level LCD file-protocol probe: sends official-style frames and prints every ACK.
// Read-mostly; if a BEGIN is sent it is always followed by ABORT. Used to adapt the
// upload path to the official 0.0.64 main firmware.
//
//   node tools/probe_lcd.mjs [--gif path]   (default: dist/whale-girl/background.gif)
// SPDX-License-Identifier: MIT.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const HID = require('node-hid');
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const web = (n) => new URL('file://' + path.join(ROOT, 'web', n).replace(/\\/g, '/'));
const { frame, crc16 } = await import(web('protocol.mjs'));

const VID = 0x36b0;
const APP_PID = 0x3075;
const ACK_READ = new Uint8Array([0xbe, 0xe4, 10, 0x84, 4, 0, 0, 0x34, 2, 0xed]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const hex = (a) => Array.from(a).map((v) => v.toString(16).padStart(2, '0')).join(' ');

const gifPath = (() => {
  const i = process.argv.indexOf('--gif');
  return i > 0 ? process.argv[i + 1] : path.join(ROOT, 'dist/whale-girl/background.gif');
})();

async function openDevice() {
  const info = (await HID.devicesAsync()).find(
    (d) => d.vendorId === VID && d.productId === APP_PID && d.usagePage === 0xff60 && d.usage === 0x61);
  if (!info) throw Error('找不到 0x3075 厂商接口');
  const h = await HID.HIDAsync.open(info.path);
  const queue = [];
  const waiters = [];
  h.on('data', (raw) => {
    let b = Buffer.from(raw);
    if (b.length === 257 && b[0] === 0) b = b.subarray(1);
    const copy = new Uint8Array(b);
    const w = waiters.shift();
    if (w) w(copy); else queue.push(copy);
  });
  h.on('error', () => {});
  const read = (ms = 1500) => new Promise((resolve) => {
    if (queue.length) return resolve(queue.shift());
    const t = setTimeout(() => resolve(null), ms);
    waiters.push((r) => { clearTimeout(t); resolve(r); });
  });
  const send = async (bytes) => {
    const p = new Uint8Array(256);
    p.set(bytes.subarray(0, 256));
    await h.write([0, ...p]);
  };
  return { h, send, read };
}

function decodeAck(r) {
  if (!r || r.length < 11 || r[0] !== 0xbe || r[1] !== 0xe4) return null;
  return { sub: r[7], status: r[8], value: r[9] | (r[10] << 8) };
}

async function pollAck(dev, label, ms = 4000) {
  const start = Date.now();
  const seen = [];
  while (Date.now() - start < ms) {
    await dev.send(ACK_READ);
    const r = await dev.read(600);
    const a = decodeAck(r);
    if (a) {
      seen.push(a);
      console.log(`  ${label} ack sub=${a.sub} status=${a.status} value=${a.value}`);
      if (a.sub !== 13 || a.status !== 255) return a;
    }
    await sleep(120);
  }
  console.log(`  ${label} 超时，最后 ACK: ${seen.length ? JSON.stringify(seen[seen.length - 1]) : 'none'}`);
  return null;
}

const dev = await openDevice();
try {
  console.log('设备已打开，whale gif =', gifPath);
  console.log('\n[0] 读取当前 ACK 槽');
  await pollAck(dev, 'idle', 1500);

  console.log('\n[1] query (sub=0) 预检');
  await dev.send(frame(0));
  await pollAck(dev, 'query', 3000);

  console.log('\n[2] info (sub=10)');
  await dev.send(frame(10));
  await pollAck(dev, 'info', 3000);

  console.log('\n[3] list (sub=11 offset=0)');
  await dev.send(frame(11, 0));
  await pollAck(dev, 'list0', 3000);

  console.log('\n[4] begin GIF S1');
  const bytes = new Uint8Array(fs.readFileSync(gifPath));
  const crc = crc16(bytes);
  const begin = new Uint8Array(17);
  begin.set(new TextEncoder().encode('S1      GIF'));
  new DataView(begin.buffer).setUint32(11, bytes.length, true);
  new DataView(begin.buffer).setUint16(15, crc, true);
  console.log('  size', bytes.length, 'crc', crc.toString(16), 'payload', hex(begin));
  await dev.send(frame(1, 0, 0, 1, begin));  // c=1: replace existing S1 file
  const began = await pollAck(dev, 'begin', 12000);

  console.log('\n[5] abort (sub=4)');
  await dev.send(frame(4));
  await pollAck(dev, 'abort', 2000);
  console.log('\n结果:', began ? 'begin 有应答，状态 ' + began.status : 'begin 无应答');
} finally {
  await dev.h.close().catch(() => {});
}
