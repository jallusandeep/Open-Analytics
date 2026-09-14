import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
spec = importlib.util.spec_from_file_location("report_failures", Path(__file__).parents[1] / "report_failures.py")
reporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter)


def test_extracts_failures_and_errors_only(tmp_path):
    (tmp_path / "unit-results.xml").write_text('''<testsuites><testsuite>
      <testcase classname="auth" name="passed"/>
      <testcase classname="auth" name="skipped"><skipped/></testcase>
      <testcase classname="auth" name="failed"><failure message="Assertion failed">traceback</failure></testcase>
      <testcase classname="db" name="errored"><error message="Fixture error">details</error></testcase>
    </testsuite></testsuites>''', encoding="utf-8")
    failures = reporter.collect_failures(tmp_path)
    assert [failure["test"] for failure in failures] == ["auth::failed", "db::errored"]
    assert failures[0]["details"] == "traceback"
    assert failures[1]["message"] == "Fixture error"


def test_missing_reports_produce_no_issues(tmp_path):
    assert reporter.collect_failures(tmp_path) == []
