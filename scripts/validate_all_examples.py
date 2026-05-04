from __future__ import annotations

from pathlib import Path

from asiep_validator import validate_file


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    exit_code = 0
    for path in sorted((ROOT / "examples").glob("*.json")):
        report = validate_file(path)
        print(f"{path.name}: {report.codes}")
        if path.name.startswith("valid_") and not report.valid:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
