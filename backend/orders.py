from backend.db import get_connection
from datetime import datetime

def get_all_orders():
    conn = get_connection()
    orders = conn.execute("""
        SELECT o.*,
               u.username AS account_username,
               GROUP_CONCAT(p.name || ' x ' || od.quantity, ', ') AS items
        FROM orders o
        LEFT JOIN users u ON o.user_id = u.id
        LEFT JOIN order_details od ON o.order_id = od.order_id
        LEFT JOIN products p ON od.product_id = p.product_id
        GROUP BY o.order_id
        ORDER BY o.order_id DESC
    """).fetchall()
    conn.close()
    return orders

def get_orders_by_user(user_id):
    conn = get_connection()
    orders = conn.execute("""
        SELECT o.*,
               GROUP_CONCAT(p.name || ' x ' || od.quantity, ', ') AS items
        FROM orders o
        LEFT JOIN order_details od ON o.order_id = od.order_id
        LEFT JOIN products p ON od.product_id = p.product_id
        WHERE o.user_id = ?
        GROUP BY o.order_id
        ORDER BY o.order_id DESC
    """, (user_id,)).fetchall()
    conn.close()
    return orders

def create_order(
    customer_name,
    customer_address,
    order_items,
    user_id=None,
    payment_status="Pending",
    payment_id=None,
    payment_method=None
):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if not order_items:
            raise ValueError("Cannot create an empty order.")

        total = 0
        final_items = []
        
        # Validate stock and calculate total with discount
        for item in order_items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            
            # Fetch current product details to verify price and stock
            product_row = cursor.execute(
                "SELECT price, stock, discount FROM products WHERE product_id = ?", 
                (product_id,)
            ).fetchone()
            
            if not product_row:
                raise ValueError(f"Product ID {product_id} not found.")

            price = product_row["price"]
            stock = product_row["stock"]
            discount = product_row["discount"]

            if quantity > stock:
                raise ValueError(f"Insufficient stock for Product ID {product_id}. Available: {stock}, Requested: {quantity}")

            final_price = price * (1 - discount / 100)
            total += final_price * quantity
            
            final_items.append({
                "product_id": product_id,
                "quantity": quantity
            })

        date = datetime.now().strftime("%Y-%m-%d %H:%M")

        cursor.execute("""
            INSERT INTO orders (
                user_id,
                customer_name,
                customer_address,
                order_date,
                total_amount,
                payment_status,
                payment_id,
                payment_method,
                order_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            customer_name,
            customer_address,
            date,
            total,
            payment_status,
            payment_id,
            payment_method,
            "Pending"
        ))
        order_id = cursor.lastrowid

        for item in final_items:
            cursor.execute(
                "INSERT INTO order_details (order_id, product_id, quantity) VALUES (?, ?, ?)",
                (order_id, item["product_id"], item["quantity"])
            )
            # Deduct stock
            cursor.execute(
                "UPDATE products SET stock = stock - ? WHERE product_id = ?",
                (item["quantity"], item["product_id"])
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    return order_id


def get_order_details(order_id):
    conn = get_connection()
    details = conn.execute("""
        SELECT p.name, p.price, p.unit, p.discount, od.quantity
        FROM order_details od
        JOIN products p ON od.product_id = p.product_id
        WHERE od.order_id = ?
    """, (order_id,)).fetchall()
    conn.close()
    return details

def get_order(order_id, user_id=None):
    conn = get_connection()
    if user_id is None:
        order = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    else:
        order = conn.execute(
            "SELECT * FROM orders WHERE order_id = ? AND user_id = ?",
            (order_id, user_id)
        ).fetchone()
    conn.close()
    return order

def get_order_by_payment_id(payment_id, user_id=None):
    conn = get_connection()
    if user_id is None:
        order = conn.execute(
            "SELECT * FROM orders WHERE payment_id = ?",
            (payment_id,)
        ).fetchone()
    else:
        order = conn.execute(
            "SELECT * FROM orders WHERE payment_id = ? AND user_id = ?",
            (payment_id, user_id)
        ).fetchone()
    conn.close()
    return order



def delete_order(order_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM order_details WHERE order_id = ?", (order_id,))
    cursor.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()

