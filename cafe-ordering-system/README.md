# Cafe Ordering System

A command line ordering system for a cafe, with a priced menu, validated input,
SQLite persistence and a sales report.

## Running it

```bash
python -m cafe.cli                 # interactive ordering
python -m cafe.cli --report        # revenue and best sellers
python -m cafe.cli --order 3       # reprint a saved order
python -m cafe.cli --db test.db    # use a different database file
```

No dependencies beyond the standard library. `pytest` is needed only for the tests.

```bash
pip install pytest
python -m pytest
```

## Structure

| Module | Responsibility |
|---|---|
| `cafe/menu.py` | Menu items, prices, lookup by name or number |
| `cafe/order.py` | Basket logic, quantity validation, totals |
| `cafe/storage.py` | SQLite schema, saving, loading, reporting queries |
| `cafe/cli.py` | Every `input()` and `print()` in the project |

The split matters: `order.py` never touches stdin or stdout, which is what lets
the test suite exercise the validation rules directly rather than simulating a
user typing. Without that separation none of the logic would be testable.

## Design decisions

**Prices are snapshotted onto each order line.** `order_items` stores its own
`unit_price_pence` rather than referencing the menu. If the cafe raises the
price of a latte next month, every historical order would otherwise silently
change value, and last month's revenue figure would no longer match the receipts
that were printed.

**Money is `Decimal` in memory and integer pence in the database.** Floats
cannot represent 0.10 exactly, so adding float prices drifts. SQLite has no
decimal type, and storing pounds as `REAL` would reintroduce the same problem,
so the database holds whole pence.

**Rounding is half up, not banker's rounding.** Python's default rounds 2.675
down to 2.67. A customer reading a receipt expects it to go up.

**Saving an order is one transaction.** A failure part way through cannot leave
an order header in the database with no lines attached to it.

**Booleans are rejected as quantities.** `bool` subclasses `int` in Python, so
`True` would otherwise be silently accepted as the quantity 1.

## Tests

42 tests across two files. `tests/test_order.py` covers validation edge cases
(zero, negative, blank, non-numeric, decimal strings, above the cap, booleans)
and order arithmetic including line merging and empty order totals.
`tests/test_storage.py` runs against an in-memory database and covers the save
and load round trip, the price snapshot behaviour, and the reporting queries.

## Things I would change next

- Concurrent access: SQLite locks the whole file on write, which is fine for one
  till and wrong for several.
- The menu is hardcoded. It belongs in the database with an effective date per
  price, which would also make the snapshot question moot.
- No refunds or voids, so revenue only ever goes up.
