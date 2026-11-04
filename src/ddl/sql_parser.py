
from __future__ import annotations

import argparse
import json
import sys

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import sqlglot
from sqlglot import exp


@dataclass
class ColumnDefinition:
    name: str
    data_type: str
    description: Optional[str]
    table: str
    file: str


@dataclass
class ParseResult:
    file: str
    statements: int
    columns: list[ColumnDefinition]
    errors: list[str]


def find_sql_files(path: str) -> list[Path]:
    """Localiza arquivos SQL em um diretório ou recebe um arquivo."""

    target = Path(path)

    if not target.exists():
        return []

    if target.is_file():
        return [target] if target.suffix.lower() == ".sql" else []

    return sorted(target.rglob("*.sql"))


def parse_sql(content: str) -> list[exp.Expression]:
    """Interpreta SQL utilizando o dialeto Databricks."""

    statements = sqlglot.parse(
        content,
        read="databricks",
        error_level="RAISE"
    )

    return [statement for statement in statements if statement is not None]


def get_comment(node: Optional[exp.Expression]) -> Optional[str]:
    """Extrai o conteúdo de um comentário SQL."""

    if node is None:
        return None

    if isinstance(node, exp.Literal):
        return str(node.this)

    return node.sql(dialect="databricks").strip("'\"")


def extract_column_comment(column: exp.ColumnDef) -> Optional[str]:
    """Extrai COMMENT associado à definição de uma coluna."""

    # COMMENT pode ser armazenado diretamente no nó.
    comment = column.args.get("comment")

    if comment is not None:
        return get_comment(comment)

    # Algumas versões do SQLGlot representam COMMENT como constraint.
    for constraint in column.args.get("constraints") or []:

        if not hasattr(constraint, "args"):
            continue

        kind = constraint.args.get("kind")

        if isinstance(kind, exp.CommentColumnConstraint):
            return get_comment(kind.this)

    return None


def extract_table_name(create: exp.Create) -> str:
    """Extrai o nome completo da tabela."""

    target = create.this

    if isinstance(target, exp.Schema):
        target = target.this

    if target is None:
        return "<unknown>"

    return target.sql(dialect="databricks")


def extract_columns(
    statement: exp.Expression,
    file: str
) -> list[ColumnDefinition]:
    """Extrai colunas, tipos e comentários de um CREATE TABLE."""

    if not isinstance(statement, exp.Create):
        return []

    if not isinstance(statement.this, exp.Schema):
        raise ValueError(
            "CREATE TABLE sem definição explícita de colunas. "
            "CTAS e LIKE não são suportados por este parser."
        )

    table_name = extract_table_name(statement)
    columns = []

    for column in statement.this.expressions:

        if not isinstance(column, exp.ColumnDef):
            continue

        data_type = column.args.get("kind")

        if data_type is None:
            raise ValueError(
                f"Tipo não identificado para coluna {column.this.name}"
            )

        columns.append(
            ColumnDefinition(
                name=column.this.name,
                data_type=data_type.sql(
                    dialect="databricks"
                ).upper(),
                description=extract_column_comment(column),
                table=table_name,
                file=file
            )
        )

    return columns


def process_file(file: Path) -> ParseResult:
    """Valida e extrai metadados de um arquivo SQL."""

    errors = []
    columns = []
    statement_count = 0

    try:
        content = file.read_text(encoding="utf-8")

        statements = parse_sql(content)
        statement_count = len(statements)

        if not statements:
            errors.append("Arquivo SQL vazio ou sem comandos válidos.")

        for index, statement in enumerate(statements, start=1):

            if not isinstance(statement, exp.Create):
                errors.append(
                    f"Comando {index}: somente CREATE TABLE é permitido."
                )
                continue

            try:
                columns.extend(
                    extract_columns(statement, str(file))
                )

            except ValueError as exc:
                errors.append(
                    f"Comando {index}: {exc}"
                )

    except sqlglot.errors.ParseError as exc:
        errors.append(f"Erro de sintaxe SQL: {exc}")

    except UnicodeDecodeError:
        errors.append("Arquivo não está codificado em UTF-8.")

    except Exception as exc:
        errors.append(f"Erro inesperado: {exc}")

    return ParseResult(
        file=str(file),
        statements=statement_count,
        columns=columns,
        errors=errors
    )


def validate_directory(path: str) -> list[ParseResult]:
    """Processa todos os arquivos SQL encontrados."""

    sql_files = find_sql_files(path)

    if not sql_files:
        return [
            ParseResult(
                file=path,
                statements=0,
                columns=[],
                errors=["Nenhum arquivo SQL encontrado."]
            )
        ]

    return [
        process_file(file)
        for file in sql_files
    ]


def generate_report(results: list[ParseResult]) -> dict:
    """Gera relatório consolidado da validação."""

    errors = [
        {
            "file": result.file,
            "error": error
        }
        for result in results
        for error in result.errors
    ]

    columns = [
        asdict(column)
        for result in results
        for column in result.columns
    ]

    return {
        "valid": not errors,
        "files_processed": len(results),
        "statements_processed": sum(
            result.statements for result in results
        ),
        "columns_extracted": len(columns),
        "errors": errors,
        "columns": columns
    }


def main() -> int:

    parser = argparse.ArgumentParser(
        description="Parser e validador DDL Databricks"
    )

    parser.add_argument(
        "--path",
        default="sql",
        help="Arquivo ou diretório contendo SQL"
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Caminho opcional para salvar relatório JSON"
    )

    args = parser.parse_args()

    results = validate_directory(args.path)
    report = generate_report(results)

    print("\n========== DDL VALIDATION ==========\n")

    print(f"Arquivos: {report['files_processed']}")
    print(f"Comandos: {report['statements_processed']}")
    print(f"Colunas: {report['columns_extracted']}")

    for error in report["errors"]:
        message = f"{error['file']}: {error['error']}"
        print(f"::error::{message}")

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)

        output.write_text(
            json.dumps(
                report,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

    if report["valid"]:
        print("\nSQL VALIDATION PASSED")
        return 0

    print("\nSQL VALIDATION FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
