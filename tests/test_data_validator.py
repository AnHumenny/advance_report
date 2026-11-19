import unittest
from datetime import date
from decimal import Decimal

from app.domain.models import (
    Contract,
    Payment,
    PaymentStatus,
    Work,
    WorkStatus,
)
from app.validators.data_validator import validate_data


def make_contract(
    contract_id: str = "D-1",
    amount: str = "200.00",
    ) -> Contract:
    """Создаёт тестовый договор."""

    return Contract(
        contract_id=contract_id,
        contractor="Подрядчик",
        amount=Decimal(amount),
        signed_at=date(2026, 1, 1),
    )


def make_work(
    work_id: str = "W-1",
    contract_id: str = "D-1",
    price: str = "100.00",
    status: WorkStatus = WorkStatus.PLANNED,
    completed_at: date | None = None,
    cancelled_at: date | None = None,
) -> Work:
    """Создаёт тестовую работу."""

    return Work(
        work_id=work_id,
        contract_id=contract_id,
        title=f"Работа {work_id}",
        price=Decimal(price),
        status=status,
        completed_at=completed_at,
        cancelled_at=cancelled_at,
    )


def make_payment(
    payment_id: str = "P-1",
    contract_id: str = "D-1",
    work_id: str | None = None,
    amount: str = "50.00",
    status: PaymentStatus = PaymentStatus.PAID,
    created_at: date = date(2026, 10, 1),
    paid_at: date | None = date(2026, 10, 5),
    refunded_at: date | None = None,
) -> Payment:
    """Создаёт тестовый платёж."""

    return Payment(
        payment_id=payment_id,
        contract_id=contract_id,
        work_id=work_id,
        purpose="Оплата",
        amount=Decimal(amount),
        status=status,
        created_at=created_at,
        paid_at=paid_at,
        refunded_at=refunded_at,
    )


