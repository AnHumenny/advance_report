from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class WorkStatus(str, Enum):
    """Статусы выполнения работ."""

    PLANNED = "planned"
    DONE = "done"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Статусы платежей."""

    PAID = "paid"
    QUEUED = "queued"
    REFUNDED = "refunded"


@dataclass(frozen=True, slots=True)
class Contract:
    """Договор с подрядчиком."""

    contract_id: str
    contractor: str
    amount: Decimal
    signed_at: date


@dataclass(frozen=True, slots=True)
class Work:
    """Работа, входящая в договор."""

    work_id: str
    contract_id: str
    title: str
    price: Decimal
    status: WorkStatus
    completed_at: date | None = None
    cancelled_at: date | None = None


@dataclass(frozen=True, slots=True)
class Payment:
    """Платёж по договору или отдельной работе."""

    payment_id: str
    contract_id: str
    work_id: str | None
    purpose: str
    amount: Decimal
    status: PaymentStatus
    created_at: date
    paid_at: date | None = None
    refunded_at: date | None = None


class FinancialStatus(str, Enum):
    """Финансовые статусы оплаты работ."""

    NOT_PAID = "Не оплачено"
    PARTIALLY_PAID = "Оплачено частично"
    FULLY_PAID = "Оплачено полностью"
    OVERPAID = "Переплата"
    REQUIRES_CLARIFICATION = "Требует уточнения"
