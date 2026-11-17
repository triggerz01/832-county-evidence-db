"""Refresh the standalone V3 design page from the audited source lists."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "832_research_system_v3.html"
SOURCE_FILES = {
    "PUBLIC_REPORTS": ROOT / "ruc_832_public_reports.json",
    "COUNTY_AUDIT": ROOT / "county_source_audit.json",
    "OFFICIAL_PROJECTS": ROOT / "official_project_rows.json",
}

page = PAGE.read_text(encoding="utf-8")
for variable, source in SOURCE_FILES.items():
    data = json.loads(source.read_text(encoding="utf-8"))
    encoded = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
    pattern = rf"(?m)^const {variable} = .*;$"
    page, count = re.subn(pattern, lambda _: f"const {variable} = {encoded};", page)
    if count != 1:
        raise RuntimeError(f"Expected one assignment for {variable}, got {count}")
PAGE.write_text(page, encoding="utf-8")
print(f"Embedded {len(json.loads(SOURCE_FILES['PUBLIC_REPORTS'].read_text(encoding='utf-8')))} reports")
print(f"Embedded {len(json.loads(SOURCE_FILES['COUNTY_AUDIT'].read_text(encoding='utf-8'))['sources'])} official source records")
projects = json.loads(SOURCE_FILES["OFFICIAL_PROJECTS"].read_text(encoding="utf-8"))
print(f"Embedded {len(projects['projects'])} projects and {len(projects['project_location_rows'])} location rows")
