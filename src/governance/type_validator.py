
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
class TypeIssue:
    file: str
    table: str
    column: str
    data_type: str
    issue: str
    message: str


@dataclass
class TypeValidationResult:
    valid: bool
    total_columns: int
    validated_columns: int
    issues: list[TypeIssue]


def normalize_type(data_type: str) -> str:
    """
    Normaliza a representação do tipo SQL.

    Exemplos:
        STRING          -> STRING
        DECIMAL(10,2)   -> DECIMAL
        ARRAY<STRING>   -> ARRAY
        MAP<STRING,INT> -> MAP
        STRUCT<id:INT>  -> STRUCT
    """

    normalized = data_type.strip().upper()

    # Remove espaços desnecessários.
    normalized = re.sub(r"\s+", " ", normalized)

    # Identifica tipos complexos.
    complex_match = re.match(
        r"^(ARRAY|MAP|STRUCT)\s*<",
        normalized,
    )

    if complex_match:
        return complex_match.group(1)

    # Identifica tipos parametrizados.
    parameterized_match = re.match(
        r"^([A-Z][A-Z0-9_]*)\s*\(",
        normalized,
    )

    if parameterized_match:
        return parameterized_match.group(1)

    return normalized


def load_type_rules(path: Path) -> dict:
    """
    Carrega as regras de tipos SQL.

    Estrutura esperada:

    types:
      STRING:
        enabled: true
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo de regras não encontrado: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        content = yaml.safe_load(file) or {}

    types = content.get("types")

    if not isinstance(types, dict) or not types:
        raise ValueError(
            "O arquivo precisa possuir uma seção 'types' válida."
        )

    normalized_types = {}

    for data_type, definition in types.items():

        if not isinstance(definition, dict):
            raise ValueError(
                f"Configuração inválida para o tipo '{data_type}'."
            )

        enabled = definition.get("enabled")

        if not isinstance(enabled, bool):
            raise ValueError(
                f"O campo enabled deve ser booleano para '{data_type}'."
            )

        normalized_name = normalize_type(data_type)

        if normalized_name in normalized_types:
            raise ValueError(
                f"Tipo duplicado após normalização: '{data_type}'."
            )

        normalized_types[normalized_name] = {
            "enabled": enabled,
            "complex": definition.get("complex", False),
            "parameters": definition.get("parameters", {}),
        }

    return normalized_types


def extract_decimal_parameters(data_type: str) -> tuple[int, int] | None:
    """
    Extrai precisão e escala de DECIMAL.

    Exemplos:
        DECIMAL(10,2) -> (10, 2)
        DECIMAL(18)   -> (18, 0)
        DECIMAL       -> None
    """

    match = re.fullmatch(
        r"\s*DECIMAL\s*(?:\(\s*(\d+)\s*(?:,\s*(\d+)\s*)?\))?\s*",
        data_type,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    precision = int(match.group(1)) if match.group(1) else 10
    scale = int(match.group(2)) if match.group(2) else 0

    return precision, scale


def validate_decimal(
    data_type: str,
    definition: dict,
) -> list[tuple[str, str]]:
    """
    Valida precisão e escala do DECIMAL.

    Retorna uma lista de problemas encontrados.
    """

    issues = []

    parameters = definition.get("parameters", {})
    decimal_rules = parameters.get("precision", {})
    scale_rules = parameters.get("scale", {})

    values = extract_decimal_parameters(data_type)

    if values is None:
        return issues

    precision, scale = values

    min_precision = decimal_rules.get("min", 1)
    max_precision = decimal_rules.get("max", 38)

    min_scale = scale_rules.get("min", 0)
    max_scale = scale_rules.get("max", 38)

    if not min_precision <= precision <= max_precision:

        issues.append((
            "INVALID_PRECISION",
            (
                f"Precisão {precision} fora do intervalo permitido: "
                f"{min_precision} a {max_precision}."
            ),
        ))

    if not min_scale <= scale <= max_scale:

        issues.append((
            "INVALID_SCALE",
            (
                f"Escala {scale} fora do intervalo permitido: "
                f"{min_scale} a {max_scale}."
            ),
        ))

    if (
        scale_rules.get("must_not_exceed_precision", True)
        and scale > precision
    ):

        issues.append((
            "SCALE_EXCEEDS_PRECISION",
            (
                f"A escala ({scale}) não pode ser maior "
                f"que a precisão ({precision})."
            ),
        ))

    return issues


def validate_column_type(
    column: ColumnDefinition,
    rules: dict,
) -> list[TypeIssue]:

    issues = []

    original_type = column.data_type.strip()
    normalized_type = normalize_type(original_type)

    # 1. Verifica se o tipo está cadastrado.
    definition = rules.get(normalized_type)

    if definition is None:

        issues.append(
            TypeIssue(
                file=column.file,
                table=column.table,
                column=column.name,
                data_type=original_type,
                issue="UNKNOWN_DATA_TYPE",
                message=(
                    f"O tipo SQL '{original_type}' não está "
                    "cadastrado em type_rules.yml."
                ),
            )
        )

        return issues

    # 2. Verifica se o tipo está habilitado.
    if not definition["enabled"]:

        issues.append(
            TypeIssue(
                file=column.file,
                table=column.table,
                column=column.name,
                data_type=original_type,
                issue="DISABLED_DATA_TYPE",
                message=(
                    f"O tipo SQL '{normalized_type}' está "
                    "desabilitado nas regras corporativas."
                ),
            )
        )

        return issues

    # 3. Valida parâmetros do DECIMAL.
    if normalized_type == "DECIMAL":

        decimal_issues = validate_decimal(
            original_type,
            definition,
        )

        for issue_code, message in decimal_issues:

            issues.append(
                TypeIssue(
                    file=column.file,
                    table=column.table,
                    column=column.name,
                    data_type=original_type,
                    issue=issue_code,
                    message=message,
                )
            )

    return issues


def validate_types(
    columns: list[ColumnDefinition],
    rules: dict,
) -> TypeValidationResult:

    issues = []

    for column in columns:

        issues.extend(
            validate_column_type(
                column,
                rules,
            )
        )

    return TypeValidationResult(
        valid=len(issues) == 0,
        total_columns=len(columns),
        validated_columns=len(columns),
        issues=issues,
    )


def generate_report(
    result: TypeValidationResult,
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
            "Validação de tipos SQL de colunas Databricks."
        )
    )

    parser.add_argument(
        "--sql-path",
        default="sql",
        help="Diretório dos arquivos SQL."
    )

    parser.add_argument(
        "--rules",
        default="governance/type_rules.yml",
        help="Caminho do arquivo type_rules.yml."
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Caminho opcional para salvar o relatório JSON."
    )

    args = parser.parse_args()

    try:

        # 1. Carrega regras de tipos.
        rules = load_type_rules(
            Path(args.rules)
        )

        # 2. Executa parser SQL.
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
                "Validação de tipos interrompida: "
                "existem erros no parser SQL."
            )

            return 1

        # 3. Consolida colunas extraídas.
        columns = [
            column
            for result in parse_results
            for column in result.columns
        ]

        # 4. Executa validações.
        result = validate_types(
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
            "Validação de tipos SQL concluída com sucesso."
        )

        return 0

    except Exception as error:

        print(f"::error::{error}")

        return 1


if __name__ == "__main__":
    sys.exit(main())
