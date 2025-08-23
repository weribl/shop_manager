"""
models.py — классы данных для интернет-магазина.

Содержит:
- ValidationError — исключение валидации;
- Customer/Person — наследование для демонстрации ООП;
- Product/DiscountedProduct — наследование + полиморфизм (переопределение to_dict/price);
- Order/OrderItem — заказ и позиции;
- quicksort_orders — рекурсивная сортировка заказов.

Докстринги оформлены в стиле numpydoc.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
import re

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\+?[0-9\s\-()]{7,}$")


class ValidationError(ValueError):
    """Ошибка валидации входных данных (email/телефон/количество и т.п.)."""


class BaseModel:
    """Базовый класс для сериализации.

    Notes
    -----
    Метод :meth:`to_dict` может быть переопределён в наследниках (полиморфизм).
    """
    def to_dict(self) -> Dict[str, Any]:
        """Вернуть словарь (по умолчанию — dataclasses.asdict)."""
        return asdict(self)  # type: ignore


@dataclass
class Person(BaseModel):
    """Простой базовый класс для людей (показывает наследование)."""
    name: str


@dataclass
class Customer(Person):
    """Клиент интернет-магазина.

    Parameters
    ----------
    name : str
        Полное имя клиента.
    email : str
        Почта (проверяется по регулярному выражению).
    phone : str
        Телефон (проверяется по регулярному выражению).
    city : str, optional
        Город для аналитики по географии.
    id : int, optional
        Идентификатор базы данных.
    """
    email: str
    phone: str
    city: str = "Unknown"
    id: Optional[int] = None

    def __post_init__(self) -> None:
        if not EMAIL_RE.match(self.email):
            raise ValidationError(f"Некорректный email: {self.email}")
        if not PHONE_RE.match(self.phone):
            raise ValidationError(f"Некорректный номер телефона: {self.phone}")


@dataclass
class Product(BaseModel):
    """Товар каталога."""
    name: str
    price: float
    sku: str
    id: Optional[int] = None

    def __post_init__(self) -> None:
        if self.price < 0:
            raise ValidationError("Цена не может быть отрицательной")


@dataclass
class DiscountedProduct(Product):
    """Товар со скидкой (наследник Product)."""
    discount_pct: float = 0.0

    @property
    def final_price(self) -> float:
        """Итоговая цена с учётом скидки (инкапсуляция через property)."""
        pct = max(0.0, min(100.0, self.discount_pct))
        return round(self.price * (1 - pct / 100.0), 2)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["final_price"] = self.final_price
        return d


@dataclass
class OrderItem(BaseModel):
    """Позиция заказа (товар/количество/цена)."""
    product_id: int
    quantity: int
    unit_price: float

    def subtotal(self) -> float:
        """Промежуточная сумма по строке."""
        return round(self.quantity * self.unit_price, 2)


@dataclass
class Order(BaseModel):
    """Заказ клиента."""
    customer_id: int
    created_at: datetime
    items: List[OrderItem] = field(default_factory=list)
    status: str = "new"
    id: Optional[int] = None

    def total(self) -> float:
        """Итог заказа (сумма всех позиций)."""
        return round(sum(i.subtotal() for i in self.items), 2)

    def add_item(self, item: OrderItem) -> None:
        """Добавить позицию заказа с базовой валидацией."""
        if item.quantity <= 0:
            raise ValidationError("Количество должно быть положительным")
        self.items.append(item)


# ===== Алгоритмы (рекурсия, лямбда) =====
def quicksort_orders(orders: List[Order], key: Callable[[Order], Any]) -> List[Order]:
    """Рекурсивная сортировка заказов (quicksort).

    Parameters
    ----------
    orders : list of Order
        Список для сортировки.
    key : callable
        Ключ сортировки (можно передать лямбду).

    Returns
    -------
    list of Order
        Отсортированный список.
    """
    if len(orders) <= 1:
        return orders[:]
    pivot = orders[len(orders)//2]
    pk = key(pivot)
    left = [o for o in orders if key(o) < pk]
    mid = [o for o in orders if key(o) == pk]
    right = [o for o in orders if key(o) > pk]
    return quicksort_orders(left, key) + mid + quicksort_orders(right, key)
