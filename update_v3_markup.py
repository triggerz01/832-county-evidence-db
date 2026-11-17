"""Apply targeted V3 page markup changes after the source JSON has been embedded."""

from pathlib import Path

page_path = Path(__file__).with_name("832_research_system_v3.html")
page = page_path.read_text(encoding="utf-8")


def replace_once(old: str, new: str) -> None:
    global page
    count = page.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one markup match, got {count}: {old[:110]}")
    page = page.replace(old, new, 1)


replace_once(
    '.task-row>*:nth-child(5),.task-row>*:nth-child(6){display:none}',
    '.task-row>*:nth-child(3),.task-row>*:nth-child(4){display:none}',
)
replace_once(
    '<option value="member">调研队员甲</option>',
    '<option value="member">调研队员甲</option><option value="member_b">调研队员乙</option>',
)
replace_once(
    'placeholder="例如：柞水、霍邱、木耳、安徽线"',
    'placeholder="例如：柞水、霍邱、安徽线"',
)
replace_once(
    '<div class="card" style="padding:0;overflow:hidden"><div class="task-row task-head">',
    '<div class="toolbar" style="margin-bottom:9px"><div class="field wide"><label for="taskSearch">县域 / 主题 / 负责人</label><input id="taskSearch" type="search" placeholder="例：柞水、金米、队员乙"></div><div class="field"><label for="taskStatus">任务状态</label><select id="taskStatus"><option value="">全部状态</option><option>已分配</option><option>进行中</option><option>待审核</option><option>退回补正</option><option>已完成</option><option>已发布</option></select></div></div><div class="count" id="taskCount"></div><div class="card" style="padding:0;overflow:hidden"><div class="task-row task-head">',
)
replace_once(
    '<select id="newTaskAssignee"><option>队员甲</option><option>队员乙</option></select></div>',
    '<select id="newTaskAssignee"><option>队员甲</option><option>队员乙</option></select></div><div class="field"><label for="newTaskCollaborator">协作者（可选）</label><select id="newTaskCollaborator"><option value="">无</option><option>队员甲</option><option>队员乙</option></select></div><div class="field"><label for="newTaskKind">指定交付材料</label><select id="newTaskKind"><option>案例报告</option><option>调研日志</option><option>新闻速递</option><option>资料包</option></select></div>',
)
replace_once(
    '<input type="hidden" id="editCaseId"><div class="form-grid"><div class="field"><label for="newCaseCounty">',
    '<input type="hidden" id="editCaseId"><div class="form-grid"><div class="field span2"><label for="newCaseTask">关联本人案例报告任务</label><select id="newCaseTask"><option value="">选择案例报告任务</option></select></div><div class="field"><label for="newCaseCounty">',
)
replace_once(
    '并校验网址唯一性。',
    '并让同一来源网址在 source_document 中只存一次；一篇报道可供多个案例引用。',
)
replace_once(
    '<h3>演示任务状态</h3><div class="chart" id="taskChart">',
    '<h3>演示任务状态（按当前角色可见）</h3><div class="chart" id="taskChart">',
)
replace_once(
    '<div class="entity"><b>county</b><code>county_id PK · province · county_name · original_832_flag</code></div>',
    '<div class="entity"><b>county</b><code>county_id PK · province · county_name · original_832_flag</code></div><div class="entity"><b>county_alias</b><code>alias_id PK · county_id FK · title_name · match_status · checked_by</code></div>',
)
replace_once(
    '<div class="entity"><b>source_document / source_excerpt</b><code>document_id PK · url UNIQUE · provenance; excerpt_id PK · page_or_para</code></div>',
    '<div class="entity"><b>source_document / source_excerpt</b><code>document_id PK · url UNIQUE · provenance; excerpt_id PK · document_id FK · report_id FK · page_or_para</code></div><div class="entity"><b>source_row</b><code>row_id PK · document_id FK · row_label · raw_text · imported_at</code></div>',
)
replace_once(
    '<div class="entity"><b>public_report / person_mention</b><code>report_id PK · county_id FK · document_id FK; person_id FK</code></div>',
    '<div class="entity"><b>public_report / person_mention</b><code>report_id PK · county_id FK · document_id FK; mention_id PK · report_id FK · person_name · role_text</code></div>',
)
replace_once(
    '<div class="entity"><b>project_snapshot / fund_component</b><code>snapshot_id PK · version · budget DECIMAL; (snapshot_id,fund_id) PK</code></div>',
    '<div class="entity"><b>project_snapshot / fund_component</b><code>snapshot_id PK · project_id FK · snapshot_kind · version_label · budget DECIMAL · target_income · build_stage; (snapshot_id,fund_id) PK</code></div>',
)
replace_once(
    '<p class="lead">这里的队伍与任务是课程演示数据，用来验证流程。真实依据是人大公开招募说明中的县域资料采集、调研结束一周内提交日志与新闻、后续案例报告。切换右上角角色，可看到不同操作权限。</p>',
    '<p class="lead">这里的队伍与任务是课程演示数据，用来验证流程。真实依据是人大公开招募说明中的县域资料采集、调研结束一周内提交日志与新闻、后续案例报告。每条演示任务指定一种交付材料；切换右上角角色可体验不同权限。</p>',
)

page_path.write_text(page, encoding="utf-8")
print("V3 markup updated")
