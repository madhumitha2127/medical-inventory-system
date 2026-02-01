from datetime import datetime
import qrcode
import os

TABLET_FILE = "tablets.txt"
BILL_FILE = "bills.txt"


# ---------- Tablet Functions ----------

def load_tablets():
    tablets = []
    try:
        with open(TABLET_FILE, "r") as file:
            for line in file:
                name, qty, expiry, status = line.strip().split(",")
                tablets.append({
                    "name": name,
                    "qty": int(qty),
                    "expiry": expiry,
                    "status": status
                })
    except FileNotFoundError:
        pass
    return tablets


def save_tablets(tablets):
    with open(TABLET_FILE, "w") as file:
        for t in tablets:
            file.write(f"{t['name']},{t['qty']},{t['expiry']},{t['status']}\n")

from datetime import datetime

def view_tablets():
    tablets = load_tablets()
    if not tablets:
        print("No tablets available.")
        return

    today = datetime.today().date()

    print("\n--- Available Tablets ---")
    for t in tablets:
        expiry_date = datetime.strptime(t["expiry"], "%Y-%m-%d").date()
        days_left = (expiry_date - today).days

        if days_left < 0:
            status = "EXPIRED ❌"
        elif days_left <= 30:
            status = f"NEAR EXPIRY ⚠️ ({days_left} days left)"
        else:
            status = f"SAFE ✅ ({days_left} days left)"

        print(
            f"{t['name']} | Qty: {t['qty']} | Expiry: {expiry_date} | {status}"
        )

# ---------- QR Code ----------

def generate_qr(bill_text, bill_id):
    folder = "qr_codes"
    if not os.path.exists(folder):
        os.makedirs(folder)

    path = os.path.join(folder, f"bill_qr_{bill_id}.png")
    img = qrcode.make(bill_text)
    img.save(path)

    print(f"📱 QR Code saved at: {path}")


# ---------- Sell & Bill ----------
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

            # ❌ Block expired tablets
            if days_left < 0:
                print("❌ SALE BLOCKED: Tablet is EXPIRED")
                return

            # ⚠️ Warn near-expiry tablets
            if days_left <= 30:
                print(f"⚠️ WARNING: Tablet expires in {days_left} days")

            if t["qty"] < sell_qty:
                print("❌ Not enough stock available.")
                return

            t["qty"] -= sell_qty
            price = float(input("Enter price per tablet: "))
            total = sell_qty * price
            bill_id = int(datetime.now().timestamp())

            with open(BILL_FILE, "a") as bill:
                bill.write(f"{bill_id},{today},{name},{sell_qty},{price},{total}\n")

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

            print("\n--- BILL GENERATED ---")
            print("Bill ID :", bill_id)
            print("Tablet  :", name)
            print("Total   :", total)
            print("✅ Stock updated safely")
            generate_invoice(bill_id, today, name, sell_qty, price, total)

            return

    print("❌ Tablet not found.")



# ---------- Bill Verification ----------


def verify_bill():
    bill_id_input = input("\nEnter Bill ID to verify: ")

    try:
        with open(BILL_FILE, "r") as bill:
            for line in bill:
                parts = line.strip().split(",")

                # Skip invalid/old bill records
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


# ---------- Main Menu ----------
def search_tablet():
    tablets = load_tablets()
    if not tablets:
        print("No tablets available.")
        return

    search_name = input("\nEnter tablet name to search: ").lower()
    today = datetime.today().date()
    found = False

    print("\n--- Search Results ---")
    for t in tablets:
        if search_name in t["name"].lower():
            expiry_date = datetime.strptime(t["expiry"], "%Y-%m-%d").date()
            days_left = (expiry_date - today).days

            if days_left < 0:
                status = "EXPIRED ❌"
            elif days_left <= 30:
                status = f"NEAR EXPIRY ⚠️ ({days_left} days left)"
            else:
                status = f"SAFE ✅ ({days_left} days left)"

            print(
                f"{t['name']} | Qty: {t['qty']} | Expiry: {expiry_date} | {status}"
            )
            found = True

    if not found:
        print("❌ No matching tablet found.")
