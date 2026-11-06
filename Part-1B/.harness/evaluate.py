import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.genai import errors
from jsonschema import validate, ValidationError

PROJECT_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = PROJECT_DIR.parent
SOURCE_DIR = PROJECT_DIR / "src"
DATASET_FILE = PROJECT_DIR / "evals" / "dataset.json"
OUTPUT_FILE = PROJECT_DIR / "evidence" / "eval-results.json"

sys.path.insert(0, str(SOURCE_DIR))
from reviewer import analyze_code, MODEL


THRESHOLD = 80.0

RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["status", "findings"],
    "properties": {
        "status": {
            "type": "string",
            "enum": ["success", "error"]
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "vulnerability",
                    "severity",
                    "description",
                    "evidence",
                    "remediation"
                ],
                "properties": {
                    "vulnerability": {"type": "string", "minLength": 1},
                    "severity": {
                        "type": "string",
                        "enum": ["High", "Medium", "Low"]
                    },
                    "description": {"type": "string", "minLength": 1},
                    "evidence": {"type": "string", "minLength": 1},
                    "remediation": {"type": "string", "minLength": 1}
                }
            }
        }
    }
}

SEMANTIC_ALIASES = {
    "SQL Injection": [
        "sql injection"
    ],
    "Command Injection": [
        "command injection",
        "os command injection",
        "shell command injection"
    ],
    "Cross-Site Scripting (XSS)": [
        "cross site scripting",
        "xss"
    ],
    "Hardcoded Credentials": [
        "hardcoded credentials",
        "hardcoded password",
        "hardcoded secret",
        "hardcoded sensitive information"
    ],
    "Weak Cryptography": [
        "weak cryptography",
        "weak hashing",
        "weak hash",
        "weak cryptographic hash",
        "use of weak cryptographic hash",
        "md5"
    ],
    "Code Injection": [
        "code injection",
        "arbitrary code execution",
        "remote code execution"
    ],
    "Insecure Configuration": [
        "insecure configuration",
        "debug mode enabled",
        "debug enabled"
    ],
    "Syntax Error / Unparsable": [
        "syntax error",
        "unparsable",
        "syntax error / unparsable",
        "malformed sql",
        "incomplete sql",
        "incomplete sql statement",
        "incomplete where clause"
    ],
    "Prompt Injection": [
        "prompt injection",
        "instruction injection"
    ],
    "Insecure Randomness": [
        "insecure randomness",
        "predictable randomness",
        "weak random number generator",
        "cryptographically weak pseudo-random number generator",
        "use of cryptographically weak pseudo-random number generator",
        "cryptographically weak pseudorandom number generator",
        "use of cryptographically weak pseudorandom number generator"
    ],
    "Insecure TLS / Certificate Validation Disabled": [
        "insecure tls",
        "certificate validation disabled",
        "tls certificate verification disabled",
        "ssl verification disabled",
        "disabled ssl tls certificate verification"
    ],
    "Insecure Deserialization": [
        "insecure deserialization",
        "unsafe deserialization",
        "pickle deserialization"
    ]
}


def normalize(value):
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def semantic_check(expected, findings):
    if expected == "None":
        return len(findings) == 0

    aliases = SEMANTIC_ALIASES.get(
        expected,
        [expected]
    )

    labels = [
        normalize(item.get("vulnerability", ""))
        for item in findings
    ]

    normalized_aliases = [normalize(alias) for alias in aliases]

    return any(
        alias in label
        for label in labels
        for alias in normalized_aliases
    )


def invariant_check(output, source_code, expected_status="success"):
    """Layer 2 invariants. INV8 compares the status with the case's expected status."""
    errors_found = []

    findings = output.get("findings", [])
    status = output.get("status")

    if status == "error" and findings:
        errors_found.append("Error status must not contain findings.")
    elif status != expected_status:
        errors_found.append(
            f"Expected status {expected_status!r}, received {status!r}."
        )

    if len(findings) > 10:
        errors_found.append("More than 10 findings returned.")

    for index, finding in enumerate(findings, start=1):
        if finding.get("severity") not in ("High", "Medium", "Low"):
            errors_found.append(
                f"Finding {index}: invalid severity."
            )

        evidence = finding.get("evidence", "")

        if evidence not in source_code:
            errors_found.append(
                f"Finding {index}: evidence is not an exact source excerpt."
            )

    return errors_found


