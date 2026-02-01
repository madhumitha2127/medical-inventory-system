from datetime import datetime

TABLET_FILE = "tablets.txt"

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

    for t in tablets:
        if t["name"].lower() == name.lower():
            print("❌ Tablet already exists.")
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
