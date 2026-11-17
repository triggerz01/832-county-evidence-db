# DESIGN.md · 832 县域产业证据管理数据库 阶段汇报

场景路由：学术风（开题 / 中期 / 答辩）。受众 = 任课教师 + 同班同学，时长 10–12 分钟，正式度中高。

## ① 画布与安全区

- 1280×720，padding 60（内容区 1160×600，y 60–660）
- 页眉：全篇 A3 模式 —— 顶部 8px 深蓝实条（y 0–8）
- 标题块：y 60–104（主标 34px Bold）
- 视觉母题：主标题下 1px 贯通细线，只在主标题处出现一次
- 页脚：y 670；左「832 县域产业证据管理数据库 · 课程阶段汇报」14px 灰；右页码 14px 深蓝

## ② 配色

| 槽 | 值 | 用途 |
|---|---|---|
| 主色 | `#1E4FA8` | 顶条、编号、强调 |
| 藏蓝 | `#0E3F8C` | 主标题、章节扉页 |
| 辅色 | `#F0F5FC` / `#E8EFF8` | 卡片底、表头浅底 |
| 强调 | `#D9534F` | 异常、风险、被拒（单页 ≤3%） |
| 数据黄 | `#FFC107` | 仅图表/关键数字底标（单页 ≤3%） |
| 文本 | `#1A2230` / `#4A5568` / `#8B97A8` | 主 / 副 / 辅助 |
| 线 | `#D6DCE5` / `#E5E7EB` | 分隔、表格线 |
| 底 | `#FFFFFF` / `#F7F9FC` | 背景 |

禁：紫粉玫红、橙绿大色块、渐变卡底、金色、3D。

## ③ 字体

- 中文：Microsoft YaHei（黑体一套到底）
- 西文：Times New Roman，仅用于封面英文长标题
- 阶梯：封面主标 64 / 章节大字 150 / 巨数字 76–96 / 页主标 34 / 卡内标 24 / 正文 20–22 / 表格 17–18 / 注释 14

## ④ 视觉母题

主标题下 1px `#D6DCE5` 贯通线（1160px），全篇仅此处用线；卡片一律无内部线。

## ⑤ 配图清单

| 文件 | 用途 | 来源 | 使用页 |
|---|---|---|---|
| `assets/er_overview.png` | 总览 E-R 图（主角） | 项目 docs/er 生成 | P8 |
| `assets/er_domain1.png` | 资料与案例域 | 同上 | P9 |
| `assets/er_domain2.png` | 任务与审核域 | 同上 | P9 |
| `assets/er_domain3.png` | 政府项目与核验域 | 同上 | P9 |
| `assets/shot_dashboard.png` | 总览页截图（可替换） | 项目实测截图 | P5 |
| `assets/shot_case_detail.png` | 案例详情（可替换） | 同上 | P12 |
| `assets/shot_stats.png` | 统计核验页（可替换） | 同上 | P14 |
| `assets/shot_cases.png` | 案例列表（可替换） | 同上 | P15 |

> 用户要求「截图自己贴」，以上截图均为**尺寸已定好的占位**，右键「更改图片」即可替换，版式不跑。

## 页面清单（18 页）

| # | type | role | 标题 |
|---|---|---|---|
| 1 | cover | hero | 832 县域产业证据管理数据库 |
| 2 | catalog | supporting | 目录 |
| 3 | section | transition | 01 场景与对象 |
| 4 | content | supporting | 297 篇报道散在网页里，同一个县的说法互相对不上 |
| 5 | content | supporting | 四类角色，四种看得见的东西 |
| 6 | section | transition | 02 数据库设计与 E-R |
| 7 | content | hero | 22 张表分三个域，一个域对应一类问题 |
| 8 | content | hero | 总览 E-R：三条主链撑起整个库 |
| 9 | content | supporting | 三个分域各自带一张明细 E-R |
| 10 | content | supporting | 范式到 3NF，两处冗余是故意留的 |
| 11 | section | transition | 03 功能实现 |
| 12 | content | supporting | 一条案例从草稿到公开发布，五步都有痕迹 |
| 13 | content | supporting | 每项需求都能落到一张表、一条 SQL、一个函数 |
| 14 | content | hero | 统计页上每个数字都由库里一条 SQL 现算 |
| 15 | content | supporting | 权限写在 WHERE 里，约束交给数据库自己拦 |
| 16 | section | transition | 04 进展与边界 |
| 17 | content | supporting | 能跑的已经有，不能跑的说清楚 |
| 18 | ending | hero | 请老师批评指正 |