def view_blocked_tablets():
    tablets = load_tablets()
    if not tablets:
        print("No tablets available.")
        return

    today = datetime.today().date()
    found = False

    print("\n--- BLOCKED (EXPIRED) TABLETS ---")
    for t in tablets:
        expiry_date = datetime.strptime(t["expiry"], "%Y-%m-%d").date()
        days_left = (expiry_date - today).days

        if days_left < 0:
            print(
                f"{t['name']} | Qty: {t['qty']} | Expired on: {expiry_date} ❌"
            )
            found = True

    if not found:
        print("✅ No blocked tablets found.")
def add_tablet():
    tablets = load_tablets()

    print("\n--- Add New Tablet ---")
    name = input("Enter tablet name: ")

    # Check duplicate
    for t in tablets:
        if t["name"].lower() == name.lower():
            print("❌ Tablet already exists in inventory.")
            return

    qty = int(input("Enter quantity: "))
    expiry_input = input("Enter expiry date (DD-MM-YYYY): ")

    expiry_date = datetime.strptime(expiry_input, "%d-%m-%Y").date()
    today = datetime.today().date()

    status = "VALID"
    if expiry_date < today:
        status = "EXPIRED"

    tablets.append({
        "name": name,
        "qty": qty,
        "expiry": expiry_date.strftime("%Y-%m-%d"),
        "status": status
    })

    save_tablets(tablets)

    print("✅ Tablet added successfully.")

def generate_invoice(bill_id, date, name, qty, price, total):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        print("DEBUG base_dir =", base_dir)

        folder = os.path.join(base_dir, "invoices")
        print("DEBUG invoice folder =", folder)

        os.makedirs(folder, exist_ok=True)
        print("DEBUG folder ensured")

        file_path = os.path.join(folder, f"invoice_{bill_id}.txt")
        print("DEBUG invoice file path =", file_path)

        with open(file_path, "w", encoding="utf-8") as f:
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

        print("✅ INVOICE FILE WRITTEN SUCCESSFULLY")

    except Exception as e:
        print("❌ INVOICE ERROR:", e)


while True:
    print("\n===== Medical Inventory System =====")
    print("1. Add Tablet")
    print("2. View Tablets")
    print("3. Sell Tablet (Generate Bill + QR)")
    print("4. Verify Bill")
    print("5. Search Tablet")
    print("6. View Blocked (Expired) Tablets")
    print("7. Exit")

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
        print("Goodbye 👋")
        break
    else:
        print("Invalid choice")


# from datetime import datetime
# import qrcode

# TABLET_FILE = "tablets.txt"
# BILL_FILE = "bills.txt"


# def load_tablets():
#     tablets = []
#     try:
#         with open(TABLET_FILE, "r") as file:
#             for line in file:
#                 name, qty, expiry, status = line.strip().split(",")
#                 tablets.append({
#                     "name": name,
#                     "qty": int(qty),
#                     "expiry": expiry,
#                     "status": status
#                 })
#     except FileNotFoundError:
#         pass
#     return tablets


# def save_tablets(tablets):
#     with open(TABLET_FILE, "w") as file:
#         for t in tablets:
#             file.write(f"{t['name']},{t['qty']},{t['expiry']},{t['status']}\n")


# def view_tablets():
#     tablets = load_tablets()
#     if not tablets:
#         print("No tablets available.")
#         return

#     print("\n--- Available Tablets ---")
#     for t in tablets:
#         print(f"{t['name']} | Qty: {t['qty']} | Expiry: {t['expiry']} | {t['status']}")


# import os

# def generate_qr(bill_text, bill_id):
#     folder_name = "qr_codes"

#     # Create folder if it doesn't exist
#     if not os.path.exists(folder_name):
#         os.makedirs(folder_name)

#     file_path = os.path.join(folder_name, f"bill_qr_{bill_id}.png")

#     img = qrcode.make(bill_text)
#     img.save(file_path)

#     print(f"📱 QR Code saved in folder: {file_path}")



# def sell_tablet():
#     tablets = load_tablets()
#     if not tablets:
#         print("No tablets in inventory.")
#         return

#     view_tablets()
#     name = input("\nEnter tablet name to sell: ")
#     sell_qty = int(input("Enter quantity to sell: "))

#     for t in tablets:
#         if t["name"].lower() == name.lower():
#             if t["qty"] < sell_qty:
#                 print("❌ Not enough stock available.")
#                 return

#             t["qty"] -= sell_qty
#             price = float(input("Enter price per tablet: "))
#             total = sell_qty * price
#             today = datetime.today().date()
#             bill_id = int(datetime.now().timestamp())

