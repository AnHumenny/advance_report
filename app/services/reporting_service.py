from datetime import date
from decimal import Decimal

from app.domain.models import FinancialStatus, WorkStatus
from app.services.allocation_service import AllocationResult, WorkAllocation


def _format_money(value: Decimal | None) -> str:
    """Форматирует денежное значение с точностью до двух знаков."""

    if value is None:
        return ""

    return f"{value:.2f}"


def _get_financial_status(item: WorkAllocation) -> FinancialStatus:
    """Определяет финансовый статус оплаты работы."""

    if item.work.status == WorkStatus.CANCELLED:
        return FinancialStatus.REQUIRES_CLARIFICATION

    if item.overpayment is not None and item.overpayment > 0:
        return FinancialStatus.OVERPAID

    if item.remaining == 0:
        return FinancialStatus.FULLY_PAID

    if item.paid_total > 0:
        return FinancialStatus.PARTIALLY_PAID

    return FinancialStatus.NOT_PAID


def build_work_report(
    allocation: AllocationResult,
    report_date: date,
) -> list[dict[str, str]]:
    """Формирует строки отчёта с финансовыми данными по каждой работе."""

    rows = []

    for item in allocation.works:
        work = item.work
        financial_status = _get_financial_status(item)

        rows.append({
            "Дата отчёта": report_date.isoformat(),
            "Договор": work.contract_id,
            "Работа": work.work_id,
            "Название": work.title,
            "Статус работы": work.status.value,
            "Цена": _format_money(work.price),
            "Прямая оплата": _format_money(item.direct_paid),
            "Расчётное распределение": _format_money(item.allocated_paid),
            "Всего выплачено": _format_money(item.paid_total),
            "Осталось оплатить": _format_money(item.remaining),
            "Переплата": _format_money(item.overpayment),
            "Финансовый статус": financial_status.value,
        })

    return rows


def build_contract_report(
    allocation: AllocationResult,
    report_date: date,
) -> list[dict[str, str]]:
    """Формирует строки итогового отчёта с финансовыми данными по договорам."""

    rows = []

    for item in allocation.contracts:
        contract = item.contract

        rows.append({
            "Дата отчёта": report_date.isoformat(),
            "Договор": contract.contract_id,
            "Подрядчик": contract.contractor,
            "Сумма договора": _format_money(contract.amount),
            "Всего выплачено": _format_money(item.paid_total),
            "Осталось оплатить": _format_money(item.remaining),
            "Переплата": _format_money(item.overpayment),
            "Нераспределено": _format_money(item.unallocated),
        })

    return rows
