from datetime import date
from decimal import Decimal
import unittest

from app.domain.models import (
    Contract,
    FinancialStatus,
    Work,
    WorkStatus,
)
from app.services.allocation_service import (
    AllocationResult,
    ContractAllocation,
    WorkAllocation,
)
from app.services.reporting_service import (
    build_contract_report,
    build_work_report,
)


REPORT_DATE = date(2026, 11, 10)


def make_contract() -> Contract:
    """Создаёт тестовый договор."""
    return Contract(
        contract_id="D-1",
        contractor="Подрядчик",
        amount=Decimal("200.00"),
        signed_at=date(2026, 1, 1),
    )


def make_work(
    work_id: str = "W-1",
    status: WorkStatus = WorkStatus.DONE,
    price: str = "100.00",
) -> Work:
    """Создаёт тестовую работу."""
    return Work(
        work_id=work_id,
        contract_id="D-1",
        title="Тестовая работа",
        price=Decimal(price),
        status=status,
        completed_at=date(2026, 2, 1),
    )


class ReportingServiceTests(unittest.TestCase):
    def test_work_report_contains_all_fields(self) -> None:
        """Отчёт по работам содержит все необходимые колонки."""
        work = make_work()

        allocation = AllocationResult(
            works=[
                WorkAllocation(
                    work=work,
                    direct_paid=Decimal("30.00"),
                    allocated_paid=Decimal("20.00"),
                    paid_total=Decimal("50.00"),
                    remaining=Decimal("50.00"),
                    overpayment=Decimal("0.00"),
                ),
            ],
            contracts=[],
        )

        rows = build_work_report(allocation, REPORT_DATE)

        self.assertEqual(
            rows,
            [
                {
                    "Дата отчёта": "2026-11-10",
                    "Договор": "D-1",
                    "Работа": "W-1",
                    "Название": "Тестовая работа",
                    "Статус работы": "done",
                    "Цена": "100.00",
                    "Прямая оплата": "30.00",
                    "Расчётное распределение": "20.00",
                    "Всего выплачено": "50.00",
                    "Осталось оплатить": "50.00",
                    "Переплата": "0.00",
                    "Финансовый статус": FinancialStatus.PARTIALLY_PAID.value,
                },
            ],
        )

    def test_work_report_formats_cancelled_work(self) -> None:
        """Для отменённой работы финансовые значения None отображаются пустыми."""
        work = make_work(status=WorkStatus.CANCELLED)

        allocation = AllocationResult(
            works=[
                WorkAllocation(
                    work=work,
                    direct_paid=Decimal("0.00"),
                    allocated_paid=Decimal("0.00"),
                    paid_total=Decimal("0.00"),
                    remaining=None,
                    overpayment=None,
                ),
            ],
            contracts=[],
        )

        rows = build_work_report(allocation, REPORT_DATE)

        self.assertEqual(rows[0]["Осталось оплатить"], "")
        self.assertEqual(rows[0]["Переплата"], "")
        self.assertEqual(
            rows[0]["Финансовый статус"],
            FinancialStatus.REQUIRES_CLARIFICATION.value,
        )

    def test_not_paid_status(self) -> None:
        """Работа без оплат получает статус «Не оплачено»."""
        work = make_work()

        allocation = AllocationResult(
            works=[
                WorkAllocation(
                    work=work,
                    direct_paid=Decimal("0.00"),
                    allocated_paid=Decimal("0.00"),
                    paid_total=Decimal("0.00"),
                    remaining=Decimal("100.00"),
                    overpayment=Decimal("0.00"),
                ),
            ],
            contracts=[],
        )

        rows = build_work_report(allocation, REPORT_DATE)

        self.assertEqual(
            rows[0]["Финансовый статус"],
            FinancialStatus.NOT_PAID.value,
        )

    def test_fully_paid_status(self) -> None:
        """Полностью оплаченная работа получает соответствующий статус."""
        work = make_work()

        allocation = AllocationResult(
            works=[
                WorkAllocation(
                    work=work,
                    direct_paid=Decimal("100.00"),
                    allocated_paid=Decimal("0.00"),
                    paid_total=Decimal("100.00"),
                    remaining=Decimal("0.00"),
                    overpayment=Decimal("0.00"),
                ),
            ],
            contracts=[],
        )

        rows = build_work_report(allocation, REPORT_DATE)

        self.assertEqual(
            rows[0]["Финансовый статус"],
            FinancialStatus.FULLY_PAID.value,
        )

    def test_overpaid_status(self) -> None:
        """Переплата по работе получает соответствующий статус."""
        work = make_work()

        allocation = AllocationResult(
            works=[
                WorkAllocation(
                    work=work,
                    direct_paid=Decimal("120.00"),
                    allocated_paid=Decimal("0.00"),
                    paid_total=Decimal("120.00"),
                    remaining=Decimal("0.00"),
                    overpayment=Decimal("20.00"),
                ),
            ],
            contracts=[],
        )

        rows = build_work_report(allocation, REPORT_DATE)

        self.assertEqual(
            rows[0]["Финансовый статус"],
            FinancialStatus.OVERPAID.value,
        )

    def test_contract_report_contains_all_fields(self) -> None:
        """Отчёт по договорам содержит финансовые итоги."""
        contract = make_contract()

        allocation = AllocationResult(
            works=[],
            contracts=[
                ContractAllocation(
                    contract=contract,
                    paid_total=Decimal("150.00"),
                    remaining=Decimal("50.00"),
                    overpayment=Decimal("0.00"),
                    unallocated=Decimal("10.00"),
                ),
            ],
        )

        rows = build_contract_report(allocation, REPORT_DATE)

        self.assertEqual(
            rows,
            [
                {
                    "Дата отчёта": "2026-11-10",
                    "Договор": "D-1",
                    "Подрядчик": "Подрядчик",
                    "Сумма договора": "200.00",
                    "Всего выплачено": "150.00",
                    "Осталось оплатить": "50.00",
                    "Переплата": "0.00",
                    "Нераспределено": "10.00",
                },
            ],
        )

    def test_empty_allocation_returns_empty_reports(self) -> None:
        """При отсутствии данных отчёты содержат пустые списки."""
        allocation = AllocationResult(
            works=[],
            contracts=[],
        )

        self.assertEqual(build_work_report(allocation, REPORT_DATE), [])
        self.assertEqual(build_contract_report(allocation, REPORT_DATE), [])


if __name__ == "__main__":
    unittest.main()
