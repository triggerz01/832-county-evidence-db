"""Add concrete official project and person evidence views to the V3 prototype."""

from pathlib import Path

page_path = Path(__file__).with_name("832_research_system_v3.html")
page = page_path.read_text(encoding="utf-8")


def replace_once(old: str, new: str) -> None:
    global page
    count = page.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one markup match, got {count}: {old[:110]}")
    page = page.replace(old, new, 1)


project_and_person = '''
      <div class="section" id="projectSection"><div class="head"><div><div class="kicker">官方 XLSX + 政府网页逐项交叉核对</div><h2>涞水 2024 年项目与实施地点</h2></div><p>43 个项目拆成 158 条实施地点行；预算字段为 2024 年计划安排，项目编号同时保留网页和 XLSX 两套原号。</p></div><div class="note"><b>这是真实可检索的项目数据</b>43 个项目的 2024 年安排资金合计 19,518 万元，与县政府正文披露的到位资金总额相同。这个数值交叉校验不代表已经支付、完工或产生收入。</div><div class="toolbar" style="margin-top:9px"><div class="field wide"><label for="projectSearch">项目名称 / 地点 / 责任单位</label><input id="projectSearch" type="search" placeholder="例：农特产品、酸枣、南关村"></div><div class="field"><label for="projectCategory">项目类别</label><select id="projectCategory"><option value="">全部类别</option></select></div></div><div class="count" id="projectCount"></div><div class="table-wrap"><table><thead><tr><th>政府项目</th><th>类别</th><th>2024 安排资金</th><th>实施行</th><th>网页 / 表格编号</th><th>操作</th></tr></thead><tbody id="projectRows"></tbody></table></div><div class="pager"><span id="projectPager"></span><div><button id="prevProject">上一页</button> <button id="nextProject">下一页</button></div></div></div>
      <div class="section"><div class="head"><div><div class="kicker">三县官方来源交叉核验</div><h2>8 条带原表行的证据核对</h2></div><p>保留不一致、尚待确认的地方；不会把资金计划、企业产值或报告自述直接当作项目收益。</p></div><div class="toolbar"><div class="field"><label for="evidenceCounty">县域</label><select id="evidenceCounty"><option value="">全部县域</option><option>柞水县</option><option>霍邱县</option><option>涞水县</option></select></div><div class="field wide"><label for="evidenceSearch">项目与原始事实</label><input id="evidenceSearch" type="search" placeholder="例：金米、预算、莲藕"></div></div><div class="count" id="evidenceCount"></div><div class="case-grid" id="evidenceGrid"></div></div>
      <div class="section"><div class="head"><div><div class="kicker">人物提及关系表样本</div><h2>按公开报道中的人物检索</h2></div><p>目前只人工提取柞水一篇报道中的 4 条公开人物提及；按姓名检索可回到具体报道，不把人员名单当成完整访谈档案。</p></div><div class="toolbar"><div class="field wide"><label for="personSearch">姓名 / 身份 / 县域</label><input id="personSearch" type="search" placeholder="例：李正森、农业农村局"></div></div><div class="count" id="personCount"></div><div class="case-grid" id="personGrid"></div></div>
'''
replace_once('    </section>\n    <section id="tasks" class="page">', project_and_person + '    </section>\n    <section id="tasks" class="page">')

replace_once(
    '<div class="num">165</div><div class="lab">柞水 2024 进度表行号上限</div><div class="sub">与项目库不是同一总体</div>',
    '<div class="num">43 / 158</div><div class="lab">涞水项目 / 实施地点行</div><div class="sub">2024 计划安排 19,518 万元</div>',
)
replace_once(
    '<div class="section"><div class="head"><div><div class="kicker">业务问题驱动 SQL',
    '<div class="section card"><h3>涞水 43 个项目：按类别分组的真实计划资金</h3><p>从项目表按项目唯一键汇总，避免 158 条实施地点行重复计算预算。单位：万元。</p><div class="chart" id="projectCategoryChart"></div></div><div class="section"><div class="head"><div><div class="kicker">业务问题驱动 SQL',
)
replace_once(
    '<div class="entity"><b>government_project / project_source_match</b><code>project_id PK · project_year · county_id FK; (project_id,row_id) PK</code></div>',
    '<div class="entity"><b>government_project / project_location</b><code>project_id PK · project_year · county_id FK · category · planned_2024_funding; location_id PK · project_id FK · source_row_id FK</code></div><div class="entity"><b>project_source_match</b><code>(project_id,row_id) PK · match_method · checked_by · checked_at</code></div>',
)
replace_once(
    '<div class="api"><b>组合检索</b><p><code>GET /search</code>',
    '<div class="api"><b>项目与证据详情</b><p><code>GET /projects</code> 输入县域、类别、项目名与页码；输出项目、原始两套编号、实施地点行、来源链接及口径说明。跨来源匹配须人工确认。</p></div><div class="api"><b>组合检索</b><p><code>GET /search</code>',
)
replace_once(
    '柞水首轮手工核对 30–50 条产业项目库明细、10–20 条对应目标和进度；涞水 43 项网页可做跨县扩展。宽表 PDF/XLSX 需校对原文。',
    '已逐项核对涞水 43 个项目与 158 条 XLSX 实施行；柞水项目库再手工核对 30–50 条产业项目及版本，霍邱保留核验样本。PDF/XLSX 宽表仍需校对原文。',
)
replace_once(
    '<div class="entity"><b>county_indicator / audit_log</b><code>indicator_id PK · year · unit · source_id FK; log_id PK · actor_id FK</code></div>',
    '<div class="entity"><b>county_indicator / audit_log</b><code>indicator_id PK · year · unit · source_id FK; log_id PK · actor_id FK</code></div>',
)

page_path.write_text(page, encoding="utf-8")
print("V3 data views added")