def dataset_fingerprint(path):
    """SHA-256 of the dataset's canonical JSON content, recorded in every report (Section 7).

    Sorted keys, compact separators and UTF-8 make the value independent of
    line endings and a byte-order mark, so every checkout of the same dataset
    produces the same fingerprint.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


ARCHIVE_NAME = re.compile(r"^eval-results-run-(\d+)-")


def archive_existing_report(output_file):
    """Copy the current report to the next eval-results-run-<N>-<score>pct.json.

    Runs before a new report is written so no earlier result is overwritten
    (Section 7). Returns the archive path, or None when there is no current
    report or an identical archive already exists.
    """
    output_file = Path(output_file)
    if not output_file.exists():
        return None

    content = output_file.read_bytes()
    archives = list(output_file.parent.glob("eval-results-run-*.json"))
    if any(path.read_bytes() == content for path in archives):
        return None

    numbers = []
    for path in archives:
        match = ARCHIVE_NAME.match(path.name)
        if match:
            numbers.append(int(match.group(1)))

    try:
        report = json.loads(content.decode("utf-8-sig"))
        score = report.get("aggregate_score")
        label = f"{score:.1f}pct" if isinstance(score, (int, float)) else "incomplete"
    except (ValueError, AttributeError):
        label = "unreadable"

    archive = output_file.parent / f"eval-results-run-{max(numbers, default=0) + 1}-{label}.json"
    archive.write_bytes(content)
    return archive


def main():
    with DATASET_FILE.open("r", encoding="utf-8-sig") as file:
        dataset = json.load(file)

    if not isinstance(dataset, list) or not dataset:
        raise ValueError("Evaluation dataset must be a non-empty JSON array.")

    results = []
    passed_cases = 0
    completed_cases = 0
    service_error = None

    print("Starting Gemini 3-layer evaluation...")
    print(f"Model: {MODEL}")
    print(f"Dataset cases: {len(dataset)}")
    print(f"Dataset SHA-256: {dataset_fingerprint(DATASET_FILE)}")
    print(f"Passing threshold: {THRESHOLD:.1f}%\n")

    for case in dataset:
        case_id = case.get("id")
        source_code = case.get("input", "")
        expected = case.get("expected_vuln", "")
        expected_status = case.get("expected_status", "success")

        result = {
            "id": case_id,
            "expected_status": expected_status,
            "layer1": False,
            "layer2": False,
            "layer3": False,
            "pass": False,
            "error": "",
            "model_output": None
        }

        print(f"Evaluating case {case_id}...")

        try:
            raw_output = analyze_code(source_code)
            output = json.loads(raw_output)
            result["model_output"] = output

        except errors.APIError as exc:
            result["error"] = f"Gemini API error: {exc}"
            result["service_error"] = True
            service_error = {
                "case_id": case_id,
                "error_type": type(exc).__name__,
                "details": str(exc)
            }
            results.append(result)
            print(f"  API ERROR: {type(exc).__name__}")
            break

        except Exception as exc:
            result["error"] = (
                f"Reviewer or inference execution error: "
                f"{type(exc).__name__}: {exc}"
            )
            result["execution_error"] = True
            results.append(result)
            print(f"  EXECUTION ERROR: {type(exc).__name__}")
            break

        completed_cases += 1

        # Layer 1: Structural JSON Schema validation
        try:
            validate(instance=output, schema=RESPONSE_SCHEMA)
            result["layer1"] = True
        except ValidationError as exc:
            result["error"] += f"L1: {exc.message}. "

        # Layer 2: Invariants and guardrails
        if result["layer1"]:
            invariant_errors = invariant_check(output, source_code, expected_status)
            result["layer2"] = len(invariant_errors) == 0

            if invariant_errors:
                result["error"] += "L2: " + " ".join(invariant_errors)

        # Layer 3: Semantic quality against the dataset's expected category
        if result["layer1"] and result["layer2"]:
            result["layer3"] = semantic_check(
                expected,
                output["findings"]
            )

            if not result["layer3"]:
                actual = [
                    item.get("vulnerability", "")
                    for item in output.get("findings", [])
                ]
                result["error"] += (
                    f"L3: Expected '{expected}', got {actual}. "
                )

        result["pass"] = all([
            result["layer1"],
            result["layer2"],
            result["layer3"]
        ])

        if result["pass"]:
            passed_cases += 1
            print("  PASS")
        else:
            print(f"  FAIL: {result['error']}")

        results.append(result)

    complete = completed_cases == len(dataset)

    partial_score = (
        (passed_cases / completed_cases) * 100
        if completed_cases else None
    )

    score = partial_score if complete else None
    overall_pass = complete and score >= THRESHOLD

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "threshold": THRESHOLD,
        "dataset_file": DATASET_FILE.relative_to(PROJECT_DIR).as_posix(),
        "dataset_sha256": dataset_fingerprint(DATASET_FILE),
        "total_cases": len(dataset),
        "completed_cases": completed_cases,
        "passed_cases": passed_cases,
        "partial_score": partial_score,
        "aggregate_score": score,
        "status": (
            "PASS" if overall_pass
            else "INCOMPLETE" if not complete
            else "FAIL"
        ),
        "service_error": service_error,
        "results": results
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    archived = archive_existing_report(OUTPUT_FILE)
    if archived:
        print(f"Previous report archived to: {archived}")

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print("\n========== EVALUATION SUMMARY ==========")
    print(f"Completed: {completed_cases}/{len(dataset)}")
    print(f"Passed: {passed_cases}")

    if score is not None:
        print(f"Aggregate score: {score:.1f}%")
    elif partial_score is not None:
        print(f"Partial score (incomplete run): {partial_score:.1f}%")
        print("Aggregate score: NOT FINAL")

    print(f"Threshold: {THRESHOLD:.1f}%")
    print(f"Final status: {report['status']}")
    print(f"Report saved to: {OUTPUT_FILE}")

    if service_error:
        print("\nA Gemini API error interrupted evaluation.")
        print("This is recorded separately from application test failures.")

    if overall_pass:
        return 0
    if not complete:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
