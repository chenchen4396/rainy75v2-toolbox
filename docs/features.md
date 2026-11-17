# 功能支持清单

本文档列出当前代码仓**实际支持**的功能、入口、验证状态与限制，方便确认"能做什么、怎么开、验证到哪一步"。

状态口径：

- **构建验证**：本机用匹配的 `inputs/ips-stock.bin` 成功构建，镜像校验（SHA/补丁/钩子）通过；
- **模型验证**：离线预览/仿真与固件构图一致（像素级比对），不是设备实测；
- **实机验证**：在真实键盘上确认过。命中"实机"字样的功能才代表设备上验证过。

> 目前所有互动像素功能均为**构建 + 模型验证**；实机效果以你刷机后的反馈为准。

## 一、屏幕固件

### 基础屏幕版（`layout=minimal`，能力号 L6 `0x5536`）

| 功能 | 说明 | 状态 |
| --- | --- | --- |
| 大单键图标 | 显示最近按键的图形化图标，松开后保留 | 构建验证 |
| 时钟 | 主控校时后显示 `HH:MM`；未校时显示 `--:--` | 构建验证 |
| 电量与连接 | 电量图标、充电闪电、连接状态图标 | 构建验证 |
| 本地缓存动画 | 上传的 GIF 由屏幕本地播放，不依赖电脑 | 构建验证（依赖素材评测） |
| 无电脑后台 | 不引入全局键盘监听或按键历史采集 | 设计约束 |

构建命令：

```sh
python tools/build.py ips --stock inputs/ips-stock.bin --theme pink --out build/ips-base
```

### 互动像素版（`layout=pixel-interactive`，能力号 `0x5537`，`uiVersion 1.0.0-fx`）

固件：`firmware/ips/native_ui_reactive.c`。方案格式：`rainy75-px/2`（含 2.1/2.2 扩展）。

| 功能 | 实现/开关 | 状态 | 说明 |
| --- | --- | --- | --- |
| 四帧情绪 | 每层 4 个掩码（calm/caps/react/sleepy） | 构建+模型 | CapsLock 亮起、打字互动、长时间待机分别切帧 |
| 粒子特效 | `FX_COUNT>0`，数值宏驱动 | 构建+模型 | 20+ 可调参数（数量/大小/速度/重力/寿命/形状/触发） |
| 脉冲层 | `PX_PULSE_LAYER>=0` | 构建+模型 | 某层颜色做三角波呼吸 |
| 角色动作 motion | 层 `motion` 字段（v2.1） | 构建+模型 | 2–8 帧循环 + 按键位移 + 每键加帧；`px6-cat-run` 演示 |
| 按键面板 keyPanel | 层外可选面板（v2.2） | 构建+模型 | 大键帽显示上一个按键：**有原厂点阵大图的键直接复用 `profiles/keys.json` 图标**（Enter/方向/PgUp/PgDn/Win，经 `tools/gen_keyicons.py` 生成 `reactive_keyicons.h`），字母/数字用 5×7 字体 scale 8，其余特殊键用 2–3 字符缩写；面板字体精简为 A–Z、0–9、`-`（37 字形）以保住 4976 B 预算 |
| 顶部状态栏 topBar | `topBar`（v2.2） | 构建+模型 | 左电量（图标+百分比+充电闪电）、右 CapsLock 徽标 |
| Caps 校准 | 快速双击 Caps | 待实机确认 | 只翻转屏幕显示方向，不改变实际大小写；重启复位 |
| 键码与图标 | `firmware/ips/reactive_keylabel.h`、`reactive_keyicons.h`、`tools/gen_keyicons.py` | 构建+模型+宿主自检 | 按 `profiles/keys.json` 原生键码映射：普通键 HID 码，修饰键 `0xF8..0xFF`→`CTL/SHF/ALT/WIN`，Fn `401..405`→`FN1..FN5`，Win `227`→`WIN`；导航/小键盘/PRT-SCR-PAU；未知键 `K+两位十六进制`。图标表来自 `profiles/keys.json`（当前 8 个：Enter/方向/PgUp/PgDn/Win），字体 37 字形。自检：`tests/test_keylabel.py` 编译 wasm 在 Node 里跑全部用例 |
| 兼容旧方案 | 无 keyPanel/topBar/motion 时整段编译掉 | 构建+模型 | 非面板方案只多两个 `#define ... 0` |

已知硬限制：

- IPS 追加区只有 **4976 B**（`.text+.rodata`），`.data` 必须为 0，模块 RAM 4 KiB；
- **粒子 + 面板 + 顶栏不能同时开**（同时开会超预算），当前组合上限：面板+顶栏 4569–4900 B 级别；
- 面板与顶栏依赖 67 字形字库（259 B）+ 面板位图缓存（约 1.7 KiB `.bss`）。

## 二、方案与工具链

