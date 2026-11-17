#!/usr/bin/env node
// One-command USB flasher for a Rainy75 V2 build pack (IPS screen target).
//
// It reuses the same protocol code as the WebHID studio (web/protocol.mjs and
// web/hid.mjs) through a node-hid transport shim, so the bytes on the wire are the
// ones already exercised by the browser tool.
//
//   node tools/flash_scheme.mjs --dir dist/cat-run-demo --dry-run
//   node tools/flash_scheme.mjs --dir dist/cat-run-demo --yes
//   node tools/flash_scheme.mjs --dir dist/cat-run-demo --yes --no-asset
//   node tools/flash_scheme.mjs --dir dist/cat-run-demo --yes --flash-only
//
// The pack directory must contain rainy75v2-ips.bin + manifest.json and optionally
// background.gif (uploaded to the S1 slot before flashing).  Nothing is written
// without --yes.  SPDX-License-Identifier: MIT.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const HID = require('node-hid');
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const web = (name) => new URL('file://' + path.join(ROOT, 'web', name).replace(/\\/g, '/'));
const { AppClient, FlashClient, HidIO } = await import(web('hid.mjs'));
const { validateBuild } = await import(web('protocol.mjs'));

const VID = 0x36b0;
const APP_PID = 0x3075;
const IPS_IAP_PID = 0x3078;
const MAIN_IAP_PID = 0x3079;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function args() {
  const out = { dir: path.join(ROOT, 'dist/cat-run-demo'), yes: false, asset: null,
                noAsset: false, flashOnly: false, dryRun: false, assetOnly: false,
                skipAppCheck: false };
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--dir') out.dir = path.resolve(argv[++i]);
    else if (a === '--asset') out.asset = path.resolve(argv[++i]);
    else if (a === '--yes' || a === '-y') out.yes = true;
    else if (a === '--no-asset') out.noAsset = true;
    else if (a === '--flash-only') out.flashOnly = true;
    else if (a === '--dry-run') out.dryRun = true;
    else if (a === '--asset-only') out.assetOnly = true;
    else if (a === '--skip-app-check') out.skipAppCheck = true;
    else if (a === '--help' || a === '-h') out.help = true;
    else throw Error('unknown argument: ' + a);
  }
  return out;
}

function usage() {
  console.log(`Rainy75 V2 IPS flasher (node-hid, reuses the WebHID protocol code)

  node tools/flash_scheme.mjs --dir <pack-dir> [options]

  --dir <dir>     build pack directory (default dist/cat-run-demo)
  --asset <file>  GIF to upload to the S1 slot (default <dir>/background.gif)
  --no-asset      skip the S1 upload, flash firmware only
  --flash-only    device is already in IAP mode; skip APP checks/asset upload
  --skip-app-check  skip version/asset step (screen APP protocol too old/damaged),
                    enter IAP and flash, then reconnect and run --asset-only
  --asset-only    only upload the S1 background GIF, no firmware write
  --dry-run       validate the pack and print the plan, touch no device
  --yes           actually write to the device (required)`)
}

