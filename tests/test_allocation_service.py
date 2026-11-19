from datetime import date
from decimal import Decimal
import unittest

from app.domain.models import (
    Contract,
    Payment,
    PaymentStatus,
    Work,
    WorkStatus,
)
from app.services.allocation_service import allocate_payments


REPORT_DATE = date(2026, 11, 10)


def make_contract(amount: str = "300.00") -> Contract:
    return Contract(
        contract_id="D-1",
        contractor="Подрядчик",
        amount=Decimal(amount),
        signed_at=date(2026, 1, 1),
    )


def make_work(
    work_id: str,
    price: str = "100.00",
    status: WorkStatus = WorkStatus.PLANNED,
) -> Work:
    return Work(
        work_id=work_id,
        contract_id="D-1",
        title=f"Работа {work_id}",
        price=Decimal(price),
        status=status,
    )


def make_payment(
    payment_id: str,
    amount: str,
    work_id: str | None = None,
    status: PaymentStatus = PaymentStatus.PAID,
    paid_at: date | None = date(2026, 11, 1),
    refunded_at: date | None = None,
) -> Payment:
    return Payment(
        payment_id=payment_id,
        contract_id="D-1",
        work_id=work_id,
        purpose="Оплата",
        amount=Decimal(amount),
        status=status,
        created_at=date(2026, 10, 1),
        paid_at=paid_at,
        refunded_at=refunded_at,
    )


class AllocationServiceTests(unittest.TestCase):

    def test_common_payment_is_allocated_fifo(self) -> None:
        """Общий платёж распределяется в порядке работ."""

        result = allocate_payments(
            contracts=[make_contract()],
            works=[
                make_work("W-1"),
                make_work("W-2"),
            ],
            payments=[
                make_payment("P-1", "150.00"),
            ],
            report_date=REPORT_DATE,
        )

        self.assertEqual(result.works[0].allocated_paid, Decimal("100.00"))
        self.assertEqual(result.works[1].allocated_paid, Decimal("50.00"))

    def test_direct_payment_is_allocated_before_common_payment(self) -> None:
        """Прямая оплата учитывается раньше общего аванса."""

        result = allocate_payments(
            contracts=[make_contract()],
            works=[
                make_work("W-1"),
                make_work("W-2"),
            ],
            payments=[
                make_payment("P-1", "30.00", work_id="W-1"),
                make_payment("P-2", "80.00"),
            ],
            report_date=REPORT_DATE,
        )

        self.assertEqual(result.works[0].direct_paid, Decimal("30.00"))
        self.assertEqual(result.works[0].allocated_paid, Decimal("70.00"))
        self.assertEqual(result.works[1].allocated_paid, Decimal("10.00"))

    def test_common_payment_does_not_exceed_work_price(self) -> None:
        """Общий платёж не превышает стоимость работы."""

        result = allocate_payments(
            contracts=[make_contract()],
            works=[make_work("W-1")],
            payments=[
                make_payment("P-1", "150.00"),
            ],
            report_date=REPORT_DATE,
        )

        work = result.works[0]

        self.assertEqual(work.paid_total, Decimal("100.00"))
        self.assertEqual(work.remaining, Decimal("0.00"))
        self.assertEqual(result.contracts[0].unallocated, Decimal("50.00"))

    def test_direct_overpayment_is_not_transferred_to_other_works(self) -> None:
        """Переплата по прямому платежу не переносится на другие работы."""

        result = allocate_payments(
            contracts=[make_contract()],
            works=[
                make_work("W-1"),
                make_work("W-2"),
            ],
            payments=[
                make_payment("P-1", "120.00", work_id="W-1"),
            ],
            report_date=REPORT_DATE,
        )

        self.assertEqual(result.works[0].overpayment, Decimal("20.00"))
        self.assertEqual(result.works[1].paid_total, Decimal("0.00"))

    def test_queued_payment_is_not_counted(self) -> None:
        """Платёж в очереди не считается выплаченным."""

        result = allocate_payments(
            contracts=[make_contract()],
            works=[make_work("W-1")],
            payments=[
                make_payment(
                    "P-1",
                    "100.00",
                    status=PaymentStatus.QUEUED,
                ),
            ],
            report_date=REPORT_DATE,
        )

        self.assertEqual(result.works[0].paid_total, Decimal("0.00"))
        self.assertEqual(result.contracts[0].paid_total, Decimal("0.00"))

    def test_future_payment_is_not_counted(self) -> None:
        """Оплата после даты отчёта не учитывается."""

        result = allocate_payments(
            contracts=[make_contract()],
            works=[make_work("W-1")],
            payments=[
                make_payment(
                    "P-1",
                    "100.00",
                    paid_at=date(2026, 11, 15),
                ),
            ],
            report_date=REPORT_DATE,
        )

        self.assertEqual(result.works[0].paid_total, Decimal("0.00"))

    def test_refunded_payment_is_excluded_after_refund_date(self) -> None:
        """Возвращённый платёж не учитывается после даты возврата."""

        result = allocate_payments(
            contracts=[make_contract()],
            works=[make_work("W-1")],
            payments=[
                make_payment(
                    "P-1",
                    "100.00",
                    status=PaymentStatus.REFUNDED,
                    refunded_at=date(2026, 11, 5),
                ),
            ],
            report_date=REPORT_DATE,
        )

        self.assertEqual(result.works[0].paid_total, Decimal("0.00"))

    def test_payment_refunded_after_report_date_is_counted(self) -> None:
        """Возврат после даты отчёта не отменяет прежнюю оплату."""

        result = allocate_payments(
            contracts=[make_contract()],
            works=[make_work("W-1")],
            payments=[
                make_payment(
                    "P-1",
                    "100.00",
                    status=PaymentStatus.REFUNDED,
                    refunded_at=date(2026, 11, 15),
                ),
            ],
            report_date=REPORT_DATE,
        )

        self.assertEqual(result.works[0].paid_total, Decimal("100.00"))

    def test_cancelled_work_is_skipped_by_fifo(self) -> None:
        """Отменённая работа не участвует в распределении общего аванса."""

        result = allocate_payments(
            contracts=[make_contract()],
            works=[
                make_work("W-1", status=WorkStatus.CANCELLED),
                make_work("W-2"),
            ],
            payments=[
                make_payment("P-1", "100.00"),
            ],
            report_date=REPORT_DATE,
        )

        self.assertIsNone(result.works[0].remaining)
        self.assertIsNone(result.works[0].overpayment)
        self.assertEqual(result.works[1].allocated_paid, Decimal("100.00"))

    def test_unallocated_amount_is_preserved(self) -> None:
        """Неиспользованный остаток общего платежа сохраняется."""

        result = allocate_payments(
            contracts=[make_contract()],
            works=[make_work("W-1")],
            payments=[
                make_payment("P-1", "150.00"),
            ],
            report_date=REPORT_DATE,
        )

        self.assertEqual(result.contracts[0].paid_total, Decimal("150.00"))
        self.assertEqual(result.contracts[0].unallocated, Decimal("50.00"))
        self.assertEqual(result.contracts[0].overpayment, Decimal("0.00"))


if __name__ == "__main__":
    unittest.main()
