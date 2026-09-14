import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
spec = importlib.util.spec_from_file_location("build_report_site", Path(__file__).parents[1] / "build_report_site.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_site_contains_reports_and_coverage_but_not_failure_payload(tmp_path, monkeypatch):
    source = tmp_path / "reports"
    source.mkdir()
    (source / "unit-tests.html").write_text("unit", encoding="utf-8")
    (source / "failures.json").write_text("private failure payload", encoding="utf-8")
    coverage = source / "coverage"
    coverage.mkdir()
    (coverage / "index.html").write_text("coverage", encoding="utf-8")
    (coverage / "style.css").write_text("css", encoding="utf-8")
    monkeypatch.setenv("GITHUB_REF_NAME", "<branch>")
    destination = tmp_path / "site"
    builder.build_site(source, destination)
    index = (destination / "index.html").read_text(encoding="utf-8")
    assert 'href="unit-tests.html"' in index
    assert 'href="coverage/index.html"' in index
    assert "&lt;branch&gt;" in index
    assert (destination / "coverage/style.css").exists()
    assert not (destination / "failures.json").exists()
    assert "integration-tests.html" not in index


def test_no_reports_refuses_publication(tmp_path):
    with pytest.raises(RuntimeError, match="No HTML reports"):
        builder.build_site(tmp_path / "missing", tmp_path / "site")
