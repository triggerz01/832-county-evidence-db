"""Export actual SQLite query results to a standalone, read-only HTML viewer."""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "832_research_sample.sqlite"
OUT = ROOT / "832_sqlite_results_demo.html"
SQL_FILE = ROOT / "832_verified_queries.sql"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row


def run(sql: str):
    cursor = conn.execute(sql)
    return {
        "columns": [col[0] for col in cursor.description],
        "rows": [list(row) for row in cursor.fetchall()],
    }


query_sql = [piece.strip() + ";" for piece in SQL_FILE.read_text(encoding="utf-8").split(";") if piece.strip()]
assert len(query_sql) == 6
query_info = [
    ("公开报道按省汇总", "真实公开数据", "按省份统计本地核实的 297 篇人大公开报道。这里统计报道篇数，不计算 832 县覆盖率。"),
    ("同时涉及就业与土地流转的案例", "公开报道整理", "通过案例—帮扶方式多对多关系找出同时具有两种方式的案例。"),
    ("逾期未交指定材料的任务", "课程模拟", "根据任务截止日与指定材料类型，用 NOT EXISTS 找出未按期提交者。查询日期固定为 2026-10-29。"),
    ("涞水年度项目按类别汇总", "真实政府计划", "按 43 个唯一项目汇总 2024 年计划安排资金；158 条实施地点行不重复计预算。"),
    ("项目预算与实施行金额是否不符", "真实政府计划", "检查逐项目的实施行金额之和是否与项目计划金额一致。零行只表示本次金额核对通过。"),
    ("公开报道尚未提取案例的篇数", "整理进度", "表示本样本库的结构化整理缺口，不代表报道正文没有产业案例。"),
]
query_sources = [
    [("人大公开报道目录", "https://ae.ruc.edu.cn/xwzx/xydt/index.htm")],
    [("人大霍邱逐县报道", "https://ae.ruc.edu.cn/xwzx/xydt/fba7a54b0346410884e7eee36bd3bbc7.htm")],
    [],
    [("涞水政府项目计划网页", "https://www.laishui.gov.cn/index.php?a=show&c=index&catid=118&id=16947&m=content"), ("涞水官方 XLSX", "https://www.laishui.gov.cn/uploadfile/2025/0612/407795562290887859.xlsx")],
    [("涞水官方 XLSX", "https://www.laishui.gov.cn/uploadfile/2025/0612/407795562290887859.xlsx")],
    [("人大公开报道目录", "https://ae.ruc.edu.cn/xwzx/xydt/index.htm")],
]
display_columns = [
    ["省份", "报道篇数"], ["案例编号", "案例名称", "县域"],
    ["任务编号", "县域", "负责人", "指定交付", "截止日期"],
    ["项目类别", "项目数", "2024 计划资金（万元）"],
    ["项目编号", "项目名称", "项目计划（万元）", "实施行合计（万元）"],
    ["尚未提取案例的报道篇数"],
]
queries = []
for i, sql in enumerate(query_sql):
    result = run(sql)
    title, kind, meaning = query_info[i]
    queries.append({"title": title, "kind": kind, "meaning": meaning, "sql": sql,
                    "sources": query_sources[i], "displayColumns": display_columns[i], **result})

