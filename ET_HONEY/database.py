import sqlite3
from datetime import datetime
import pandas as pd
import os
import logging

DB_NAME = "honey_trading.db"
DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Customers Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            email TEXT,
            region TEXT,
            customer_type TEXT,
            status TEXT DEFAULT 'Pending',
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tickets Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT,
            subject TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migration for existing tables (safe to run if columns exist)
    try:
        c.execute("ALTER TABLE tickets ADD COLUMN subject TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE tickets ADD COLUMN attachment_path TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE customers ADD COLUMN is_admin INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE customers ADD COLUMN username TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN price REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE customers ADD COLUMN language TEXT DEFAULT 'en'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE products ADD COLUMN available_quantities TEXT")
    except sqlite3.OperationalError:
        pass
    
    # Messages Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            sender_type TEXT, -- 'user' or 'admin'
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(ticket_id) REFERENCES tickets(id)
        )
    ''')

    # Orders Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_name TEXT,
            quantity INTEGER,
            delivery_address TEXT,
            payment_type TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Feedback Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            rating INTEGER,
            comment TEXT,
            photo_path TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Products Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            price REAL,
            stock INTEGER DEFAULT 0,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def add_product(name, description, price, stock, image_path=None, available_quantities=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO products (name, description, price, stock, image_path, available_quantities)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, description, price, stock, image_path, available_quantities))
    product_id = c.lastrowid
    conn.commit()
    conn.close()
    return product_id

def update_customer_language(telegram_id, language):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE customers SET language = ? WHERE telegram_id = ?', (language, telegram_id))
    conn.commit()
    conn.close()

def get_all_products():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM products ORDER BY name')
    products = c.fetchall()
    conn.close()
    return products

def get_product(product_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = c.fetchone()
    conn.close()
    return product

def delete_product(product_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()

def update_product_stock(product_id, new_stock):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE products SET stock = ? WHERE id = ?', (new_stock, product_id))
    conn.commit()
    conn.close()

def create_feedback(user_id, rating, comment, photo_path=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO feedback (user_id, rating, comment, photo_path)
        VALUES (?, ?, ?, ?)
    ''', (user_id, rating, comment, photo_path))
    feedback_id = c.lastrowid
    conn.commit()
    conn.close()
    return feedback_id

