"""SQLite persistence for completed orders.

Two tables. `orders` holds one row per completed order, `order_items` holds
one row per line. The line rows carry their own unit_price so that a later
menu price change cannot rewrite the value of an order already taken.
"""

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .order import Order, OrderLine

DEFAULT_DB = Path("cafe.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    placed_at   TEXT    NOT NULL,
    total_pence INTEGER NOT NULL CHECK (total_pence >= 0)
);

CREATE TABLE IF NOT EXISTS order_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    item_name       TEXT    NOT NULL,
    unit_price_pence INTEGER NOT NULL CHECK (unit_price_pence >= 0),
    quantity        INTEGER NOT NULL CHECK (quantity > 0)
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
"""


def to_pence(amount: Decimal) -> int:
    """Store money as whole pence.

    SQLite has no decimal type, and storing pounds as REAL reintroduces the
    float rounding problem the Decimal work was avoiding. Integers of the
    smallest currency unit sidestep it entirely.
    """
    return int(amount * 100)


def from_pence(pence: int) -> Decimal:
    return (Decimal(pence) / 100).quantize(Decimal("0.01"))


def connect(path: Path | str = DEFAULT_DB) -> sqlite3.Connection:
    """Open a connection and make sure the schema exists."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def save_order(conn: sqlite3.Connection, order: Order) -> int:
    """Persist a completed order and return its new id.

    The whole thing runs in one transaction, so a failure part way through
    cannot leave an order header with no lines attached to it.
    """
    if order.is_empty():
        raise ValueError("cannot save an empty order")

    placed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:
        cursor = conn.execute(
            "INSERT INTO orders (placed_at, total_pence) VALUES (?, ?)",
            (placed_at, to_pence(order.total)),
        )
        order_id = cursor.lastrowid
        conn.executemany(
            "INSERT INTO order_items (order_id, item_name, unit_price_pence, quantity)"
            " VALUES (?, ?, ?, ?)",
            [
                (order_id, ln.item_name, to_pence(ln.unit_price), ln.quantity)
                for ln in order.lines
            ],
        )
    return order_id


def load_order(conn: sqlite3.Connection, order_id: int) -> Order | None:
    """Rebuild a saved order from the database, or None if it does not exist."""
    header = conn.execute("SELECT id FROM orders WHERE id = ?", (order_id,)).fetchone()
    if header is None:
        return None

    rows = conn.execute(
        "SELECT item_name, unit_price_pence, quantity FROM order_items"
        " WHERE order_id = ? ORDER BY id",
        (order_id,),
    ).fetchall()

    order = Order()
    order.lines = [
        OrderLine(r["item_name"], from_pence(r["unit_price_pence"]), r["quantity"])
        for r in rows
    ]
    return order


def recent_orders(conn: sqlite3.Connection, limit: int = 10) -> list[sqlite3.Row]:
    """The most recent orders, newest first."""
    return conn.execute(
        "SELECT id, placed_at, total_pence FROM orders ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()


def revenue_total(conn: sqlite3.Connection) -> Decimal:
    """Sum of every order ever taken."""
    row = conn.execute("SELECT COALESCE(SUM(total_pence), 0) AS t FROM orders").fetchone()
    return from_pence(row["t"])


def best_sellers(conn: sqlite3.Connection, limit: int = 5) -> list[sqlite3.Row]:
    """Top items by units sold, with the revenue each has brought in."""
    return conn.execute(
        """
        SELECT item_name,
               SUM(quantity)                        AS units,
               SUM(quantity * unit_price_pence)     AS revenue_pence
        FROM order_items
        GROUP BY item_name
        ORDER BY units DESC, revenue_pence DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
