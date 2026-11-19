from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.models import (
    Contract,
    Payment,
    PaymentStatus,
    Work,
    WorkStatus,
)


ZERO = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class WorkAllocation:
    """Результат распределения платежей для отдельной работы."""

    work: Work
    direct_paid: Decimal
    allocated_paid: Decimal
    paid_total: Decimal
    remaining: Decimal | None
    overpayment: Decimal | None


@dataclass(frozen=True, slots=True)
class ContractAllocation:
    """Финансовые итоги по отдельному договору."""

    contract: Contract
    paid_total: Decimal
    remaining: Decimal
    overpayment: Decimal
    unallocated: Decimal


@dataclass(frozen=True, slots=True)
class AllocationResult:
    """Результаты распределения платежей по работам и договорам."""

    works: list[WorkAllocation]
    contracts: list[ContractAllocation]


def _get_paid_amount(payment: Payment, report_date: date) -> Decimal:
    """Возвращает сумму платежа, фактически выплаченную на дату отчёта."""

    if payment.status == PaymentStatus.QUEUED:
        return ZERO

    if payment.paid_at is None or payment.paid_at > report_date:
        return ZERO

    if (
        payment.status == PaymentStatus.REFUNDED
        and payment.refunded_at is not None
        and payment.refunded_at <= report_date
    ):
        return ZERO

    return payment.amount


def allocate_payments(
    contracts: list[Contract],
    works: list[Work],
    payments: list[Payment],
    report_date: date,
) -> AllocationResult:
    """Распределяет платежи по работам и рассчитывает итоги договоров."""

    contract_paid: dict[str, Decimal] = {
        contract.contract_id: ZERO
        for contract in contracts
    }

    direct_paid: dict[str, Decimal] = {
        work.work_id: ZERO
        for work in works
    }

    unallocated_payments: dict[str, Decimal] = {
        contract.contract_id: ZERO
        for contract in contracts
    }

    for payment in payments:
        paid_amount = _get_paid_amount(payment, report_date)

        if paid_amount == ZERO:
            continue

        contract_paid[payment.contract_id] += paid_amount

        if payment.work_id is None:
            unallocated_payments[payment.contract_id] += paid_amount
        else:
            direct_paid[payment.work_id] += paid_amount

    allocated_common: dict[str, Decimal] = {
        work.work_id: ZERO
        for work in works
    }

    for work in works:
        if work.status == WorkStatus.CANCELLED:
            continue

        available = max(
            work.price - direct_paid[work.work_id],
            ZERO,
        )

        if available == ZERO:
            continue

        common_amount = unallocated_payments[work.contract_id]

        if common_amount == ZERO:
            continue

        allocation = min(available, common_amount)

        allocated_common[work.work_id] += allocation
        unallocated_payments[work.contract_id] -= allocation

    work_results: list[WorkAllocation] = []

    for work in works:
        direct = direct_paid[work.work_id]
        common = allocated_common[work.work_id]
        paid_total = direct + common

        if work.status == WorkStatus.CANCELLED:
            remaining = None
            overpayment = None
        else:
            remaining = max(work.price - paid_total, ZERO)
            overpayment = max(paid_total - work.price, ZERO)

        work_results.append(
            WorkAllocation(
                work=work,
                direct_paid=direct,
                allocated_paid=common,
                paid_total=paid_total,
                remaining=remaining,
                overpayment=overpayment,
            )
        )

    contract_results: list[ContractAllocation] = []

    for contract in contracts:
        paid_total = contract_paid[contract.contract_id]

        remaining = max(contract.amount - paid_total, ZERO)
        overpayment = max(paid_total - contract.amount, ZERO)

        contract_results.append(
            ContractAllocation(
                contract=contract,
                paid_total=paid_total,
                remaining=remaining,
                overpayment=overpayment,
                unallocated=unallocated_payments[contract.contract_id],
            )
        )

    return AllocationResult(
        works=work_results,
        contracts=contract_results,
    )
