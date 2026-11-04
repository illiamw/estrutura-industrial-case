from src.ddl.sql_parser import read_sql_file


def test_read_sql_file_returns_utf8_contents(tmp_path) -> None:
    sql_file = tmp_path / "example.sql"
    sql_file.write_text("SELECT 1;", encoding="utf-8")

    assert read_sql_file(sql_file) == "SELECT 1;"
