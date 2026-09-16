"""Command line interface. All input and output lives here."""

import argparse
from decimal import Decimal

from .menu import UnknownItemError, categories, find_by_number, find_item
from .order import Order, ValidationError, validate_quantity
from .storage import (
    best_sellers,
    connect,
    from_pence,
    load_order,
    recent_orders,
    revenue_total,
    save_order,
)

RULE = "=" * 46


def show_menu() -> None:
    print("\n" + RULE)
    print("MENU".center(46))
    print(RULE)
    for category, entries in categories().items():
        print(f"\n{category}")
        for number, item in entries:
            print(f"  {number:>2}. {item.name:<20} £{item.price:>5}")
    print()


def show_order(order: Order) -> None:
    if order.is_empty():
        print("\nYour order is empty.\n")
        return
    print("\n" + RULE)
    print("YOUR ORDER".center(46))
    print(RULE)
    for line in order.lines:
        label = f"{line.quantity} x {line.item_name}"
        print(f"  {label:<32} £{line.subtotal:>7}")
    print("-" * 46)
    print(f"  {'TOTAL (' + str(order.item_count) + ' items)':<32} £{order.total:>7}")
    print(RULE + "\n")


def prompt_add(order: Order) -> None:
    """Ask for an item and quantity, and add it to the order."""
    raw_item = input("Item number or name (blank to cancel): ").strip()
    if not raw_item:
        return

    try:
        item = find_by_number(int(raw_item)) if raw_item.isdigit() else find_item(raw_item)
    except (UnknownItemError, ValueError) as exc:
        print(f"  ! {exc}")
        return

    raw_quantity = input(f"Quantity of {item.name} [1]: ").strip() or "1"
    try:
        quantity = validate_quantity(raw_quantity)
    except ValidationError as exc:
        print(f"  ! {exc}")
        return

    line = order.add(item, quantity)
    print(f"  Added. {line.quantity} x {line.item_name} = £{line.subtotal}")


def prompt_remove(order: Order) -> None:
    if order.is_empty():
        print("  ! Nothing to remove.")
        return
    name = input("Item name to remove: ").strip()
    before = len(order.lines)
    order.remove(name)
    if len(order.lines) == before:
        print(f"  ! {name!r} is not in your order.")
    else:
        print(f"  Removed {name}.")


def checkout(order: Order, db_path: str) -> bool:
    if order.is_empty():
        print("  ! Cannot check out an empty order.")
        return False
    show_order(order)
    if input("Confirm order? [y/N]: ").strip().casefold() != "y":
        print("  Cancelled.")
        return False
    with connect(db_path) as conn:
        order_id = save_order(conn, order)
    print(f"\n  Order #{order_id} saved. Total £{order.total}. Thank you.\n")
    order.clear()
    return True


def run_report(db_path: str) -> None:
    conn = connect(db_path)
    print("\n" + RULE)
    print("SALES REPORT".center(46))
    print(RULE)
    print(f"\n  Total revenue: £{revenue_total(conn)}")

    rows = best_sellers(conn)
    if rows:
        print("\n  Best sellers")
        for row in rows:
            revenue = from_pence(row["revenue_pence"])
            print(f"    {row['item_name']:<22} {row['units']:>4} sold   £{revenue:>8}")

    recent = recent_orders(conn, limit=5)
    if recent:
        print("\n  Recent orders")
        for row in recent:
            total = from_pence(row["total_pence"])
            print(f"    #{row['id']:<5} {row['placed_at']}   £{total:>7}")
    print()
    conn.close()


def show_saved_order(db_path: str, order_id: int) -> None:
    conn = connect(db_path)
    order = load_order(conn, order_id)
    conn.close()
    if order is None:
        print(f"  ! No order #{order_id}.")
        return
    print(f"\nOrder #{order_id}")
    show_order(order)


MENU_TEXT = """
  1  Show menu
  2  Add item
  3  Remove item
  4  View order
  5  Checkout
  6  Sales report
  q  Quit
"""


def interactive(db_path: str) -> None:
    order = Order()
    print("\nCafe ordering system. Type the number of an action.")
    while True:
        print(MENU_TEXT)
        choice = input("> ").strip().casefold()
        if choice in {"q", "quit", "exit"}:
            if not order.is_empty():
                if input("You have an unsaved order. Quit anyway? [y/N]: ").strip().casefold() != "y":
                    continue
            print("Goodbye.")
            return
        elif choice == "1":
            show_menu()
        elif choice == "2":
            prompt_add(order)
        elif choice == "3":
            prompt_remove(order)
        elif choice == "4":
            show_order(order)
        elif choice == "5":
            checkout(order, db_path)
        elif choice == "6":
            run_report(db_path)
        else:
            print("  ! Unrecognised option.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cafe ordering system")
    parser.add_argument("--db", default="cafe.db", help="path to the SQLite database")
    parser.add_argument("--report", action="store_true", help="print the sales report and exit")
    parser.add_argument("--order", type=int, metavar="ID", help="print a saved order and exit")
    args = parser.parse_args(argv)

    if args.report:
        run_report(args.db)
        return 0
    if args.order is not None:
        show_saved_order(args.db, args.order)
        return 0

    try:
        interactive(args.db)
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