tables = [
    ("public_report", "公开报道", "SELECT r.report_id AS 编号,d.title AS 报道标题,c.province_raw AS 省份,c.county_name_raw AS 县名,r.published_date AS 日期,d.url AS 原文链接 FROM public_report r JOIN county c ON c.county_id=r.county_id JOIN source_document d ON d.document_id=r.document_id ORDER BY r.published_date DESC,r.report_id DESC"),
    ("government_project", "政府项目", "SELECT p.project_id AS 项目编号,p.project_name AS 项目名称,p.category AS 类别,s.budget_wan AS 年度计划万元,p.html_project_no AS 网页序号,p.xlsx_project_no AS 表格序号,d.url AS XLSX来源 FROM government_project p JOIN project_snapshot s ON s.project_id=p.project_id JOIN source_document d ON d.document_id=s.document_id ORDER BY p.html_project_no"),
    ("project_location", "项目实施行", "SELECT l.xlsx_row AS XLSX行号,p.project_id AS 项目编号,p.project_name AS 项目名称,l.implementation_location_raw AS 实施地点,l.planned_2024_funding_wan AS 年度计划万元,d.url AS 原表链接 FROM project_location l JOIN government_project p ON p.project_id=l.project_id JOIN source_document d ON d.document_id=l.document_id ORDER BY l.xlsx_row"),
    ("industry_case", "产业案例", "SELECT c.case_id AS 案例编号,c.title AS 案例名称,c.industry AS 产业,c.status AS 状态,c.data_kind AS 数据性质,COALESCE(GROUP_CONCAT(DISTINCT m.name),'') AS 帮扶方式,se.locator AS 原文位置,d.url AS 来源链接 FROM industry_case c LEFT JOIN case_mechanism cm ON cm.case_id=c.case_id LEFT JOIN mechanism m ON m.mechanism_id=cm.mechanism_id LEFT JOIN case_evidence ce ON ce.case_id=c.case_id LEFT JOIN source_excerpt se ON se.excerpt_id=ce.excerpt_id LEFT JOIN source_document d ON d.document_id=se.document_id GROUP BY c.case_id ORDER BY c.case_id"),
    ("field_task", "调研任务", "SELECT t.task_id AS 任务编号,c.county_name_raw AS 县名,t.topic AS 具体问题,t.required_kind AS 指定交付,t.due_at AS 截止日,t.state AS 状态,u.display_name AS 负责人,t.data_kind AS 数据性质 FROM field_task t JOIN county c ON c.county_id=t.county_id JOIN task_assignment a ON a.task_id=t.task_id AND a.is_lead=1 JOIN user_account u ON u.user_id=a.user_id ORDER BY t.task_id"),
    ("review_action", "审核记录", "SELECT r.review_id AS 审核编号,v.task_id AS 任务编号,v.version_no AS 提交版本,r.decision AS 结论,r.reason AS 意见,u.display_name AS 审核人,r.acted_at AS 日期 FROM review_action r JOIN deliverable_version v ON v.version_id=r.version_id JOIN user_account u ON u.user_id=r.reviewer_id ORDER BY r.review_id"),
    ("evidence_issue", "跨来源核验", "SELECT e.issue_id AS 核验编号,c.county_name_raw AS 县名,e.project_name_raw AS 项目名称,e.facts_json AS 原文事实,e.do_not_infer AS 不可推断,e.review_status AS 状态 FROM evidence_issue e JOIN county c ON c.county_id=e.county_id ORDER BY e.issue_id"),
    ("person_mention", "人物提及", "SELECT p.person_name AS 姓名,p.role_text AS 公开身份,p.context_summary AS 提及位置,d.title AS 报道,d.url AS 原文链接 FROM person_mention p JOIN public_report r ON r.report_id=p.report_id JOIN source_document d ON d.document_id=r.document_id ORDER BY p.mention_id"),
    ("source_document", "来源文件", "SELECT document_id AS 编号,publisher AS 发布机构,title AS 标题,source_kind AS 来源类型,checked_on AS 核验日期,url AS 链接 FROM source_document ORDER BY document_id"),
]
browser = []
for key, title, sql in tables:
    browser.append({"key": key, "title": title, **run(sql)})

hq_url = "https://ae.ruc.edu.cn/xwzx/xydt/fba7a54b0346410884e7eee36bd3bbc7.htm"
relations = {
    "reportCases": run(
        "SELECT c.case_id AS case_id,c.title AS title,c.industry AS industry "
        "FROM industry_case c JOIN case_evidence ce ON ce.case_id=c.case_id "
        "JOIN source_excerpt se ON se.excerpt_id=ce.excerpt_id "
        "JOIN source_document d ON d.document_id=se.document_id "
        "WHERE d.url=? ORDER BY c.case_id".replace("?", "'" + hq_url + "'")
    )["rows"],
    "caseModes": run(
        "SELECT m.name FROM case_mechanism cm JOIN mechanism m ON m.mechanism_id=cm.mechanism_id "
        "WHERE cm.case_id='C-003' ORDER BY m.name"
    )["rows"],
    "exampleProject": run(
        "SELECT p.project_id,p.project_name,s.budget_wan,COUNT(l.location_id),SUM(l.planned_2024_funding_wan) "
        "FROM government_project p JOIN project_snapshot s ON s.project_id=p.project_id "
        "JOIN project_location l ON l.project_id=p.project_id "
        "GROUP BY p.project_id ORDER BY COUNT(l.location_id) DESC LIMIT 1"
    )["rows"][0],
}

