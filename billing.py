from datetime import datetime
import os
from inventory import load_tablets, save_tablets

# File to store bills
BILL_FILE = "bills.txt"


# ==============================
# ✅ GENERATE INVOICE
# ==============================

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

    print(f"🧾 Invoice generated at: {file_path}")


# ==============================
# ✅ SELL TABLET (API + Backend Logic)
# ==============================

def sell_tablet_logic(name, qty, price):

    tablets = load_tablets()
    today = datetime.today().date()

    for t in tablets:

        if t["name"].lower() == name.lower():

            expiry_date = datetime.strptime(t["expiry"], "%Y-%m-%d").date()
            days_left = (expiry_date - today).days

            # ❌ Block expired tablets
            if days_left < 0:
                return {"error": "Tablet is expired"}

            if t["qty"] < int(qty):
                return {"error": "Not enough stock"}

            # Update stock
            t["qty"] -= int(qty)
            save_tablets(tablets)

            total = int(qty) * float(price)
            bill_id = int(datetime.now().timestamp())

            # Save bill
            with open(BILL_FILE, "a") as bill:
                bill.write(f"{bill_id},{today},{name},{qty},{price},{total}\n")

            # Generate invoice
            generate_invoice(bill_id, today, name, qty, price, total)

            return {
                "message": "Tablet sold successfully",
                "bill_id": bill_id,
                "total": total
            }

    return {"error": "Tablet not found"}


# ==============================
# ✅ VERIFY BILL (CLI)
# ==============================

def verify_bill():

    bill_id_input = input("\nEnter Bill ID to verify: ")

    try:
        with open(BILL_FILE, "r") as bill:

            for line in bill:

                parts = line.strip().split(",")

                if len(parts) != 6:
                    continue

                bill_id, date, name, qty, price, total = parts

                if bill_id == bill_id_input:

                    print("\n✅ BILL VERIFIED")
                    print("Bill ID :", bill_id)
                    print("Date    :", date)
                    print("Tablet  :", name)
                    print("Quantity:", qty)
                    print("Price   :", price)
                    print("Total   :", total)

                    return

        print("❌ Invalid Bill ID")

    except FileNotFoundError:
        print("❌ No bills found.")


# ==============================
# ✅ SALES ANALYTICS (FOR API)
# ==============================

def sales_analytics_data():

    try:
        with open(BILL_FILE, "r") as bill:
            lines = bill.readlines()

        if not lines:
            return {
                "total_revenue": 0,
                "total_items_sold": 0,
                "most_sold_tablet": "None"
            }

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

        most_sold = max(tablet_sales, key=tablet_sales.get) if tablet_sales else "None"

        return {
            "total_revenue": total_revenue,
            "total_items_sold": total_items,
            "most_sold_tablet": most_sold
        }

    except FileNotFoundError:

        return {
            "total_revenue": 0,
            "total_items_sold": 0,
            "most_sold_tablet": "None"
        }
def get_all_bills():

    bills = []

    try:
        with open(BILL_FILE, "r") as file:

            for line in file:

                parts = line.strip().split(",")

                if len(parts) != 6:
                    continue

                bill_id, date, tablet, qty, price, total = parts

                bill_data = {
                    "bill_id": bill_id,
                    "date": date,
                    "tablet": tablet,
                    "qty": int(qty),
                    "price": float(price),
                    "total": float(total),
                    "qr": f"/static/qr_codes/bill_qr_{bill_id}.png"
                }

                bills.append(bill_data)

        return bills

    except FileNotFoundError:
        return []
