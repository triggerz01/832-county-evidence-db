"""Exercise V3's task, case, review, publication, and official-data paths in Edge."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "832_research_system_v3.html"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
TEMP = ROOT / "tmp"
TEMP.mkdir(exist_ok=True)
TEST_PAGE = TEMP / "v3_smoke.html"
TEST_PAGE.write_text(
    PAGE.read_text(encoding="utf-8").replace(
        "</body>",
        r'''
<script>
try {
  const ok=(condition,label)=>{if(!condition)throw Error(label)};
  ok(["projectSection","evidenceSection","personSection"].every(id=>!!el(id)),"search jump targets");
  state={tasks:structuredClone(seedTasks),cases:structuredClone(seedCases),nextTask:6,nextCase:7};
  role="member";renderTasks();renderManageCases();renderCaseSearch();
  ok(canSeeTask(state.tasks[0]),"member A visibility");
  ok(!canSeeTask(state.tasks[1]),"member A isolation");
  taskAction("start","T-001");
  ok(state.tasks[0].status==="进行中","start transition");
  el("newCaseTask").value="T-001";
  el("newCaseCounty").value="柞水县";
  el("newCaseTitle").value="金米木耳案例核对";
  el("newCaseIndustry").value="测试产业丁";
  el("newCaseMechanisms").value="借袋还耳,菌包认领";
  el("newCaseClaim").value="依据公开报道核对菌包认领方式。";
  el("newCaseSource").value=RUC_ZS;
  saveCase();
  const c=state.cases[state.cases.length-1];
  ok(c.taskId==="T-001"&&c.status==="草稿","case draft linked to task");
  openTask("T-001",c.id);
  ok(el("submitCaseId").value===c.id,"case preselected for submission");
  taskAction("submit","T-001");
  ok(c.status==="待审核"&&state.tasks[0].versions[0].caseId===c.id,"case submission linked to version");
  role="reviewer";openTask("T-001");el("reviewReason").value="来源核对通过";taskAction("approve","T-001");
  ok(c.status==="已审核"&&state.tasks[0].status==="已完成","review transition");
  role="leader";openTask("T-001");taskAction("publish","T-001");
  ok(c.status==="已发布"&&state.tasks[0].status==="已发布","publish transition");
  role="public";renderCaseSearch();renderCharts();renderQueries();
  ok(!visibleCases().some(x=>x.id==="C-006"),"public draft isolation");
  ok(canSeeTask(state.tasks[0])&&!canSeeTask(state.tasks[1]),"public task isolation");
  el("reportSearch").value="测试产业丁";renderReportSearch();
  ok(el("reportCount").textContent.includes("1 / 297"),"published case keyword search");
  role="member_b";ok(canSeeTask(state.tasks[1]),"member B visibility");
  role="admin";
  state.tasks.push({id:"T-099",county:"柞水县",topic:"管理员自审保护",assignee:"队员甲",requiredKind:"资料包",due:"2026-11-01",status:"进行中",versions:[],reviews:[],logs:[]});
  openTask("T-099");el("submitTitle").value="来源核对";el("submitUrl").value=RUC_ZS;el("submitNote").value="核对原文";taskAction("submit","T-099");
  ok(!canReview(state.tasks[state.tasks.length-1]),"self-review blocked");
  ok(OFFICIAL_PROJECTS.projects.length===43&&OFFICIAL_PROJECTS.project_location_rows.length===158,"project record counts");
  ok(Math.abs(OFFICIAL_PROJECTS.projects.reduce((n,p)=>n+p.planned_2024_funding_wan,0)-19518)<1e-6,"project funding total");
  document.body.setAttribute("data-smoke","PASS");
} catch(error) { document.body.setAttribute("data-smoke","FAIL: "+error.message); }
</script>
</body>''',
        1,
    ),
    encoding="utf-8",
)

process = subprocess.run(
    [
        str(EDGE),
        "--headless=new",
        "--disable-gpu",
        "--disable-extensions",
        "--no-first-run",
        "--virtual-time-budget=3500",
        f"--user-data-dir={TEMP / 'edge_smoke_profile'}",
        "--dump-dom",
        TEST_PAGE.as_uri(),
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=30,
)
match = re.search(r'data-smoke="([^"]+)"', process.stdout)
if not match:
    raise RuntimeError("Edge did not return a smoke-test result: " + process.stderr[-500:])
print(match.group(1))
if match.group(1) != "PASS":
    raise SystemExit(1)
