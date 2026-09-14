"""Extract JUnit failures for the GitHub Actions issue reporting step."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def collect_failures(directory):
    failures = []
    for report in sorted(Path(directory).glob("*-results.xml")):
        root = ET.parse(report).getroot()
        for case in root.iter("testcase"):
            failure = case.find("failure")
            if failure is None:
                failure = case.find("error")
            if failure is None:
                continue
            failures.append({
                "test": f"{case.get('classname', '')}::{case.get('name', '')}",
                "suite": report.stem,
                "message": failure.get("message", "Test failed")[:2000],
                "details": (failure.text or "")[:6000],
            })
    return failures


if __name__ == "__main__":
    Path("reports").mkdir(exist_ok=True)
    Path("reports/failures.json").write_text(json.dumps(collect_failures(".")), encoding="utf-8")
