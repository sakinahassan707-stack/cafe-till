"""Tests for persistence and reporting."""

from decimal import Decimal

import pytest

from cafe.order import Order
from cafe.storage import (
    best_sellers,
    connect,
    from_pence,
    load_order,
    recent_orders,
    revenue_total,
    save_order,
    to_pence,
)


@pytest.fixture
def conn():
    connection = connect(":memory:")
    yield connection
    connection.close()


def make_order(*pairs) -> Order:
    order = Order()
    for name, qty in pairs:
        order.add(name, qty)
    return order


class TestMoneyConversion:
    def test_round_trip(self):
        assert from_pence(to_pence(Decimal("3.20"))) == Decimal("3.20")

    def test_to_pence(self):
        assert to_pence(Decimal("12.80")) == 1280


class TestSaveAndLoad:
    def test_save_returns_id(self, conn):
        assert save_order(conn, make_order(("Latte", 2))) == 1

    def test_ids_increment(self, conn):
        save_order(conn, make_order(("Tea", 1)))
        assert save_order(conn, make_order(("Tea", 1))) == 2

    def test_cannot_save_empty_order(self, conn):
        with pytest.raises(ValueError):
            save_order(conn, Order())

    def test_round_trip_preserves_total(self, conn):
        original = make_order(("Latte", 2), ("Brownie", 1))
        order_id = save_order(conn, original)
        assert load_order(conn, order_id).total == original.total

    def test_round_trip_preserves_lines(self, conn):
        original = make_order(("Espresso", 3), ("Toastie", 1))
        loaded = load_order(conn, save_order(conn, original))
        assert [(l.item_name, l.quantity) for l in loaded.lines] == [
            (l.item_name, l.quantity) for l in original.lines
        ]

    def test_load_missing_order_returns_none(self, conn):
        assert load_order(conn, 999) is None

    def test_historical_price_survives_menu_change(self, conn):
        # the point of storing unit_price on the line
        order = Order()
        order.add("Latte", 1)
        order.lines[0].unit_price = Decimal("9.99")
        loaded = load_order(conn, save_order(conn, order))
        assert loaded.lines[0].unit_price == Decimal("9.99")


class TestReporting:
    def test_revenue_of_empty_db_is_zero(self, conn):
        assert revenue_total(conn) == Decimal("0.00")

    def test_revenue_sums_orders(self, conn):
        save_order(conn, make_order(("Latte", 2)))    # 6.40
        save_order(conn, make_order(("Brownie", 1)))  # 2.80
        assert revenue_total(conn) == Decimal("9.20")

    def test_best_sellers_ranks_by_units(self, conn):
        save_order(conn, make_order(("Tea", 5), ("Latte", 1)))
        save_order(conn, make_order(("Tea", 2)))
        top = best_sellers(conn)
        assert top[0]["item_name"] == "Tea"
        assert top[0]["units"] == 7

    def test_recent_orders_newest_first(self, conn):
        save_order(conn, make_order(("Tea", 1)))
        save_order(conn, make_order(("Latte", 1)))
        assert [r["id"] for r in recent_orders(conn)] == [2, 1]

    def test_recent_orders_respects_limit(self, conn):
        for _ in range(5):
            save_order(conn, make_order(("Tea", 1)))
        assert len(recent_orders(conn, limit=3)) == 3
