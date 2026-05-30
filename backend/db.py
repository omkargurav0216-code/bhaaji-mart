import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_DIR = os.path.join(BASE_DIR, "..", "database")
os.makedirs(DB_DIR, exist_ok=True)

DB_NAME = os.path.join(DB_DIR, "grocery_store.db")

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # PRODUCTS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        unit TEXT NOT NULL,
        stock REAL NOT NULL DEFAULT 0 CHECK(stock >= 0),
        discount REAL NOT NULL DEFAULT 0 CHECK(discount >= 0 AND discount <= 100)
    )
    """)

    # ORDERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        customer_name TEXT,
        customer_address TEXT,
        order_date TEXT,
        total_amount REAL,
        payment_status TEXT DEFAULT 'Pending',
        payment_id TEXT,
        payment_method TEXT,
        order_status TEXT DEFAULT 'Pending',
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    order_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(orders)").fetchall()
    }
    if "user_id" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN user_id INTEGER REFERENCES users(id)")
    if "payment_status" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT 'Pending'")
    if "payment_id" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN payment_id TEXT")
    if "payment_method" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT")
    if "order_status" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN order_status TEXT DEFAULT 'Pending'")
    
    #ORDER DETAILS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity REAL,
        FOREIGN KEY(order_id) REFERENCES orders(order_id),
        FOREIGN KEY(product_id) REFERENCES products(product_id)
    )
    """)

    #USERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'customer'))
    )
    """)

    # CART TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 1,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(product_id) REFERENCES products(product_id)
    )
    """)

    cart_fks = cursor.execute("PRAGMA foreign_key_list(cart)").fetchall()
    has_wrong_product_fk = any(
        fk["table"] == "products" and fk["to"] != "product_id"
        for fk in cart_fks
    )
    if has_wrong_product_fk:
        cursor.execute("ALTER TABLE cart RENAME TO cart_old")
        cursor.execute("""
        CREATE TABLE cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(product_id) REFERENCES products(product_id)
        )
        """)
        cursor.execute("""
        INSERT INTO cart (id, user_id, product_id, quantity)
        SELECT c.id, c.user_id, c.product_id, c.quantity
        FROM cart_old c
        JOIN users u ON c.user_id = u.id
        JOIN products p ON c.product_id = p.product_id
        WHERE c.quantity > 0
        """)
        cursor.execute("DROP TABLE cart_old")

    conn.commit()
    conn.close()


def add_to_cart(user_id, product_id, quantity=1.0):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    conn = get_connection()
    cursor = conn.cursor()

    product = cursor.execute("""
        SELECT product_id, stock FROM products
        WHERE product_id = ?
    """, (product_id,)).fetchone()

    if not product:
        conn.close()
        raise ValueError("Product not found.")

    if product["stock"] <= 0:
        conn.close()
        raise ValueError("This product is out of stock.")

    item = cursor.execute("""
        SELECT id, quantity FROM cart
        WHERE user_id = ? AND product_id = ?
    """, (user_id, product_id)).fetchone()

    if item:
        new_qty = item["quantity"] + quantity
        if new_qty > product["stock"]:
            conn.close()
            raise ValueError(f"Cannot add more than available stock ({product['stock']}).")

        cursor.execute("""
            UPDATE cart
            SET quantity = ?
            WHERE id = ?
        """, (new_qty, item["id"]))
    else:
        if quantity > product["stock"]:
            conn.close()
            raise ValueError(f"Cannot add more than available stock ({product['stock']}).")

        cursor.execute("""
            INSERT INTO cart (user_id, product_id, quantity)
            VALUES (?, ?, ?)
        """, (user_id, product_id, quantity))

    conn.commit()
    conn.close()


def get_cart_items(user_id):
    conn = get_connection()
    items = conn.execute("""
        SELECT c.id,
               c.product_id,
               c.quantity,
               p.name,
               p.price,
               p.unit,
               p.stock,
               p.discount,
               (p.price * (1 - p.discount / 100)) AS final_price,
               (p.price * (1 - p.discount / 100) * c.quantity) AS total
        FROM cart c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.user_id = ?
        ORDER BY c.id DESC
    """, (user_id,)).fetchall()
    conn.close()
    return items


def get_cart_item(cart_id, user_id):
    conn = get_connection()
    item = conn.execute("""
        SELECT c.id, c.product_id, c.quantity, p.stock
        FROM cart c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.id = ? AND c.user_id = ?
    """, (cart_id, user_id)).fetchone()
    conn.close()
    return item


def get_cart_count(user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) AS count FROM cart WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return row["count"] if row else 0


def remove_from_cart(cart_id, user_id):
    conn = get_connection()
    conn.execute("""
        DELETE FROM cart
        WHERE id = ? AND user_id = ?
    """, (cart_id, user_id))
    conn.commit()
    conn.close()


def update_cart_quantity(cart_id, user_id, quantity):
    if quantity <= 0:
        remove_from_cart(cart_id, user_id)
        return

    conn = get_connection()
    item = conn.execute("""
        SELECT c.id, p.stock
        FROM cart c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.id = ? AND c.user_id = ?
    """, (cart_id, user_id)).fetchone()

    if not item:
        conn.close()
        raise ValueError("Cart item not found.")

    if quantity > item["stock"]:
        conn.close()
        raise ValueError("Cannot set quantity higher than available stock.")

    conn.execute("""
        UPDATE cart
        SET quantity = ?
        WHERE id = ? AND user_id = ?
    """, (quantity, cart_id, user_id))
    conn.commit()
    conn.close()


def clear_cart(user_id):
    conn = get_connection()
    conn.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
