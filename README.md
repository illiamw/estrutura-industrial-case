# Databricks DDL Template

Estrutura inicial para organizar DDLs por camada, validar convenções de governança e
implantar os objetos usando Databricks Asset Bundles.

## Estrutura

- `sql/`: definições DDL separadas em `bronze`, `silver` e `gold`.
- `src/ddl/`: implantação e leitura de arquivos SQL.
- `src/governance/`: validadores de nomenclatura, descrição e tipos.
- `governance/`: tesauro e regras de nomenclatura.
- `tests/`: testes unitários e de integração.
- `.github/workflows/`: pipeline de validação e implantação.

Os arquivos de exemplo são pontos de partida. Ajuste catálogo, schema, regras e
credenciais aos ambientes do projeto antes de executar a implantação.
