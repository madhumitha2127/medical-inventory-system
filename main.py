from datetime import datetime

from inventory import (
    add_tablet,
    view_tablets,
    search_tablet,
    view_blocked_tablets,
    load_tablets,
    save_tablets
)

from qr_utils import generate_qr
from billing import generate_invoice, verify_bill, sales_analytics


def sell_tablet():
    tablets = load_tablets()
    if not tablets:
        print("No tablets in inventory.")
        return

    view_tablets()
    name = input("\nEnter tablet name to sell: ")
    sell_qty = int(input("Enter quantity to sell: "))
    today = datetime.today().date()

    for t in tablets:
        if t["name"].lower() == name.lower():
            expiry_date = datetime.strptime(t["expiry"], "%Y-%m-%d").date()
            days_left = (expiry_date - today).days

            if days_left < 0:
                print("❌ SALE BLOCKED: Tablet is EXPIRED")
                return

            if days_left <= 30:
                print(f"⚠️ WARNING: Tablet expires in {days_left} days")

            if t["qty"] < sell_qty:
                print("❌ Not enough stock available.")
                return

            t["qty"] -= sell_qty
            price = float(input("Enter price per tablet: "))
            total = sell_qty * price
            bill_id = int(datetime.now().timestamp())

            with open("bills.txt", "a") as bill:
                bill.write(
                    f"{bill_id},{today},{name},{sell_qty},{price},{total}\n"
                )

            save_tablets(tablets)

            bill_text = (
                f"Bill ID: {bill_id}\n"
                f"Date: {today}\n"
                f"Tablet: {name}\n"
                f"Quantity: {sell_qty}\n"
                f"Price: {price}\n"
                f"Total: {total}"
            )

            generate_qr(bill_text, bill_id)
            generate_invoice(bill_id, today, name, sell_qty, price, total)

            print("✅ Sale completed successfully")
            return

    print("❌ Tablet not found.")


def main():
    while True:
        print("\n===== Medical Inventory System =====")
        print("1. Add Tablet")
        print("2. View Tablets")
        print("3. Sell Tablet")
        print("4. Verify Bill")
        print("5. Search Tablet")
        print("6. View Blocked (Expired) Tablets")
        print("7. Sales Analytics")
        print("8. Exit")

        choice = input("Enter choice: ")

        if choice == "1":
            add_tablet()
        elif choice == "2":
            view_tablets()
        elif choice == "3":
            sell_tablet()
        elif choice == "4":
            verify_bill()
        elif choice == "5":
            search_tablet()
        elif choice == "6":
            view_blocked_tablets()
        elif choice == "7":
            sales_analytics()
        elif choice == "8":
            print("Goodbye 👋")
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()
