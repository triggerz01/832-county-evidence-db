"""生成可放进 PPT 的 E-R 图：16:9 画布（1280×720），输出 SVG 与 2 倍 PNG。

用法：
    python docs/er/build_er.py
产物：
    docs/er/00_总览.svg / .png
    docs/er/01_资料与案例域.svg / .png
    docs/er/02_任务与审核域.svg / .png
    docs/er/03_政府项目与核验域.svg / .png
    docs/er/index.html   （预览与 A4 横向打印）

图形规范（教材式 E-R）：
    矩形 = 实体（框内列属性，主键加下划线）
    菱形 = 联系（连线旁标 1 / n / m）
    椭圆 = 联系的属性
"""

import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent
W, H = 1280, 720

FONT = '"Microsoft YaHei","PingFang SC","Hiragino Sans GB",-apple-system,sans-serif'

INK = "#1d1d1b"
INK2 = "#5f5e5a"
INK3 = "#8a8880"
LINE = "#9c9a92"
BLUE_F, BLUE_S, BLUE_T = "#EEF5FC", "#2C6FA8", "#14486F"
AMB_F, AMB_S, AMB_T = "#FDF3E2", "#C2801F", "#7A4708"
TEAL_F, TEAL_S = "#E9F5F0", "#2F8A6B"
CARD = "#FCFCFA"


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


class Entity:
    def __init__(self, name, x, y, w, pk, attrs, note=None):
        self.name, self.x, self.y, self.w = name, x, y, w
        self.pk, self.attrs, self.note = pk, attrs, note
        self.h = 50 + 26 * (len(attrs) + 1) + 14 + (26 if note else 0)

    def anchor(self, side):
        cx, cy = self.x + self.w / 2, self.y + self.h / 2
        return {"l": (self.x, cy), "r": (self.x + self.w, cy),
                "t": (cx, self.y), "b": (cx, self.y + self.h)}[side]

    def svg(self):
        rows = [self.pk] + self.attrs
        parts = [
            f'<rect x="{self.x}" y="{self.y}" width="{self.w}" height="{self.h}" '
            f'rx="10" fill="{BLUE_F}" stroke="{BLUE_S}" stroke-width="1.6"/>',
            f'<text x="{self.x + 18}" y="{self.y + 32}" font-size="19" font-weight="600" '
            f'fill="{BLUE_T}">{esc(self.name)}</text>',
            f'<line x1="{self.x + 14}" y1="{self.y + 44}" x2="{self.x + self.w - 14}" '
            f'y2="{self.y + 44}" stroke="{BLUE_S}" stroke-width="1" opacity="0.45"/>',
        ]
        for i, row in enumerate(rows):
            ty = self.y + 70 + i * 26
            under = (' text-decoration="underline"' if i == 0 else "")
            weight = ' font-weight="600"' if i == 0 else ""
            fill = BLUE_T if i == 0 else "#3f3f3c"
            parts.append(
                f'<text x="{self.x + 18}" y="{ty}" font-size="15"{weight} fill="{fill}"{under}>'
                f'{esc(row)}</text>')
        if self.note:
            parts.append(
                f'<text x="{self.x + 18}" y="{self.y + 70 + len(rows) * 26}" font-size="13" '
                f'fill="{INK3}">{esc(self.note)}</text>')
        return "".join(parts)


