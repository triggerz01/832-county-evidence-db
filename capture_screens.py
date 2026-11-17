"""把登录后的页面渲染成静态 HTML，再用 headless Edge 截图，产出 docs/screenshots。

不启动服务器：直接用 Flask 测试客户端取页面，并把 CSS 链接改写成本地绝对路径。
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "screenshots"
TMP = ROOT / "tmp" / "shots"
OUT.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)

EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
CSS = (ROOT / "static" / "style.css").as_uri()

import app as application  # noqa: E402


def client_for(name=None):
    c = application.app.test_client()
    if name:
        c.post("/login", data={"display_name": name, "password": "832demo"})
    return c


SHOTS = [
    ("01_login", None, "/login", "登录：六种角色与统一演示口令"),
    ("02_dashboard_leader", "队长", "/", "总览：逾期任务、状态分布、真实数据量"),
    ("03_reports", "队长", "/reports?kw=%E9%9C%8D%E9%82%B1", "资料检索：按县查报道并回跳原文"),
    ("04_cases", "研究员", "/cases?mechanism=%E5%B0%B1%E4%B8%9A", "案例组合检索：按帮扶方式筛选"),
    ("05_case_detail", "研究员", "/cases/C-003", "案例详情：帮扶方式与出处摘录"),
    ("06_task_detail", "队长", "/tasks/T-003", "任务详情：版本、审核记录与操作流水"),
    ("07_stats", "队长", "/stats", "统计核验：分组、聚合、金额勾稽"),
    ("08_task_submit", "队员甲", "/tasks/T-001", "队员视角：可提交版本的入口"),
]


def capture(tag, html, note):
    page = TMP / f"{tag}.html"
    page.write_text(html.replace('href="/static/style.css"', f'href="{CSS}"'),
                    encoding="utf-8")
    png = OUT / f"{tag}.png"
    run = subprocess.run(
        [str(EDGE), "--headless=new", "--disable-gpu", "--disable-extensions",
         "--no-first-run", "--hide-scrollbars", "--force-device-scale-factor=1.5",
         "--window-size=1280,1000", "--virtual-time-budget=3000",
         f"--screenshot={png}", page.as_uri()],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    ok = png.exists() and png.stat().st_size > 8000
    print(("  OK  " if ok else "  FAIL") + f" {png.name}  {note}")
    if not ok:
        print(run.stderr[-300:])
    return ok


def main():
    application.app.config.update(TESTING=True)
    failed = 0
    for tag, user, path, note in SHOTS:
        c = client_for(user)
        resp = c.get(path)
        if resp.status_code != 200:
            print(f"  FAIL {tag} HTTP {resp.status_code}")
            failed += 1
            continue
        if not capture(tag, resp.get_data(as_text=True), note):
            failed += 1
    print(f"\n共 {len(SHOTS)} 张，失败 {failed} 张，输出目录：{OUT}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
