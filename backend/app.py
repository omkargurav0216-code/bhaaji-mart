import stripe
import logging
import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
logger = logging.getLogger(__name__)
from backend.db import create_tables
from backend.products import add_product, get_all_products, delete_product, get_product, update_product
from backend.orders import (
    create_order,
    delete_order,
    get_all_orders,
    get_order,
    get_order_by_payment_id,
    get_order_details,
    get_orders_by_user,
)
from backend.db import (
    add_to_cart,
    clear_cart,
    get_cart_count,
    get_cart_item,
    get_cart_items,
    remove_from_cart,
    update_cart_quantity,
)


from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from backend.db import get_connection
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

app.secret_key = 'super_secret_key_for_grocery_store_app' # Required for session

import uuid
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads', 'products')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def delete_old_product_image(product_id):
    product = get_product(product_id)
    if product and product['image_url']:
        old_path = os.path.join(app.static_folder, product['image_url'])
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception as e:
                logger.error(f"Error removing old product image: {e}")

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore

# User Model
class User(UserMixin):
    def __init__(self, id, username, password_hash, role):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = get_connection()
    user_data = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['password_hash'], user_data['role'])
    return None

# Authorization Decorators
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            return "403 Forbidden: Admins only", 403
        return f(*args, **kwargs)
    return decorated_function

def customer_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'customer':
            return "403 Forbidden: Customers only", 403
        return f(*args, **kwargs)
    return decorated_function

create_tables()

@app.context_processor
def inject_cart_count():
    if current_user.is_authenticated and current_user.role == 'customer':
        return {"cart_count": get_cart_count(current_user.id)}
    return {"cart_count": 0}

def init_db_data():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if admin exists
    admin_user = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
    if not admin_user:
        hashed_password = generate_password_hash("admin123")
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                       ('admin', hashed_password, 'admin'))
        print("Admin user created.")

    # Check if customer exists
    customer_user = conn.execute("SELECT * FROM users WHERE username = 'customer'").fetchone()
    if not customer_user:
        hashed_password = generate_password_hash("custom123")
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                       ('customer', hashed_password, 'customer'))
        print("Customer user created.")

    conn.commit()
    conn.close()

init_db_data()

@app.route("/")
@login_required
def index():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return render_template("home.html")

@app.route("/my_orders")
@customer_required
def my_orders():
    orders = get_orders_by_user(current_user.id)
    return render_template("my_orders.html", orders=orders)

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    orders = get_all_orders()
    total_sales = sum(
        order["total_amount"] or 0
        for order in orders
        if order["payment_status"] == "Paid"
    )
    unpaid_count = sum(1 for order in orders if order["payment_status"] != "Paid")
    return render_template(
        "admin_dashboard.html",
        orders=orders,
        total_sales=total_sales,
        unpaid_count=unpaid_count
    )

@app.route("/admin/orders")
@admin_required
def admin_orders():
    orders = get_all_orders()
    return render_template("admin_orders.html", orders=orders)

