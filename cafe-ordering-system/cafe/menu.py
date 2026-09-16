"""The cafe menu: item definitions and lookup."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MenuItem:
    """A single item available for sale.

    Price is a Decimal, never a float. Floats cannot represent 0.10 exactly,
    so repeated addition of float prices drifts away from the true total.
    """

    name: str
    price: Decimal
    category: str


MENU: tuple[MenuItem, ...] = (
    MenuItem("Espresso", Decimal("2.20"), "Drinks"),
    MenuItem("Flat White", Decimal("3.10"), "Drinks"),
    MenuItem("Latte", Decimal("3.20"), "Drinks"),
    MenuItem("Cappuccino", Decimal("3.20"), "Drinks"),
    MenuItem("Tea", Decimal("2.00"), "Drinks"),
    MenuItem("Hot Chocolate", Decimal("3.40"), "Drinks"),
    MenuItem("Croissant", Decimal("2.60"), "Food"),
    MenuItem("Bacon Roll", Decimal("4.50"), "Food"),
    MenuItem("Toastie", Decimal("4.80"), "Food"),
    MenuItem("Soup of the Day", Decimal("5.20"), "Food"),
    MenuItem("Brownie", Decimal("2.80"), "Cakes"),
    MenuItem("Carrot Cake", Decimal("3.60"), "Cakes"),
)


class UnknownItemError(KeyError):
    """Raised when a requested item is not on the menu."""


def find_item(name: str) -> MenuItem:
    """Look up a menu item by name, ignoring case and surrounding whitespace.

    Raises UnknownItemError if there is no such item.
    """
    needle = name.strip().casefold()
    for item in MENU:
        if item.name.casefold() == needle:
            return item
    raise UnknownItemError(f"{name!r} is not on the menu")


def find_by_number(number: int) -> MenuItem:
    """Look up a menu item by its 1-based position, as shown in the CLI."""
    if not 1 <= number <= len(MENU):
        raise UnknownItemError(f"no menu item numbered {number}")
    return MENU[number - 1]


def categories() -> dict[str, list[tuple[int, MenuItem]]]:
    """Group the menu by category, keeping each item's 1-based menu number."""
    grouped: dict[str, list[tuple[int, MenuItem]]] = {}
    for position, item in enumerate(MENU, start=1):
        grouped.setdefault(item.category, []).append((position, item))
    return grouped
