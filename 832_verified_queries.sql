-- Q1: Public reports by province in the checked local catalogue.
SELECT c.province_raw, COUNT(*) AS report_count
FROM public_report AS r
JOIN county AS c ON c.county_id = r.county_id
GROUP BY c.province_raw
ORDER BY report_count DESC;

-- Q2: Published cases with both employment and land transfer.
SELECT ic.case_id, ic.title, c.county_name_raw
FROM industry_case AS ic
JOIN county AS c ON c.county_id = ic.county_id
JOIN case_mechanism AS cm ON cm.case_id = ic.case_id
JOIN mechanism AS m ON m.mechanism_id = cm.mechanism_id
WHERE ic.status = '已发布' AND m.name IN ('就业','土地流转')
GROUP BY ic.case_id, ic.title, c.county_name_raw
HAVING COUNT(DISTINCT m.name) = 2;

-- Q3: Demo tasks overdue without the required deliverable by the due date.
SELECT t.task_id, c.county_name_raw, u.display_name, t.required_kind, t.due_at
FROM field_task AS t
JOIN county AS c ON c.county_id = t.county_id
JOIN task_assignment AS a ON a.task_id = t.task_id AND a.is_lead = 1
JOIN user_account AS u ON u.user_id = a.user_id
WHERE t.due_at < '2026-10-29'
  AND NOT EXISTS (
    SELECT 1 FROM deliverable_version AS v
    WHERE v.task_id = t.task_id
      AND v.kind = t.required_kind
      AND v.submitted_at <= t.due_at
  );

-- Q4: Real 2024 Laishui projects, grouped by category. Budget is a plan.
SELECT gp.category, COUNT(*) AS project_count,
       ROUND(SUM(ps.budget_wan), 6) AS planned_funding_wan
FROM government_project AS gp
JOIN project_snapshot AS ps ON ps.project_id = gp.project_id
WHERE gp.plan_year = 2024
  AND ps.snapshot_kind = '年度计划'
  AND ps.version_label = '涞水2024县政府计划'
GROUP BY gp.category
ORDER BY planned_funding_wan DESC;

-- Q5: Projects whose sum of 158 implementation rows differs from the project plan.
-- Zero rows are expected for this audited extract. The two noted village-count
-- discrepancies remain source-text issues, not funding-total discrepancies.
SELECT gp.project_id, gp.project_name, ps.budget_wan,
       ROUND(SUM(pl.planned_2024_funding_wan), 6) AS row_sum_wan
FROM government_project AS gp
JOIN project_snapshot AS ps ON ps.project_id = gp.project_id
JOIN project_location AS pl ON pl.project_id = gp.project_id
GROUP BY gp.project_id, gp.project_name, ps.budget_wan
HAVING ABS(SUM(pl.planned_2024_funding_wan) - ps.budget_wan) > 0.000001;

-- Q6: Public reports with no case excerpt linked in this sample database.
-- This is a cataloguing backlog, not proof that the report has no industry case.
SELECT COUNT(*) AS not_yet_structured_reports
FROM public_report AS pr
WHERE NOT EXISTS (
  SELECT 1 FROM source_excerpt AS se
  JOIN case_evidence AS ce ON ce.excerpt_id = se.excerpt_id
  WHERE se.document_id = pr.document_id
);
