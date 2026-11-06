"""Reading saved harness runs (contracts/consumed-files.md; FR-017; task T022)."""

import json

from app.harness_results import latest_run

MAX_BYTES = 1_048_576


def write_run(results_dir, name, result="PASS", transcripts=None, summary_text=None):
    run_dir = results_dir / name
    run_dir.mkdir(parents=True)
    transcripts = transcripts if transcripts is not None else {"01-ruff.txt": "All checks passed!"}
    gates = []
    for index, (file_name, text) in enumerate(transcripts.items()):
        (run_dir / file_name).write_text(text, encoding="utf-8")
        gates.append(
            {"name": f"GATE {index}", "command": "cmd", "exit_code": 0, "result": result,
             "transcript": file_name}
        )
    summary = {"harness": "Part-1A", "timestamp_utc": f"{name}Z", "gates": gates, "result": result}
    (run_dir / "summary.json").write_text(summary_text or json.dumps(summary), encoding="utf-8")
    return run_dir


def test_missing_directory_means_no_results(tmp_path):
    assert latest_run(tmp_path / "absent", MAX_BYTES) == {"available": False, "history": []}


def test_empty_directory_means_no_results(tmp_path):
    assert latest_run(tmp_path, MAX_BYTES)["available"] is False


def test_latest_run_is_chosen_by_folder_name(tmp_path):
    write_run(tmp_path, "20261106-185500", "PASS")
    write_run(tmp_path, "20261106-185552", "FAIL")
    write_run(tmp_path, "20261106-185625", "PASS", {"01-ruff.txt": "latest transcript"})

    result = latest_run(tmp_path, MAX_BYTES)

    assert result["available"] is True
    assert result["run"] == "20261106-185625"
    assert result["transcripts"] == {"GATE 0": "latest transcript"}
    assert [(run["run"], run["result"]) for run in result["history"]] == [
        ("20261106-185625", "PASS"),
        ("20261106-185552", "FAIL"),
        ("20261106-185500", "PASS"),
    ]


def test_transcripts_outside_the_run_folder_are_ignored(tmp_path):
    (tmp_path / "secret.txt").write_text("SECRET", encoding="utf-8")
    run_dir = write_run(tmp_path, "20261107-000000")
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    summary["gates"].append(
        {"name": "ESCAPE", "command": "x", "exit_code": 0, "result": "PASS",
         "transcript": "../secret.txt"}
    )
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

    result = latest_run(tmp_path, MAX_BYTES)

    assert "ESCAPE" not in result["transcripts"]
    assert "SECRET" not in json.dumps(result["transcripts"])


def test_malformed_summary_is_skipped(tmp_path):
    write_run(tmp_path, "20261106-185500", "PASS")
    write_run(tmp_path, "20261106-185600", summary_text="{not json")
    assert latest_run(tmp_path, MAX_BYTES)["run"] == "20261106-185500"


def test_oversized_transcript_is_not_read(tmp_path):
    run_dir = write_run(tmp_path, "20261107-000000", transcripts={"01-ruff.txt": "x" * 5_000})
    limit = (run_dir / "summary.json").stat().st_size + 10  # summary fits, transcript does not
    result = latest_run(tmp_path, limit)
    assert result["available"] is True
    assert result["transcripts"] == {}


def test_endpoint_serves_saved_part1a_runs(client):
    body = client.get("/api/part-1a/harness").json()
    assert body["available"] is True
    assert body["summary"]["harness"] == "Part-1A"
    assert body["summary"]["result"] in {"PASS", "FAIL"}
    gate_names = {gate["name"] for gate in body["summary"]["gates"]}
    assert set(body["transcripts"]) <= gate_names
    assert len(body["history"]) >= 1