@app.route("/admin/analytics")
@admin_required
def sales_analytics():
    from backend.db import get_connection
    from datetime import datetime, timedelta
    
    conn = get_connection()
    
    # 1. Fetch all paid orders
    paid_orders = conn.execute("""
        SELECT o.order_id, o.order_date, o.total_amount
        FROM orders o
        WHERE o.payment_status = 'Paid'
        ORDER BY o.order_id ASC
    """).fetchall()

    # 2. Fetch all paid order details
    paid_details = conn.execute("""
        SELECT od.quantity, p.name, p.price, p.discount
        FROM order_details od
        JOIN orders o ON od.order_id = o.order_id
        JOIN products p ON od.product_id = p.product_id
        WHERE o.payment_status = 'Paid'
    """).fetchall()
    
    conn.close()

    total_orders = len(paid_orders)
    has_data = total_orders > 0

    if not has_data:
        return render_template(
            "sales_analytics.html",
            has_data=False
        )

    # 3. Calculate basic metrics
    total_revenue = sum(order["total_amount"] or 0.0 for order in paid_orders)
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0.0

    # Category and product maps
    def get_category(product_name):
        name = product_name.lower()
        if any(k in name for k in ['tamatar', 'aaloo', 'baigan', 'potato', 'tomato', 'onion', 'garlic', 'ginger', 'chili', 'vegetable', 'bhindi', 'gobi', 'carrot', 'cabbage']):
            return "Vegetables"
        elif any(k in name for k in ['apple', 'banana', 'mango', 'orange', 'grape', 'fruit', 'lemon', 'anar', 'papaya', 'watermelon']):
            return "Fruits"
        elif any(k in name for k in ['milk', 'dahi', 'paneer', 'cheese', 'butter', 'curd', 'ghee', 'dairy']):
            return "Dairy"
        elif any(k in name for k in ['rice', 'flour', 'atta', 'dal', 'pulse', 'sugar', 'salt', 'oil', 'masala', 'wheat', 'staple', 'poha', 'besan']):
            return "Staples"
        elif any(k in name for k in ['soap', 'shampoo', 'surf', 'wash', 'clean', 'detergent', 'toothpaste', 'brush']):
            return "Household"
        else:
            return "Groceries"

    category_revenue = {}
    product_quantities = {}

    for item in paid_details:
        qty = item["quantity"] or 0.0
        name = item["name"] or "Product"
        price = item["price"] or 0.0
        discount = item["discount"] or 0.0
        final_price = price * (1 - discount / 100)
        line_total = final_price * qty
        
        cat = get_category(name)
        category_revenue[cat] = category_revenue.get(cat, 0.0) + line_total
        product_quantities[name] = product_quantities.get(name, 0.0) + qty

    # Top selling category
    top_category = "N/A"
    if category_revenue:
        top_category = max(category_revenue, key=category_revenue.get)

    # 4. Hourly Sales calculation (all 24 hours format)
    hourly_sales_map = [0.0] * 24
    for order in paid_orders:
        date_str = order["order_date"]
        if date_str:
            try:
                # Format: YYYY-MM-DD HH:MM
                time_part = date_str.split(" ")[1]
                hour = int(time_part.split(":")[0])
                if 0 <= hour < 24:
                    hourly_sales_map[hour] += order["total_amount"] or 0.0
            except Exception:
                pass

    # Hourly labels: e.g. ["12 AM", "1 AM", ..., "11 PM"]
    hourly_labels = []
    for h in range(24):
        if h == 0:
            hourly_labels.append("12 AM")
        elif h < 12:
            hourly_labels.append(f"{h} AM")
        elif h == 12:
            hourly_labels.append("12 PM")
        else:
            hourly_labels.append(f"{h - 12} PM")

    # 5. Top Products (horizontal bar chart: top 7)
    sorted_products = sorted(product_quantities.items(), key=lambda x: x[1], reverse=True)[:7]
    top_products_labels = [p[0] for p in sorted_products]
    top_products_data = [p[1] for p in sorted_products]

    # 6. Category contribution labels/data
    category_labels = list(category_revenue.keys())
    category_data = list(category_revenue.values())

    # 7. Weekly Stats comparison (Revenue vs Expense vs Profit)
    weekly_labels = []
    weekly_revenue = []
    weekly_expenses = []
    weekly_profit = []

    # Get stats for the last 7 days
    daily_stats = {}
    for i in range(6, -1, -1):
        target_date = (datetime.now() - timedelta(days=i))
        date_str = target_date.strftime("%Y-%m-%d")
        display_str = target_date.strftime("%b %d") # e.g. "May 30"
        daily_stats[date_str] = {"display": display_str, "revenue": 0.0}

    for order in paid_orders:
        date_str = order["order_date"]
        if date_str:
            try:
                d = date_str.split(" ")[0] # YYYY-MM-DD
                if d in daily_stats:
                    daily_stats[d]["revenue"] += order["total_amount"] or 0.0
            except Exception:
                pass

    # Sort days and build datasets
    sorted_days = sorted(daily_stats.keys())
    for d in sorted_days:
        rev = daily_stats[d]["revenue"]
        # Configurable placeholder logic: Expenses = 68% of Revenue, Profit = 32%
        exp = rev * 0.68
        prof = rev - exp
        
        weekly_labels.append(daily_stats[d]["display"])
        weekly_revenue.append(round(rev, 2))
        weekly_expenses.append(round(exp, 2))
        weekly_profit.append(round(prof, 2))

    return render_template(
        "sales_analytics.html",
        has_data=True,
        total_revenue=total_revenue,
        total_orders=total_orders,
        avg_order_value=avg_order_value,
        top_category=top_category,
        hourly_labels=hourly_labels,
        hourly_data=hourly_sales_map,
        top_products_labels=top_products_labels,
        top_products_data=top_products_data,
        category_labels=category_labels,
        category_data=category_data,
        weekly_labels=weekly_labels,
        weekly_revenue=weekly_revenue,
        weekly_expenses=weekly_expenses,
        weekly_profit=weekly_profit
    )

