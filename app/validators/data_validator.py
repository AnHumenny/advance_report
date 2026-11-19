from dataclasses import dataclass
from decimal import Decimal

from app.domain.models import (
    Contract,
    Payment,
    PaymentStatus,
    Work,
    WorkStatus,
)


@dataclass
class ValidationResult:
    """Результат проверки данных: критические ошибки и предупреждения."""

    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        """Возвращает True, если критических ошибок нет."""

        return not self.errors


def _find_duplicates(values: list[str]) -> set[str]:
    """Находит повторяющиеся значения в списке."""

    seen = set()
    duplicates = set()

    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)

    return duplicates


def validate_data(
    contracts: list[Contract],
    works: list[Work],
    payments: list[Payment],
) -> ValidationResult:
    """Проверяет договоры, работы и платежи на корректность и согласованность."""

    errors: list[str] = []
    warnings: list[str] = []

    for entity_name, identifiers in [
        ("договоров", [item.contract_id for item in contracts]),
        ("работ", [item.work_id for item in works]),
        ("платежей", [item.payment_id for item in payments]),
    ]:
        for identifier in sorted(_find_duplicates(identifiers)):
            errors.append(
                f"Повторяющийся ID {entity_name}: {identifier}"
            )

    contracts_by_id = {
        contract.contract_id: contract
        for contract in contracts
    }

    works_by_id = {
        work.work_id: work
        for work in works
    }

    for contract in contracts:
        if not contract.contract_id:
            errors.append("Договор: отсутствует contract_id")

        if not contract.contractor:
            errors.append(
                f"Договор {contract.contract_id}: отсутствует подрядчик"
            )

        if not contract.amount.is_finite():
            errors.append(
                f"Договор {contract.contract_id}: "
                "некорректная сумма (NaN или Infinity)"
            )
        elif contract.amount < 0:
            errors.append(
                f"Договор {contract.contract_id}: отрицательная сумма"
            )

        if contract.signed_at is None:
            errors.append(
                f"Договор {contract.contract_id}: отсутствует signed_at"
            )

    for work in works:
        if not work.work_id:
            errors.append("Работа: отсутствует work_id")

        if not work.contract_id:
            errors.append(
                f"Работа {work.work_id}: отсутствует contract_id"
            )
        elif work.contract_id not in contracts_by_id:
            errors.append(
                f"Работа {work.work_id}: "
                f"не найден договор {work.contract_id}"
            )

        if not work.title:
            errors.append(
                f"Работа {work.work_id}: отсутствует название"
            )

        if not work.price.is_finite():
            errors.append(
                f"Работа {work.work_id}: "
                "некорректная цена (NaN или Infinity)"
            )
        elif work.price < 0:
            errors.append(
                f"Работа {work.work_id}: отрицательная цена"
            )

        if work.status == WorkStatus.DONE:
            if work.completed_at is None:
                errors.append(
                    f"Работа {work.work_id}: "
                    "статус done, но отсутствует completed_at"
                )

            if work.cancelled_at is not None:
                errors.append(
                    f"Работа {work.work_id}: "
                    "у выполненной работы заполнен cancelled_at"
                )

        elif work.status == WorkStatus.CANCELLED:
            if work.cancelled_at is None:
                errors.append(
                    f"Работа {work.work_id}: "
                    "статус cancelled, но отсутствует cancelled_at"
                )

            if work.completed_at is not None:
                errors.append(
                    f"Работа {work.work_id}: "
                    "у отменённой работы заполнен completed_at"
                )

        elif work.status == WorkStatus.PLANNED:
            if work.completed_at is not None or work.cancelled_at is not None:
                errors.append(
                    f"Работа {work.work_id}: "
                    "у запланированной работы заполнена дата выполнения "
                    "или отмены"
                )

    for payment in payments:
        if not payment.payment_id:
            errors.append("Платёж: отсутствует payment_id")

        if not payment.contract_id:
            errors.append(
                f"Платёж {payment.payment_id}: отсутствует contract_id"
            )
        elif payment.contract_id not in contracts_by_id:
            errors.append(
                f"Платёж {payment.payment_id}: "
                f"не найден договор {payment.contract_id}"
            )

        if not payment.purpose:
            errors.append(
                f"Платёж {payment.payment_id}: отсутствует назначение"
            )

        if not payment.amount.is_finite():
            errors.append(
                f"Платёж {payment.payment_id}: "
                "некорректная сумма (NaN или Infinity)"
            )
        elif payment.amount < 0:
            errors.append(
                f"Платёж {payment.payment_id}: отрицательная сумма"
            )

        if payment.created_at is None:
            errors.append(
                f"Платёж {payment.payment_id}: отсутствует created_at"
            )

        if payment.work_id is not None:
            linked_work = works_by_id.get(payment.work_id)

            if linked_work is None:
                errors.append(
                    f"Платёж {payment.payment_id}: "
                    f"не найдена работа {payment.work_id}"
                )
            elif linked_work.contract_id != payment.contract_id:
                errors.append(
                    f"Платёж {payment.payment_id}: "
                    f"работа {payment.work_id} относится к другому договору"
                )
            elif linked_work.status == WorkStatus.CANCELLED:
                warnings.append(
                    f"Платёж {payment.payment_id} привязан "
                    f"к отменённой работе {payment.work_id}"
                )

        if (
            payment.created_at is not None
            and payment.paid_at is not None
            and payment.paid_at < payment.created_at
        ):
            errors.append(
                f"Платёж {payment.payment_id}: "
                "дата оплаты раньше даты создания"
            )

        if (
            payment.paid_at is not None
            and payment.refunded_at is not None
            and payment.refunded_at < payment.paid_at
        ):
            errors.append(
                f"Платёж {payment.payment_id}: "
                "дата возврата раньше даты оплаты"
            )

        if payment.status == PaymentStatus.PAID:
            if payment.paid_at is None:
                errors.append(
                    f"Платёж {payment.payment_id}: "
                    "статус paid, но отсутствует paid_at"
                )

            if payment.refunded_at is not None:
                errors.append(
                    f"Платёж {payment.payment_id}: "
                    "статус paid, но заполнен refunded_at"
                )

        elif payment.status == PaymentStatus.REFUNDED:
            if payment.paid_at is None or payment.refunded_at is None:
                errors.append(
                    f"Платёж {payment.payment_id}: "
                    "статус refunded, но отсутствует дата оплаты "
                    "или возврата"
                )

        elif payment.status == PaymentStatus.QUEUED:
            if payment.paid_at is not None or payment.refunded_at is not None:
                errors.append(
                    f"Платёж {payment.payment_id}: "
                    "статус queued, но заполнена дата оплаты или возврата"
                )

    works_by_contract: dict[str, list[Work]] = {}

    for work in works:
        works_by_contract.setdefault(work.contract_id, []).append(work)

    for contract in contracts:
        if not contract.amount.is_finite():
            continue

        contract_works = works_by_contract.get(contract.contract_id, [])

        if any(not work.price.is_finite() for work in contract_works):
            continue

        works_total = sum(
            (work.price for work in contract_works),
            start=Decimal("0.00"),
        )

        if works_total != contract.amount:
            warnings.append(
                f"Договор {contract.contract_id}: "
                f"сумма работ {works_total:.2f} ₽ "
                f"не совпадает с суммой договора "
                f"{contract.amount:.2f} ₽"
            )

    return ValidationResult(
        errors=errors,
        warnings=warnings,
    )
