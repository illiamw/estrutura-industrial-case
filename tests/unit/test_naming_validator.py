from pathlib import Path

import pytest

from src.ddl.sql_parser import ColumnDefinition
from src.governance.naming_validator import (
    extract_prefix,
    generate_report,
    load_naming_rules,
    normalize_data_type,
    validate_column_naming,
    validate_naming,
)


@pytest.fixture
def naming_rules_file(tmp_path: Path) -> Path:
    rules_file = tmp_path / "naming_rules.yml"
    rules_file.write_text(
        """
naming:
  pattern: "^(str|int)_[a-z][a-z0-9_]*$"
  prefixes:
    str:
      allowed_types: ["STRING"]
    int:
      allowed_types: ["INT", "INTEGER"]
""",
        encoding="utf-8",
    )
    return rules_file


def make_column(name: str, data_type: str) -> ColumnDefinition:
    return ColumnDefinition(
        name=name,
        data_type=data_type,
        description="Descrição de teste",
        table="datapulse.bronze.sensor_events",
        file="sensor_events.sql",
    )


def test_normalize_data_type_removes_precision_and_normalizes_case() -> None:
    assert normalize_data_type(" decimal (10, 2) ") == "DECIMAL"


def test_extract_prefix_returns_text_before_first_underscore() -> None:
    assert extract_prefix("str_sensor_event_id") == "str"
    assert extract_prefix("sensor") is None


def test_load_naming_rules_compiles_pattern_and_normalizes_types(
    naming_rules_file: Path,
) -> None:
    rules = load_naming_rules(naming_rules_file)

    assert rules["compiled_pattern"].fullmatch("str_sensor_id")
    assert rules["prefixes"]["int"]["allowed_types"] == {"INT", "INTEGER"}


def test_load_naming_rules_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_naming_rules(tmp_path / "missing.yml")


def test_validate_column_naming_accepts_matching_name_and_type(
    naming_rules_file: Path,
) -> None:
    rules = load_naming_rules(naming_rules_file)

    assert validate_column_naming(
        make_column("str_sensor_id", "STRING"),
        rules,
    ) == []


def test_validate_column_naming_reports_invalid_name_and_missing_prefix(
    naming_rules_file: Path,
) -> None:
    rules = load_naming_rules(naming_rules_file)

    issues = validate_column_naming(make_column("invalid", "STRING"), rules)

    assert {issue.issue for issue in issues} == {
        "INVALID_NAMING_PATTERN",
        "MISSING_PREFIX",
    }


def test_validate_column_naming_reports_unknown_prefix(
    naming_rules_file: Path,
) -> None:
    rules = load_naming_rules(naming_rules_file)

    issues = validate_column_naming(
        make_column("dbl_sensor_value", "DOUBLE"),
        rules,
    )

    assert [issue.issue for issue in issues] == [
        "INVALID_NAMING_PATTERN",
        "UNKNOWN_PREFIX",
    ]


def test_validate_column_naming_reports_incompatible_type(
    naming_rules_file: Path,
) -> None:
    rules = load_naming_rules(naming_rules_file)

    issues = validate_column_naming(make_column("str_sensor_id", "INT"), rules)

    assert [issue.issue for issue in issues] == ["INCOMPATIBLE_DATA_TYPE"]


def test_validate_naming_and_report_summarize_all_columns(
    naming_rules_file: Path,
) -> None:
    result = validate_naming(
        [
            make_column("str_sensor_id", "STRING"),
            make_column("int_sensor_count", "BIGINT"),
        ],
        load_naming_rules(naming_rules_file),
    )

    report = generate_report(result)

    assert result.valid is False
    assert report["total_columns"] == 2
    assert report["validated_columns"] == 2
    assert report["total_issues"] == 1
    assert report["issues"][0]["issue"] == "INCOMPATIBLE_DATA_TYPE"