def get_feedback(feedback_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM feedback WHERE id = ?', (feedback_id,))
    feedback = c.fetchone()
    conn.close()
    return feedback

def update_feedback_status(feedback_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE feedback SET status = ? WHERE id = ?', (status, feedback_id))
    conn.commit()
    conn.close()

def create_order(user_id, product_name, quantity, delivery_address, payment_type, price=0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO orders (user_id, product_name, quantity, delivery_address, payment_type, price)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, product_name, quantity, delivery_address, payment_type, price))
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_order(order_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    order = c.fetchone()
    conn.close()
    return order

def update_order_status(order_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    conn.close()

# --- Customer Functions ---
def add_customer(data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO customers (telegram_id, username, full_name, phone, email, region, customer_type, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data['telegram_id'], data['username'], data['full_name'], data['phone'], data['email'], data['region'], data['customer_type'], 'Approved'))
    customer_id = c.lastrowid
    conn.commit()
    conn.close()
    return customer_id

def get_customer(customer_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
    customer = c.fetchone()
    conn.close()
    return customer

def get_customer_by_telegram_id(telegram_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM customers WHERE telegram_id = ?', (telegram_id,))
    customer = c.fetchone()
    logging.info(f"get_customer_by_telegram_id for {telegram_id} returned: {customer}")
    conn.close()
    return customer

def get_customer_by_username(username):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM customers WHERE LOWER(username) = LOWER(?)', (username,))
    customer = c.fetchone()
    logging.info(f"get_customer_by_username for {username} returned: {customer}")
    conn.close()
    return customer

def get_all_customers():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM customers ORDER BY full_name')
    customers = c.fetchall()
    conn.close()
    return customers

def set_admin_status(telegram_id, is_admin):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE customers SET is_admin = ? WHERE telegram_id = ?', (is_admin, telegram_id))
    conn.commit()
    conn.close()

def update_customer_status(customer_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE customers SET status = ? WHERE id = ?', (status, customer_id))
    conn.commit()
    conn.close()

def set_admin_by_username(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE customers SET is_admin = 1, status = "Approved" WHERE LOWER(username) = LOWER(?)', (username,))
    conn.commit()
    conn.close()
    logging.info(f"Set admin status for username {username} to 1 and status to Approved.")

def update_customer_status_by_telegram_id(telegram_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE customers SET status = ? WHERE telegram_id = ?', (status, telegram_id))
    conn.commit()
    conn.close()

# --- Ticket & Support Functions ---

def create_ticket(user_id, category, subject, message, attachment_path=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create Ticket
    c.execute('''
        INSERT INTO tickets (user_id, category, subject, status, attachment_path) 
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, category, subject, 'Pending', attachment_path))
    ticket_id = c.lastrowid
    
    # Add initial message
    c.execute('''
        INSERT INTO messages (ticket_id, sender_type, message) 
        VALUES (?, ?, ?)
    ''', (ticket_id, 'user', message))
    
    conn.commit()
    conn.close()
    return ticket_id

def add_message(ticket_id, sender_type, message):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO messages (ticket_id, sender_type, message) VALUES (?, ?, ?)', 
              (ticket_id, sender_type, message))
    
    # Update ticket updated_at
    c.execute('UPDATE tickets SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (ticket_id,))
    conn.commit()
    conn.close()

def update_ticket_status(ticket_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE tickets SET status = ? WHERE id = ?', (status, ticket_id))
    conn.commit()
    conn.close()

def get_active_ticket(user_id):
    """Returns the most recent open ticket for a user."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Check for 'Open' or 'Pending' (maybe user shouldn't open new if pending?)
    # For now, let's assume 'Open' is the active state allowing chat.
    c.execute("SELECT * FROM tickets WHERE user_id = ? AND status IN ('Open', 'Pending', 'Approved') ORDER BY created_at DESC LIMIT 1", (user_id,))
    ticket = c.fetchone()
    conn.close()
    return ticket

def get_ticket(ticket_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,))
    ticket = c.fetchone()
    conn.close()
    return ticket

def update_feedback_photo_path(feedback_id, photo_path):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE feedback SET photo_path = ? WHERE id = ?', (photo_path, feedback_id))
    conn.commit()
    conn.close()

def update_ticket_attachment_path(ticket_id, attachment_path):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE tickets SET attachment_path = ? WHERE id = ?', (attachment_path, ticket_id))
    conn.commit()
    conn.close()

def get_orders_by_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # user_id in orders table is the telegram_id
    c.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    orders = c.fetchall()
    conn.close()
    return orders

def get_tickets_by_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # user_id in tickets table is the telegram_id
    c.execute('SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    tickets = c.fetchall()
    conn.close()
    return tickets

def get_feedback_by_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM feedback WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    feedback = c.fetchall()
    conn.close()
    return feedback

def export_table_to_excel(table_name):
    conn = sqlite3.connect(DB_PATH)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{table_name}_export_{timestamp}.xlsx"
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, file_name)

    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        df.to_excel(file_path, index=False, engine='openpyxl')
        print(f"Successfully exported {table_name} to {file_path}")
        return file_path
    except Exception as e:
        print(f"Error exporting {table_name}: {e}")
        return None
    finally:
        conn.close()

def delete_customer(telegram_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Update customer status to 'Deleted'
    c.execute('UPDATE customers SET status = ? WHERE telegram_id = ?', ('Deleted', telegram_id))
    conn.commit()
    conn.close()

def permanently_delete_customer(telegram_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    logging.info(f"Attempting to permanently delete customer with telegram_id: {telegram_id}")
    # Get customer_id first
    c.execute('SELECT id FROM customers WHERE telegram_id = ?', (telegram_id,))
    customer_id = c.fetchone()
    if customer_id:
        customer_id = customer_id[0]
        logging.info(f"Found customer_id {customer_id} for telegram_id {telegram_id}. Proceeding with permanent deletion.")
        # Delete related orders
        c.execute('DELETE FROM orders WHERE user_id = ?', (customer_id,))
        # Delete related tickets
        c.execute('DELETE FROM tickets WHERE user_id = ?', (customer_id,))
        # Delete related feedback
        c.execute('DELETE FROM feedback WHERE user_id = ?', (customer_id,))
        # Finally, delete the customer
        c.execute('DELETE FROM customers WHERE telegram_id = ?', (telegram_id,))
        logging.info(f"Customer with telegram_id {telegram_id} and customer_id {customer_id} permanently deleted from database.")
    else:
        logging.info(f"No customer found with telegram_id {telegram_id} for permanent deletion.")
    conn.commit()
    conn.close()

def get_recent_users(limit=10):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM customers ORDER BY created_at DESC LIMIT ?', (limit,))
    users = c.fetchall()
    conn.close()
    return users

def get_total_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM customers")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_total_revenue():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Assuming orders table has 'total_price' or we calculate from product price * quantity
    # But wait, orders table structure: user_id, product_name, quantity, address, payment, status, created_at.
    # It doesn't store price! We need to join with products or store price in orders.
    # Storing price in orders is better for historical accuracy.
    # For now, I'll check if orders has price.
    c.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in c.fetchall()]
    conn.close()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if 'price' in columns:
        c.execute('SELECT SUM(price * quantity) FROM orders WHERE status = "Approved"')
    else:
        # Fallback: join with products (inaccurate if price changed)
        # Or just return 0 for now if column missing.
        # Actually, let's just count orders for now.
        return 0 
        
    result = c.fetchone()[0]
    conn.close()
    return result if result else 0

def get_total_orders_count():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM orders')
    result = c.fetchone()[0]
    conn.close()
    return result

def get_total_tickets_count():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM tickets')
    result = c.fetchone()[0]
    conn.close()
    return result

def get_total_messages():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tickets")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_pending_messages():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tickets WHERE status = 'Pending'")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_resolved_messages():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tickets WHERE status = 'closed'")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_all_tickets(filter_status=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if filter_status:
        c.execute("SELECT * FROM tickets WHERE status = ? ORDER BY created_at DESC", (filter_status,))
    else:
        c.execute("SELECT * FROM tickets ORDER BY created_at DESC")
    tickets = c.fetchall()
    conn.close()
    return tickets

def get_messages_for_ticket(ticket_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM messages WHERE ticket_id = ? ORDER BY created_at ASC", (ticket_id,))
    messages = c.fetchall()
    conn.close()
    return messages

def close_ticket(ticket_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE tickets SET status = ? WHERE id = ?', ('closed', ticket_id))
    conn.commit()
    conn.close()

def update_feedback_photo_path(feedback_id, photo_path):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE feedback SET photo_path = ? WHERE id = ?', (photo_path, feedback_id))
    conn.commit()
    conn.close()

def update_ticket_attachment_path(ticket_id, attachment_path):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE tickets SET attachment_path = ? WHERE id = ?', (attachment_path, ticket_id))
    conn.commit()
    conn.close()