class Relation:
    def __init__(self, name, a, b, cx, cy, w=110, h=54, route=None,
                 card_a="1", card_b="n", attr=None, card_pos=None):
        self.name, self.a, self.b = name, a, b
        self.cx, self.cy, self.w, self.h = cx, cy, w, h
        self.route = route
        self.card_a, self.card_b = card_a, card_b
        self.attr = attr
        self.card_pos = card_pos

    def _point(self, end):
        if end[0] == "pt":
            return end[1]
        return end[0].anchor(end[1])

    def geometry(self):
        pa, pb = self._point(self.a), self._point(self.b)
        if self.route:
            pts = [pa] + self.route + [pb]
            return " ".join(f"{x},{y}" for x, y in pts)
        return f"{pa[0]},{pa[1]} {pb[0]},{pb[1]}"

    def svg_lines(self):
        return (f'<polyline points="{self.geometry()}" fill="none" stroke="{LINE}" '
                f'stroke-width="1.8" stroke-linejoin="round"/>')

    def svg_diamond(self):
        cx, cy, w, h = self.cx, self.cy, self.w, self.h
        pts = f"{cx},{cy - h / 2} {cx + w / 2},{cy} {cx},{cy + h / 2} {cx - w / 2},{cy}"
        n = len(self.name)
        fs = 16 if n <= 2 else 15
        return (
            f'<polygon points="{pts}" fill="{AMB_F}" stroke="{AMB_S}" stroke-width="1.6"/>'
            f'<text x="{cx}" y="{cy + 6}" font-size="{fs}" font-weight="600" '
            f'fill="{AMB_T}" text-anchor="middle">{esc(self.name)}</text>')

    def svg_cards(self, entities=()):
        """基数标签：白描边压在线上；间距过窄放菱形两侧；落进实体框则整体外推。"""
        out = []
        for idx, (end, text) in enumerate(((self.a, self.card_a), (self.b, self.card_b))):
            px, py = self._point(end)
            dx, dy = self.cx - px, self.cy - py
            dist = max((dx * dx + dy * dy) ** 0.5, 1)
            if self.card_pos:
                lx, ly = self.card_pos[idx]
            elif dist < 80:
                lx = self.cx - self.w / 2 - 17 if idx == 0 else self.cx + self.w / 2 + 17
                ly = self.cy + 6
            else:
                ux, uy = dx / dist, dy / dist
                step = min(36.0, max(18.0, dist * 0.30))
                lx, ly = px + ux * step - uy * 14, py + uy * step + ux * 14
            for _ in range(20):
                if not any(e.x - 6 < lx < e.x + e.w + 6 and e.y - 6 < ly < e.y + e.h + 6
                           for e in entities):
                    break
                lx += (dx / dist) * 14
                ly += (dy / dist) * 14
            else:
                lx = self.cx - self.w / 2 - 17 if idx == 0 else self.cx + self.w / 2 + 17
                ly = self.cy + 6
            out.append(
                f'<text x="{lx:.0f}" y="{ly:.0f}" font-size="17" font-weight="600" '
                f'fill="{INK}" text-anchor="middle" stroke="#ffffff" stroke-width="4" '
                f'paint-order="stroke">{esc(text)}</text>')
        return "".join(out)

    def svg_attr(self):
        if not self.attr:
            return ""
        ax, ay = self.attr
        return (
            f'<line x1="{self.cx}" y1="{self.cy + self.h / 2}" x2="{ax}" y2="{ay - 16}" '
            f'stroke="{LINE}" stroke-width="1.6"/>'
            f'<ellipse cx="{ax}" cy="{ay}" rx="52" ry="19" fill="#F3F1FB" stroke="#6A5CB8" '
            f'stroke-width="1.6"/>'
            f'<text x="{ax}" y="{ay + 5}" font-size="14" fill="#3E3489" '
            f'text-anchor="middle">是否负责人</text>')


def header(title, subtitle, accent=BLUE_S):
    return (
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>'
        f'<rect x="48" y="44" width="7" height="42" rx="3.5" fill="{accent}"/>'
        f'<text x="70" y="66" font-size="27" font-weight="600" fill="{INK}">{esc(title)}</text>'
        f'<text x="70" y="90" font-size="15" fill="{INK2}">{esc(subtitle)}</text>')


