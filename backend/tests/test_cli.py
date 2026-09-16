import os
import json
import pytest

from backend.app.cli import scan_directory_cli, compute_letter_grade, main


def test_compute_letter_grade():
    assert compute_letter_grade(95.0) == "A"
    assert compute_letter_grade(85.0) == "B"
    assert compute_letter_grade(75.0) == "C"
    assert compute_letter_grade(65.0) == "D"
    assert compute_letter_grade(45.0) == "F"


def test_cli_scan_demo_repository():
    demo_dir = os.path.abspath("demo_repository")
    if not os.path.exists(demo_dir):
        pytest.skip("demo_repository not present")

    report = scan_directory_cli(demo_dir)
    assert "health_score" in report
    assert "letter_grade" in report
    assert "vitals" in report
    assert "security_score" in report["vitals"]
    assert "quality_score" in report["vitals"]
    assert "dependency_score" in report["vitals"]
    assert report["health_score"] >= 0.0


def test_cli_main_success():
    demo_dir = os.path.abspath("demo_repository")
    if not os.path.exists(demo_dir):
        pytest.skip("demo_repository not present")

    # Pass with lenient threshold
    exit_code = main(["scan", demo_dir, "--fail-under", "10.0"])
    assert exit_code == 0


def test_cli_main_failure():
    demo_dir = os.path.abspath("demo_repository")
    if not os.path.exists(demo_dir):
        pytest.skip("demo_repository not present")

    # Fail with impossible threshold
    exit_code = main(["scan", demo_dir, "--fail-under", "99.9"])
    assert exit_code == 1


def test_cli_json_mode(capsys):
    demo_dir = os.path.abspath("demo_repository")
    if not os.path.exists(demo_dir):
        pytest.skip("demo_repository not present")

    exit_code = main(["scan", demo_dir, "--json"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "health_score" in data
    assert "vitals" in data