@app.route("/products", methods=["GET", "POST"])
@admin_required
def products():
    if request.method == "POST":
        file = request.files.get('product_image')
        image_url = None
        
        if file and file.filename != '':
            if allowed_file(file.filename):
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                filename = secure_filename(file.filename)
                ext = filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4().hex}.{ext}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                image_url = f"uploads/products/{unique_filename}"
            else:
                flash("Invalid file format. Allowed formats: PNG, JPG, JPEG, WEBP.")
                return redirect("/products")

        add_product(
            request.form["name"],
            request.form["price"],
            request.form["unit"],
            float(request.form.get("stock", 0)), # type: ignore
            float(request.form.get("discount", 0)), # type: ignore
            image_url=image_url
        )
        return redirect("/products?success=product_added")

    products = get_all_products()
    return render_template("products.html", products=products)

@app.route("/new_order", methods=["GET", "POST"])
@customer_required
def new_order():
    products = get_all_products()

    if request.method == "POST":
        customer_name = request.form["customer_name"]
        customer_address = request.form["customer_address"]

        items = []
        for p in products:
            qty = request.form.get(f"qty_{p['product_id']}")
            if qty and float(qty) > 0:
                if float(qty) > p["stock"]:
                    return render_template(
                        "new_order.html", 
                        products=products, 
                        error=f"Insufficient stock for {p['name']}. Available: {p['stock']}, Requested: {qty}",
                        customer_name=customer_name,
                        customer_address=customer_address
                    )
                items.append({
                    "product_id": p["product_id"],
                    "name": p["name"],
                    "unit": p["unit"],
                    "price": p["price"] * (1 - p["discount"] / 100),
                    "quantity": float(qty),
                    "total": p["price"] * (1 - p["discount"] / 100) * float(qty),
                })
        
        if not items:
            return render_template(
                "new_order.html", 
                products=products, 
                error="Order cannot be empty. Please select at least one product.",
                customer_name=customer_name,
                customer_address=customer_address
            )

        return begin_stripe_checkout(items, customer_address, customer_name, source="direct")
    
    error = request.args.get("error")
    return render_template("new_order.html", products=products, error=error)

@app.route("/order/<int:order_id>")
@login_required
def order_details(order_id):
    if current_user.role == 'customer':
        order = get_order(order_id, current_user.id)
        back_url = url_for('my_orders')
    else:
        order = get_order(order_id)
        back_url = url_for('admin_orders')

    if not order:
        abort(404)

    details = get_order_details(order_id)
    return render_template("order_details.html", details=details, order=order, back_url=back_url)



@app.route("/admin/orders/<int:order_id>/cancel")
@admin_required
def cancel_order(order_id):
    delete_order(order_id)
    flash("Order cancelled.")
    return redirect(url_for('admin_orders'))

@app.route("/delete_product/<int:product_id>")
@admin_required
def remove_product(product_id):
    delete_old_product_image(product_id)
    delete_product(product_id)
    return redirect("/products")