| 能力 | 命令/文件 | 状态 |
| --- | --- | --- |
| 方案生成 | `tools/schemes/px6_*.py` | 已交付 50 套家族方案 + `px6-motion-demo` 演示（`px6-cat-run`） |
| 方案格式 | `docs/pixel-scheme-format.md` | schema `rainy75-px/2` / `2.1` / `2.2` |
| 方案校验 | `python tools/verify_schemes.py --glob 'px6-*' --dir build/design-gallery` | 52/52 通过 |
| 批量构建 | `python tools/build_matrix.py` | 52/52 构建通过，最紧 4916 B（余量 60 B） |
| 固件尺寸门禁 | `python tools/fx_size.py <elf>` | 4976 B 上限断言 |
| 画廊/预览 | `python tools/scheme_gallery.py` | 总览图、50+ 打字 GIF、`index.html` |
| 打包器 | `python tools/pixel_pack.py` | v2 方案 → `px_assets.h` / `px_font.h` / `background.gif` |
| 刷机脚本 | `node tools/flash_scheme.mjs` | 校验 -> 上传 S1 素材 -> 进 IAP -> 烧录 -> 全字节校验 |
| 恢复 | `python tools/build.py ips --stock ... --restore-stock` | 只动应用区，见 `docs/recovery.md` |

刷机脚本参数：

```sh
node tools/flash_scheme.mjs --dir dist/whale-girl --dry-run     # 预演，不碰设备
node tools/flash_scheme.mjs --dir dist/whale-girl --yes         # 上传素材 + 刷固件
node tools/flash_scheme.mjs --dir dist/base-pink --yes          # 基础版
node tools/flash_scheme.mjs --dir dist/whale-girl --yes --skip-app-check  # 旧实验固件不认版本校验时
node tools/flash_scheme.mjs --dir dist/whale-girl --asset-only  # 只补 S1 素材
node tools/flash_scheme.mjs --dir dist/whale-girl --flash-only  # 设备已在 IAP 时
```

## 三、按键显示与基础版差异

- **基础版**（`native_ui.c`）不自己画按键：它保留原厂按键图标缓存（`profiles/keys.json` 里的 `glyphs`），
  只覆盖右上角状态区，所以原厂大图标路径不受影响。
- **互动像素版**的按键面板是文本绘制，使用同一套**原生键码**：普通键为 HID usage id
  （A=4、Enter=40、方向 79–82…），修饰键为 `-8..-1` 的 8 位补码 `0xF8..0xFF`
  （Shift 左 = `0xF9`，所以之前显示成 `KF9`），Fn 为 `401..405`，Win 为 `227`。
- 映射与预期值集中放在 `firmware/ips/reactive_keylabel.h`，由 `tests/test_keylabel.py`
  编译成 wasm 在 Node 中逐条断言，避免再出现“Shift 显示 KF9”这类回归。

## 四、改动解耦说明

新增功能全部可选，基础路径保持原行为：

| 类别 | 文件 | 解耦方式 |
| --- | --- | --- |
| 互动引擎 | `firmware/ips/native_ui_reactive.c` | 独立固件文件，仅 `--fx` 构建使用；基础版不引用 |
| 方案格式/工具 | `tools/pixel_scheme.py`、`pixel_pack.py`、`verify_schemes.py`、`build_matrix.py`、`scheme_gallery.py`、`fx_size.py` | v1 打包路径未改；v2 只在 `--pixel` 且 schema 匹配时启用 |
| 刷机脚本 | `tools/flash_scheme.mjs` | 独立 CLI，复用 WebHID 协议代码；不参与固件构建 |
| 交互验收 | `web/hid.mjs`、`web/protocol.mjs` | 只放宽能力号与 `interactive-v1` 清单校验，基础/歌词路径不变 |
| 构建入口 | `tools/build.py` | 新增 `--fx` 分支，要求同时 `--pixel`；其余分支保持 |
| 方案素材 | `tools/schemes/px6_*.py` + `build/design-gallery/` | 生成物在忽略目录；源码可整体移除而不影响基础构建 |
| 个人角色 | `local/whale/` | 已移入 `.gitignore` 的 `local/`，不随 MIT 源码发布 |

回退方式：删除上表新增文件、保留 `tools/build.py`/`web` 的兼容改动即可恢复"只有基础屏幕版"的仓库；基础构建命令不依赖任何新增文件。

## 五、验证入口

```sh
python -m unittest discover -s tests -p "test_*.py"
npm test
python tools/check_release.py
python tools/verify_schemes.py --glob 'px6-*' --dir build/design-gallery
python tools/build_matrix.py
```

## 六、未验证 / 已知问题

- 所有互动像素功能**未做设备实测**，只到构建与模型比对；
- Fn 键是否转发取决于键盘主控：若按下无变化，固件层拿不到该事件；
- Caps 显示方向依赖双击校准，重启后复位；
- 角色形象为个人参考图衍生素材，仅本地使用；
- 歌词播放器是独立可选路径（`firmware/ips-lyrics/`、`desktop/`），不在本清单范围内，见 `docs/lyrics.md`。