class DataValidatorTests(unittest.TestCase):

    def test_valid_data_has_no_errors(self) -> None:
        """Корректные исходные данные проходят проверку."""

        result = validate_data(
            contracts=[make_contract(amount="200.00")],
            works=[
                make_work("W-1", price="100.00"),
                make_work("W-2", price="100.00"),
            ],
            payments=[make_payment()],
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])


    def test_duplicate_contract_id_is_error(self) -> None:
        """Повторяющийся ID договора считается ошибкой."""

        result = validate_data(
            contracts=[
                make_contract(),
                make_contract(),
            ],
            works=[],
            payments=[],
        )

        self.assertFalse(result.is_valid)
        self.assertTrue(
            any("Повторяющийся ID договоров: D-1" in error
                for error in result.errors)
        )

    def test_duplicate_work_id_is_error(self) -> None:
        """Повторяющийся ID работы считается ошибкой."""

        result = validate_data(
            contracts=[make_contract()],
            works=[
                make_work("W-1"),
                make_work("W-1"),
            ],
            payments=[],
        )

        self.assertTrue(
            any("Повторяющийся ID работ: W-1" in error
                for error in result.errors)
        )

    def test_duplicate_payment_id_is_error(self) -> None:
        """Повторяющийся ID платежа считается ошибкой."""

        result = validate_data(
            contracts=[make_contract()],
            works=[],
            payments=[
                make_payment(),
                make_payment(),
            ],
        )

        self.assertTrue(
            any("Повторяющийся ID платежей: P-1" in error
                for error in result.errors)
        )

    def test_negative_contract_amount_is_error(self) -> None:
        """Отрицательная сумма договора считается ошибкой."""

        result = validate_data(
            contracts=[make_contract(amount="-100.00")],
            works=[],
            payments=[],
        )

        self.assertTrue(
            any("отрицательная сумма" in error
                for error in result.errors)
        )

    def test_negative_work_price_is_error(self) -> None:
        """Отрицательная стоимость работы считается ошибкой."""

        result = validate_data(
            contracts=[make_contract()],
            works=[make_work(price="-10.00")],
            payments=[],
        )

        self.assertTrue(
            any("отрицательная цена" in error
                for error in result.errors)
        )

    def test_negative_payment_amount_is_error(self) -> None:
        """Отрицательная сумма платежа считается ошибкой."""

        result = validate_data(
            contracts=[make_contract()],
            works=[],
            payments=[make_payment(amount="-10.00")],
        )

        self.assertTrue(
            any("отрицательная сумма" in error
                for error in result.errors)
        )

    def test_work_without_contract_is_error(self) -> None:
        """Работа со ссылкой на отсутствующий договор вызывает ошибку."""

        result = validate_data(
            contracts=[make_contract()],
            works=[make_work(contract_id="D-999")],
            payments=[],
        )

        self.assertTrue(
            any("не найден договор D-999" in error
                for error in result.errors)
        )

    def test_payment_without_contract_is_error(self) -> None:
        """Платёж со ссылкой на отсутствующий договор вызывает ошибку."""

        result = validate_data(
            contracts=[make_contract()],
            works=[],
            payments=[make_payment(contract_id="D-999")],
        )

        self.assertTrue(
            any("не найден договор D-999" in error
                for error in result.errors)
        )

    def test_payment_without_work_is_allowed(self) -> None:
        """Платёж без привязки к работе допустим."""

        result = validate_data(
            contracts=[make_contract()],
            works=[make_work("W-1"), make_work("W-2")],
            payments=[make_payment(work_id=None)],
        )

        self.assertTrue(result.is_valid)

    def test_payment_linked_to_missing_work_is_error(self) -> None:
        """Платёж со ссылкой на отсутствующую работу вызывает ошибку."""

        result = validate_data(
            contracts=[make_contract()],
            works=[],
            payments=[make_payment(work_id="W-999")],
        )

        self.assertTrue(
            any("не найдена работа W-999" in error
                for error in result.errors)
        )

    def test_payment_linked_to_another_contract_is_error(self) -> None:
        """Работа и платёж должны относиться к одному договору."""

        result = validate_data(
            contracts=[
                make_contract("D-1"),
                make_contract("D-2"),
            ],
            works=[
                make_work("W-1", contract_id="D-1"),
            ],
            payments=[
                make_payment(
                    contract_id="D-2",
                    work_id="W-1",
                ),
            ],
        )

        self.assertTrue(
            any("относится к другому договору" in error
                for error in result.errors)
        )

    def test_done_work_requires_completed_date(self) -> None:
        """У выполненной работы должна быть дата завершения."""

        result = validate_data(
            contracts=[make_contract()],
            works=[
                make_work(status=WorkStatus.DONE),
            ],
            payments=[],
        )

        self.assertTrue(
            any("отсутствует completed_at" in error
                for error in result.errors)
        )

    def test_cancelled_work_requires_cancelled_date(self) -> None:
        """У отменённой работы должна быть дата отмены."""

        result = validate_data(
            contracts=[make_contract()],
            works=[
                make_work(status=WorkStatus.CANCELLED),
            ],
            payments=[],
        )

        self.assertTrue(
            any("отсутствует cancelled_at" in error
                for error in result.errors)
        )

    def test_queued_payment_cannot_have_paid_date(self) -> None:
        """У платежа в очереди не должно быть даты оплаты."""

        result = validate_data(
            contracts=[make_contract()],
            works=[],
            payments=[
                make_payment(
                    status=PaymentStatus.QUEUED,
                    paid_at=date(2026, 10, 5),
                ),
            ],
        )

        self.assertTrue(
            any("статус queued" in error
                for error in result.errors)
        )

    def test_paid_payment_requires_paid_date(self) -> None:
        """У оплаченного платежа должна быть дата оплаты."""

        result = validate_data(
            contracts=[make_contract()],
            works=[],
            payments=[
                make_payment(
                    status=PaymentStatus.PAID,
                    paid_at=None,
                ),
            ],
        )

        self.assertTrue(
            any("отсутствует paid_at" in error
                for error in result.errors)
        )

    def test_refunded_payment_requires_refund_date(self) -> None:
        """У возвращённого платежа должна быть дата возврата."""

        result = validate_data(
            contracts=[make_contract()],
            works=[],
            payments=[
                make_payment(
                    status=PaymentStatus.REFUNDED,
                    refunded_at=None,
                ),
            ],
        )

        self.assertTrue(
            any("статус refunded" in error
                for error in result.errors)
        )

    def test_payment_date_cannot_precede_creation_date(self) -> None:
        """Дата оплаты не может быть раньше даты создания платежа."""

        result = validate_data(
            contracts=[make_contract()],
            works=[],
            payments=[
                make_payment(
                    created_at=date(2026, 10, 10),
                    paid_at=date(2026, 10, 5),
                ),
            ],
        )

        self.assertTrue(
            any("дата оплаты раньше даты создания" in error
                for error in result.errors)
        )

    def test_refund_date_cannot_precede_payment_date(self) -> None:
        """Дата возврата не может быть раньше даты оплаты."""

        result = validate_data(
            contracts=[make_contract()],
            works=[],
            payments=[
                make_payment(
                    status=PaymentStatus.REFUNDED,
                    paid_at=date(2026, 10, 10),
                    refunded_at=date(2026, 10, 5),
                ),
            ],
        )

        self.assertTrue(
            any("дата возврата раньше даты оплаты" in error
                for error in result.errors)
        )

    def test_payment_to_cancelled_work_is_warning(self) -> None:
        """Платёж по отменённой работе вызывает предупреждение, а не ошибку."""

        result = validate_data(
            contracts=[make_contract(amount="100.00")],
            works=[
                make_work(
                    status=WorkStatus.CANCELLED,
                    cancelled_at=date(2026, 10, 5),
                ),
            ],
            payments=[
                make_payment(work_id="W-1"),
            ],
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("отменённой работе W-1", result.warnings[0])

    def test_contract_amount_mismatch_is_warning(self) -> None:
        """Несовпадение суммы работ и договора вызывает предупреждение."""

        result = validate_data(
            contracts=[make_contract(amount="300.00")],
            works=[
                make_work("W-1", price="100.00"),
                make_work("W-2", price="100.00"),
            ],
            payments=[],
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertTrue(
            any("сумма работ 200.00 ₽" in warning
                for warning in result.warnings)
        )

    def test_non_finite_amount_is_error(self) -> None:
        """NaN и Infinity не допускаются в денежных значениях."""

        result = validate_data(
            contracts=[make_contract(amount="NaN")],
            works=[],
            payments=[],
        )

        self.assertTrue(
            any("NaN или Infinity" in error
                for error in result.errors)
        )


if __name__ == "__main__":
    unittest.main()
