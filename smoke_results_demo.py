"""Check the SQLite results viewer in headless Edge."""

import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
source = root / "832_sqlite_results_demo.html"
test_page = root / "tmp" / "results_demo_smoke.html"
test_page.parent.mkdir(exist_ok=True)
probe = r'''
<script>
try {
 const check=(ok,label)=>{if(!ok)throw Error(label)};
 check(DATA.queries.length===6,"six queries");
 check(DATA.browser.length===9,"nine record views");
 check(DATA.counts.reports===297&&DATA.counts.projects===43&&DATA.counts.locations===158,"base counts");
 check(el("queryTable").textContent.includes("11548.386018"),"budget result visible");
 document.querySelector('[data-query="1"]').click();
 check(el("queryTable").textContent.includes("C-003"),"dual-mechanism query");
 document.querySelector('[data-query="4"]').click();
 check(el("queryCount").textContent.includes("0 行"),"zero-row amount check");
 document.querySelector('[data-view="browse"]').click();
 el("tableSelect").value="1";el("tableSelect").dispatchEvent(new Event("change"));
 check(el("tableCount").textContent.includes("43 行"),"project browser");
 el("tableSearch").value="酸枣";el("tableSearch").dispatchEvent(new Event("input"));
 check(el("tableCount").textContent.includes("显示 1 / 43 行"),"project search");
 document.querySelector('[data-view="relations"]').click();
 check(el("relationCards").children.length===3,"relationship examples");
 document.body.setAttribute("data-demo-smoke","PASS");
} catch(error) {document.body.setAttribute("data-demo-smoke","FAIL: "+error.message)}
</script>
'''
html = source.read_text(encoding="utf-8")
test_page.write_text(html.replace("</body></html>", probe + "</body></html>", 1), encoding="utf-8")

edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
run = subprocess.run(
    [str(edge), "--headless=new", "--disable-gpu", "--disable-extensions", "--no-first-run",
     "--virtual-time-budget=3000", "--dump-dom", test_page.as_uri()],
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
)
result = re.search(r'data-demo-smoke="([^"]+)"', run.stdout)
if not result:
    raise RuntimeError("No browser test result: " + run.stderr[-400:])
print(result.group(1))
if result.group(1) != "PASS":
    raise SystemExit(1)
