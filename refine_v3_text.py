"""Keep V3 prose and relation fields aligned with the working prototype."""

from pathlib import Path

page_path = Path(__file__).with_name("832_research_system_v3.html")
page = page_path.read_text(encoding="utf-8")

replacements = {
    '这里按报道标题、县名与省份筛选，打开官方原文阅读。正式系统可继续抽取报道中的公开人物、产业段落与案例，建立全文索引。':
        '这里可按报道元数据，以及已人工整理的案例主题和公开人物检索，点击后回到官方原文。目前只对少量文章做了人物和案例抽取；正式系统可再建立全文索引。',
    '报道标题 / 县名 / 队伍': '报道 / 县名 / 队伍 / 已提取主题或人物',
    'placeholder="例如：柞水、霍邱、安徽线"': 'placeholder="例如：柞水、木耳、李正森、安徽线"',
    '案例 / 产业 / 帮扶方式 / 公开人物': '案例 / 产业 / 帮扶方式 / 机构',
    '已发布的真实样本不可直接改写；草稿可编辑或软删除。':
        '已发布真实样本不可直接改写；本人草稿可编辑或软删除，退回补正可编辑重交。',
    'task_id PK · county_id FK · due_at · state; (task_id,user_id) PK':
        'task_id PK · county_id FK · due_at · required_kind · state; (task_id,user_id) PK · is_lead',
    'project_id PK · project_year · county_id FK · category · planned_2024_funding; location_id PK · project_id FK · source_row_id FK':
        'project_id PK · project_year · county_id FK · category; location_id PK · project_id FK · source_row_id FK',
    '研究员以上。后端执行参数化 JOIN、GROUP BY、NOT EXISTS 等查询，返回图表与可追溯明细。':
        '内部任务统计限授权角色；公开项目汇总可对外展示。后端执行参数化 JOIN、GROUP BY、NOT EXISTS 查询，返回图表与来源明细。',
    '来源页记录可获得什么、怎样获取、哪些字段可信。页面中的“已调研县数”与“本地实际采到的公开报道数”分开展示；政府项目库预算只代表计划，进度“完工”不证明实际增收。':
        '来源页记录可获得什么、怎样获取、哪些字段可信。297 篇公开报道与人大“已调研县数”分开；43 个涞水项目、158 条实施行也分开；政府项目库预算只代表计划，进度“完工”不证明实际增收。',
    '公开报道条数 ≠ 人大已调研县数；项目库 485 个计划项目 ≠ 进度表 165 行的完工率分母；计划受益人数/预算 ≠ 实际增收/支付。':
        '公开报道条数 ≠ 人大已调研县数；柞水项目库 485 个计划项目 ≠ 进度表 165 行的完工率分母；涞水 43 个项目 ≠ 158 条实施地点行；计划受益人数/预算 ≠ 实际增收/支付。',
}

for old, new in replacements.items():
    count = page.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one text match, got {count}: {old[:100]}")
    page = page.replace(old, new, 1)

page_path.write_text(page, encoding="utf-8")
print("V3 copy and model labels refined")
