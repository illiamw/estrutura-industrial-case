from pathlib import Path

import pytest

from src.ddl.sql_parser import ColumnDefinition
from src.governance.type_validator import (
    extract_decimal_parameters,
    generate_report,
    load_type_rules,
    normalize_type,
    validate_column_type,
    validate_decimal,
    validate_types,
)


@pytest.fixture
def type_rules_file(tmp_path: Path) -> Path:
    rules_file = tmp_path / "type_rules.yml"
    rules_file.write_text(
        """
types:
  STRING:
    enabled: true
  INT:
    enabled: false
  DECIMAL:
    enabled: true
    parameters:
      precision:
        min: 1
        max: 10
      scale:
        min: 0
        max: 2
  ARRAY:
    enabled: true
    complex: true
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


@pytest.mark.parametrize(
    ("data_type", "expected"),
    [
        (" string ", "STRING"),
        ("decimal(10, 2)", "DECIMAL"),
        ("ARRAY<STRING>", "ARRAY"),
        ("MAP<STRING, INT>", "MAP"),
    ],
)
def test_normalize_type_returns_base_type(
    data_type: str,
    expected: str,
) -> None:
    assert normalize_type(data_type) == expected


@pytest.mark.parametrize(
    ("data_type", "expected"),
    [
        ("DECIMAL(18, 2)", (18, 2)),
        ("decimal(8)", (8, 0)),
        ("DECIMAL", (10, 0)),
        ("STRING", None),
    ],
)
def test_extract_decimal_parameters(
    data_type: str,
    expected: tuple[int, int] | None,
) -> None:
    assert extract_decimal_parameters(data_type) == expected


def test_load_type_rules_normalizes_names_and_rejects_missing_file(
    type_rules_file: Path,
    tmp_path: Path,
) -> None:
    rules = load_type_rules(type_rules_file)

    assert rules["ARRAY"]["enabled"] is True
    assert rules["DECIMAL"]["parameters"]["precision"]["max"] == 10

    with pytest.raises(FileNotFoundError):
        load_type_rules(tmp_path / "missing.yml")


def test_validate_decimal_reports_precision_and_scale_violations(
    type_rules_file: Path,
) -> None:
    rules = load_type_rules(type_rules_file)

    issues = validate_decimal("DECIMAL(12, 4)", rules["DECIMAL"])

    assert {issue for issue, _ in issues} == {"INVALID_PRECISION", "INVALID_SCALE"}


@pytest.mark.parametrize(
    ("data_type", "expected_issue"),
    [
        ("STRING", None),
        ("INT", "DISABLED_DATA_TYPE"),
        ("DOUBLE", "UNKNOWN_DATA_TYPE"),
        ("DECIMAL(12, 4)", "INVALID_PRECISION"),
    ],
)
def test_validate_column_type_reports_configured_type_issues(
    type_rules_file: Path,
    data_type: str,
    expected_issue: str | None,
) -> None:
    issues = validate_column_type(
        make_column("str_sensor_value", data_type),
        load_type_rules(type_rules_file),
    )

    if expected_issue is None:
        assert issues == []
    else:
        assert expected_issue in {issue.issue for issue in issues}


def test_validate_types_and_report_summarize_columns(
    type_rules_file: Path,
) -> None:
    result = validate_types(
        [
            make_column("str_sensor_id", "STRING"),
            make_column("int_sensor_count", "INT"),
        ],
        load_type_rules(type_rules_file),
    )
    report = generate_report(result)

    assert result.valid is False
    assert report["total_columns"] == 2
    assert report["validated_columns"] == 2
    assert report["total_issues"] == 1
    assert report["issues"][0]["issue"] == "DISABLED_DATA_TYPE"