#             with open(BILL_FILE, "a") as bill:
#                 bill.write(f"{bill_id},{today},{name},{sell_qty},{price},{total}\n")

#             save_tablets(tablets)

#             bill_text = (
#                 f"Bill ID: {bill_id}\n"
#                 f"Date: {today}\n"
#                 f"Tablet: {name}\n"
#                 f"Quantity: {sell_qty}\n"
#                 f"Price: {price}\n"
#                 f"Total: {total}"
#             )

#             generate_qr(bill_text, bill_id)

#             print("\n--- BILL GENERATED ---")
#             print("Tablet :", name)
#             print("Qty    :", sell_qty)
#             print("Total  :", total)
#             print("✅ Stock updated & QR generated")
#             return

#     print("❌ Tablet not found.")


# while True:
#     print("\n===== Medical Inventory System =====")
#     print("1. View Tablets")
#     print("2. Sell Tablet (Generate Bill + QR)")
#     print("3. Exit")

#     choice = input("Enter choice: ")

#     if choice == "1":
#         view_tablets()
#     elif choice == "2":
#         sell_tablet()
#     elif choice == "3":
#         print("Goodbye 👋")
#         break
#     else:
#         print("Invalid choice")


















# # from datetime import datetime

# # TABLET_FILE = "tablets.txt"
# # BILL_FILE = "bills.txt"


# # def load_tablets():
# #     tablets = []
# #     try:
# #         with open(TABLET_FILE, "r") as file:
# #             for line in file:
# #                 name, qty, expiry, status = line.strip().split(",")
# #                 tablets.append({
# #                     "name": name,
# #                     "qty": int(qty),
# #                     "expiry": expiry,
# #                     "status": status
# #                 })
# #     except FileNotFoundError:
# #         pass
# #     return tablets


# # def save_tablets(tablets):
# #     with open(TABLET_FILE, "w") as file:
# #         for t in tablets:
# #             file.write(f"{t['name']},{t['qty']},{t['expiry']},{t['status']}\n")


# # def view_tablets():
# #     tablets = load_tablets()
# #     if not tablets:
# #         print("No tablets available.")
# #         return

# #     print("\n--- Available Tablets ---")
# #     for t in tablets:
# #         print(f"{t['name']} | Qty: {t['qty']} | Expiry: {t['expiry']} | {t['status']}")


# # def sell_tablet():
# #     tablets = load_tablets()
# #     if not tablets:
# #         print("No tablets in inventory.")
# #         return

# #     view_tablets()
# #     name = input("\nEnter tablet name to sell: ")
# #     sell_qty = int(input("Enter quantity to sell: "))

# #     for t in tablets:
# #         if t["name"].lower() == name.lower():
# #             if t["qty"] < sell_qty:
# #                 print("❌ Not enough stock available.")
# #                 return

# #             t["qty"] -= sell_qty
# #             price = float(input("Enter price per tablet: "))
# #             total = sell_qty * price
# #             today = datetime.today().date()

# #             with open(BILL_FILE, "a") as bill:
# #                 bill.write(f"{today},{name},{sell_qty},{price},{total}\n")

# #             save_tablets(tablets)

# #             print("\n--- BILL GENERATED ---")
# #             print("Tablet :", name)
# #             print("Qty    :", sell_qty)
# #             print("Total  :", total)
# #             print("✅ Stock updated successfully")
# #             return

# #     print("❌ Tablet not found.")


# # while True:
# #     print("\n===== Medical Inventory System =====")
# #     print("1. View Tablets")
# #     print("2. Sell Tablet")
# #     print("3. Exit")

# #     choice = input("Enter choice: ")

# #     if choice == "1":
# #         view_tablets()
# #     elif choice == "2":
# #         sell_tablet()
# #     elif choice == "3":
# #         print("Goodbye 👋")
# #         break
# #     else:
# #         print("Invalid choice")

# # # from datetime import datetime

# # # TABLET_FILE = "tablets.txt"
# # # BILL_FILE = "bills.txt"

# # # def add_tablet():
# # #     print("\n--- Add New Tablet & Generate Bill ---")
# # #     tablet_name = input("Enter tablet name: ")
# # #     quantity = int(input("Enter quantity: "))
# # #     price = float(input("Enter price per tablet: "))
# # #     expiry_input = input("Enter expiry date (DD-MM-YYYY): ")