async function openDevice(pid, reportBytes, label) {
  const devices = (await HID.devicesAsync()).filter(
    (d) => d.vendorId === VID && d.productId === pid && d.usagePage === 0xff60 && d.usage === 0x61);
  if (devices.length !== 1) {
    throw Error(`${label}: 需要且只需要一个匹配的 USB 设备（PID 0x${pid.toString(16)}），`
      + `当前找到 ${devices.length} 个。请用 USB 有线连接，关闭原厂驱动/其他网页/后台。`);
  }
  const handle = await HID.HIDAsync.open(devices[0].path);
  const listeners = new Set();
  const report = { reportId: 0, items: [{ reportSize: 8, reportCount: reportBytes }] };
  const device = {
    vendorId: VID, productId: pid, opened: true, closed: false,
    collections: [{ usagePage: 0xff60, usage: 0x61,
                    inputReports: [report], outputReports: [report] }],
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

async function loadPack(dir, assetOverride) {
  const man = path.join(dir, 'manifest.json');
  if (!fs.existsSync(man)) throw Error(`包里缺少 manifest.json：${dir}`);
  const manifest = JSON.parse(fs.readFileSync(man, 'utf8'));
  const target = manifest.target === 'main' ? 'main' : 'ips';
  const bin = path.join(dir, `rainy75v2-${target}.bin`);
  if (!fs.existsSync(bin)) throw Error(`包里缺少 rainy75v2-${target}.bin：${dir}`);
  const bytes = new Uint8Array(fs.readFileSync(bin));
  const plan = await validateBuild(bytes, manifest);
  let asset = null;
  if (!assetOverride) {
    const candidate = path.join(dir, 'background.gif');
    if (fs.existsSync(candidate)) asset = candidate;
  } else if (fs.existsSync(assetOverride)) {
    asset = assetOverride;
  }
  return { plan, manifest, asset, bin, man };
}

function printPlan(pack, opts) {
  const { plan, manifest, asset } = pack;
  console.log('=== 准备写入 ===');
  console.log('方案      :', manifest.scheme || '(未命名)');
  console.log('界面版本  :', manifest.uiVersion, '/', manifest.layout);
  console.log('目标      :', plan.target === 'ips' ? 'IPS 屏幕 (AT32F435)' : plan.target,
              ' PID 0x' + plan.pid.toString(16));
  console.log('应用起点  : 0x' + plan.base.toString(16));
  console.log('镜像大小  :', plan.bytes.length, 'bytes');
  console.log('SHA-256   :', plan.sha256);
  console.log('特效      :', JSON.stringify(manifest.fxEffect || manifest.animation || {}));
  console.log('S1 素材   :', asset ? asset : '(跳过)');
  console.log('动作      :', opts.flashOnly ? '仅烧录（设备应已在 IAP）'
              : 'APP 检查' + (asset ? ' + 上传素材' : '') + ' + 进入 IAP + 烧录校验');
}

async function uploadAsset(assetPath, { skipCapCheck = false } = {}) {
  console.log('\n[1/3] APP 模式：检查固件版本 + 上传 S1 素材');
  const io = await openDevice(APP_PID, 256, '键盘 APP');
  const app = new AppClient(io);
  try {
    if (skipCapCheck) {
      console.log('      跳过能力查询（--skip-app-check），直接上传素材');
    } else {
      const st = await app.status();
      console.log('      主控能力 0x' + st.mainCap.toString(16),
                  '屏幕能力 0x' + st.ipsCap.toString(16),
                  '时间 ' + (st.screenTime ? st.screenTime.text : '--:--:--'));
    }
    const data = new Uint8Array(fs.readFileSync(assetPath));
    console.log('      上传', assetPath, data.length, 'bytes（覆盖 S1 槽位）');
    let last = -1;
    await app.upload(data, { replaceConfirmed: true, skipCapCheck, progress: (p) => {
      const pct = Math.round(p * 100);
      if (pct !== last && pct % 20 === 0) { console.log('      ', pct + '%'); last = pct; }
    } });
    console.log('      素材已应答；请确认屏幕出现新画面（应答不等同于可见成功）。');
  } finally {
    await app.close().catch(() => {});
  }
}

async function enterIap(target) {
  console.log('\n[2/3] 发送 ' + (target === 'main' ? '主控' : 'IPS 屏幕') + ' 升级模式命令');
  const io = await openDevice(APP_PID, 256, '键盘 APP');
  const app = new AppClient(io);
  try {
    await app.enterIap(target);
    console.log('      命令已发送，等待屏幕重新枚举为 IAP 设备…');
  } finally {
    await app.close().catch(() => {});
  }
}

async function openIap(target) {
  const pid = target === 'main' ? MAIN_IAP_PID : IPS_IAP_PID;
  const label = (target === 'main' ? '主控' : 'IPS') + ' IAP';
  const deadline = Date.now() + 20000;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const io = await openDevice(pid, 64, label);
      console.log('      已连接 ' + label + ' 设备');
      return io;
    } catch (err) {
      lastError = err;
      await sleep(500);
    }
  }
  throw Error('等待 ' + label + ' 升级设备超时。目标可能未进入 IAP 或仍被其他驱动占用。\n'
              + (lastError ? lastError.message : ''));
}

