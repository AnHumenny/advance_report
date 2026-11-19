import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.domain.models import (
    Contract,
    Payment,
    PaymentStatus,
    Work,
    WorkStatus,
)


class CsvLoaderError(Exception):
    """Ошибка чтения или преобразования CSV."""


def _read_csv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    """Читает CSV-файл и проверяет наличие обязательных колонок."""

    if not path.exists():
        raise CsvLoaderError(f"Файл не найден: {path}")

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            if not reader.fieldnames:
                raise CsvLoaderError(f"Файл пустой: {path}")

            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise CsvLoaderError(
                    f"Обнаружены повторяющиеся заголовки в файле: {path}"
                )

            missing = required_columns - set(reader.fieldnames)

            if missing:
                raise CsvLoaderError(
                    f"В файле {path} отсутствуют колонки: {', '.join(sorted(missing))}"
                )

            rows = []

            for line_number, row in enumerate(reader, start=2):
                if None in row:
                    raise CsvLoaderError(
                        f"Лишние значения в строке {line_number}, файл {path}"
                    )

                if all(value is None or not value.strip() for value in row.values()):
                    continue

                rows.append(row)

            return rows

    except UnicodeDecodeError as error:
        raise CsvLoaderError(f"Ошибка кодировки файла {path}") from error
    except csv.Error as error:
        raise CsvLoaderError(f"Ошибка чтения CSV {path}: {error}") from error


def _parse_date(value: str | None, field: str) -> date | None:
    """Преобразует строку в дату или возвращает None для пустого значения."""

    if value is None or not value.strip():
        return None

    try:
        return date.fromisoformat(value.strip())
    except ValueError as error:
        raise CsvLoaderError(
            f"Некорректная дата в поле {field}: {value}"
        ) from error


def _parse_required_date(value: str | None, field: str) -> date:
    """Преобразует обязательное поле даты и проверяет, что оно заполнено."""

    parsed_date = _parse_date(value, field)

    if parsed_date is None:
        raise CsvLoaderError(
            f"Обязательное поле даты не заполнено: {field}"
        )

    return parsed_date


def _parse_decimal(value: str, field: str) -> Decimal:
    """Преобразует строку в Decimal для точной работы с денежными суммами."""

    try:
        return Decimal(value.strip())
    except (InvalidOperation, AttributeError) as error:
        raise CsvLoaderError(
            f"Некорректное денежное значение в поле {field}: {value}"
        ) from error


def load_contracts(path: Path) -> list[Contract]:
    """Загружает договоры из CSV-файла."""

    rows = _read_csv(
        path,
        {"contract_id", "contractor", "amount", "signed_at"},
    )

    return [
        Contract(
            contract_id=row["contract_id"].strip(),
            contractor=row["contractor"].strip(),
            amount=_parse_decimal(row["amount"], "amount"),
            signed_at=_parse_required_date(row["signed_at"], "signed_at"),
        )
        for row in rows
    ]


def load_works(path: Path) -> list[Work]:
    """Загружает работы из CSV-файла."""

    rows = _read_csv(
        path,
        {
            "work_id",
            "contract_id",
            "title",
            "price",
            "status",
            "completed_at",
            "cancelled_at",
        },
    )

    result = []

    for row in rows:
        try:
            status = WorkStatus(row["status"].strip())
        except ValueError as error:
            raise CsvLoaderError(
                f"Неизвестный статус работы {row['work_id']}: {row['status']}"
            ) from error

        result.append(
            Work(
                work_id=row["work_id"].strip(),
                contract_id=row["contract_id"].strip(),
                title=row["title"].strip(),
                price=_parse_decimal(row["price"], "price"),
                status=status,
                completed_at=_parse_date(row["completed_at"], "completed_at"),
                cancelled_at=_parse_date(row["cancelled_at"], "cancelled_at"),
            )
        )

    return result


def load_payments(path: Path) -> list[Payment]:
    """Загружает платежи из CSV-файла."""

    rows = _read_csv(
        path,
        {
            "payment_id",
            "contract_id",
            "work_id",
            "purpose",
            "amount",
            "status",
            "created_at",
            "paid_at",
            "refunded_at",
        },
    )

    result = []

    for row in rows:
        try:
            status = PaymentStatus(row["status"].strip())
        except ValueError as error:
            raise CsvLoaderError(
                f"Неизвестный статус платежа {row['payment_id']}: {row['status']}"
            ) from error

        result.append(
            Payment(
                payment_id=row["payment_id"].strip(),
                contract_id=row["contract_id"].strip(),
                work_id=row["work_id"].strip() or None,
                purpose=row["purpose"].strip(),
                amount=_parse_decimal(row["amount"], "amount"),
                status=status,
                created_at=_parse_required_date(row["created_at"], "created_at"),
                paid_at=_parse_date(row["paid_at"], "paid_at"),
                refunded_at=_parse_date(row["refunded_at"], "refunded_at"),
            )
        )

    return result
