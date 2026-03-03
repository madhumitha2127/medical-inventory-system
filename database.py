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
            expiry_date TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
if __name__ == "__main__":
    init_db()
    print("Database created successfully!")