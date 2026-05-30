from backend.db import get_connection

def add_product(name, price, unit, stock=0, discount=0, image_url=None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO products (name, price, unit, stock, discount, image_url) VALUES (?, ?, ?, ?, ?, ?)",
        (name, price, unit, stock, discount, image_url)
    )
    conn.commit()
    conn.close()

def get_all_products():
    conn = get_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return products

def delete_product(product_id):
    conn = get_connection()
    conn.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()

def get_product(product_id):
    conn = get_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE product_id = ?", (product_id,)
    ).fetchone()
    conn.close()
    return product

def update_product(product_id, name, price, unit, stock, discount, image_url=None, remove_image=False):
    conn = get_connection()
    if remove_image:
        conn.execute("""
            UPDATE products
            SET name = ?, price = ?, unit = ?, stock = ?, discount = ?, image_url = NULL
            WHERE product_id = ?
        """, (name, price, unit, stock, discount, product_id))
    elif image_url is not None:
        conn.execute("""
            UPDATE products
            SET name = ?, price = ?, unit = ?, stock = ?, discount = ?, image_url = ?
            WHERE product_id = ?
        """, (name, price, unit, stock, discount, image_url, product_id))
    else:
        conn.execute("""
            UPDATE products
            SET name = ?, price = ?, unit = ?, stock = ?, discount = ?
            WHERE product_id = ?
        """, (name, price, unit, stock, discount, product_id))
    conn.commit()
    conn.close()

