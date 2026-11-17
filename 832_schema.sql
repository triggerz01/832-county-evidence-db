PRAGMA foreign_keys = ON;

CREATE TABLE county (
  county_id INTEGER PRIMARY KEY,
  province_raw TEXT NOT NULL,
  county_name_raw TEXT NOT NULL,
  match_status TEXT NOT NULL DEFAULT '待核对' CHECK (match_status IN ('待核对','已核对')),
  UNIQUE (province_raw, county_name_raw)
);
CREATE TABLE county_alias (
  alias_id INTEGER PRIMARY KEY,
  county_id INTEGER NOT NULL REFERENCES county(county_id),
  title_name TEXT NOT NULL,
  source_document_id INTEGER,
  match_status TEXT NOT NULL DEFAULT '待核对',
  UNIQUE (title_name, county_id)
);
CREATE TABLE source_document (
  document_id INTEGER PRIMARY KEY,
  external_id TEXT UNIQUE,
  url TEXT NOT NULL UNIQUE,
  publisher TEXT NOT NULL,
  title TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  checked_on TEXT NOT NULL
);
CREATE TABLE public_report (
  report_id INTEGER PRIMARY KEY,
  document_id INTEGER NOT NULL UNIQUE REFERENCES source_document(document_id),
  county_id INTEGER NOT NULL REFERENCES county(county_id),
  published_date TEXT NOT NULL
);
CREATE INDEX idx_report_county_date ON public_report(county_id, published_date);
CREATE TABLE person_mention (
  mention_id INTEGER PRIMARY KEY,
  report_id INTEGER NOT NULL REFERENCES public_report(report_id),
  person_name TEXT NOT NULL,
  role_text TEXT NOT NULL,
  context_summary TEXT NOT NULL
);
CREATE INDEX idx_mention_name ON person_mention(person_name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mention_unique ON person_mention(report_id, person_name);
CREATE TABLE source_excerpt (
  excerpt_id INTEGER PRIMARY KEY,
  document_id INTEGER NOT NULL REFERENCES source_document(document_id),
  locator TEXT NOT NULL,
  summary TEXT NOT NULL
);

CREATE TABLE team (
  team_id INTEGER PRIMARY KEY,
  team_name TEXT NOT NULL UNIQUE,
  data_kind TEXT NOT NULL CHECK (data_kind = '课程模拟')
);
CREATE TABLE user_account (
  user_id INTEGER PRIMARY KEY,
  team_id INTEGER REFERENCES team(team_id),
  display_name TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL CHECK (role IN ('admin','leader','member','reviewer','researcher')),
  password_hash TEXT,
  data_kind TEXT NOT NULL CHECK (data_kind = '课程模拟')
);
CREATE TABLE field_task (
  task_id TEXT PRIMARY KEY,
  county_id INTEGER NOT NULL REFERENCES county(county_id),
  topic TEXT NOT NULL,
  required_kind TEXT NOT NULL CHECK (required_kind IN ('调研日志','新闻速递','案例报告','资料包')),
  due_at TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('已分配','进行中','待审核','退回补正','已完成','已发布')),
  created_by INTEGER NOT NULL REFERENCES user_account(user_id),
  data_kind TEXT NOT NULL CHECK (data_kind = '课程模拟')
);
CREATE TABLE task_assignment (
  task_id TEXT NOT NULL REFERENCES field_task(task_id),
  user_id INTEGER NOT NULL REFERENCES user_account(user_id),
  is_lead INTEGER NOT NULL CHECK (is_lead IN (0,1)),
  PRIMARY KEY (task_id,user_id)
);
CREATE UNIQUE INDEX idx_one_task_lead ON task_assignment(task_id) WHERE is_lead = 1;

CREATE TABLE industry_case (
  case_id TEXT PRIMARY KEY,
  county_id INTEGER NOT NULL REFERENCES county(county_id),
  task_id TEXT REFERENCES field_task(task_id),
  title TEXT NOT NULL,
  industry TEXT NOT NULL,
  claim_summary TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('草稿','待审核','退回补正','已审核','已发布')),
  data_kind TEXT NOT NULL CHECK (data_kind IN ('公开报道整理','课程模拟')),
  owner_id INTEGER REFERENCES user_account(user_id)
);
CREATE TABLE case_evidence (
  case_id TEXT NOT NULL REFERENCES industry_case(case_id),
  excerpt_id INTEGER NOT NULL REFERENCES source_excerpt(excerpt_id),
  PRIMARY KEY (case_id,excerpt_id)
);
CREATE TABLE mechanism (
  mechanism_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);
CREATE TABLE case_mechanism (
  case_id TEXT NOT NULL REFERENCES industry_case(case_id),
  mechanism_id INTEGER NOT NULL REFERENCES mechanism(mechanism_id),
  PRIMARY KEY (case_id,mechanism_id)
);
CREATE TABLE deliverable_version (
  version_id INTEGER PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES field_task(task_id),
  version_no INTEGER NOT NULL CHECK (version_no > 0),
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  document_id INTEGER NOT NULL REFERENCES source_document(document_id),
  case_id TEXT REFERENCES industry_case(case_id),
  note TEXT NOT NULL,
  submitted_by INTEGER NOT NULL REFERENCES user_account(user_id),
  submitted_at TEXT NOT NULL,
  UNIQUE (task_id,version_no)
);
CREATE TABLE review_action (
  review_id INTEGER PRIMARY KEY,
  version_id INTEGER NOT NULL REFERENCES deliverable_version(version_id),
  reviewer_id INTEGER NOT NULL REFERENCES user_account(user_id),
  decision TEXT NOT NULL CHECK (decision IN ('通过','退回')),
  reason TEXT NOT NULL,
  acted_at TEXT NOT NULL,
  CHECK (decision != '退回' OR length(trim(reason)) > 0)
);
CREATE TRIGGER prevent_self_review BEFORE INSERT ON review_action
WHEN (SELECT submitted_by FROM deliverable_version WHERE version_id = NEW.version_id) = NEW.reviewer_id
BEGIN SELECT RAISE(ABORT, 'submitter cannot review own version'); END;
CREATE TABLE audit_log (
  log_id INTEGER PRIMARY KEY,
  actor_id INTEGER NOT NULL REFERENCES user_account(user_id),
  task_id TEXT REFERENCES field_task(task_id),
  case_id TEXT REFERENCES industry_case(case_id),
  action TEXT NOT NULL,
  acted_at TEXT NOT NULL
);