@app.route("/edit_product/<int:product_id>", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    if request.method == "POST":
        remove_image = request.form.get("remove_image") == "true"
        file = request.files.get("product_image")
        image_url = None
        
        if remove_image or (file and file.filename != ''):
            delete_old_product_image(product_id)
            
        if file and file.filename != '':
            if allowed_file(file.filename):
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                filename = secure_filename(file.filename)
                ext = filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4().hex}.{ext}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                image_url = f"uploads/products/{unique_filename}"
            else:
                flash("Invalid file format. Allowed formats: PNG, JPG, JPEG, WEBP.")
                return redirect(url_for('edit_product', product_id=product_id))

        update_product(
            product_id,
            request.form["name"],
            request.form["price"],
            request.form["unit"],
            float(request.form.get("stock", 0)),
            float(request.form.get("discount", 0)),
            image_url=image_url,
            remove_image=remove_image
        )
        return redirect("/products")

    product = get_product(product_id)
    return render_template("edit_product.html", product=product)

@app.route('/add_to_cart/<int:product_id>')
@customer_required
def add_product_to_cart(product_id):
    try:
        qty_param = request.args.get("quantity")
        qty = float(qty_param) if qty_param else 1.0
        add_to_cart(current_user.id, product_id, qty)
        flash("Product added to cart.")
    except ValueError as e:
        flash(str(e))
    return redirect(request.referrer or url_for('new_order'))

@app.route('/cart')
@customer_required
def cart():
    items = get_cart_items(current_user.id)
    grand_total = sum(item["total"] for item in items)
    return render_template("cart.html", items=items, grand_total=grand_total)

@app.route('/remove_from_cart/<int:cart_id>')
@customer_required
def remove_cart_item(cart_id):
    remove_from_cart(cart_id, current_user.id)
    flash("Item removed from cart.")
    return redirect(url_for('cart'))

@app.route('/increase_quantity/<int:cart_id>')
@customer_required
def increase_quantity(cart_id):
    item = get_cart_item(cart_id, current_user.id)
    if not item:
        flash("Cart item not found.")
        return redirect(url_for('cart'))

    try:
        update_cart_quantity(cart_id, current_user.id, item["quantity"] + 1)
        flash("Cart quantity updated.")
    except ValueError as e:
        flash(str(e))
    return redirect(url_for('cart'))

@app.route('/decrease_quantity/<int:cart_id>')
@customer_required
def decrease_quantity(cart_id):
    item = get_cart_item(cart_id, current_user.id)
    if not item:
        flash("Cart item not found.")
        return redirect(url_for('cart'))

    if item["quantity"] <= 1:
        remove_from_cart(cart_id, current_user.id)
        flash("Item removed from cart.")
    else:
        update_cart_quantity(cart_id, current_user.id, item["quantity"] - 1)
        flash("Cart quantity updated.")
    return redirect(url_for('cart'))

@app.route('/checkout', methods=["POST"])
@customer_required

def checkout():
    payment_method = request.form.get('payment_method', 'stripe')
    if payment_method == 'qr':
        # Prepare QR pending data and redirect to QR payment page
        items = get_cart_items(current_user.id)
        if not items:
            flash("Your cart is empty.")
            return redirect(url_for('cart'))
        customer_address = request.form.get('customer_address', '').strip()
        if not customer_address:
            flash("Please enter a delivery address before checkout.")
            return redirect(url_for('cart'))
        # Build checkout items list
        checkout_items = []
        total_amount = 0
        for item in items:
            if item["quantity"] > item["stock"]:
                flash(f"Insufficient stock for {item['name']}. Available: {item['stock']}, Requested: {item['quantity']}")
                return redirect(url_for('cart'))
            checkout_items.append({
                "product_id": item["product_id"],
                "name": item["name"],
                "unit": item["unit"],
                "price": item["final_price"],
                "quantity": item["quantity"],
                "total": item["total"]
            })
            total_amount += item["total"]
        # Store pending QR payment info in session
        session['qr_pending'] = {
            "customer_name": current_user.username,
            "customer_address": customer_address,
            "items": checkout_items,
            "total_amount": total_amount,
            "source": "qr"
        }
        session.modified = True
        return redirect(url_for('qr_payment'))
    else:
        # Default Stripe flow
        return create_checkout_session()

