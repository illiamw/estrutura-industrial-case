import json
from pathlib import Path

import pytest
import sqlglot

from src.ddl.sql_parser import (
    ColumnDefinition,
    ParseResult,
    extract_columns,
    extract_table_name,
    find_sql_files,
    generate_report,
    get_comment,
    main,
    parse_sql,
    process_file,
    read_sql_file,
    validate_directory,
)


VALID_DDL = """\
CREATE TABLE datapulse.bronze.sensor_events (
    str_sensor_id STRING COMMENT 'Identificador do sensor',
    dbl_temperature DOUBLE
)
USING DELTA
COMMENT 'Eventos dos sensores';
"""


def test_read_sql_file_reads_utf8_contents(tmp_path: Path) -> None:
    sql_file = tmp_path / "example.sql"
    sql_file.write_text("-- Medição: válida\nSELECT 1;", encoding="utf-8")

    assert read_sql_file(sql_file) == "-- Medição: válida\nSELECT 1;"


def test_find_sql_files_returns_sql_files_recursively_in_sorted_order(
    tmp_path: Path,
) -> None:
    (tmp_path / "z.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not SQL", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "a.sql").write_text("SELECT 2;", encoding="utf-8")

    assert find_sql_files(str(tmp_path)) == [nested / "a.sql", tmp_path / "z.sql"]


def test_find_sql_files_accepts_sql_file_and_rejects_other_paths(
    tmp_path: Path,
) -> None:
    sql_file = tmp_path / "one.sql"
    uppercase_sql_file = tmp_path / "uppercase.SQL"
    text_file = tmp_path / "one.txt"
    sql_file.touch()
    uppercase_sql_file.touch()
    text_file.touch()

    assert find_sql_files(str(sql_file)) == [sql_file]
    assert find_sql_files(str(uppercase_sql_file)) == [uppercase_sql_file]
    assert find_sql_files(str(text_file)) == []
    assert find_sql_files(str(tmp_path / "missing")) == []


def test_parse_sql_parses_multiple_databricks_statements() -> None:
    statements = parse_sql("SELECT 1; SELECT 2;")

    assert len(statements) == 2
    assert all(isinstance(statement, sqlglot.exp.Expression) for statement in statements)


def test_parse_sql_returns_empty_list_for_empty_input() -> None:
    assert parse_sql(" ; \n ") == []


def test_parse_sql_propagates_sqlglot_parse_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_parse_error(*args: object, **kwargs: object) -> list[object]:
        raise sqlglot.errors.ParseError("invalid SQL")

    monkeypatch.setattr(sqlglot, "parse", raise_parse_error)

    with pytest.raises(sqlglot.errors.ParseError):
        parse_sql("SELECT 1")


def test_get_comment_handles_none_and_sql_literal() -> None:
    statement = parse_sql(
        "CREATE TABLE sample (id STRING COMMENT 'Identificador')"
    )[0]
    columns = extract_columns(statement, "sample.sql")

    assert get_comment(None) is None
    assert columns[0].description == "Identificador"


def test_extract_table_name_returns_qualified_name() -> None:
    statement = parse_sql("CREATE TABLE datapulse.bronze.sample (id INT)")[0]

    assert extract_table_name(statement) == "datapulse.bronze.sample"


def test_extract_columns_extracts_column_names_types_and_comments() -> None:
    statement = parse_sql(VALID_DDL)[0]

    columns = extract_columns(statement, "sensor_events.sql")

    assert columns == [
        ColumnDefinition(
            name="str_sensor_id",
            data_type="STRING",
            description="Identificador do sensor",
            table="datapulse.bronze.sensor_events",
            file="sensor_events.sql",
        ),
        ColumnDefinition(
            name="dbl_temperature",
            data_type="DOUBLE",
            description=None,
            table="datapulse.bronze.sensor_events",
            file="sensor_events.sql",
        ),
    ]


def test_extract_columns_returns_empty_for_non_create_statement() -> None:
    statement = parse_sql("SELECT 1")[0]

    assert extract_columns(statement, "query.sql") == []


@pytest.mark.parametrize(
    "statement",
    [
        "CREATE TABLE target AS SELECT 1 AS id",
        "CREATE TABLE target LIKE source",
    ],
)
def test_extract_columns_rejects_ddl_without_explicit_schema(
    statement: str,
) -> None:
    create = parse_sql(statement)[0]

    with pytest.raises(ValueError, match="sem definição explícita"):
        extract_columns(create, "target.sql")


def test_process_file_extracts_valid_ddl(tmp_path: Path) -> None:
    sql_file = tmp_path / "sensor_events.sql"
    sql_file.write_text(VALID_DDL, encoding="utf-8")

    result = process_file(sql_file)

    assert result.file == str(sql_file)
    assert result.statements == 1
    assert len(result.columns) == 2
    assert result.errors == []


def test_process_file_reports_empty_file(tmp_path: Path) -> None:
    sql_file = tmp_path / "empty.sql"
    sql_file.write_text("  ;  ", encoding="utf-8")

    result = process_file(sql_file)

    assert result.statements == 0
    assert result.columns == []
    assert result.errors == ["Arquivo SQL vazio ou sem comandos válidos."]


