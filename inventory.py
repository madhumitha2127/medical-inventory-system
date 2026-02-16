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


def add_tablet(name, qty, expiry):
    tablets = load_tablets()

    for t in tablets:
        if t["name"].lower() == name.lower():
            return {"error": "Tablet already exists"}

    expiry_date = parse_date(expiry)

    today = datetime.today().date()

    status = "EXPIRED" if expiry_date < today else "VALID"

    tablets.append({
        "name": name,
        "qty": int(qty),
        "expiry": expiry,
        "status": status
    })

    save_tablets(tablets)
    return {"message": "Tablet added successfully"}
from datetime import datetime

def parse_date(date_str):

    formats = [
        "%d %m %Y",
        "%d-%m-%Y",
        "%Y-%m-%d"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue

    raise ValueError("Invalid date format")