def legend():
    y = H - 26
    items = [
        ("rect", "实体", BLUE_F, BLUE_S),
        ("diamond", "联系", AMB_F, AMB_S),
        ("ellipse", "联系的属性", "#F3F1FB", "#6A5CB8"),
    ]
    out = [f'<line x1="48" y1="{y - 26}" x2="{W - 48}" y2="{y - 26}" stroke="#e6e3da"/>']
    x = 48
    for kind, label, fill, stroke in items:
        if kind == "rect":
            shape = (f'<rect x="{x}" y="{y - 11}" width="26" height="17" rx="3" '
                     f'fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
        elif kind == "diamond":
            shape = (f'<polygon points="{x + 13},{y - 12} {x + 27},{y - 3} {x + 13},{y + 6} '
                     f'{x - 1},{y - 3}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
        else:
            shape = (f'<ellipse cx="{x + 13}" cy="{y - 3}" rx="14" ry="9" '
                     f'fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
        out.append(shape)
        out.append(f'<text x="{x + 34}" y="{y + 2}" font-size="14" fill="{INK2}">{label}</text>')
        x += 34 + len(label) * 15 + 26
    out.append(
        f'<text x="{x}" y="{y + 2}" font-size="14" fill="{INK2}">'
        f'下划线 = 主键　　1 / n / m = 联系基数</text>')
    out.append(
        f'<text x="{W - 48}" y="{y + 2}" font-size="13" fill="#a8a59c" text-anchor="end">'
        f'832 工程 · 调研任务与县域产业证据管理系统</text>')
    return "".join(out)


def build(title, subtitle, entities, relations, accent=BLUE_S):
    body = [header(title, subtitle, accent)]
    body += [r.svg_lines() for r in relations]
    body += [e.svg() for e in entities]
    body += [r.svg_diamond() for r in relations]
    body += [r.svg_attr() for r in relations]
    body += [r.svg_cards(entities) for r in relations]
    body.append(legend())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="{W}" height="{H}" font-family=\'{FONT}\'>' + "".join(body) + "</svg>")


# ---------------------------------------------------------------- 图 1：资料与案例域

def diagram_cases():
    src = Entity("来源文档", 60, 120, 220, "文档ID", ["网址（唯一）", "发布方", "文档类别"])
    rep = Entity("公开报道", 400, 120, 230, "报道ID", ["发布日期"],
                 note="标题取自来源文档")
    cty = Entity("县域", 930, 120, 250, "县域ID", ["省份", "县名", "核对状态"])
    exc = Entity("出处摘录", 70, 340, 230, "摘录ID", ["定位（段落）", "摘要"])
    case = Entity("产业案例", 760, 340, 300, "案例ID", ["标题", "所属产业", "发布状态"])
    mech = Entity("帮扶方式", 790, 540, 240, "方式ID", ["名称"])

    rels = [
        Relation("对应", (src, "r"), (rep, "l"), 340, 189, w=100, h=52,
                 card_a="1", card_b="1"),
        Relation("摘录", (src, "b"), (exc, "t"), 170, 299, w=100, h=54,
                 card_a="1", card_b="n"),
        Relation("发布", (rep, "r"), (cty, "l"), 780, 189, w=112, h=54,
                 card_a="n", card_b="1"),
        Relation("所属", (cty, "b"), (case, "t"), 1055, 299, w=100, h=54,
                 card_a="1", card_b="n"),
        Relation("采用", (case, "b"), (mech, "t"), 910, 509, w=100, h=40,
                 card_a="m", card_b="n"),
        Relation("佐证", (exc, "r"), (case, "l"), 520, 402, w=112, h=56,
                 card_a="m", card_b="n"),
    ]
    return build(
        "资料与案例域",
        "一篇报道可整理出多个案例；案例与帮扶方式、案例与出处摘录均为 m:n，靠桥表落地",
        [src, rep, cty, exc, case, mech], rels)


# ---------------------------------------------------------------- 图 2：任务与审核域

def diagram_tasks():
    team = Entity("调研队", 60, 110, 220, "调研队ID", ["队名", "数据性质"])
    user = Entity("用户账号", 60, 340, 240, "用户ID", ["姓名", "角色", "口令散列"])
    task = Entity("调研任务", 390, 110, 300, "任务ID", ["主题", "材料类型", "截止时间", "状态"])
    ver = Entity("提交版本", 820, 110, 290, "版本ID", ["版本号", "材料类型", "提交时间"])
    rev = Entity("审核动作", 820, 400, 290, "审核ID", ["决定", "理由", "时间"])

    rels = [
        Relation("隶属", (team, "b"), (user, "t"), 175, 294, w=100, h=52,
                 card_a="1", card_b="n"),
        Relation("承担", (user, "r"), (task, "l"), 345, 310, w=104, h=56,
                 card_a="m", card_b="n", attr=(378, 372)),
        Relation("提交", (task, "r"), (ver, "l"), 745, 189, w=110, h=52,
                 card_a="1", card_b="n"),
        Relation("撰写", ("pt", (300, 462)), (ver, "b"), 620, 337, w=110, h=56,
                 card_a="1", card_b="n"),
        Relation("审核", (ver, "b"), (rev, "t"), 965, 324, w=100, h=54,
                 card_a="1", card_b="n"),
        Relation("执行", (user, "b"), (rev, "l"), 450, 487, w=100, h=54,
                 card_a="1", card_b="n"),
    ]
    return build(
        "任务与审核域",
        "「承担」是带属性的 m:n 联系（是否负责人）；版本—审核为一对多，退回后可再审",
        [team, user, task, ver, rev], rels, accent=AMB_S)


# ---------------------------------------------------------------- 图 3：政府项目与核验域

def diagram_projects():
    cty = Entity("县域", 70, 110, 230, "县域ID", ["省份", "县名"])
    proj = Entity("政府项目", 420, 110, 300, "项目编号", ["项目名称", "类别", "计划年度"])
    issue = Entity("证据核对记录", 860, 110, 330, "核对ID",
                   ["项目原名", "库内使用方式", "禁止推断事项"])
    snap = Entity("项目快照", 70, 400, 270, "快照ID", ["口径", "版本标签", "计划资金"])
    loc = Entity("实施地点", 420, 400, 300, "地点ID",
                 ["原表行号", "实施地点原文", "计划资金"])
    doc = Entity("来源文档", 860, 420, 330, "文档ID", ["网址（唯一）", "发布方"])

    rels = [
        Relation("拥有", (cty, "r"), (proj, "l"), 360, 172, w=100, h=52),
        Relation("编制", (proj, "b"), (snap, "t"), 350, 340, w=100, h=54),
        Relation("落点", (proj, "b"), (loc, "t"), 595, 325, w=100, h=54),
        Relation("依据", (loc, "r"), (doc, "l"), 790, 472, w=96, h=52),
        Relation("依据", (doc, "b"), (snap, "b"), 600, 610, w=100, h=52,
                 route=[(1025, 610), (205, 610)], card_a="n", card_b="1",
                 card_pos=((1043, 560), (186, 578))),
        Relation("引用", (doc, "t"), (issue, "b"), 1025, 347, w=100, h=54,
                 card_a="n", card_b="m"),
    ]
    return build(
        "政府项目与核验域",
        "43 个项目 × 158 条实施地点；金额两处独立存储，用于勾稽核对（计划口径，非实际支出）",
        [cty, proj, issue, snap, loc, doc], rels, accent=TEAL_S)


# ---------------------------------------------------------------- 图 0：总览

def chip(x, y, w, text, count=None, fill="#ffffff", stroke="#cfd9e4", size=16):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="42" rx="8" fill="{fill}" '
           f'stroke="{stroke}" stroke-width="1.3"/>',
           f'<text x="{x + 16}" y="{y + 27}" font-size="{size}" fill="{INK}">{esc(text)}</text>']
    if count is not None:
        out.append(f'<text x="{x + w - 16}" y="{y + 27}" font-size="14" fill="{INK3}" '
                   f'text-anchor="end">{esc(count)}</text>')
    return "".join(out)


def diagram_overview():
    panels = [
        ("资料与案例域", BLUE_S, 48, [
            ("来源文档", "313"), ("公开报道", "297"), ("出处摘录", "6"),
            ("产业案例", "6"), ("帮扶方式", "17"), ("县域", "298")]),
        ("任务与审核域", AMB_S, 456, [
            ("调研队 / 账号", "1 / 6"), ("调研任务", "5"), ("任务分派", "5"),
            ("提交版本", "4"), ("审核动作", "3"), ("操作日志", "12")]),
        ("政府项目与核验域", TEAL_S, 864, [
            ("政府项目", "43"), ("项目快照", "43"), ("实施地点", "158"),
            ("证据核对记录", "8"), ("来源文档", "313")]),
    ]
    body = [header("实体与联系总览", "22 张表 = 18 张实体表 + 4 张 m:n 桥表；三域共用「县域」与「来源文档」两个维度")]

    for title, accent, x, items in panels:
        body.append(f'<rect x="{x}" y="120" width="368" height="386" rx="14" '
                    f'fill="{CARD}" stroke="#e4e1d8" stroke-width="1.3"/>')
        body.append(f'<rect x="{x}" y="120" width="368" height="52" rx="14" fill="{accent}"/>')
        body.append(f'<rect x="{x}" y="150" width="368" height="22" fill="{accent}"/>')
        body.append(f'<text x="{x + 20}" y="154" font-size="19" font-weight="600" '
                    f'fill="#ffffff">{esc(title)}</text>')
        for i, (name, cnt) in enumerate(items):
            body.append(chip(x + 18, 190 + i * 52, 332, name, cnt))

    body.append(f'<rect x="48" y="530" width="1184" height="120" rx="14" '
                f'fill="#FBF9F4" stroke="#e4e1d8" stroke-width="1.3"/>')
    body.append('<text x="70" y="562" font-size="17" font-weight="600" fill="#7A4708">'
                '4 张 m:n 联系表（菱形落地的结果）</text>')
    bridges = [("case_mechanism", "案例 ↔ 帮扶方式", "18"),
               ("case_evidence", "案例 ↔ 出处摘录", "6"),
               ("task_assignment", "任务 ↔ 成员（带是否负责人）", "5"),
               ("evidence_issue_source", "核对记录 ↔ 来源文档", "15")]
    for i, (tbl, desc, n) in enumerate(bridges):
        bx = 48 + i * 294
        body.append(f'<rect x="{bx + 18}" y="578" width="268" height="54" rx="10" '
                    f'fill="#BA7517" fill-opacity="0.10" stroke="#C2801F" stroke-width="1.2"/>')
        body.append(f'<text x="{bx + 32}" y="600" font-size="15" font-weight="600" '
                    f'fill="#7A4708">{esc(tbl)}　{esc(n)} 行</text>')
        body.append(f'<text x="{bx + 32}" y="620" font-size="14" fill="{INK2}">{esc(desc)}</text>')

    body.append(legend())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="{W}" height="{H}" font-family=\'{FONT}\'>' + "".join(body) + "</svg>")


