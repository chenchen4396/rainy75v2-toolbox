# 互动像素方案格式（rainy75-px/2）

一个“方案”就是一块 320×172 的像素场景 + 若干贴纸矩形 + 四个情绪帧 + 一份粒子参数。固件不读图片，只读构建时生成的 `px_assets.h`；上传的 GIF 是平静帧的完整画面。

## 目录结构

```
build/design-gallery/px6-<slug>/
├─ background.png        平静场景（无贴纸），用于检查矩形底色是否纯色
├─ background.gif        上传素材：平静帧合成图（两帧相同，40 ms）
├─ masks.bin             PackBits 压缩的唯一掩码（帧间相同则复用）
├─ meta.json             schema、层/帧表、粒子/脉冲/反应参数、预览索引
├─ preview-idle.png      帧 0（平静）
├─ preview-caps.png      帧 1（Caps）
├─ preview-react.png     帧 2（互动）
├─ preview-sleepy.png    帧 3（待机）
└─ preview-typing.png    帧 2 + 一次按键粒子快照
```

源码方案放在 `tools/schemes/px6_*.py`，用共享库 `tools/pixel_scheme.py` 生成。

## 四个情绪帧

| 索引 | id | 含义 | 固件行为 |
| --- | --- | --- | --- |
| 0 | calm | 平静 | 不绘制，直接用上传 GIF |
| 1 | caps | CapsLock 打开 | 重绘贴纸层 |
| 2 | react | 最近按键（`reactHoldMs`）或充电 | 重绘贴纸层 |
| 3 | sleepy | 空闲超过 `sleepyAfterMs` | 重绘贴纸层 |

帧的优先级：Caps > 互动 > 待机 > 平静。

## 贴纸层

每层是一个矩形，固件先把它填成该帧的底色，再按掩码画前景色：

```python
s.sticker('咖啡杯', 74, 112, calm_grid, '#f4e3c8', '#4a332a',
          caps_fg='#ffd9b0', react=react_grid, react_fg='#ffe9d2',
          sleepy=sleepy_grid, sleepy_fg='#d8cbb8')
```

约束（`tools/verify_schemes.py` 会检查）：

- 矩形必须完全在 320×172 内，且不能与右上角状态区 `(233,12)-(310,28)` 相交。
- 背景图里该矩形必须是**单一颜色**；帧 1–3 的底色必须等于这个颜色（固件要整块覆盖）。
- 同一层的四个帧掩码尺寸一致；没给 art 的帧继承平静帧掩码。
- 2–5 层；最大层建议 ≤90×60，否则压缩掩码会超预算。
- 预算：编码后掩码 ≤1200 B（固件 flash），解码后 ≤2560 B（模块 RAM）。

## 掩码

掩码是 1 bit/像素、行优先、MSB 在前，和固件 `dot()` 一致。保存时用 PackBits 压缩：

- 控制字节 `c < 0x80`：`c+1` 个下一字节的重复；
- 控制字节 `c >= 0x80`：`c & 0x7f + 1` 个紧跟的字面字节。

帧间相同的掩码只存一份，层表用 `off[4]` 指向解码缓冲区。

## 粒子（effect）

```python
s.set_effect('petal', trigger='key', spawn=(16, 2, 212, 12), count=6, size=4,
             colors=['#ffd0e2', '#ffffff', '#ff6fa6'], vx=(-46, 46), vy=(50, 85),
             gravity=22, life_ms=2600, edge='die', shape='square', energy_bonus=True)
```

| 字段 | 说明 |
| --- | --- |
| `kind` | 预设名，仅决定下列默认数值 |
| `trigger` | `key`（按键）、`continuous`（持续）或 `both` |
| `spawn` | 生成矩形 `[x,y,w,h]`，不能进状态区 |
| `count` / `size` | 每次生成 0–12 个、1–5 px |
| `vx` / `vy` | 初速度范围 px/s |
| `gravity` | px/s²，负值向上 |
| `lifeMs` | 寿命 |
| `edge` | `die` 消失 / `wrap` 环绕 / `bounce` 反弹 |
| `shape` | `square` / `plus` / `x` / `diamond` |
| `energyBonus` | 连打时额外多生成一半（上限 24 个） |

预设：`petal` `snow` `rain` `spark` `confetti` `bubble` `ember` `firefly` `dust` `note` `heart` `none`。

## 角色动作（motion，v2.1）

贴纸层可以带一段逐帧动画，在“打字互动”时播放，用来让角色真的动起来（猫跑步、车窗外掠过、波浪推进），而不是只撒粒子：

```python
s.set_motion('橘猫',
             frames=[(cat_run(p), 0, 0) for p in range(6)],
             period_ms=260, key_period_ms=80, advance_per_key=1,
             travel_range=200, step_per_key=14, axis='x')
```