def test_process_file_reports_non_create_statement(tmp_path: Path) -> None:
    sql_file = tmp_path / "query.sql"
    sql_file.write_text("SELECT 1;", encoding="utf-8")

    result = process_file(sql_file)

    assert result.statements == 1
    assert result.errors == ["Comando 1: somente CREATE TABLE é permitido."]


def test_process_file_reports_unsupported_ctas(tmp_path: Path) -> None:
    sql_file = tmp_path / "ctas.sql"
    sql_file.write_text(
        "CREATE TABLE target AS SELECT 1 AS id;",
        encoding="utf-8",
    )

    result = process_file(sql_file)

    assert result.statements == 1
    assert result.columns == []
    assert "Comando 1: CREATE TABLE sem definição explícita" in result.errors[0]


def test_process_file_reports_sql_parse_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sql_file = tmp_path / "invalid.sql"
    sql_file.write_text("SELECT 1;", encoding="utf-8")

    def raise_parse_error(content: str) -> list[sqlglot.exp.Expression]:
        raise sqlglot.errors.ParseError("invalid SQL")

    monkeypatch.setattr("src.ddl.sql_parser.parse_sql", raise_parse_error)

    result = process_file(sql_file)

    assert result.statements == 0
    assert result.columns == []
    assert result.errors == ["Erro de sintaxe SQL: invalid SQL"]


def test_process_file_reports_invalid_utf8(tmp_path: Path) -> None:
    sql_file = tmp_path / "invalid_encoding.sql"
    sql_file.write_bytes(b"\xff")

    result = process_file(sql_file)

    assert result.errors == ["Arquivo não está codificado em UTF-8."]


def test_process_file_reports_unexpected_read_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sql_file = tmp_path / "unreadable.sql"
    sql_file.touch()
    original_read_text = Path.read_text

    def raise_read_error(path: Path, *args: object, **kwargs: object) -> str:
        if path == sql_file:
            raise OSError("permission denied")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", raise_read_error)

    result = process_file(sql_file)

    assert result.errors == ["Erro inesperado: permission denied"]


def test_validate_directory_processes_sql_files_recursively(
    tmp_path: Path,
) -> None:
    (tmp_path / "b.sql").write_text(VALID_DDL, encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "a.sql").write_text(VALID_DDL, encoding="utf-8")

    results = validate_directory(str(tmp_path))

    assert [Path(result.file).name for result in results] == ["b.sql", "a.sql"]
    assert all(result.statements == 1 for result in results)


@pytest.mark.parametrize("target_kind", ["missing", "empty_directory"])
def test_validate_directory_reports_no_sql_files(
    tmp_path: Path,
    target_kind: str,
) -> None:
    target = tmp_path / "missing"
    if target_kind == "empty_directory":
        target.mkdir()

    results = validate_directory(str(target))

    assert results == [
        ParseResult(
            file=str(target),
            statements=0,
            columns=[],
            errors=["Nenhum arquivo SQL encontrado."],
        )
    ]


def test_generate_report_flattens_columns_and_errors() -> None:
    results = [
        ParseResult(
            file="valid.sql",
            statements=1,
            columns=[
                ColumnDefinition(
                    name="sensor_id",
                    data_type="STRING",
                    description="Id",
                    table="sample",
                    file="valid.sql",
                )
            ],
            errors=[],
        ),
        ParseResult(
            file="invalid.sql",
            statements=0,
            columns=[],
            errors=["Erro de sintaxe SQL"],
        ),
    ]

    report = generate_report(results)

    assert report == {
        "valid": False,
        "files_processed": 2,
        "statements_processed": 1,
        "columns_extracted": 1,
        "errors": [{"file": "invalid.sql", "error": "Erro de sintaxe SQL"}],
        "columns": [
            {
                "name": "sensor_id",
                "data_type": "STRING",
                "description": "Id",
                "table": "sample",
                "file": "valid.sql",
            }
        ],
    }


def test_main_writes_json_report_and_returns_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sql_file = tmp_path / "sample.sql"
    sql_file.write_text(VALID_DDL, encoding="utf-8")
    report_file = tmp_path / "reports" / "result.json"
    monkeypatch.setattr(
        "sys.argv",
        ["sql_parser", "--path", str(sql_file), "--output", str(report_file)],
    )

    exit_code = main()

    assert exit_code == 0
    assert "SQL VALIDATION PASSED" in capsys.readouterr().out
    report = json.loads(report_file.read_text(encoding="utf-8"))
    assert report["valid"] is True
    assert report["columns_extracted"] == 2


def test_main_returns_failure_and_prints_ci_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sql_file = tmp_path / "invalid.sql"
    sql_file.write_text("SELECT 1;", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["sql_parser", "--path", str(sql_file)])

    exit_code = main()
    output = capsys.readouterr().out

    assert exit_code == 1
    assert f"::error::{sql_file}: Comando 1:" in output
    assert "SQL VALIDATION FAILED" in output
