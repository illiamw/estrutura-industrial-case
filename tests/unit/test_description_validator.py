from pathlib import Path

import pytest

from src.ddl.sql_parser import ColumnDefinition
from src.governance.description_validator import (
    build_synonym_index,
    contains_term,
    generate_report,
    identify_mnemonics,
    load_tesaurus,
    normalize_text,
    validate_column_description,
    validate_descriptions,
)


@pytest.fixture
def tesaurus_file(tmp_path: Path) -> Path:
    path = tmp_path / "tesaurus.yml"
    path.write_text(
        """
terms:
  maquina:
    description: "Equipamento industrial."
    synonyms:
      - máquina
      - equipamento
  codigo_maquina:
    description: "Código que identifica uma máquina."
    synonyms:
      - código da máquina
""",
        encoding="utf-8",
    )
    return path


def make_column(
    name: str,
    description: str | None,
) -> ColumnDefinition:
    return ColumnDefinition(
        name=name,
        data_type="STRING",
        description=description,
        table="datapulse.bronze.sensor_events",
        file="sensor_events.sql",
    )


def test_normalize_text_removes_accents_and_punctuation() -> None:
    assert normalize_text("  Pressão_máxima! ") == "pressao maxima"


def test_contains_term_matches_whole_terms_only() -> None:
    assert contains_term("Pressão em bar", "bar")
    assert not contains_term("barra de metal", "bar")
    assert not contains_term("qualquer texto", "")


def test_load_tesaurus_normalizes_keys_and_synonyms(
    tesaurus_file: Path,
) -> None:
    tesaurus = load_tesaurus(tesaurus_file)

    assert "maquina" in tesaurus
    assert "equipamento" in tesaurus["maquina"]["synonyms"]


def test_load_tesaurus_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_tesaurus(tmp_path / "missing.yml")


def test_build_synonym_index_rejects_ambiguous_synonym() -> None:
    tesaurus = {
        "maquina": {"synonyms": {"máquina", "equipamento"}},
        "equipamento": {"synonyms": {"equipamento", "máquina industrial"}},
    }

    with pytest.raises(ValueError, match="Sinônimo ambíguo"):
        build_synonym_index(tesaurus)


def test_identify_mnemonics_recognizes_compound_term(
    tesaurus_file: Path,
) -> None:
    tesaurus = load_tesaurus(tesaurus_file)

    matches = identify_mnemonics("str_codigo_maquina", tesaurus)

    assert "codigo_maquina" in {item["mnemonic"] for item in matches}


def test_validate_column_description_accepts_matching_description(
    tesaurus_file: Path,
) -> None:
    issues = validate_column_description(
        make_column("str_maquina", "Equipamento industrial da linha."),
        load_tesaurus(tesaurus_file),
    )

    assert issues == []


@pytest.mark.parametrize(
    ("description", "expected_issue"),
    [
        (None, "MISSING_COMMENT"),
        ("   ", "MISSING_COMMENT"),
        ("Componente elétrico", "DESCRIPTION_MISMATCH"),
    ],
)
def test_validate_column_description_reports_invalid_description(
    tesaurus_file: Path,
    description: str | None,
    expected_issue: str,
) -> None:
    issues = validate_column_description(
        make_column("str_maquina", description),
        load_tesaurus(tesaurus_file),
    )

    assert [issue.issue for issue in issues] == [expected_issue]


def test_validate_descriptions_reports_unknown_mnemonic_and_summarizes(
    tesaurus_file: Path,
) -> None:
    result = validate_descriptions(
        [make_column("str_sensor_serial", "Número de série do sensor.")],
        load_tesaurus(tesaurus_file),
    )
    report = generate_report(result)

    assert result.valid is False
    assert report["total_columns"] == 1
    assert report["total_issues"] == 1
    assert report["issues"][0]["issue"] == "UNKNOWN_MNEMONIC"
