"""Tests for validation and order arithmetic."""

from decimal import Decimal

import pytest

from cafe.menu import UnknownItemError, find_item
from cafe.order import MAX_QUANTITY, Order, ValidationError, validate_quantity


class TestValidateQuantity:
    def test_accepts_positive_int(self):
        assert validate_quantity(3) == 3

    def test_accepts_numeric_string(self):
        assert validate_quantity("7") == 7

    def test_strips_whitespace(self):
        assert validate_quantity("  4  ") == 4

    def test_rejects_zero(self):
        with pytest.raises(ValidationError):
            validate_quantity(0)

    def test_rejects_negative(self):
        with pytest.raises(ValidationError):
            validate_quantity(-2)

    def test_rejects_blank(self):
        with pytest.raises(ValidationError):
            validate_quantity("   ")

    def test_rejects_non_numeric(self):
        with pytest.raises(ValidationError):
            validate_quantity("two")

    def test_rejects_decimal_string(self):
        with pytest.raises(ValidationError):
            validate_quantity("1.5")

    def test_rejects_above_max(self):
        with pytest.raises(ValidationError):
            validate_quantity(MAX_QUANTITY + 1)

    def test_accepts_exactly_max(self):
        assert validate_quantity(MAX_QUANTITY) == MAX_QUANTITY

    def test_rejects_bool(self):
        # bool subclasses int, so True would otherwise pass as quantity 1
        with pytest.raises(ValidationError):
            validate_quantity(True)

    def test_rejects_none(self):
        with pytest.raises(ValidationError):
            validate_quantity(None)


class TestOrder:
    def test_empty_order_totals_zero(self):
        assert Order().total == Decimal("0.00")

    def test_empty_order_is_empty(self):
        assert Order().is_empty()

    def test_add_by_name(self):
        order = Order()
        order.add("Latte", 2)
        assert order.total == Decimal("6.40")

    def test_add_is_case_insensitive(self):
        order = Order()
        order.add("lAtTe", 1)
        assert order.lines[0].item_name == "Latte"

    def test_add_unknown_item_raises(self):
        with pytest.raises(UnknownItemError):
            Order().add("Unicorn Frappe", 1)

    def test_add_bad_quantity_raises(self):
        with pytest.raises(ValidationError):
            Order().add("Latte", 0)

    def test_repeat_item_merges_into_one_line(self):
        order = Order()
        order.add("Tea", 1)
        order.add("Tea", 2)
        assert len(order.lines) == 1
        assert order.lines[0].quantity == 3

    def test_merge_respecting_max_quantity(self):
        order = Order()
        order.add("Tea", MAX_QUANTITY)
        with pytest.raises(ValidationError):
            order.add("Tea", 1)

    def test_mixed_order_total(self):
        order = Order()
        order.add("Espresso", 2)   # 4.40
        order.add("Brownie", 3)    # 8.40
        assert order.total == Decimal("12.80")

    def test_item_count_counts_units_not_lines(self):
        order = Order()
        order.add("Tea", 4)
        order.add("Croissant", 2)
        assert order.item_count == 6
        assert len(order.lines) == 2

    def test_remove_drops_line(self):
        order = Order()
        order.add("Tea", 1)
        order.remove("Tea")
        assert order.is_empty()

    def test_remove_unknown_is_silent(self):
        order = Order()
        order.add("Tea", 1)
        order.remove("Nonsense")
        assert len(order.lines) == 1

    def test_set_quantity(self):
        order = Order()
        order.add("Latte", 1)
        order.set_quantity("Latte", 5)
        assert order.lines[0].quantity == 5

    def test_set_quantity_unknown_raises(self):
        with pytest.raises(ValidationError):
            Order().set_quantity("Latte", 2)

    def test_line_price_is_snapshotted(self):
        order = Order()
        order.add("Latte", 1)
        assert order.lines[0].unit_price == find_item("Latte").price

    def test_clear(self):
        order = Order()
        order.add("Tea", 2)
        order.clear()
        assert order.is_empty()
