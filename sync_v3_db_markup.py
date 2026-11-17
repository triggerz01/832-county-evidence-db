"""Describe the materialized SQLite sample accurately in the V3 design page."""

from pathlib import Path

path = Path(__file__).with_name("832_research_system_v3.html")
page = path.read_text(encoding="utf-8")


def swap(old: str, new: str) -> None:
    global page
    if page.count(old) != 1:
        raise RuntimeError(f"Expected one occurrence: {old[:100]}")
    page = page.replace(old, new, 1)


swap(
    '统计分成两个口径：公开报道/政府项目是现实来源；任务、审核和演示案例是课程模拟。下面的图表由本页数据计算，SQL 示例说明正式版如何由后端关系数据库得到结果。',
    '统计分成两个口径：公开报道/政府项目是现实来源；任务、审核和演示案例是课程模拟。图表由本页数据计算；另附已运行的 SQLite 样本库与 6 条可复现 SQL。',
)
swap(
    '本页 SQL 采用 PostgreSQL 命名示意；实际作业应给出 DDL、索引、参数化接口及运行截图。',
    '下方 7 条业务 SQL 中，跨版本目标比较需继续导入柞水原表；其余查询可在附带 SQLite 样本库中按字段执行。另见已逐条运行的 SQL 文件。',
)
swap(
    '正式作业选择“传统动态网站”路线：前端调用后端 API，后端执行 SQLite/PostgreSQL 查询。页面下方把输入、前置条件、输出与表操作写清，避免只列口号。',
    '正式作业选择“传统动态网站”路线：前端调用后端 API，后端执行 SQLite/PostgreSQL 查询。目前已建立来源标记明确的 SQLite 样本库，页面操作仍是浏览器演示；下方把输入、前置条件、输出与表操作写清。',
)
swap(
    '<div class="section"><div class="head"><div><div class="kicker">关系结构</div>',
    '<div class="section note"><b>已生成可实际查询的关系数据库样本</b>297 篇人大公开报道、43 个涞水项目、158 条实施地点行、5 条公开案例及 1 条模拟案例、5 条模拟任务和 8 条来源核验记录已写入 SQLite。6 条 SQL 已运行并核对结果；外键、URL 唯一约束、项目与地点关联、自审拦截触发器也已验证。<br><a href="832_research_sample.sqlite" download>下载 SQLite 样本库</a>　<a href="832_schema.sql" target="_blank">查看 DDL</a>　<a href="832_verified_queries.sql" target="_blank">查看已运行 SQL</a></div><div class="section"><div class="head"><div><div class="kicker">关系结构</div>',
)
swap(
    '县域 1:N 公开报道；报道 1:N 来源片段；案例 N:M 来源片段；案例 N:M 帮扶方式；任务 N:M 队员；任务 1:N 提交版本；提交版本 1:N 审核流水；政府项目 N:M 原表行，目标和进度按版本存储。',
    '县域 1:N 公开报道；来源文件 1:N 来源片段；案例 N:M 来源片段；案例 N:M 帮扶方式；任务 N:M 队员；任务 1:N 提交版本；提交版本 1:N 审核流水；政府项目 1:N 实施地点行，计划金额按项目版本存储。',
)
for old, new in {
    'county_id PK · province · county_name · original_832_flag': 'county_id PK · province_raw · county_name_raw · match_status',
    'alias_id PK · county_id FK · title_name · match_status · checked_by': 'alias_id PK · county_id FK · title_name · match_status',
    'version_id PK · task_id FK · type · version_no · source_url · submitted_at': 'version_id PK · task_id FK · kind · version_no · document_id FK · case_id FK',
    'document_id PK · url UNIQUE · provenance; excerpt_id PK · document_id FK · report_id FK · page_or_para': 'document_id PK · url UNIQUE · source_kind; excerpt_id PK · document_id FK · locator',
    '<div class="entity"><b>source_row</b><code>row_id PK · document_id FK · row_label · raw_text · imported_at</code></div>': '',
    'project_id PK · project_year · county_id FK · category; location_id PK · project_id FK · source_row_id FK': 'project_id PK · plan_year · county_id FK · category; location_id PK · project_id FK · xlsx_row',
    '<div class="entity"><b>project_source_match</b><code>(project_id,row_id) PK · match_method · checked_by · checked_at</code></div>': '',
    'snapshot_id PK · project_id FK · snapshot_kind · version_label · budget DECIMAL · target_income · build_stage; (snapshot_id,fund_id) PK': 'snapshot_id PK · project_id FK · snapshot_kind · version_label · budget_wan NUMERIC',
    'indicator_id PK · year · unit · source_id FK; log_id PK · actor_id FK': 'log_id PK · actor_id FK · task_id FK · action · acted_at',
}.items():
    swap(old, new)
swap('<b>project_snapshot / fund_component</b>', '<b>project_snapshot</b>')
swap('<b>county_indicator / audit_log</b>', '<b>audit_log</b>')
swap(
    '这份 HTML 是可操作的选题设计原型，浏览器本地状态只用于演示。课程提交须另建关系数据库、写 DDL/约束、后端 API 与真实 SQL、教材式 E-R 图、运行说明和截图。',
    '这份 HTML 是可操作的设计原型，浏览器中的新增、审核与发布仍保存在本地，尚未接入已生成的 SQLite 样本库。完整课程成品还需后端 API、登录鉴权、教材式 E-R 图、运行说明及截图。',
)
swap(
    '同项目不同来源的预算目标',
    '同项目不同来源的目标口径（后续扩展）',
)
swap(
    '先人工核验 10–20 个产业案例与公开人物，再建立来源片段。',
    '样本库已人工核验 5 个公开产业案例和 4 条人物提及；下一轮再扩至 10–20 个案例。',
)

path.write_text(page, encoding="utf-8")
print("V3 page aligned with SQLite sample")
