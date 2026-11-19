import csv
from pathlib import Path


def export_csv(
    rows: list[dict[str, str]],
    path: Path,
) -> None:
    """Сохраняет отчёт в CSV с разделителем ';' и кодировкой UTF-8 BOM."""

    if not rows:
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows[0].keys())

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            delimiter=";",
        )

        writer.writeheader()
        writer.writerows(rows)