# # #     expiry_date = datetime.strptime(expiry_input, "%d-%m-%Y").date()
# # #     today = datetime.today().date()

# # #     status = "VALID"
# # #     if expiry_date < today:
# # #         status = "EXPIRED"

# # #     total_cost = quantity * price
# # #     bill_date = today

# # #     # Save tablet data
# # #     with open(TABLET_FILE, "a") as file:
# # #         file.write(f"{tablet_name},{quantity},{expiry_date},{status}\n")

# # #     # Save bill data
# # #     with open(BILL_FILE, "a") as bill:
# # #         bill.write(f"{bill_date},{tablet_name},{quantity},{price},{total_cost}\n")

# # #     print("\n--- BILL GENERATED ---")
# # #     print("Tablet Name :", tablet_name)
# # #     print("Quantity    :", quantity)
# # #     print("Price/unit  :", price)
# # #     print("Total Cost  :", total_cost)
# # #     print("Status      :", status)


# # # def view_bills():
# # #     print("\n--- Billing History ---")
# # #     try:
# # #         with open(BILL_FILE, "r") as bill:
# # #             lines = bill.readlines()

# # #             if not lines:
# # #                 print("No bills found.")
# # #                 return

# # #             for line in lines:
# # #                 date, name, qty, price, total = line.strip().split(",")
# # #                 print(
# # #                     f"Date: {date} | Tablet: {name} | Qty: {qty} | Price: {price} | Total: {total}"
# # #                 )

# # #     except FileNotFoundError:
# # #         print("No billing data found.")


# # # while True:
# # #     print("\n===== Medical Inventory System =====")
# # #     print("1. Add Tablet & Generate Bill")
# # #     print("2. View Bills")
# # #     print("3. Exit")

# # #     choice = input("Enter your choice: ")

# # #     if choice == "1":
# # #         add_tablet()
# # #     elif choice == "2":
# # #         view_bills()
# # #     elif choice == "3":
# # #         print("Exiting system. Goodbye 👋")
# # #         break
# # #     else:
# # #         print("Invalid choice. Please try again.")
# # # 1
# # # # from datetime import datetime

# # # # FILE_NAME = "tablets.txt"

# # # # def add_tablet():
# # # #     print("\n--- Add New Tablet ---")
# # # #     tablet_name = input("Enter tablet name: ")
# # # #     quantity = int(input("Enter quantity: "))
# # # #     expiry_input = input("Enter expiry date (DD-MM-YYYY): ")

# # # #     expiry_date = datetime.strptime(expiry_input, "%d-%m-%Y").date()
# # # #     today = datetime.today().date()

# # # #     status = "VALID"
# # # #     if expiry_date < today:
# # # #         status = "EXPIRED"

# # # #     # Save to file
# # # #     with open(FILE_NAME, "a") as file:
# # # #         file.write(f"{tablet_name},{quantity},{expiry_date},{status}\n")

# # # #     print("\nTablet saved successfully ✅")
# # # #     print("Status:", status)


# # # # def view_tablets():
# # # #     print("\n--- Stored Tablets ---")

# # # #     try:
# # # #         with open(FILE_NAME, "r") as file:
# # # #             lines = file.readlines()

# # # #             if not lines:
# # # #                 print("No tablets found.")
# # # #                 return

# # # #             for line in lines:
# # # #                 tablet_name, quantity, expiry_date, status = line.strip().split(",")
# # # #                 print(
# # # #                     f"Name: {tablet_name} | Qty: {quantity} | Expiry: {expiry_date} | Status: {status}"
# # # #                 )

# # # #     except FileNotFoundError:
# # # #         print("No data file found. Add tablets first.")


# # # # while True:
# # # #     print("\n===== Medical Inventory System =====")
# # # #     print("1. Add Tablet")
# # # #     print("2. View Tablets")
# # # #     print("3. Exit")

# # # #     choice = input("Enter your choice: ")

# # # #     if choice == "1":
# # # #         add_tablet()
# # # #     elif choice == "2":
# # # #         view_tablets()
# # # #     elif choice == "3":
# # # #         print("Exiting system. Goodbye 👋")
# # # #         break
# # # #     else:
# # # #         print("Invalid choice. Please try again.")