CREATE TABLE government_project (
  project_id TEXT PRIMARY KEY,
  county_id INTEGER NOT NULL REFERENCES county(county_id),
  plan_year INTEGER NOT NULL,
  project_name TEXT NOT NULL,
  category TEXT NOT NULL,
  html_project_no INTEGER NOT NULL,
  xlsx_project_no INTEGER NOT NULL,
  UNIQUE (county_id,plan_year,html_project_no),
  UNIQUE (county_id,plan_year,xlsx_project_no)
);
CREATE TABLE project_snapshot (
  snapshot_id INTEGER PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES government_project(project_id),
  document_id INTEGER NOT NULL REFERENCES source_document(document_id),
  snapshot_kind TEXT NOT NULL,
  version_label TEXT NOT NULL,
  budget_wan NUMERIC NOT NULL CHECK (budget_wan >= 0),
  UNIQUE (project_id,snapshot_kind,version_label)
);
CREATE TABLE project_location (
  location_id INTEGER PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES government_project(project_id),
  document_id INTEGER NOT NULL REFERENCES source_document(document_id),
  xlsx_row INTEGER NOT NULL,
  implementation_location_raw TEXT NOT NULL,
  planned_2024_funding_wan NUMERIC NOT NULL CHECK (planned_2024_funding_wan >= 0),
  UNIQUE (document_id,xlsx_row)
);
CREATE INDEX idx_project_county_category ON government_project(county_id,category);
CREATE INDEX idx_project_location_project ON project_location(project_id);

CREATE TABLE evidence_issue (
  issue_id TEXT PRIMARY KEY,
  county_id INTEGER NOT NULL REFERENCES county(county_id),
  project_name_raw TEXT NOT NULL,
  facts_json TEXT NOT NULL,
  database_use TEXT NOT NULL,
  do_not_infer TEXT NOT NULL,
  review_status TEXT NOT NULL DEFAULT '待人工核对'
);
CREATE TABLE evidence_issue_source (
  issue_id TEXT NOT NULL REFERENCES evidence_issue(issue_id),
  document_id INTEGER NOT NULL REFERENCES source_document(document_id),
  PRIMARY KEY (issue_id,document_id)
);

-- 以下对象由 migrate_v4.py 增量补齐，从零建库时同样生效。
CREATE INDEX IF NOT EXISTS idx_case_status ON industry_case(status, county_id);
CREATE INDEX IF NOT EXISTS idx_task_state ON field_task(state, due_at);
CREATE INDEX IF NOT EXISTS idx_version_task ON deliverable_version(task_id, version_no);

CREATE VIEW IF NOT EXISTS v_published_case AS
SELECT ic.case_id, ic.title, c.province_raw, c.county_name_raw, ic.industry,
       (SELECT group_concat(m.name, '、')
          FROM case_mechanism cm JOIN mechanism m ON m.mechanism_id = cm.mechanism_id
         WHERE cm.case_id = ic.case_id) AS mechanisms,
       (SELECT COUNT(*) FROM case_evidence ce WHERE ce.case_id = ic.case_id) AS evidence_count
FROM industry_case ic
JOIN county c ON c.county_id = ic.county_id
WHERE ic.status = '已发布';

CREATE VIEW IF NOT EXISTS v_task_progress AS
SELECT t.task_id, t.topic, t.required_kind, t.due_at, t.state,
       c.province_raw, c.county_name_raw,
       (SELECT u.display_name
          FROM task_assignment a JOIN user_account u ON u.user_id = a.user_id
         WHERE a.task_id = t.task_id AND a.is_lead = 1) AS lead_name,
       (SELECT MAX(v.version_no) FROM deliverable_version v WHERE v.task_id = t.task_id) AS latest_no,
       (SELECT COUNT(*) FROM deliverable_version v WHERE v.task_id = t.task_id) AS version_count,
       (SELECT COUNT(*) FROM review_action r
          JOIN deliverable_version v ON v.version_id = r.version_id
         WHERE v.task_id = t.task_id) AS review_count
FROM field_task t
JOIN county c ON c.county_id = t.county_id;

CREATE VIEW IF NOT EXISTS v_project_category AS
SELECT gp.category, COUNT(DISTINCT gp.project_id) AS project_count,
       ROUND(SUM(ps.budget_wan), 6) AS planned_funding_wan
FROM government_project gp
JOIN project_snapshot ps ON ps.project_id = gp.project_id
WHERE gp.plan_year = 2024
  AND ps.snapshot_kind = '年度计划'
  AND ps.version_label = '涞水2024县政府计划'
GROUP BY gp.category;
