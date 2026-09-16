"""Order logic.

Nothing in this module reads from stdin or writes to stdout. That is what
makes it testable: every function here is pure input to output, so the test
suite can exercise the validation rules without simulating a user typing.
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from .menu import MenuItem, find_item

MAX_QUANTITY = 99


class ValidationError(ValueError):
    """Raised when a quantity or item fails validation."""


def validate_quantity(raw: object) -> int:
    """Coerce and validate a quantity.

    Accepts an int or a string of digits. Rejects anything that is not a whole
    number, zero or below, or above MAX_QUANTITY. Booleans are rejected
    explicitly because bool subclasses int in Python, so True would otherwise
    sneak through as the quantity 1.
    """
    if isinstance(raw, bool):
        raise ValidationError("quantity must be a number, not a boolean")

    if isinstance(raw, int):
        quantity = raw
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            raise ValidationError("quantity cannot be blank")
        try:
            quantity = int(text)
        except ValueError:
            raise ValidationError(f"{raw!r} is not a whole number") from None
    else:
        raise ValidationError(f"{raw!r} is not a valid quantity")

    if quantity <= 0:
        raise ValidationError("quantity must be at least 1")
    if quantity > MAX_QUANTITY:
        raise ValidationError(f"quantity cannot exceed {MAX_QUANTITY}")
    return quantity


def money(amount: Decimal) -> Decimal:
    """Round a Decimal to two places, half up, the way cash registers do.

    Python's default rounding is banker's rounding, which rounds 2.675 down.
    A customer looking at a receipt expects it to round up.
    """
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class OrderLine:
    """One line of an order.

    unit_price is stored here rather than looked up from the menu at display
    time. If the cafe raises the price of a latte next month, every historical
    order would otherwise silently change value.
    """

    item_name: str
    unit_price: Decimal
    quantity: int

    @property
    def subtotal(self) -> Decimal:
        return money(self.unit_price * self.quantity)


@dataclass
class Order:
    """A basket of order lines."""

    lines: list[OrderLine] = field(default_factory=list)

    def add(self, item: MenuItem | str, quantity: object = 1) -> OrderLine:
        """Add an item to the order, merging with an existing line if present.

        Accepts either a MenuItem or an item name. Raises UnknownItemError for
        an unknown name and ValidationError for a bad quantity.
        """
        if isinstance(item, str):
            item = find_item(item)
        count = validate_quantity(quantity)

        for line in self.lines:
            if line.item_name == item.name:
                merged = validate_quantity(line.quantity + count)
                line.quantity = merged
                return line

        line = OrderLine(item.name, item.price, count)
        self.lines.append(line)
        return line

    def remove(self, item_name: str) -> None:
        """Remove every line for the given item. Unknown names are ignored."""
        needle = item_name.strip().casefold()
        self.lines = [ln for ln in self.lines if ln.item_name.casefold() != needle]

    def set_quantity(self, item_name: str, quantity: object) -> None:
        """Set an existing line to an exact quantity."""
        count = validate_quantity(quantity)
        for line in self.lines:
            if line.item_name.casefold() == item_name.strip().casefold():
                line.quantity = count
                return
        raise ValidationError(f"{item_name!r} is not in this order")

    def clear(self) -> None:
        self.lines.clear()

    @property
    def item_count(self) -> int:
        """Total number of physical items, not number of distinct lines."""
        return sum(line.quantity for line in self.lines)

    @property
    def total(self) -> Decimal:
        """Order total. An empty order totals 0.00, not an error."""
        return money(sum((line.subtotal for line in self.lines), Decimal("0")))

    def is_empty(self) -> bool:
        return not self.lines
