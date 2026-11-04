"""Ferramentas de leitura, validação e processamento de DDL."""

from src.ddl.sql_parser import (
    ColumnDefinition,
    ParseResult,
    extract_columns,
    extract_table_name,
    find_sql_files,
    generate_report,
    get_comment,
    parse_sql,
    process_file,
    read_sql_file,
    validate_directory,
)

__all__ = [
    "ColumnDefinition",
    "ParseResult",
    "extract_columns",
    "extract_table_name",
    "find_sql_files",
    "generate_report",
    "get_comment",
    "parse_sql",
    "process_file",
    "read_sql_file",
    "validate_directory",
]