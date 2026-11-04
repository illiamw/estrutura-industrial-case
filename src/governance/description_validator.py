
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata

from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from src.ddl.sql_parser import (
    validate_directory,
    ColumnDefinition,
)


@dataclass
class DescriptionIssue:
    file: str
    table: str
    column: str
    issue: str
    message: str


@dataclass
class DescriptionValidationResult:
    valid: bool
    total_columns: int
    validated_columns: int
    issues: list[DescriptionIssue]


def normalize_text(value: str) -> str:
    """
    Normaliza texto para comparação.

    Trata:
    - Maiúsculas e minúsculas.
    - Acentos.
    - Underscores.
    - Hífens.
    - Pontuação.
    - Espaços duplicados.
    """

    value = unicodedata.normalize("NFKD", value.lower())

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = re.sub(r"[^a-z0-9]+", " ", value)

    return " ".join(value.split())


def contains_term(text: str, term: str) -> bool:
    """
    Verifica se um termo aparece como expressão completa.

    Evita, por exemplo, que 'bar' seja encontrado dentro
    de 'barramento'.
    """

    normalized_text = normalize_text(text)
    normalized_term = normalize_text(term)

    if not normalized_text or not normalized_term:
        return False

    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(normalized_term)
        + r"(?![a-z0-9])"
    )

    return bool(re.search(pattern, normalized_text))


