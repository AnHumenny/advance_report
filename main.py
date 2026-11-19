import argparse
import sys
from datetime import date
from pathlib import Path

from app.infrastructure.csv_exporter import export_csv
from app.infrastructure.csv_loader import (
    CsvLoaderError,
    load_contracts,
    load_payments,
    load_works,
)
from app.services.allocation_service import allocate_payments
from app.services.reporting_service import (
    build_contract_report,
    build_work_report,
)
from app.validators.data_validator import validate_data


DEFAULT_DATE = date(2026, 11, 10)


def get_interactive_args() -> argparse.Namespace:
    """Запрашивает параметры запуска в интерактивном режиме."""

    default_data_dir = "data"
    default_output_dir = "reports"

    data_dir = (
        input(f"Папка с исходными данными [{default_data_dir}]: ").strip()
        or default_data_dir
    )

    report_date = (
        input(f"Дата отчёта [{DEFAULT_DATE}]: ").strip()
        or DEFAULT_DATE.isoformat()
    )

    output_dir = (
        input(f"Папка для сохранения отчётов [{default_output_dir}]: ").strip()
        or default_output_dir
    )

    return argparse.Namespace(
        data_dir=Path(data_dir),
        date=date.fromisoformat(report_date),
        output_dir=Path(output_dir),
    )


def parse_args() -> argparse.Namespace:
    """Разбирает аргументы командной строки или запускает интерактивный ввод."""

    parser = argparse.ArgumentParser(
        description="Формирование отчёта по авансам и оплатам договоров."
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Папка с исходными CSV-файлами (по умолчанию: data).",
    )

    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=DEFAULT_DATE,
        help="Дата отчёта в формате YYYY-MM-DD.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports"),
        help="Папка для готовых отчётов (по умолчанию: reports).",
    )

    if len(sys.argv) == 1:
        return get_interactive_args()

    return parser.parse_args()


def main() -> int:
    """Загружает, проверяет и обрабатывает данные, формирует CSV-отчёты."""

    try:
        args = parse_args()

        contracts = load_contracts(args.data_dir / "contracts.csv")
        works = load_works(args.data_dir / "works.csv")
        payments = load_payments(args.data_dir / "payments.csv")

        validation = validate_data(
            contracts=contracts,
            works=works,
            payments=payments,
        )

        if validation.warnings:
            print("\nПредупреждения:")

            for warning in validation.warnings:
                print(f"  - {warning}")

        if validation.errors:
            print("\nОбнаружены ошибки в исходных данных:")

            for error in validation.errors:
                print(f"  - {error}")

            return 1

        allocation = allocate_payments(
            contracts=contracts,
            works=works,
            payments=payments,
            report_date=args.date,
        )

        work_report = build_work_report(
            allocation=allocation,
            report_date=args.date,
        )

        contract_report = build_contract_report(
            allocation=allocation,
            report_date=args.date,
        )

        work_path = args.output_dir / "work_report.csv"
        contract_path = args.output_dir / "contract_report.csv"

        export_csv(work_report, work_path)
        export_csv(contract_report, contract_path)

        print("\nОтчёты успешно сформированы.")
        print(f"Дата отчёта: {args.date}")
        print(f"Отчёт по работам: {work_path}")
        print(f"Отчёт по договорам: {contract_path}")

        return 0

    except (CsvLoaderError, ValueError) as error:
        print(f"\nОшибка: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