| 字段 | 说明 |
| --- | --- |
| `frames` | 2–8 个同尺寸网格 `(Grid, dx, dy)`，循环播放 |
| `period_ms` | 空闲/慢速时的帧间隔 |
| `key_period_ms` | 打字时的帧间隔（更小 = 跑得更快） |
| `advance_per_key` | 每按一次键额外前进几帧（制造“被推动”的感觉） |
| `travel_range` | 整个层最多沿轴移动多少像素（0 = 原地跑） |
| `step_per_key` | 每次按键推进多少像素 |
| `axis` | `x` 或 `y` |

固件只在帧 2（打字互动）播放 motion 帧；平静/Caps/待机仍用静态掩码。位置公式是 `X = x + (axis==x ? travel : 0) + dx[i]`、`Y = y + (axis==y ? travel : 0) + dy[i]`，`travel = min(travel_range, keys*step_per_key)`，并夹在屏幕内。示例见 `tools/schemes/px6_motion_demo.py`（`px6-cat-run`，零粒子、纯跑步动画）。travel 走廊范围内背景必须是纯色，否则角色移动时会擦出突兀的色块。

## 按键面板（keyPanel，v2.2）

在屏幕左侧留一块**纯色矩形**给固件实时绘制“上一个按键”，方案只声明几何与颜色，字形不占素材：

```python
s.set_key_panel(20, 54, 146, 82, scale=8, fg='#3a4670', bg='#ffffff')
```

| 字段 | 说明 |
| --- | --- |
| `x/y/w/h` | 键帽内区，必须是背景里的纯色块（固件先填充 `bg` 再画字） |
| `scale` | 单字符放大倍数（字母/数字）；特殊键有原厂图标时直接画图标，否则降为 2–3 字符缩写 |
| `fg/bg` | 文字色 / 底色的 RGB565 十六进制 |

固件优先使用 `profiles/keys.json` 的原厂点阵图标（Enter/方向/PgUp/PgDn/Win），没有图标的键用标签：`ENT/ESC/DEL/TAB/SPC`、`F1–F12`、`INS/DEL`、`PRT/SCR/PAU`、`NUM/KP`、`CAPS`；修饰键按原生码 `0xF8..0xFF` 映射为 `CTL/SHF/ALT/WIN`，
Fn 码 `401..405` 显示 `FN1..FN5`，Win `227` 显示 `WIN`；未识别键显示 `K` + 两位十六进制码。

## 顶部状态栏（topBar，v2.2）

```python
s.set_top_bar(battery=True, caps=True)
```

声明后固件用固定布局绘制：左侧电量（图标 + 百分比 + 充电闪电，绿/黄/红三档），右侧 CapsLock 徽标
（开启蓝底白字，关闭灰底灰字）。启用 topBar 时不再绘制默认的连接/时钟小图标；几何由固件固定，
方案不需要提供坐标。Caps 显示方向可通过**快速双击 Caps** 校准（不改变实际大小写）。

## 脉冲（pulse）

```python
s.set_pulse('月亮', period_ms=2600, minimum=170)
```

固件用三角波把该层前景色在 `minimum..255` 之间缩放，用来做呼吸灯、心跳、月光起伏。

## 反应参数

```python
s.set_reaction(reactHoldMs=900, sleepyAfterMs=22000,
               energyKeys=3, energyWindowMs=1500, chargeUsesReact=False)
```

- `reactHoldMs`：最后一次按键后保持帧 2 的时长；
- `sleepyAfterMs`：多久没按键进入帧 3（建议 15–30 秒）；
- `chargeUsesReact`：充电时是否用帧 2 代替平静。

## 生成与验证

```sh
python tools/schemes/px6_example.py
python tools/verify_schemes.py --glob 'px6-warm-coffee' --dir build/design-gallery
python tools/scheme_gallery.py          # 总览图 + 离线网页 + 按键动画 GIF
```

`verify_schemes.py` 会做：元数据完整性、slug/家族、层矩形纯色与状态区、掩码往返（重新贴一遍必须和 preview 完全一致）、粒子/脉冲参数范围、预算。

## 构建固件

```sh
python tools/build.py ips --stock inputs/ips-stock.bin \
  --pixel build/design-gallery/px6-warm-coffee --fx \
  --clang "/path/to/clang" --out build/ips-fx
```

产物：`build/ips-fx/ips/rainy75v2-ips.bin`、`manifest.json`、`background.gif`。`manifest.json` 的 `variant` 为 `interactive-v1`，网页烧录工具会核对 SHA 与长度。

批量检查所有方案是否还在 flash 预算内：

```sh
python tools/build_matrix.py --dir build/design-gallery
```
