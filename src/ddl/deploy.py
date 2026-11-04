"""Entry point for deploying SQL DDL files to Databricks."""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sql-dir", type=Path, required=True)
    args = parser.parse_args()

    sql_files = sorted(args.sql_dir.rglob("*.sql"))
    if not sql_files:
        parser.error(f"No SQL files found in {args.sql_dir}")

    raise NotImplementedError(
        "Connect this entry point to the project's Databricks execution strategy."
    )


if __name__ == "__main__":
    main()