async function flash(plan, io) {
  console.log('\n[3/3] 擦除应用区 + 写入 + 全字节校验');
  const flasher = new FlashClient(io, plan);
  let last = '';
  await flasher.flash((phase, p) => {
    const pct = Math.round(p * 100);
    const line = `${phase} ${pct}%`;
    if (pct % 10 === 0 && line !== last) { console.log('      ' + line); last = line; }
  });
  console.log('      烧录与校验完成。');
}

async function main() {
  const opts = args();
  if (opts.help) { usage(); return; }
  const pack = await loadPack(opts.dir, opts.asset);
  printPlan(pack, opts);

  const isRestore = /factory restore/i.test(String(pack.manifest.status || ''));
  if (!isRestore && pack.manifest.variant && pack.manifest.variant !== 'interactive-v1') {
    throw Error('这个包不是互动像素版（variant=' + pack.manifest.variant + '），已停止。');
  }
  if (opts.dryRun) {
    console.log('\n预演完成：包校验通过，未连接设备。确认后加 --yes 实际写入。');
    return;
  }
  if (!opts.yes) {
    console.log('\n这是预演（没有 --yes）。确认无误后运行：');
    console.log('  node tools/flash_scheme.mjs --dir "' + opts.dir + '" --yes'
                + (opts.noAsset ? ' --no-asset' : '') + (opts.flashOnly ? ' --flash-only' : ''));
    return;
  }

  console.log('\n开始写入。请保持 USB 连接与供电，不要关闭本窗口；'
              + '中断后按 docs/recovery.md 处理。');
  if (opts.assetOnly) {
    if (!pack.asset) throw Error('包里没有 background.gif，无法只上传素材');
    await uploadAsset(pack.asset);
    console.log('\n素材上传结束。');
    return;
  }
  if (!opts.flashOnly) {
    if (!opts.skipAppCheck) {
      if (!opts.noAsset && pack.asset) await uploadAsset(pack.asset);
    } else if (!opts.noAsset && pack.asset) {
      console.log('\n[1/3] 跳过版本查询，直接上传素材（--skip-app-check）');
      await uploadAsset(pack.asset, { skipCapCheck: true });
    } else {
      console.log('\n[1/3] 跳过版本检查与素材上传（--skip-app-check --no-asset）');
    }
    await enterIap(pack.plan.target);
  }
  const io = await openIap(pack.plan.target);
  try {
    await flash(pack.plan, io);
  } finally {
    await io.close().catch(() => {});
  }
  console.log('\n完成。请重新插拔 USB，确认屏幕进入新方案；'
              + '若画面异常，用同版本恢复 BIN 刷回应用区（不会影响设置区）。');
  if (opts.skipAppCheck && pack.asset) {
    console.log('本次跳过了素材上传：屏幕刷新后重新连接，再运行 '
                + 'node tools/flash_scheme.mjs --dir "' + opts.dir + '" --asset-only');
  }
}

main().catch((err) => {
  const msg = err && err.message ? err.message : String(err);
  console.error('\n[停止] ' + msg);
  if (/不是支持的 L6|不是支持的 V7\.1|能力号/.test(msg)) {
    console.error(`
诊断：屏幕/主控当前跑的是另一个实验分支（能力号不符），但升级通道本身可用。
两个选择：
  A. 先按 docs/usage.md 刷回本版基础 IPS（能力号 0x5536），再正常刷互动版；
  B. 直接跳过 APP 阶段检查进入 IAP（不校验屏幕当前固件，也不上传素材）：
     node tools/flash_scheme.mjs --dir <包目录> --yes --skip-app-check
     刷完重新插拔 USB，再补素材：
     node tools/flash_scheme.mjs --dir <包目录> --asset-only`);
  }
  process.exitCode = 1;
});