@app.route('/qr_payment', methods=['GET', 'POST'])
@customer_required
def qr_payment():
    pending = session.get('qr_pending')
    if not pending:
        flash('No pending QR payment found.')
        return redirect(url_for('cart'))
    if request.method == 'POST':
        # User confirms they have paid
        from backend.orders import create_order
        order_items = [{"product_id": i["product_id"], "quantity": i["quantity"]} for i in pending["items"]]
        try:
            order_id = create_order(
                pending["customer_name"],
                pending["customer_address"],
                order_items,
                current_user.id,
                payment_status="Paid",
                payment_id="QR_" + pending["customer_address"],
                payment_method="QR"
            )
            clear_cart(current_user.id)
            session.pop('qr_pending', None)
            flash('Payment received via QR. Order created.')
            return redirect(url_for('my_orders'))
        except ValueError as e:
            flash(str(e))
            return redirect(url_for('cart'))
    # GET: generate QR code image
    from backend.qr_utils import generate_qr_code
    import uuid, os
    qr_dir = os.path.join(app.static_folder, 'qr')
    os.makedirs(qr_dir, exist_ok=True)
    filename = f"qr_{uuid.uuid4().hex}.png"
    upi_str = f"upi://pay?pa=grocerydemo@upi&pn=GreenShelf&am={pending['total_amount']:.2f}"
    try:
        generate_qr_code(upi_str, os.path.join(qr_dir, filename))
        logger.info(f"QR code generated: {filename}")
    except Exception as e:
        logger.error(f"Failed to generate QR code: {e}")
        flash('Error generating QR code. Please try again.')
        return redirect(url_for('cart'))
    session['qr_image'] = filename
    return render_template('qr_payment.html', qr_filename=filename, total=pending['total_amount'], upi=upi_str)

def begin_stripe_checkout(checkout_items, customer_address, customer_name, source="cart"):
    total_amount = sum(item["total"] for item in checkout_items)
    line_items = []

    for item in checkout_items:
        qty = item['quantity']
        if qty == int(qty):
            line_items.append({
                'price_data': {
                    'currency': 'inr',
                    'product_data': {
                        'name': f"{item['name']} (per {item['unit']})",
                    },
                    'unit_amount': int(round(item['price'] * 100)),
                },
                'quantity': int(qty),
            })
        else:
            line_items.append({
                'price_data': {
                    'currency': 'inr',
                    'product_data': {
                        'name': f"{item['name']} x {qty} {item['unit']}",
                    },
                    'unit_amount': int(round(item['total'] * 100)),
                },
                'quantity': 1,
            })

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            client_reference_id=str(current_user.id),
            metadata={
                "user_id": str(current_user.id),
                "username": current_user.username,
            },
            success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payment_cancel', _external=True),
        )
    except Exception as e:
        flash(f"Unable to start Stripe Checkout: {e}")
        return redirect(url_for('cart'))

    session["pending_checkout"] = {
        "stripe_session_id": checkout_session.id,
        "user_id": current_user.id,
        "customer_name": customer_name,
        "customer_address": customer_address,
        "items": checkout_items,
        "total_amount": total_amount,
        "source": source,
    }
    session.modified = True

    return redirect(checkout_session.url, code=303)

@app.route('/create-checkout-session', methods=["GET", "POST"])
@customer_required
def create_checkout_session():
    items = get_cart_items(current_user.id)
    if not items:
        flash("Your cart is empty.")
        return redirect(url_for('cart'))

    customer_address = request.form.get("customer_address", "").strip()
    if not customer_address:
        flash("Please enter a delivery address before checkout.")
        return redirect(url_for('cart'))

    checkout_items = []

    for item in items:
        if item["quantity"] > item["stock"]:
            flash(f"Insufficient stock for {item['name']}. Available: {item['stock']}, Requested: {item['quantity']}")
            return redirect(url_for('cart'))
        checkout_items.append({
            "product_id": item["product_id"],
            "name": item["name"],
            "unit": item["unit"],
            "price": item["final_price"],
            "quantity": item["quantity"],
            "total": item["total"],
        })

    return begin_stripe_checkout(checkout_items, customer_address, current_user.username, source="cart")

