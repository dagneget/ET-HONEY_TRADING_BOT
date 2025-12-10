import sqlite3

DB_NAME = "honey_trading.db"

def query_customers_table():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, telegram_id, username, is_admin, status FROM customers')
    rows = c.fetchall()
    conn.close()
    
    if rows:
        print("Customers Table Contents:")
        for row in rows:
            print(dict(row))
    else:
        print("No customers found in the database.")

query_customers_table()
