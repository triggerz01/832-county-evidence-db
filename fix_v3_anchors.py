from pathlib import Path

path = Path(__file__).with_name("832_research_system_v3.html")
html = path.read_text(encoding="utf-8")
for old, new in [
    ('<div class="section"><div class="head"><div><div class="kicker">三县官方来源交叉核验</div>', '<div class="section" id="evidenceSection"><div class="head"><div><div class="kicker">三县官方来源交叉核验</div>'),
    ('<div class="section"><div class="head"><div><div class="kicker">人物提及关系表样本</div>', '<div class="section" id="personSection"><div class="head"><div><div class="kicker">人物提及关系表样本</div>'),
]:
    if html.count(old) != 1:
        raise RuntimeError(f"Missing unique anchor: {old}")
    html = html.replace(old, new, 1)
path.write_text(html, encoding="utf-8")
print("V3 jump targets fixed")
