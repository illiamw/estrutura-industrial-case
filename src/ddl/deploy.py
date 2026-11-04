
"""
Databricks DDL Deployment

Executa scripts SQL no Spark SQL do Databricks.
"""

import argparse
import logging
import sys
import time

from pathlib import Path
from typing import List

from pyspark.sql import SparkSession


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("ddl_deploy")


def resolve_sql_path(path: str) -> Path:
    """Resolve o diretório SQL a partir da raiz do projeto."""

    requested_path = Path(path)

    if requested_path.is_absolute():
        resolved = requested_path
    else:
        project_root = Path(__file__).resolve().parents[2]

        candidates = [
            Path.cwd() / requested_path,
            project_root / requested_path,
        ]

        resolved = next(
            (candidate for candidate in candidates if candidate.is_dir()),
            candidates[-1],
        )

    if not resolved.is_dir():
        raise FileNotFoundError(
            f"Diretório SQL não encontrado: {resolved}"
        )

    return resolved.resolve()


def split_sql_statements(content: str) -> List[str]:
    """
    Divide um script SQL em instruções independentes.

    Preserva ponto e vírgula dentro de strings e ignora
    delimitadores presentes em comentários.
    """

    statements = []
    buffer = []

    in_single_quote = False
    in_double_quote = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False

    i = 0

    while i < len(content):
        char = content[i]
        next_char = content[i + 1] if i + 1 < len(content) else ""

        if in_line_comment:
            if char == "\n":
                in_line_comment = False
                buffer.append(char)

            i += 1
            continue

        if in_block_comment:
            if char == "*" and next_char == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1

            continue

        if not (in_single_quote or in_double_quote or in_backtick):
            if char == "-" and next_char == "-":
                in_line_comment = True
                i += 2
                continue

            if char == "/" and next_char == "*":
                in_block_comment = True
                i += 2
                continue

        if char == "'" and not (in_double_quote or in_backtick):
            if in_single_quote and next_char == "'":
                buffer.extend([char, next_char])
                i += 2
                continue

            in_single_quote = not in_single_quote

        elif char == '"' and not (in_single_quote or in_backtick):
            if in_double_quote and next_char == '"':
                buffer.extend([char, next_char])
                i += 2
                continue

            in_double_quote = not in_double_quote

        elif char == "`" and not (in_single_quote or in_double_quote):
            in_backtick = not in_backtick

        if (
            char == ";"
            and not in_single_quote
            and not in_double_quote
            and not in_backtick
        ):
            statement = "".join(buffer).strip()

            if statement:
                statements.append(statement)

            buffer = []
        else:
            buffer.append(char)

        i += 1

    if in_block_comment:
        raise ValueError("Comentário SQL de bloco não foi fechado.")

    if in_single_quote or in_double_quote or in_backtick:
        raise ValueError("String ou identificador SQL não foi fechado.")

    remaining = "".join(buffer).strip()

    if remaining:
        statements.append(remaining)

    return statements


def discover_sql_files(sql_path: Path) -> List[Path]:
    """Localiza os arquivos SQL recursivamente."""

    files = sorted(
        file
        for file in sql_path.rglob("*.sql")
        if file.is_file()
    )

    if not files:
        raise FileNotFoundError(
            f"Nenhum arquivo SQL encontrado em: {sql_path}"
        )

    return files


def deploy_file(spark: SparkSession, sql_file: Path) -> int:
    """Executa todas as instruções de um arquivo SQL."""

    logger.info("Processando arquivo: %s", sql_file)

    content = sql_file.read_text(encoding="utf-8-sig")
    statements = split_sql_statements(content)

    if not statements:
        logger.warning("Arquivo sem instruções SQL: %s", sql_file)
        return 0

    logger.info("Instruções encontradas: %d", len(statements))

    for index, statement in enumerate(statements, start=1):
        logger.info(
            "Executando instrução %d/%d | Arquivo: %s",
            index,
            len(statements),
            sql_file.name,
        )

        start_time = time.perf_counter()

        try:
            spark.sql(statement)

            elapsed = time.perf_counter() - start_time

            logger.info(
                "Instrução %d executada com sucesso (%.2fs)",
                index,
                elapsed,
            )

        except Exception:
            logger.exception(
                "Falha na instrução %d do arquivo %s",
                index,
                sql_file,
            )
            raise

    return len(statements)


def deploy(sql_path: str) -> None:
    """Orquestra o deploy de todos os scripts SQL."""

    start_time = time.perf_counter()

    resolved_path = resolve_sql_path(sql_path)
    sql_files = discover_sql_files(resolved_path)

    logger.info("=" * 60)
    logger.info("INICIANDO DEPLOY DDL")
    logger.info("Diretório: %s", resolved_path)
    logger.info("Arquivos encontrados: %d", len(sql_files))
    logger.info("=" * 60)

    spark = SparkSession.builder.getOrCreate()

    total_statements = 0
    successful_files = 0

    for sql_file in sql_files:
        total_statements += deploy_file(spark, sql_file)
        successful_files += 1

    elapsed = time.perf_counter() - start_time

    logger.info("=" * 60)
    logger.info("DEPLOY CONCLUÍDO COM SUCESSO")
    logger.info("Arquivos executados: %d", successful_files)
    logger.info("Instruções executadas: %d", total_statements)
    logger.info("Tempo total: %.2fs", elapsed)
    logger.info("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy de scripts DDL no Databricks."
    )

    parser.add_argument(
        "--sql-path",
        required=True,
        help="Diretório contendo os scripts SQL.",
    )

    args = parser.parse_args()

    try:
        deploy(args.sql_path)

    except Exception:
        logger.exception("DEPLOY DDL FINALIZADO COM ERRO")
        sys.exit(1)


if __name__ == "__main__":
    main()