payload = {
    "queries": queries,
    "browser": browser,
    "relations": relations,
    "counts": {
        "reports": conn.execute("SELECT COUNT(*) FROM public_report").fetchone()[0],
        "projects": conn.execute("SELECT COUNT(*) FROM government_project").fetchone()[0],
        "locations": conn.execute("SELECT COUNT(*) FROM project_location").fetchone()[0],
        "sourceDocuments": conn.execute("SELECT COUNT(*) FROM source_document").fetchone()[0],
        "cases": conn.execute("SELECT COUNT(*) FROM industry_case").fetchone()[0],
        "tasks": conn.execute("SELECT COUNT(*) FROM field_task").fetchone()[0],
    },
}
conn.close()

html = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>832 SQLite 样本库｜真实查询结果演示</title>
<style>
:root{--deep:#17363b;--ink:#1c3438;--green:#16705f;--pale:#eaf4ee;--paper:#f6f7f2;--line:#dce7df;--muted:#617773;--gold:#dba96a}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.65 "Microsoft YaHei","PingFang SC",system-ui,sans-serif}a{color:var(--green);text-underline-offset:3px}button,input,select{font:inherit}button{cursor:pointer}
.shell{max-width:1420px;margin:auto;padding:0 28px 60px}.top{display:flex;justify-content:space-between;align-items:center;gap:20px;padding:20px 0;border-bottom:1px solid var(--line)}.brand{display:flex;gap:10px;align-items:center;font-weight:900}.badge{background:var(--gold);color:var(--deep);border-radius:9px;padding:7px 10px;font:900 17px Georgia,serif}.toplinks{display:flex;gap:16px;font-size:12px}.toplinks a{text-decoration:none}
.hero{margin:25px 0 15px;background:linear-gradient(125deg,#153b40,#246556);color:white;border-radius:18px;padding:32px;display:grid;grid-template-columns:1fr 310px;gap:22px}.eyebrow{font-size:10px;font-weight:900;letter-spacing:.15em;color:#90bd9d}.hero h1{font:700 clamp(30px,3.4vw,46px)/1.2 Georgia,"Songti SC","SimSun",serif;margin:7px 0 10px}.hero p{color:#d3e6dc;max-width:770px;font-size:13px}.hero .aside{border:1px solid #68a18b;background:#214d4a;border-radius:12px;padding:17px;font-size:12px}.hero .aside b{color:#ffdfa9}.hero .aside div{border-top:1px solid #567f73;margin-top:9px;padding-top:9px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0}.stat,.card{background:#fffefa;border:1px solid var(--line);border-radius:11px;padding:17px}.stat strong{font:700 27px Georgia,serif}.stat span{display:block;font-size:11px;color:var(--muted)}.notice{border:1px solid #cfdfcf;background:#eaf4e9;padding:13px 16px;border-radius:9px;font-size:12px;color:#466a55;margin:12px 0}.notice.warn{border-color:#ead7bd;background:#fff6e9;color:#855e38}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:24px 0 14px}.tabs button,.querynav button{border:1px solid var(--line);background:#fffefa;color:#517168;border-radius:8px;padding:10px 13px;font-size:12px}.tabs button.active,.querynav button.active{background:var(--deep);color:white;border-color:var(--deep)}.view{display:none}.view.active{display:block}.head{display:flex;justify-content:space-between;align-items:end;gap:15px;margin:18px 0 12px}.head h2{font:700 26px Georgia,"Songti SC","SimSun",serif;margin:0}.head p{font-size:11px;color:var(--muted);margin:0;max-width:600px}.twocol{display:grid;grid-template-columns:255px minmax(0,1fr);gap:12px}.querynav{display:grid;gap:7px;align-content:start}.querynav button{text-align:left}.querynav small{display:block;font-size:10px;opacity:.75}.card h3{margin:0 0 5px;font-size:18px}.card .sub{font-size:12px;color:var(--muted);margin:0 0 12px}.kind{display:inline-block;background:#e8f2e7;color:#34705a;border-radius:18px;font-size:10px;padding:3px 9px;font-weight:800;margin-bottom:9px}.code{background:#183238;color:#dcefe4;white-space:pre;overflow:auto;border-radius:9px;padding:16px;font:12px/1.6 Consolas,"Courier New",monospace;max-height:290px}
.resulttop{display:flex;justify-content:space-between;align-items:center;gap:10px;margin:17px 0 8px}.resulttop b{font-size:12px}.tablewrap{overflow:auto;border:1px solid var(--line);border-radius:9px;background:white}table{border-collapse:collapse;width:100%}th{background:#eaf2ea;color:#4b6d59;font-size:11px;text-align:left;white-space:nowrap;padding:10px}td{font-size:11px;padding:10px;border-top:1px solid #eef1eb;vertical-align:top;max-width:440px;min-width:85px;overflow-wrap:anywhere}td a{white-space:nowrap}.empty{text-align:center;padding:28px;color:var(--muted)}.toolbar{display:flex;gap:9px;flex-wrap:wrap;margin:0 0 10px}.toolbar select,.toolbar input{border:1px solid #cdded0;border-radius:7px;background:white;padding:9px 11px;font-size:12px}.toolbar input{flex:1 1 320px}.pager{display:flex;justify-content:space-between;align-items:center;gap:10px;margin:11px 0;font-size:11px;color:var(--muted)}.pager button{border:1px solid var(--line);background:white;border-radius:6px;padding:5px 10px;color:var(--green)}.pager button:disabled{opacity:.4}
.relation{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.relation .card{min-height:180px}.relation .step{font-size:10px;color:var(--green);font-weight:900}.relation h3{margin-top:7px}.relation p{font-size:12px;color:var(--muted)}.guide{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.guide h3{font-size:15px}.guide p,.guide li{font-size:12px;color:var(--muted)}.guide code{display:block;white-space:pre-wrap;word-break:break-word;background:#e8efe9;padding:10px;border-radius:6px;color:#315b4b;font-size:11px}.foot{font-size:11px;color:var(--muted);margin-top:30px;border-top:1px solid var(--line);padding-top:16px}
@media(max-width:900px){.hero{grid-template-columns:1fr}.twocol{grid-template-columns:1fr}.querynav{display:flex;overflow-x:auto}.querynav button{min-width:210px}.relation{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}}
@media(max-width:560px){.shell{padding:0 13px 35px}.top{align-items:start;flex-direction:column}.hero{padding:22px}.stats,.guide{grid-template-columns:1fr}.head{display:block}.toplinks{flex-wrap:wrap}}
</style></head><body><div class="shell">
<header class="top"><div class="brand"><span class="badge">832</span><span>SQLite 样本库 · 查询结果演示</span></div><div class="toplinks"><a href="832_research_system_v3.html">返回总设计 ↗</a><a href="832_research_sample.sqlite" download>下载 .sqlite</a><a href="832_verified_queries.sql">查看 SQL 文件</a></div></header>
<section class="hero"><div><div class="eyebrow">ACTUAL SQLITE OUTPUT · READ ONLY</div><h1>数据库里有什么，<br>查询能查出什么？</h1><p>下面的结果由 Python 直接读取同目录的 SQLite 文件、执行 6 条 SQL 后生成。你可以点选查询、查看原始记录和来源网址；所有业务模拟记录均有标记。</p></div><div class="aside"><b>看一个完整例子</b><div>报道 → 案例：人大霍邱报道提取 3 条案例</div><div>案例 → 方式：城西湖莲藕案例同时关联“就业”和“土地流转”</div><div>项目 → 地点：涞水年度项目表的 43 个项目拆为 158 条实施行</div></div></section>
<div class="stats"><div class="stat"><strong id="statReports"></strong><span>人大公开报道</span></div><div class="stat"><strong id="statProjects"></strong><span>涞水官方项目</span></div><div class="stat"><strong id="statLocations"></strong><span>项目实施地点行</span></div><div class="stat"><strong id="statDocs"></strong><span>保留网址的来源文件</span></div></div>
<div class="notice"><b>先分清数据性质：</b>报道与政府项目来自公开网页和附件；库内 6 条案例中 5 条为公开报道整理、1 条为课程模拟，5 条任务和审核记录也为课程模拟。涞水的 19,518 万元是 2024 年计划安排资金，不能解释成已支付或实际产值。</div>
<nav class="tabs"><button class="active" data-view="results">① 实跑 SQL 结果</button><button data-view="browse">② 浏览原始数据表</button><button data-view="relations">③ 看跨表关系</button><button data-view="guide">④ 如何自己打开库</button></nav>
<section id="results" class="view active"><div class="head"><h2>逐条看查询与结果</h2><p>左侧选一条业务问题，右侧先看实际返回的结果表；需要核查语句时再展开原 SQL。</p></div><div class="twocol"><div class="querynav" id="queryNav"></div><article class="card"><div class="kind" id="queryKind"></div><h3 id="queryTitle"></h3><p class="sub" id="queryMeaning"></p><div class="resulttop"><b id="queryCount"></b><span class="kind">SQLite 实测</span></div><div class="tablewrap" id="queryTable"></div><div class="notice warn" id="queryCaveat"></div><div class="sub" id="querySources"></div><details><summary>展开这条查询的原 SQL</summary><pre class="code" id="querySql"></pre></details></article></div></section>
<section id="browse" class="view"><div class="head"><h2>直接浏览数据库记录</h2><p>切换表并搜索，看到的每一行都来自 .sqlite 文件；来源网址可直接打开原文。</p></div><div class="toolbar"><select id="tableSelect" aria-label="选择数据表"></select><input id="tableSearch" type="search" placeholder="搜索当前表：项目名、县名、帮扶方式、任务状态……"></div><div class="resulttop"><b id="tableCount"></b><span class="kind">只读快照</span></div><div class="tablewrap" id="browseTable"></div><div class="pager"><span id="browsePager"></span><div><button id="prevBrowse">上一页</button> <button id="nextBrowse">下一页</button></div></div></section>
<section id="relations" class="view"><div class="head"><h2>为什么要拆成多张表</h2><p>点击“原始数据表”可以按编号核对下列关系。关联表让一篇报道对应多案例、一个案例对应多种方式。</p></div><div class="relation" id="relationCards"></div><div class="notice warn">人大报道与政府项目即便县名、产业相同，也不会自动认定为同一个项目；需要独立的跨来源匹配审核。</div></section>
<section id="guide" class="view"><div class="head"><h2>你自己怎么查看样本库</h2><p>这个页面已经展示查询结果；如果想直接打开 .sqlite 文件，可按下面两种方式。</p></div><div class="guide"><div class="card"><h3>最简单：用本页面</h3><p>“实跑 SQL 结果”看查询，“浏览原始数据表”看记录。点来源网址回到人大或县政府原文。页面是运行结果快照；修改数据库后须重新生成。</p><p><a href="832_research_sample.sqlite" download>下载原始 SQLite 文件 ↗</a></p></div><div class="card"><h3>在本机重新执行</h3><p>电脑装有 Python 时，在此文件夹的终端运行：</p><code>python show_db_queries.py</code><p>它会重新连接 .sqlite 文件并打印 6 条 SQL 的完整输出。用任意 SQLite 图形工具打开 .sqlite，也能浏览表和执行 <a href="832_verified_queries.sql">SQL 文件</a>。</p></div><div class="card"><h3>表与关系</h3><p><a href="832_schema.sql">832_schema.sql</a> 是真实建表文件，包含外键、唯一约束、任务负责人约束及阻止提交人自审的触发器。<a href="build_sample_db.py">构建脚本</a>从公开 JSON 数据重建样本库。</p></div><div class="card"><h3>原始资料</h3><p><a href="ruc_832_public_reports.json">297 篇报道清单</a>、<a href="official_project_rows.json">43 个项目与 158 行实施数据</a>、<a href="county_source_audit.json">16 项政府资料来源审计</a>均放在同目录。</p></div></div></section>
<footer class="foot">生成日期：2026-10-29。此页面是 SQLite 查询结果的静态导出，不在浏览器中执行任意 SQL；完整案例审核流程仍在 <a href="832_research_system_v3.html">总设计原型</a>中演示。</footer>
</div><script>
const DATA=__DATA__;
const el=id=>document.getElementById(id);
const esc=value=>String(value==null?"":value).replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
function cell(value){if(value==null)return "—";let str=String(value);if(/^https?:\/\//.test(str))return '<a href="'+esc(str)+'" target="_blank" rel="noopener noreferrer">打开原文 ↗</a>';if(str.length>420)return '<span title="'+esc(str)+'">'+esc(str.slice(0,420))+'…</span>';return esc(str)}
function makeTable(columns,rows){if(!rows.length)return '<div class="empty">查询返回 0 行。请结合下方口径说明理解结果。</div>';return '<table><thead><tr>'+columns.map(c=>'<th>'+esc(c)+'</th>').join("")+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map(v=>'<td>'+cell(v)+'</td>').join("")+'</tr>').join("")+'</tbody></table>'}
let queryIndex=3,tableIndex=0,browsePage=0;
function renderQuery(){el("queryNav").innerHTML=DATA.queries.map((q,i)=>'<button class="'+(i===queryIndex?"active":"")+'" data-query="'+i+'"><small>Q'+(i+1)+' · '+esc(q.kind)+'</small>'+esc(q.title)+'</button>').join("");const q=DATA.queries[queryIndex];el("queryKind").textContent=q.kind;el("queryTitle").textContent=q.title;el("queryMeaning").textContent=q.meaning;el("querySql").textContent=q.sql;el("queryCount").textContent="返回 "+q.rows.length+" 行 · "+q.columns.length+" 列";el("queryTable").innerHTML=makeTable(q.displayColumns,q.rows);let caveat=["297 篇是本次公开目录采集数，不能换算为已覆盖 832 个县。","结果来自已人工整理的公开案例，不代表所有报道都完成结构化。","任务与人员是课程模拟，日期固定以便复现，不代表人大内部真实任务。","这些金额是 2024 年计划安排，不是实际支付或产值。","零行仅表示本次金额合计一致；两份来源的村数仍有 2 处待人工核对。","295 篇只是样本库尚未提取案例；不是报道没有产业做法。"][queryIndex];el("queryCaveat").textContent="口径提示："+caveat;el("querySources").innerHTML=q.sources.length?"核对出处："+q.sources.map(s=>'<a href="'+esc(s[1])+'" target="_blank" rel="noopener noreferrer">'+esc(s[0])+' ↗</a>').join("　"):"本条查询使用课程模拟任务，没有外部数据出处。";el("queryNav").querySelectorAll("[data-query]").forEach(b=>b.onclick=()=>{queryIndex=Number(b.dataset.query);renderQuery()})}
function renderBrowse(){const table=DATA.browser[tableIndex],q=el("tableSearch").value.trim().toLowerCase();const rows=table.rows.filter(row=>!q||row.some(v=>String(v==null?"":v).toLowerCase().includes(q)));const per=15,max=Math.max(1,Math.ceil(rows.length/per));browsePage=Math.min(browsePage,max-1);el("tableCount").textContent=table.title+" · 显示 "+rows.length+" / "+table.rows.length+" 行";el("browseTable").innerHTML=makeTable(table.columns,rows.slice(browsePage*per,(browsePage+1)*per));el("browsePager").textContent="第 "+(browsePage+1)+" / "+max+" 页";el("prevBrowse").disabled=browsePage===0;el("nextBrowse").disabled=browsePage>=max-1}
function renderRelations(){const r=DATA.relations;let names=r.reportCases.map(x=>x[0]+" "+x[1]).join("、");let modes=r.caseModes.map(x=>x[0]).join("、");let p=r.exampleProject;el("relationCards").innerHTML='<div class="card"><div class="step">01　报道 1:N 案例</div><h3>一篇霍邱报道 → '+r.reportCases.length+' 个案例</h3><p>'+esc(names)+'</p></div><div class="card"><div class="step">02　案例 N:M 帮扶方式</div><h3>C-003 城西湖莲藕 → '+r.caseModes.length+' 种方式</h3><p>'+esc(modes)+'</p></div><div class="card"><div class="step">03　项目 1:N 实施地点</div><h3>'+esc(p[0])+' → '+esc(p[3])+' 行</h3><p>'+esc(p[1])+'；项目计划 '+Number(p[2]).toLocaleString("zh-CN")+' 万元，实施行合计 '+Number(p[4]).toLocaleString("zh-CN")+' 万元。</p></div>'}
function showView(id){document.querySelectorAll(".view").forEach(v=>v.classList.toggle("active",v.id===id));document.querySelectorAll("[data-view]").forEach(b=>b.classList.toggle("active",b.dataset.view===id));window.scrollTo(0,0)}
el("statReports").textContent=DATA.counts.reports;el("statProjects").textContent=DATA.counts.projects;el("statLocations").textContent=DATA.counts.locations;el("statDocs").textContent=DATA.counts.sourceDocuments;
el("tableSelect").innerHTML=DATA.browser.map((t,i)=>'<option value="'+i+'">'+esc(t.title)+' · '+t.rows.length+' 行</option>').join("");
el("tableSelect").onchange=e=>{tableIndex=Number(e.target.value);browsePage=0;el("tableSearch").value="";renderBrowse()};
el("tableSearch").oninput=()=>{browsePage=0;renderBrowse()};el("prevBrowse").onclick=()=>{browsePage--;renderBrowse()};el("nextBrowse").onclick=()=>{browsePage++;renderBrowse()};
document.querySelectorAll("[data-view]").forEach(b=>b.onclick=()=>showView(b.dataset.view));
renderQuery();renderBrowse();renderRelations();
</script></body></html>'''

encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).replace("<", "\\u003c")
OUT.write_text(html.replace("__DATA__", encoded), encoding="utf-8")
print(f"Generated {OUT.name}: {len(queries)} SQL results, {len(browser)} browsable tables")