# ---------------------------------------------------------------- 输出

DIAGRAMS = [
    ("00_总览", diagram_overview),
    ("01_资料与案例域", diagram_cases),
    ("02_任务与审核域", diagram_tasks),
    ("03_政府项目与核验域", diagram_projects),
]

EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def render_png(svg_path, png_path):
    subprocess.run(
        [str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--no-first-run", "--force-device-scale-factor=2",
         f"--window-size={W},{H}", "--default-background-color=ffffffff",
         "--virtual-time-budget=1500", f"--screenshot={png_path}", svg_path.as_uri()],
        capture_output=True, timeout=60)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = []
    for name, fn in DIAGRAMS:
        svg = fn()
        svg_path = OUT / f"{name}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        png_path = OUT / f"{name}.png"
        render_png(svg_path, png_path)
        size = png_path.stat().st_size if png_path.exists() else 0
        print(f"  {name}.svg  {len(svg) // 1024} KB   png {size // 1024} KB")
        files.append(name)

    cards = []
    for name in files:
        title = name.split("_", 1)[1]
        cards.append(f'<figure><img src="{name}.svg" alt="{title}"><figcaption>{title}</figcaption></figure>')
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>832 工程 · E-R 图</title>
<style>
@page {{ size: A4 landscape; margin: 0; }}
body {{ margin:0; background:#f3f1ec; font-family:{FONT}; color:{INK}; }}
h1 {{ font-size:20px; font-weight:600; margin:26px 0 4px 32px; }}
p.meta {{ margin:0 0 18px 32px; color:{INK2}; font-size:13px; }}
figure {{ margin:0 0 22px; background:#fff; border:1px solid #e4e1d8; border-radius:12px;
         overflow:hidden; page-break-after:always; }}
figure img {{ display:block; width:100%; }}
figcaption {{ padding:10px 16px; font-size:13px; color:{INK2}; border-top:1px solid #eeeae1; }}
.wrap {{ max-width:1320px; margin:0 auto 40px; padding:0 20px; }}
@media print {{ body {{ background:#fff; }} .wrap {{ padding:0; }} figure {{ border:0; border-radius:0; margin:0; }} figcaption {{ display:none; }} h1,p.meta {{ display:none; }} }}
</style></head><body>
<div class="wrap">
<h1>832 工程调研任务与县域产业证据管理系统 · E-R 图</h1>
<p class="meta">教材式画法：矩形=实体（框内列属性，主键加下划线），菱形=联系，椭圆=联系属性，连线旁标 1 / n / m。<br>
每张图 1280×720（16:9），同目录下的 .png 为 2 倍图，可直接插入 PPT；.svg 可无损缩放。</p>
{''.join(cards)}
</div></body></html>"""
    (OUT / "index.html").write_text(html, encoding="utf-8")
    print(f"  index.html 已生成，共 {len(files)} 张图")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