def load_tesaurus(path: Path) -> dict:
    """
    Carrega o Tesaurus corporativo.

    Estrutura esperada:

    terms:
      sensor:
        description: "Dispositivo responsável..."
        synonyms:
          - dispositivo
          - equipamento
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Tesaurus não encontrado: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        content = yaml.safe_load(file) or {}

    terms = content.get("terms")

    if not isinstance(terms, dict) or not terms:
        raise ValueError(
            "O Tesaurus precisa possuir uma seção 'terms' válida."
        )

    normalized_terms = {}

    for mnemonic, definition in terms.items():

        if not isinstance(definition, dict):
            raise ValueError(
                f"Definição inválida para '{mnemonic}'."
            )

        description = definition.get("description", "")
        synonyms = definition.get("synonyms", [])

        if not isinstance(description, str):
            raise ValueError(
                f"description inválida para '{mnemonic}'."
            )

        if not isinstance(synonyms, list):
            raise ValueError(
                f"synonyms deve ser uma lista para '{mnemonic}'."
            )

        if not all(
            isinstance(item, str)
            for item in synonyms
        ):
            raise ValueError(
                f"Todos os synonyms devem ser strings: '{mnemonic}'."
            )

        # A própria chave também é considerada um termo válido.
        aliases = {
            normalize_text(mnemonic),
            *(
                normalize_text(synonym)
                for synonym in synonyms
                if synonym.strip()
            ),
        }

        aliases.discard("")

        normalized_key = normalize_text(mnemonic)

        if normalized_key in normalized_terms:
            raise ValueError(
                f"Mnemônico duplicado após normalização: '{mnemonic}'."
            )

        normalized_terms[normalized_key] = {
            "mnemonic": mnemonic,
            "description": description,
            "synonyms": aliases,
        }

    return normalized_terms


def build_synonym_index(tesaurus: dict) -> dict:
    """
    Cria um índice reverso:

        synonym -> mnemonic

    Exemplo:

        dispositivo -> sensor
        equipamento -> sensor
        sensor -> sensor

    Se um sinônimo estiver associado a mais de um mnemônico,
    a validação será interrompida para evitar ambiguidade.
    """

    index = {}

    for mnemonic, definition in tesaurus.items():

        for synonym in definition["synonyms"]:

            if synonym in index and index[synonym] != mnemonic:

                raise ValueError(
                    f"Sinônimo ambíguo '{synonym}': associado a "
                    f"'{index[synonym]}' e '{mnemonic}'."
                )

            index[synonym] = mnemonic

    return index


def identify_mnemonics(
    column_name: str,
    tesaurus: dict,
) -> list[dict]:
    """
    Identifica os conceitos presentes no nome da coluna.

    Reconhece mnemônicos compostos por múltiplas palavras.

    Exemplo:

        str_codigo_maquina

    Identifica:
        codigo_maquina
    """

    normalized_name = normalize_text(
        column_name.replace("_", " ")
    )

    # O primeiro segmento é considerado prefixo técnico.
    parts = column_name.split("_")

    if len(parts) < 2:
        return []

    semantic_name = normalize_text(
        " ".join(parts[1:])
    )

    found = []

    # Prioriza expressões mais longas para evitar que
    # termos compostos sejam fragmentados.
    candidates = sorted(
        tesaurus.values(),
        key=lambda item: max(
            (len(alias.split()) for alias in item["synonyms"]),
            default=0,
        ),
        reverse=True,
    )

    for mnemonic in candidates:

        for synonym in mnemonic["synonyms"]:

            if contains_term(semantic_name, synonym):

                found.append(mnemonic)
                break

    return found


def validate_column_description(
    column: ColumnDefinition,
    tesaurus: dict,
) -> list[DescriptionIssue]:

    issues = []

    description = (
        column.description.strip()
        if column.description
        else ""
    )

    # 1. Comentário obrigatório
    if not description:

        issues.append(
            DescriptionIssue(
                file=column.file,
                table=column.table,
                column=column.name,
                issue="MISSING_COMMENT",
                message="A coluna não possui COMMENT obrigatório."
            )
        )

        return issues

    # 2. Identifica os mnemônicos
    mnemonics = identify_mnemonics(
        column.name,
        tesaurus,
    )

    if not mnemonics:

        issues.append(
            DescriptionIssue(
                file=column.file,
                table=column.table,
                column=column.name,
                issue="UNKNOWN_MNEMONIC",
                message=(
                    "Nenhum mnemônico reconhecido no nome da coluna. "
                    "Verifique o prefixo e o Tesaurus."
                )
            )
        )

        return issues

    # 3. Verifica compatibilidade da descrição
    for mnemonic in mnemonics:

        compatible = any(
            contains_term(description, synonym)
            for synonym in mnemonic["synonyms"]
        )

        if not compatible:

            issues.append(
                DescriptionIssue(
                    file=column.file,
                    table=column.table,
                    column=column.name,
                    issue="DESCRIPTION_MISMATCH",
                    message=(
                        f"A descrição não apresenta termos "
                        f"compatíveis com o mnemônico "
                        f"'{mnemonic['mnemonic']}'. "
                        f"Definição esperada: "
                        f"{mnemonic['description']}. "
                        f"Descrição informada: '{description}'."
                    )
                )
            )

    return issues


def validate_descriptions(
    columns: list[ColumnDefinition],
    tesaurus: dict,
) -> DescriptionValidationResult:

    issues = []

    for column in columns:

        issues.extend(
            validate_column_description(
                column,
                tesaurus,
            )
        )

    return DescriptionValidationResult(
        valid=len(issues) == 0,
        total_columns=len(columns),
        validated_columns=len(columns),
        issues=issues,
    )


def generate_report(
    result: DescriptionValidationResult,
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
            "Validação de comentários e mnemônicos "
            "de DDL Databricks."
        )
    )

    parser.add_argument(
        "--sql-path",
        default="sql",
        help="Diretório dos arquivos SQL."
    )

    parser.add_argument(
        "--tesaurus",
        default="governance/tesaurus.yml",
        help="Caminho do Tesaurus."
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Caminho do relatório JSON."
    )

    args = parser.parse_args()

    try:

        tesaurus = load_tesaurus(
            Path(args.tesaurus)
        )

        # Verifica ambiguidades no Tesaurus.
        build_synonym_index(tesaurus)

        # Executa parser SQL.
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
                "Validação semântica interrompida: "
                "existem erros no parser SQL."
            )

            return 1

        # Consolida todas as colunas.
        columns = [
            column
            for result in parse_results
            for column in result.columns
        ]

        result = validate_descriptions(
            columns,
            tesaurus,
        )

        report = generate_report(result)

        print(
            json.dumps(
                report,
                indent=4,
                ensure_ascii=False,
            )
        )

        # Salva relatório.
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

        # Publica erros no GitHub Actions.
        for issue in result.issues:

            print(
                f"::error file={issue.file}::"
                f"{issue.column}: {issue.message}"
            )

        if not result.valid:
            return 1

        print(
            "Validação de comentários concluída com sucesso."
        )

        return 0

    except Exception as error:

        print(f"::error::{error}")

        return 1


if __name__ == "__main__":
    sys.exit(main())
