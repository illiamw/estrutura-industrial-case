
from __future__ import annotations

import argparse
import json
import re
import sys
import yaml

from dataclasses import asdict, dataclass
from pathlib import Path

from src.ddl.sql_parser import (
    validate_directory,
    ColumnDefinition,
)


@dataclass
class NamingIssue:
    file: str
    table: str
    column: str
    issue: str
    message: str


@dataclass
class NamingValidationResult:
    valid: bool
    total_columns: int
    validated_columns: int
    issues: list[NamingIssue]


def load_naming_rules(path: Path) -> dict:
    """
    Carrega as regras de nomenclatura do YAML.

    Estrutura esperada:

    naming:
      pattern: "..."
      prefixes:
        str:
          allowed_types: ["STRING"]
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo de regras não encontrado: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        content = yaml.safe_load(file) or {}

    naming = content.get("naming")

    if not isinstance(naming, dict):
        raise ValueError(
            "O arquivo precisa possuir a seção 'naming'."
        )

    pattern = naming.get("pattern")
    prefixes = naming.get("prefixes")

    if not isinstance(pattern, str) or not pattern.strip():
        raise ValueError(
            "A configuração 'naming.pattern' é obrigatória."
        )

    if not isinstance(prefixes, dict) or not prefixes:
        raise ValueError(
            "A configuração 'naming.prefixes' é obrigatória."
        )

    # Valida a expressão regular durante o carregamento.
    try:
        re.compile(pattern)
    except re.error as error:
        raise ValueError(
            f"Regex inválida no naming_rules.yml: {error}"
        ) from error

    normalized_prefixes = {}

    for prefix, definition in prefixes.items():

        if not isinstance(definition, dict):
            raise ValueError(
                f"Configuração inválida para o prefixo '{prefix}'."
            )

        allowed_types = definition.get("allowed_types")

        if (
            not isinstance(allowed_types, list)
            or not allowed_types
        ):
            raise ValueError(
                f"allowed_types deve ser uma lista não vazia "
                f"para o prefixo '{prefix}'."
            )

        if not all(
            isinstance(data_type, str) and data_type.strip()
            for data_type in allowed_types
        ):
            raise ValueError(
                f"Tipos inválidos para o prefixo '{prefix}'."
            )

        normalized_prefixes[prefix] = {
            "allowed_types": {
                normalize_data_type(data_type)
                for data_type in allowed_types
            }
        }

    return {
        "pattern": pattern,
        "compiled_pattern": re.compile(pattern),
        "prefixes": normalized_prefixes,
    }


def normalize_data_type(data_type: str) -> str:
    """
    Normaliza tipos SQL para comparação.

    Exemplos:
        STRING          -> STRING
        DECIMAL(10, 2)  -> DECIMAL
        VARCHAR(100)    -> VARCHAR
    """

    normalized = data_type.strip().upper()

    # Remove parâmetros de precisão e escala.
    normalized = re.sub(
        r"\s*\(.*\)\s*$",
        "",
        normalized,
    )

    return normalized.strip()


def extract_prefix(column_name: str) -> str | None:
    """
    Extrai o prefixo técnico do nome da coluna.

    Exemplo:
        big_sensor_id -> big
        str_sensor_name -> str
    """

    if "_" not in column_name:
        return None

    return column_name.split("_", maxsplit=1)[0]


def validate_column_naming(
    column: ColumnDefinition,
    rules: dict,
) -> list[NamingIssue]:

    issues = []

    column_name = column.name
    data_type = normalize_data_type(column.data_type)

    # 1. Validação da expressão regular.
    if not rules["compiled_pattern"].fullmatch(column_name):

        issues.append(
            NamingIssue(
                file=column.file,
                table=column.table,
                column=column_name,
                issue="INVALID_NAMING_PATTERN",
                message=(
                    f"O nome '{column_name}' não atende "
                    f"ao padrão definido: {rules['pattern']}."
                ),
            )
        )

    # 2. Extração do prefixo.
    prefix = extract_prefix(column_name)

    if not prefix:

        issues.append(
            NamingIssue(
                file=column.file,
                table=column.table,
                column=column_name,
                issue="MISSING_PREFIX",
                message=(
                    "Não foi possível identificar o prefixo técnico. "
                    "O nome deve seguir o padrão prefixo_mnemonico."
                ),
            )
        )

        return issues

    # 3. Consulta ao YAML de regras.
    prefix_definition = rules["prefixes"].get(prefix)

    if not prefix_definition:

        issues.append(
            NamingIssue(
                file=column.file,
                table=column.table,
                column=column_name,
                issue="UNKNOWN_PREFIX",
                message=(
                    f"O prefixo '{prefix}' não está cadastrado "
                    "em naming_rules.yml."
                ),
            )
        )

        return issues

    # 4. Validação de compatibilidade do tipo SQL.
    allowed_types = prefix_definition["allowed_types"]

    if data_type not in allowed_types:

        issues.append(
            NamingIssue(
                file=column.file,
                table=column.table,
                column=column_name,
                issue="INCOMPATIBLE_DATA_TYPE",
                message=(
                    f"O prefixo '{prefix}' não permite o tipo "
                    f"SQL '{data_type}'. Tipos permitidos: "
                    f"{', '.join(sorted(allowed_types))}."
                ),
            )
        )

    return issues


def validate_naming(
    columns: list[ColumnDefinition],
    rules: dict,
) -> NamingValidationResult:

    issues = []

    for column in columns:

        issues.extend(
            validate_column_naming(
                column,
                rules,
            )
        )

    return NamingValidationResult(
        valid=len(issues) == 0,
        total_columns=len(columns),
        validated_columns=len(columns),
        issues=issues,
    )


def generate_report(
    result: NamingValidationResult,
) -> dict:

    return {
        "valid": result.valid,
        "total_columns": result.total_columns,
        "validated_columns": result.validated_columns,
        "total_issues": len(result.issues),
        "issues": [
            asdict(issue)
            for issue in result.issues
        ],
    }


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Validação de nomenclatura e tipos SQL "
            "de colunas Databricks."
        )
    )

    parser.add_argument(
        "--sql-path",
        default="sql",
        help="Diretório dos arquivos SQL."
    )

    parser.add_argument(
        "--rules",
        default="governance/naming_rules.yml",
        help="Caminho do arquivo naming_rules.yml."
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Caminho opcional para salvar o relatório JSON."
    )

    args = parser.parse_args()

    try:

        # 1. Carrega as regras de nomenclatura.
        rules = load_naming_rules(
            Path(args.rules)
        )

        # 2. Executa o parser SQL.
        parse_results = validate_directory(
            Path(args.sql_path)
        )

        parse_errors = [
            error
            for result in parse_results
            for error in result.errors
        ]

        if parse_errors:

            for error in parse_errors:
                print(f"::error::{error}")

            print(
                "Validação de nomenclatura interrompida: "
                "existem erros no parser SQL."
            )

            return 1

        # 3. Consolida as colunas extraídas.
        columns = [
            column
            for result in parse_results
            for column in result.columns
        ]

        # 4. Executa as validações.
        result = validate_naming(
            columns,
            rules,
        )

        report = generate_report(result)

        print(
            json.dumps(
                report,
                indent=4,
                ensure_ascii=False,
            )
        )

        # 5. Salva relatório JSON.
        if args.output:

            output_path = Path(args.output)

            output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            output_path.write_text(
                json.dumps(
                    report,
                    indent=4,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        # 6. Publica erros no GitHub Actions.
        for issue in result.issues:

            print(
                f"::error file={issue.file}::"
                f"{issue.column}: {issue.message}"
            )

        if not result.valid:
            return 1

        print(
            "Validação de nomenclatura concluída com sucesso."
        )

        return 0

    except Exception as error:

        print(f"::error::{error}")

        return 1


if __name__ == "__main__":
    sys.exit(main())
