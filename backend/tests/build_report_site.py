"""Publish only HTML reports and coverage assets, excluding failure JSON/JUnit."""
import html
import os
from pathlib import Path
import shutil
import sys


def build_site(source, destination):
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    links = []
    for filename, label in [("unit-tests.html", "Unit tests"), ("integration-tests.html", "Integration tests")]:
        report = next(source.rglob(filename), None)
        if report:
            shutil.copy2(report, destination / filename)
            links.append(f'<a href="{filename}">{label}</a>')
    coverage = next(source.rglob("coverage/index.html"), None)
    if coverage:
        shutil.copytree(coverage.parent, destination / "coverage", dirs_exist_ok=True)
        links.append('<a href="coverage/index.html">Coverage</a>')
    if not links:
        raise RuntimeError("No HTML reports found; refusing to replace the published site")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_url = html.escape(f"{server}/{repository}/actions/runs/{run_id}", quote=True)
    branch = html.escape(os.environ.get("GITHUB_REF_NAME", "local"))
    commit = html.escape(os.environ.get("GITHUB_SHA", "")[:12])
    status = html.escape(os.environ.get("TEST_RESULT", "unknown"))
    destination.joinpath("index.html").write_text(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Backend test reports</title><style>
body{{margin:0;background:#080808;color:#eee;font:14px monospace;padding:48px 24px}}
main{{max-width:760px;margin:auto}}h1{{font-size:24px}}p{{color:#aaa;line-height:1.8}}
nav{{display:grid;gap:12px;margin:28px 0}}a{{color:white}}nav a{{border:1px solid #444;padding:18px;border-radius:6px;text-decoration:none}}nav a:hover{{background:#222}}
</style></head><body><main><h1>Backend test reports</h1>
<p>Latest published run · {branch} · {commit}<br>Result: {status}</p>
<nav>{''.join(links)}</nav><a href="{run_url}">View workflow run</a>
<p>Each deployment replaces these reports with the latest published run. Download older reports from workflow artifacts.</p>
</main></body></html>''', encoding="utf-8")
    destination.joinpath(".nojekyll").touch()


if __name__ == "__main__":
    build_site(sys.argv[1], sys.argv[2])