@app.route("/login", methods=["GET", "POST"])
def login():
    role_mode = request.args.get('role')
    
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        conn = get_connection()
        user_data = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data['id'], user_data['username'], user_data['password_hash'], user_data['role'])
            login_user(user)
            if user.role == 'admin':
                return redirect("/admin/dashboard")
            else:
                return redirect("/")
        else:
            return render_template("login.html", error="Invalid username or password", is_admin=(role_mode == 'admin'))
            
    return render_template("login.html", is_admin=(role_mode == 'admin'))

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match")

        conn = get_connection()
        existing_user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        
        if existing_user:
            conn.close()
            return render_template("register.html", error="Username already exists")

        password_hash = generate_password_hash(password)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                       (username, password_hash, 'customer'))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Auto login
        user = User(user_id, username, password_hash, 'customer')
        login_user(user)
        return redirect("/")

    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

@app.route('/payment-success')
@customer_required
def payment_success():
    stripe_session_id = request.args.get("session_id")
    if not stripe_session_id:
        flash("Missing Stripe payment session.")
        return redirect(url_for('cart'))

    existing_order = get_order_by_payment_id(stripe_session_id, current_user.id)
    if existing_order:
        details = get_order_details(existing_order["order_id"])
        return render_template(
            "payment_success.html",
            order=existing_order,
            details=details,
            stripe_session_id=stripe_session_id,
        )

    pending_checkout = session.get("pending_checkout")
    if not pending_checkout:
        flash("Payment session expired. Please contact support if your card was charged.")
        return redirect(url_for('cart'))

    if pending_checkout.get("stripe_session_id") != stripe_session_id:
        flash("Invalid payment session.")
        return redirect(url_for('cart'))

    try:
        stripe_session = stripe.checkout.Session.retrieve(stripe_session_id)
    except Exception:
        flash("Could not verify the Stripe payment session.")
        return redirect(url_for('cart'))

    if getattr(stripe_session, "payment_status", None) != "paid":
        flash("Payment was not completed.")
        return redirect(url_for('cart'))

    if str(getattr(stripe_session, "client_reference_id", None)) != str(current_user.id):
        flash("Payment session does not match your account.")
        return redirect(url_for('cart'))

    expected_amount = int(round(pending_checkout["total_amount"] * 100))
    if getattr(stripe_session, "amount_total", None) != expected_amount:
        flash("Payment amount verification failed.")
        return redirect(url_for('cart'))

    order_items = [
        {
            "product_id": item["product_id"],
            "quantity": item["quantity"],
        }
        for item in pending_checkout["items"]
    ]

    try:
        order_id = create_order(
            pending_checkout["customer_name"],
            pending_checkout["customer_address"],
            order_items,
            current_user.id,
            payment_status="Paid",
            payment_id=stripe_session_id,
            payment_method="Stripe"
        )
        if pending_checkout.get("source") == "cart":
            clear_cart(current_user.id)
        session.pop("pending_checkout", None)
        session.modified = True
    except ValueError as e:
        flash(str(e))
        return redirect(url_for('cart'))

    order = get_order(order_id, current_user.id)
    details = get_order_details(order_id)
    return render_template(
        "payment_success.html",
        order=order,
        details=details,
        stripe_session_id=stripe_session_id,
    )

@app.route('/payment-cancel')
@customer_required
def payment_cancel():
    flash("Payment cancelled. Your cart is still available.")
    pending_checkout = session.get("pending_checkout") or {}
    if pending_checkout.get("source") == "direct":
        return redirect(url_for('new_order'))
    return redirect(url_for('cart'))

if __name__ == "__main__":

    app.run(debug=True)
