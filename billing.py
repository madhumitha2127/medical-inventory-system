from datetime import datetime
import os
from inventory import load_tablets, save_tablets

BILL_FILE = "bills.txt"


# ---------------- INVOICE ----------------

def generate_invoice(bill_id, date, name, qty, price, total):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    folder = os.path.join(base_dir, "invoices")
    os.makedirs(folder, exist_ok=True)

    file_path = os.path.join(folder, f"invoice_{bill_id}.txt")

    with open(file_path, "w") as f:
        f.write("====== MEDICAL INVENTORY INVOICE ======\n")
        f.write(f"Bill ID   : {bill_id}\n")
        f.write(f"Date      : {date}\n")
        f.write("-------------------------------------\n")
        f.write(f"Tablet    : {name}\n")
        f.write(f"Quantity  : {qty}\n")
        f.write(f"Price     : {price}\n")
        f.write("-------------------------------------\n")
        f.write(f"TOTAL     : {total}\n")
        f.write("=====================================\n")

    return file_path


# ---------------- SELL TABLET (API LOGIC) ----------------

def sell_tablet_logic(name, sell_qty, price):
    tablets = load_tablets()
    today = datetime.today().date()

    for t in tablets:
        if t["name"].lower() == name.lower():

            expiry_date = datetime.strptime(t["expiry"], "%Y-%m-%d").date()
            days_left = (expiry_date - today).days

            if days_left < 0:
                return {"error": "Tablet is expired. Sale blocked."}

            if t["qty"] < sell_qty:
                return {"error": "Not enough stock"}

            # Update stock
            t["qty"] -= sell_qty
            save_tablets(tablets)

            total = sell_qty * price
            bill_id = int(datetime.now().timestamp())

            # Save bill
            with open(BILL_FILE, "a") as bill:
                bill.write(f"{bill_id},{today},{name},{sell_qty},{price},{total}\n")

            # Generate invoice
            invoice_path = generate_invoice(
                bill_id, today, name, sell_qty, price, total
            )

            return {
                "message": "Sale successful",
                "bill_id": bill_id,
                "tablet": name,
                "quantity": sell_qty,
                "total": total,
                "invoice": invoice_path
            }

    return {"error": "Tablet not found"}


# ---------------- VERIFY BILL ----------------

def verify_bill_api(bill_id_input):
    try:
        with open(BILL_FILE, "r") as bill:
            for line in bill:
                parts = line.strip().split(",")
                if len(parts) != 6:
                    continue

                bill_id, date, name, qty, price, total = parts
                if bill_id == bill_id_input:
                    return {
                        "bill_id": bill_id,
                        "date": date,
                        "tablet": name,
                        "quantity": int(qty),
                        "price": float(price),
                        "total": float(total)
                    }

        return {"error": "Invalid Bill ID"}

    except FileNotFoundError:
        return {"error": "No bills found"}


# ---------------- SALES ANALYTICS ----------------

def sales_analytics():
    try:
        with open(BILL_FILE, "r") as bill:
            lines = bill.readlines()

        if not lines:
            print("No sales data available.")
            return

        total_revenue = 0
        total_items = 0
        tablet_sales = {}

        for line in lines:
            parts = line.strip().split(",")
            if len(parts) != 6:
                continue

            _, _, tablet, qty, _, total = parts
            qty = int(qty)
            total = float(total)

            total_items += qty
            total_revenue += total
            tablet_sales[tablet] = tablet_sales.get(tablet, 0) + qty

        most_sold = max(tablet_sales, key=tablet_sales.get)

        print("\n📊 SALES ANALYTICS")
        print("Total Revenue    :", total_revenue)
        print("Total Items Sold :", total_items)
        print("Most Sold Tablet :", most_sold)

    except FileNotFoundError:
        print("❌ No billing data found")
