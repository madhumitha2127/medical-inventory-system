import sqlite3

DATABASE = "medical_inventory.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            quantity    INTEGER NOT NULL,
            price       REAL NOT NULL,
            expiry_date TEXT NOT NULL,
            usage        TEXT,
            restrictions TEXT
            dosage       TEXT,
            side_effects TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_name TEXT NOT NULL,
            quantity_sold INTEGER NOT NULL,
            total_price   REAL NOT NULL,
            sold_by       TEXT NOT NULL,
            sold_on       TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database created successfully!")
