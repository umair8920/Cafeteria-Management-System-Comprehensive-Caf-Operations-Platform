from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from werkzeug.security import generate_password_hash
import mysql.connector
from flask_mysqldb import MySQL
from flask_mysqldb import MySQLdb
from datetime import timedelta
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
import random
import string
from datetime import datetime




app = Flask(__name__)

# Configure MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'uos_cafeteria'

# Initialize MySQL
mysql = MySQL(app)

# Configure the secret key for Flask sessions
app.secret_key = '9956c9db4904894696a9154760dc4d001ea4376160d7500c9629f9ae19b85e83'

# Use server-side sessions
app.config['SESSION_TYPE'] = 'filesystem'  # Alternatively, you can use Redis for faster performance.
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

# Set secure cookie flags if using HTTPS
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['WTF_CSRF_ENABLED'] = True  # Enable CSRF globally
app.config['WTF_CSRF_SSL_STRICT'] = False  # Disable strict SSL requirement for development





# Check MySQL connection
def check_mysql_connection():
    try:
        with app.app_context():
            connection = mysql.connection
            cursor = connection.cursor()
            cursor.execute('SELECT 1')
            cursor.close()

        print("MySQL connection is successful.")
    except Exception as e:
        print("Error:", e)
        print("MySQL connection failed.")

check_mysql_connection()

@app.route('/')
def index():
    return render_template('index.html')




####################################################### LOGIN ROUTES ##########################################################

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id, username, role, name):
        self.id = id
        self.username = username
        self.role = role
        self.name = name

def role_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        @login_required
        def decorated_view(*args, **kwargs):
            if current_user.role not in roles:
                flash("You do not have permission to access this page.")
                return redirect(url_for('login'))  # Redirect to login or another page
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper




@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()

    if user:
        return User(user['id'], user['username'], user['role'], user['name'])
    return None


@app.route('/admin/register', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def register_user():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("INSERT INTO users (name, username, password, role) VALUES (%s, %s, %s, %s)",
                       (name, username, hashed_password, role))
        mysql.connection.commit()
        cursor.close()

        flash(f'User {username} registered successfully.')
        return redirect(url_for('admin_dashboard'))

    return render_template('App_management/register_user.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Use DictCursor for dictionary-style access
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['username'], user['role'], user['name'])
            login_user(user_obj)
            flash('Logged in successfully.')

            # Redirect based on user role
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'coffee_shop_man':
                return redirect(url_for('coffee_shop'))
            elif user['role'] == 'fast_food_man':
                return redirect(url_for('fast_food'))
            elif user['role'] == 'desi_food_man':
                return redirect(url_for('desi_food'))
            elif user['role'] == 'tuck_shop_man':
                return redirect(url_for('tuck_shop'))
            
        flash('Invalid username or password.')
    return render_template('App_management/login.html')



@app.route('/admin/update_password', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def update_password():
    if request.method == 'POST':
        try:
            username = request.form['username']
            new_password = request.form['new_password']

            if not username or not new_password:
                flash('Username and new password are required.')
                return redirect(url_for('update_password'))

            hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')

            # Use DictCursor for consistency
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("UPDATE users SET password = %s WHERE username = %s", (hashed_password, username))
            mysql.connection.commit()
            cursor.close()

            flash(f'Password for {username} has been updated successfully.')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            flash(f'An error occurred: {e}')
            return redirect(url_for('update_password'))

    return render_template('App_management/update_password.html')




@app.route('/admin/delete_user', methods=['POST'])
@login_required
@role_required('admin')
def delete_user():
    username = request.form['username']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if user:
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        mysql.connection.commit()
        flash(f'User {username} has been deleted successfully.')
    else:
        flash(f'User {username} does not exist.')

    cursor.close()
    return redirect(url_for('admin_dashboard'))






@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))


@app.route('/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, username, name, role FROM users")
    users = cursor.fetchall()
    cursor.close()
    return render_template('App_management/admin_dashboard.html',
                           users=users)


@app.route('/coffee_shop')
@login_required
@role_required('coffee_shop_man', 'admin')
def coffee_shop():
    return redirect(url_for('coffee_shop_dasboard'))


@app.route('/fast_food')
@login_required
@role_required('fast_food_man', 'admin')
def fast_food():
    return redirect(url_for('fast_food_dasboard'))


@app.route('/desi_food')
@login_required
@role_required('desi_food_man', 'admin')
def desi_food():
    return redirect(url_for('desi_food_dasboard'))


@app.route('/tuck_shop')
@login_required
@role_required('tuck_shop_man', 'admin')
def tuck_shop():
    return redirect(url_for('tuck_shop_dasboard'))


@app.route('/view_sales', methods=['GET', 'POST'])
@role_required('admin')
def view_sales():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get the filters from the form (if any)
    bill_id = request.form.get('bill_id', '').strip()
    sale_date = request.form.get('sale_date', '').strip()
    bill_type = request.form.get('bill_type', '').strip()
    status = request.form.get('status', '').strip()
    
    # Base SQL queries
    sales_query = """
        SELECT s.id, s.section, s.item_id, s.quantity, s.total_price, s.sale_date, s.bill_id
        FROM sales s
        JOIN bills b ON s.bill_id = b.id
    """
    bills_query = """
        SELECT id, total_price, sale_date, cash_received, change_due, status, bill_type
        FROM bills
    """
    
    # List to store WHERE conditions
    filters = []
    bill_filters = []
    
    # Apply filters to the sales query
    if bill_id:
        filters.append("s.bill_id = %s")
        bill_filters.append("id = %s")
    if sale_date:
        filters.append("s.sale_date = %s")
        bill_filters.append("sale_date = %s")
    if bill_type:
        bill_filters.append("bill_type = %s")
    if status:
        bill_filters.append("status = %s")
    
    # Combine filters with SQL
    if filters:
        sales_query += " WHERE " + " AND ".join(filters)
    if bill_filters:
        bills_query += " WHERE " + " AND ".join(bill_filters)
    
    # Execute the queries
    cursor.execute(sales_query, tuple(filter(None, [bill_id, sale_date])))
    daily_sales = cursor.fetchall()

    cursor.execute(bills_query, tuple(filter(None, [bill_id, sale_date, bill_type, status])))
    daily_bills = cursor.fetchall()
    
    # Calculate total sales for a specific date
    total_sales = None
    if sale_date:
        total_sales_query = "SELECT SUM(total_price) AS total_sales FROM sales WHERE sale_date = %s"
        cursor.execute(total_sales_query, (sale_date,))
        total_sales = cursor.fetchone().get('total_sales', 0)

    # Calculate total for bills
    total_bills = None
    if sale_date:
        total_bills_query = "SELECT SUM(total_price) AS total_bills FROM bills WHERE sale_date = %s"
        cursor.execute(total_bills_query, (sale_date,))
        total_bills = cursor.fetchone().get('total_bills', 0)

    cursor.close()

    return render_template('App_management/view_sales.html',
                           daily_sales=daily_sales, 
                           daily_bills=daily_bills,
                           total_sales=total_sales,
                           total_bills=total_bills,
                           selected_bill_id=bill_id,
                           selected_sale_date=sale_date,
                           selected_bill_type=bill_type,
                           selected_status=status)



@app.route('/delete_bill/<string:bill_id>', methods=['POST'])
@role_required('admin')
def delete_bill(bill_id):
    cursor = mysql.connection.cursor()
    
    try:
        # Delete all sales records associated with the bill
        cursor.execute("DELETE FROM sales WHERE bill_id = %s", (bill_id,))
        
        # Delete the bill itself
        cursor.execute("DELETE FROM bills WHERE id = %s", (bill_id,))
        
        mysql.connection.commit()
        flash(f'Bill {bill_id} and associated sales have been deleted.', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error deleting bill {bill_id}: {str(e)}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('view_sales'))








##################################### Coffee_Shop ##############################################################


@app.route('/coffee_shop_dasboard')
@role_required('coffee_shop_man', 'admin')
def coffee_shop_dasboard():
    return render_template('Coffee_Shop/coffee_shop_dasboard.html')


@app.route('/coffee_shop_items')
@role_required('coffee_shop_man', 'admin')
def coffee_shop_items():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, name, price, category FROM coffee_shop")
    items = cursor.fetchall()
    cursor.close()
    return render_template('Coffee_Shop/show_coffee_shop_items.html', items=items)

@app.route('/add_coffee_shop_item', methods=['GET', 'POST'])
@role_required('coffee_shop_man', 'admin')
def add_coffee_shop_item():
    if request.method == 'POST':
        # Handle form submission for multiple items
        names = request.form.getlist('name')   # Get list of names
        prices = request.form.getlist('price') # Get list of prices
        categories = request.form.getlist('category')  # Get list of categories (can be empty)

        cur = mysql.connection.cursor()

        # Insert each item into the database, checking for an optional category
        for name, price, category in zip(names, prices, categories):
            if category.strip():  # If category is provided
                cur.execute("INSERT INTO coffee_shop (name, price, category) VALUES (%s, %s, %s)", 
                            (name.strip(), price.strip(), category.strip()))
            else:  # If no category is provided, set it to NULL
                cur.execute("INSERT INTO coffee_shop (name, price, category) VALUES (%s, %s, NULL)", 
                            (name.strip(), price.strip()))
        
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('coffee_shop_items'))

    return render_template('Coffee_Shop/add_coffee_shop_item.html')




@app.route('/update_coffee_shop_item/<int:id>', methods=['GET', 'POST'])
@role_required('coffee_shop_man', 'admin')
def update_coffee_shop_item(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch the existing item details
    cursor.execute("SELECT id, name, price, category FROM coffee_shop WHERE id = %s", [id])
    item = cursor.fetchone()
    
    if request.method == 'POST':
        new_name = request.form['name']
        new_price = request.form['price']
        new_category = request.form.get('category', '')  # Fetch category (empty string if not provided)
        
        # Update the item in the database
        cursor.execute("""
            UPDATE coffee_shop
            SET name = %s, price = %s, category = %s
            WHERE id = %s
        """, (new_name, new_price, new_category if new_category.strip() else None, id))
        
        mysql.connection.commit()
        cursor.close()
        
        return redirect(url_for('coffee_shop_items'))
    
    cursor.close()
    return render_template('Coffee_Shop/update_coffee_shop_item.html', item=item)



@app.route('/delete_coffee_shop_item/<int:id>', methods=['GET'])
@role_required('coffee_shop_man', 'admin')
def delete_coffee_shop_item(id):
    cursor = mysql.connection.cursor()
    
    # Delete the item from the database
    cursor.execute("DELETE FROM coffee_shop WHERE id = %s", [id])
    mysql.connection.commit()
    cursor.close()
    
    return redirect(url_for('coffee_shop_items'))


@app.route('/generate_bill_form')
@role_required('coffee_shop_man', 'admin')
def generate_bill_form():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch items with category
    cursor.execute("SELECT id, name, price, category FROM coffee_shop")
    coffee_shop_items = cursor.fetchall()

    cursor.execute("SELECT id, name, price, category FROM desi_food")
    desi_food_items = cursor.fetchall()

    cursor.execute("SELECT id, name, price, category FROM fast_food")
    fast_food_items = cursor.fetchall()

    cursor.close()

    return render_template('Coffee_Shop/generate_bill.html', 
                           coffee_shop_items=coffee_shop_items,
                           desi_food_items=desi_food_items,
                           fast_food_items=fast_food_items)


@app.route('/generate_bill', methods=['POST'])
@role_required('coffee_shop_man', 'admin')
def generate_bill():
    items = request.form.getlist('items')
    quantities = request.form.getlist('quantities')

    total_price = 0.0
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Generate a new bill ID
    bill_id = generate_random_bill_id()
    bill_type = request.form.get('bill_type', 'student')

    try:
        # Create a new bill entry
        cursor.execute("""
            INSERT INTO bills (id, sale_date, status, bill_type) 
            VALUES (%s, NOW(), 'draft', %s)
        """, (bill_id, bill_type))

        for item, quantity in zip(items, quantities):
            section, item_id = item.split('|')
            quantity = int(quantity)

            # Fetch item price from the relevant section table
            cursor.execute(f"SELECT price FROM {section} WHERE id = %s", (item_id,))
            result = cursor.fetchone()
            if result:
                price = float(result['price'])
                item_total_price = price * quantity
                total_price += item_total_price

                # Insert sales record
                cursor.execute("""
                    INSERT INTO sales (bill_id, section, item_id, quantity, total_price, sale_date) 
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (bill_id, section, item_id, quantity, item_total_price))
            else:
                print(f"Item with ID {item_id} not found in section {section}")

        cash_received = request.form.get('cash_received', type=float, default=0.0)
        change_due = cash_received - total_price

        # Update bill with total price, cash received, and change due
        cursor.execute("""
            UPDATE bills 
            SET total_price = %s, cash_received = %s, change_due = %s 
            WHERE id = %s
        """, (total_price, cash_received, change_due, bill_id))

        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        print(f"Error occurred: {e}")
        return jsonify({'success': False, 'message': 'Failed to generate bill'}), 500
    finally:
        cursor.close()

    return redirect(url_for('confirm_bill', bill_id=bill_id))


@app.route('/confirm_bill/<string:bill_id>', methods=['GET', 'POST'])
@role_required('coffee_shop_man', 'admin')
def confirm_bill(bill_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch bill details
    cursor.execute("SELECT * FROM bills WHERE id = %s AND status = 'draft'", (bill_id,))
    bill = cursor.fetchone()

    if not bill:
        return jsonify({'success': False, 'message': 'Bill not found or already confirmed/canceled'}), 404

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'confirm':
            cursor.execute("UPDATE bills SET status = 'confirmed' WHERE id = %s", (bill_id,))
            mysql.connection.commit()
            pdf_url = url_for('view_bill', bill_id=bill_id)
            return jsonify({'success': True, 'pdf_url': pdf_url})

        elif action == 'cancel':
            cursor.execute("UPDATE bills SET status = 'canceled' WHERE id = %s", (bill_id,))
            mysql.connection.commit()
            return jsonify({'success': True, 'message': 'Bill canceled'})

    return render_template('Coffee_Shop/confirm_bill.html', bill=bill)


@app.route('/view_bill/<string:bill_id>')
@role_required('coffee_shop_man', 'admin')
def view_bill(bill_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch bill details
    cursor.execute("SELECT * FROM bills WHERE id = %s AND status = 'confirmed'", (bill_id,))
    bill = cursor.fetchone()

    if not bill:
        return "Bill not confirmed or not found", 404

    # Fetch items related to this bill, grouped by section
    query = """
        SELECT s.section, s.item_id, s.quantity, s.total_price, i.name, i.price, i.category
        FROM sales s
        JOIN coffee_shop i ON s.item_id = i.id AND s.section = 'coffee_shop'
        WHERE s.bill_id = %s
        UNION ALL
        SELECT s.section, s.item_id, s.quantity, s.total_price, i.name, i.price, i.category
        FROM sales s
        JOIN desi_food i ON s.item_id = i.id AND s.section = 'desi_food'
        WHERE s.bill_id = %s
        UNION ALL
        SELECT s.section, s.item_id, s.quantity, s.total_price, i.name, i.price, i.category
        FROM sales s
        JOIN fast_food i ON s.item_id = i.id AND s.section = 'fast_food'
        WHERE s.bill_id = %s
    """
    cursor.execute(query, (bill_id, bill_id, bill_id))
    items = cursor.fetchall()
    cursor.close()

    # Group items by section
    coffee_shop_items = [item for item in items if item['section'] == 'coffee_shop']
    desi_food_items = [item for item in items if item['section'] == 'desi_food']
    fast_food_items = [item for item in items if item['section'] == 'fast_food']

    # Calculate dynamic height based on rows
    row_height = 8 * mm
    header_height = 50 * mm  # Adjusted header height for additional category info
    num_rows = max(len(coffee_shop_items), len(desi_food_items), len(fast_food_items))
    table_height = header_height + (num_rows * row_height)

    pdf_width = 80 * mm
    pdf_height = table_height + 80 * mm

    # Start creating PDF
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(pdf_width, pdf_height))

    # Helper function to draw each section
    def draw_section(items, section_name):
        # Header Section
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(pdf_width / 2, pdf_height - 15 * mm, f"{section_name} Bill")

        c.setFont("Helvetica", 8)
        c.drawString(5 * mm, pdf_height - 25 * mm, f"Bill ID: {bill_id}")
        c.drawString(5 * mm, pdf_height - 30 * mm, f"Date: {bill['sale_date']}")
        c.drawString(5 * mm, pdf_height - 35 * mm, f"Total Price: {float(bill['total_price']):.2f}")
        c.drawString(5 * mm, pdf_height - 40 * mm, f"Cash Received: {float(bill['cash_received']):.2f}")
        c.drawString(5 * mm, pdf_height - 45 * mm, f"Change Due: {float(bill['change_due']):.2f}")

        # Body Section (Table)
        data = [['Category', 'Item', 'Qty', 'Price']]
        for item in items:
            data.append([item['category'], item['name'], str(item['quantity']), f"{float(item['total_price']):.2f}"])

        table = Table(data, colWidths=[16 * mm, 16 * mm, 15 * mm, 25 * mm])

        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.black),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])
        table.setStyle(table_style)

        # Position Table
        table.wrapOn(c, pdf_width, pdf_height)
        table.drawOn(c, 5 * mm, pdf_height - 15 * mm - table_height)

        # Footer Section
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(pdf_width / 2, 25 * mm, "** UOS CAFETERIA ONE ***")

    # Page 1: Coffee Shop Items
    if coffee_shop_items:
        draw_section(coffee_shop_items, "Coffee Shop")
        c.showPage()  # Move to next page

    # Page 2: Desi Food Items
    if desi_food_items:
        draw_section(desi_food_items, "Desi Food")
        c.showPage()  # Move to next page

    # Page 3: Fast Food Items
    if fast_food_items:
        draw_section(fast_food_items, "Fast Food")
        c.showPage()

    # Finish PDF
    c.save()

    pdf_buffer.seek(0)
    return Response(pdf_buffer, mimetype='application/pdf', headers={'Content-Disposition': f'inline; filename="bill_{bill_id}.pdf"'})




##################################################### Fast Food ##############################################################




@app.route('/fast_food_dasboard')
@role_required('fast_food_man', 'admin')
def fast_food_dasboard():
    return render_template('Fast_food/fast_food_dashboard.html')


@app.route('/fast_food_items')
@role_required('fast_food_man', 'admin')
def fast_food_items():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, name, price, category FROM fast_food")
    items = cursor.fetchall()
    cursor.close()
    return render_template('Fast_food/fast_food_items.html', items=items)

@app.route('/add_fast_food_item', methods=['GET', 'POST'])
@role_required('fast_food_man', 'admin')  # Role-based access control
def add_fast_food_item():
    if request.method == 'POST':
        # Handle form submission for multiple items
        names = request.form.getlist('name')   # Get list of names
        prices = request.form.getlist('price') # Get list of prices
        categories = request.form.getlist('category')  # Get list of categories (can be empty)

        cur = mysql.connection.cursor()

        # Insert each item into the database, checking for an optional category
        for name, price, category in zip(names, prices, categories):
            if category.strip():  # If category is provided
                cur.execute("INSERT INTO fast_food (name, price, category) VALUES (%s, %s, %s)", 
                            (name.strip(), price.strip(), category.strip()))
            else:  # If no category is provided, set it to NULL
                cur.execute("INSERT INTO fast_food (name, price, category) VALUES (%s, %s, NULL)", 
                            (name.strip(), price.strip()))
        
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('fast_food_items'))

    return render_template('Fast_food/add_fast_food_item.html')


@app.route('/update_fast_food_item/<int:id>', methods=['GET', 'POST'])
@role_required('fast_food_man', 'admin')
def update_fast_food_item(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch the existing item details
    cursor.execute("SELECT id, name, price, category FROM fast_food WHERE id = %s", [id])
    item = cursor.fetchone()
    
    if request.method == 'POST':
        new_name = request.form['name']
        new_price = request.form['price']
        new_category = request.form.get('category', '')  # Fetch category (empty string if not provided)
        
        # Update the item in the database
        cursor.execute("""
            UPDATE fast_food
            SET name = %s, price = %s, category = %s
            WHERE id = %s
        """, (new_name, new_price, new_category if new_category.strip() else None, id))
        
        mysql.connection.commit()
        cursor.close()
        
        return redirect(url_for('fast_food_items'))
    
    cursor.close()
    return render_template('Fast_food/update_fast_food_item.html', item=item)


@app.route('/delete_fast_food_item/<int:id>', methods=['GET'])
@role_required('fast_food_man', 'admin')
def delete_fast_food_item(id):
    cursor = mysql.connection.cursor()
    
    # Delete the item from the database
    cursor.execute("DELETE FROM fast_food WHERE id = %s", [id])
    mysql.connection.commit()
    cursor.close()
    
    return redirect(url_for('fast_food_items'))


@app.route('/generate_fast_food_bill')
@role_required('fast_food_man', 'admin')
def generate_fast_food_bill():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch items with category
    cursor.execute("SELECT id, name, price, category FROM coffee_shop")
    coffee_shop_items = cursor.fetchall()

    cursor.execute("SELECT id, name, price, category FROM desi_food")
    desi_food_items = cursor.fetchall()

    cursor.execute("SELECT id, name, price, category FROM fast_food")
    fast_food_items = cursor.fetchall()

    cursor.close()

    return render_template('Fast_food/generate_fast_food_bill.html',
                           coffee_shop_items=coffee_shop_items,
                           desi_food_items=desi_food_items, 
                           fast_food_items=fast_food_items)



@app.route('/fast_food_bill', methods=['POST'])
@role_required('fast_food_man', 'admin')
def fast_food_bill():
    items = request.form.getlist('items')
    quantities = request.form.getlist('quantities')

    total_price = 0.0
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Generate a new bill ID
    bill_id = generate1_random_bill_id()
    bill_type = request.form.get('bill_type', 'student')

    try:
        # Create a new bill entry
        cursor.execute("""
            INSERT INTO bills (id, sale_date, status, bill_type) 
            VALUES (%s, NOW(), 'draft', %s)
        """, (bill_id, bill_type))

        for item, quantity in zip(items, quantities):
            section, item_id = item.split('|')
            quantity = int(quantity)

            # Fetch item price from the relevant section table
            cursor.execute(f"SELECT price FROM {section} WHERE id = %s", (item_id,))
            result = cursor.fetchone()
            if result:
                price = float(result['price'])
                item_total_price = price * quantity
                total_price += item_total_price

                # Insert sales record
                cursor.execute("""
                    INSERT INTO sales (bill_id, section, item_id, quantity, total_price, sale_date) 
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (bill_id, section, item_id, quantity, item_total_price))
            else:
                print(f"Item with ID {item_id} not found in section {section}")

        cash_received = request.form.get('cash_received', type=float, default=0.0)
        change_due = cash_received - total_price

        # Update bill with total price, cash received, and change due
        cursor.execute("""
            UPDATE bills 
            SET total_price = %s, cash_received = %s, change_due = %s 
            WHERE id = %s
        """, (total_price, cash_received, change_due, bill_id))

        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        print(f"Error occurred: {e}")
        return jsonify({'success': False, 'message': 'Failed to generate bill'}), 500
    finally:
        cursor.close()

    return redirect(url_for('fast_confirm_bill', bill_id=bill_id))


@app.route('/fast_confirm_bill/<string:bill_id>', methods=['GET', 'POST'])
def fast_confirm_bill(bill_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch bill details
    cursor.execute("SELECT * FROM bills WHERE id = %s AND status = 'draft'", (bill_id,))
    bill = cursor.fetchone()

    if not bill:
        return jsonify({'success': False, 'message': 'Bill not found or already confirmed/canceled'}), 404

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'confirm':
            cursor.execute("UPDATE bills SET status = 'confirmed' WHERE id = %s", (bill_id,))
            mysql.connection.commit()
            pdf_url = url_for('view_fast_food_bill', bill_id=bill_id)
            return jsonify({'success': True, 'pdf_url': pdf_url})

        elif action == 'cancel':
            cursor.execute("UPDATE bills SET status = 'canceled' WHERE id = %s", (bill_id,))
            mysql.connection.commit()
            return jsonify({'success': True, 'message': 'Bill canceled'})

    return render_template('Fast_food/fast_confirm_bill.html', bill=bill)

@app.route('/view_fast_food_bill/<string:bill_id>')
@role_required('fast_food_man', 'admin')
def view_fast_food_bill(bill_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch bill details
    cursor.execute("SELECT * FROM bills WHERE id = %s AND status = 'confirmed'", (bill_id,))
    bill = cursor.fetchone()

    if not bill:
        return "Bill not confirmed or not found", 404

    # Fetch items related to this bill, including category
    query = """
        SELECT s.section, s.item_id, s.quantity, s.total_price, i.name, i.price, i.category
        FROM sales s
        JOIN coffee_shop i ON s.item_id = i.id AND s.section = 'coffee_shop'
        WHERE s.bill_id = %s
        UNION ALL
        SELECT s.section, s.item_id, s.quantity, s.total_price, i.name, i.price, i.category
        FROM sales s
        JOIN desi_food i ON s.item_id = i.id AND s.section = 'desi_food'
        WHERE s.bill_id = %s
        UNION ALL
        SELECT s.section, s.item_id, s.quantity, s.total_price, i.name, i.price, i.category
        FROM sales s
        JOIN fast_food i ON s.item_id = i.id AND s.section = 'fast_food'
        WHERE s.bill_id = %s
    """
    cursor.execute(query, (bill_id, bill_id, bill_id))
    items = cursor.fetchall()
    cursor.close()

    # Calculate dynamic height
    row_height = 8 * mm
    header_height = 50 * mm  # Adjusted header height for additional category info
    num_rows = len(items)
    table_height = header_height + (num_rows * row_height)

    pdf_width = 80 * mm
    pdf_height = table_height + 80 * mm
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(pdf_width, pdf_height))

    # Header Section
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(pdf_width / 2, pdf_height - 15 * mm, "Coffee Shop Bill")

    c.setFont("Helvetica", 8)
    c.drawString(5 * mm, pdf_height - 25 * mm, f"Bill ID: {bill_id}")
    c.drawString(5 * mm, pdf_height - 30 * mm, f"Date: {bill['sale_date']}")
    c.drawString(5 * mm, pdf_height - 35 * mm, f"Total Price: {float(bill['total_price']):.2f}")
    c.drawString(5 * mm, pdf_height - 40 * mm, f"Cash Received: {float(bill['cash_received']):.2f}")
    c.drawString(5 * mm, pdf_height - 45 * mm, f"Change Due: {float(bill['change_due']):.2f}")

    # Body Section (Table)
    data = [['Category', 'Item', 'Qty', 'Price']]
    for item in items:
        data.append([item['category'], item['name'], str(item['quantity']), f"{float(item['total_price']):.2f}"])

    table = Table(data, colWidths=[16 * mm, 16 * mm, 15 * mm, 25 * mm])

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])
    table.setStyle(table_style)

    # Position Table
    table.wrapOn(c, pdf_width, pdf_height)
    table.drawOn(c, 5 * mm, pdf_height - 15 * mm - table_height)

    # Footer Section
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(pdf_width / 2, 25 * mm, "** UOS CAFETERIA ONE ***")

    # Finish PDF
    c.save()

    pdf_buffer.seek(0)
    return Response(pdf_buffer, mimetype='application/pdf', headers={'Content-Disposition': f'inline; filename="bill_{bill_id}.pdf"'})






##################################################### Desi Food ##############################################################




@app.route('/desi_food_dasboard')
@role_required('desi_food_man', 'admin')
def desi_food_dasboard():
    return render_template('Desi_food/desi_food_dashboard.html')


@app.route('/desi_food_items')
@role_required('desi_food_man', 'admin')
def desi_food_items():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, name, price, category FROM desi_food")
    items = cursor.fetchall()
    cursor.close()
    return render_template('Desi_food/desi_food_items.html', items=items)

@app.route('/add_desi_food_item', methods=['GET', 'POST'])
@role_required('desi_food_man', 'admin')
def add_desi_food_item():
    if request.method == 'POST':
        # Handle form submission for multiple items
        names = request.form.getlist('name')   # Get list of names
        prices = request.form.getlist('price') # Get list of prices
        categories = request.form.getlist('category')  # Get list of categories (can be empty)

        cur = mysql.connection.cursor()

        # Insert each item into the database, checking for an optional category
        for name, price, category in zip(names, prices, categories):
            if category.strip():  # If category is provided
                cur.execute("INSERT INTO desi_food (name, price, category) VALUES (%s, %s, %s)", 
                            (name.strip(), price.strip(), category.strip()))
            else:  # If no category is provided, set it to NULL
                cur.execute("INSERT INTO desi_food (name, price, category) VALUES (%s, %s, NULL)", 
                            (name.strip(), price.strip()))
        
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('desi_food_items'))

    return render_template('Desi_food/add_desi_food_item.html')


@app.route('/update_desi_food_item/<int:id>', methods=['GET', 'POST'])
@role_required('desi_food_man', 'admin')
def update_desi_food_item(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch the existing item details
    cursor.execute("SELECT id, name, price, category FROM desi_food WHERE id = %s", [id])
    item = cursor.fetchone()
    
    if request.method == 'POST':
        new_name = request.form['name']
        new_price = request.form['price']
        new_category = request.form.get('category', '')  # Fetch category (empty string if not provided)
        
        # Update the item in the database
        cursor.execute("""
            UPDATE desi_food
            SET name = %s, price = %s, category = %s
            WHERE id = %s
        """, (new_name, new_price, new_category if new_category.strip() else None, id))
        
        mysql.connection.commit()
        cursor.close()
        
        return redirect(url_for('desi_food_items'))
    
    cursor.close()
    return render_template('Desi_food/update_desi_food_item.html', item=item)


@app.route('/delete_desi_food_item/<int:id>', methods=['GET'])
@role_required('desi_food_man', 'admin')
def delete_desi_food_item(id):
    cursor = mysql.connection.cursor()
    
    # Delete the item from the database
    cursor.execute("DELETE FROM desi_food WHERE id = %s", [id])
    mysql.connection.commit()
    cursor.close()
    
    return redirect(url_for('desi_food_items'))



@app.route('/generate_desi_food_bill')
@role_required('desi_food_man', 'admin')
def generate_desi_food_bill():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch items with category
    cursor.execute("SELECT id, name, price, category FROM coffee_shop")
    coffee_shop_items = cursor.fetchall()

    cursor.execute("SELECT id, name, price, category FROM desi_food")
    desi_food_items = cursor.fetchall()

    cursor.execute("SELECT id, name, price, category FROM fast_food")
    fast_food_items = cursor.fetchall()

    cursor.close()

    return render_template('Desi_food/generate_desi_food_bill.html',
                           coffee_shop_items=coffee_shop_items, 
                           desi_food_items=desi_food_items,
                           fast_food_items=fast_food_items)



@app.route('/desi_food_bill', methods=['POST'])
@role_required('desi_food_man', 'admin')
def desi_food_bill():
    items = request.form.getlist('items')
    quantities = request.form.getlist('quantities')

    total_price = 0.0
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Generate a new bill ID
    bill_id = generate2_random_bill_id()
    bill_type = request.form.get('bill_type', 'student')

    try:
        # Create a new bill entry
        cursor.execute("""
            INSERT INTO bills (id, sale_date, status, bill_type) 
            VALUES (%s, NOW(), 'draft', %s)
        """, (bill_id, bill_type))

        for item, quantity in zip(items, quantities):
            section, item_id = item.split('|')
            quantity = int(quantity)

            # Fetch item price from the relevant section table
            cursor.execute(f"SELECT price FROM {section} WHERE id = %s", (item_id,))
            result = cursor.fetchone()
            if result:
                price = float(result['price'])
                item_total_price = price * quantity
                total_price += item_total_price

                # Insert sales record
                cursor.execute("""
                    INSERT INTO sales (bill_id, section, item_id, quantity, total_price, sale_date) 
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (bill_id, section, item_id, quantity, item_total_price))
            else:
                print(f"Item with ID {item_id} not found in section {section}")

        cash_received = request.form.get('cash_received', type=float, default=0.0)
        change_due = cash_received - total_price

        # Update bill with total price, cash received, and change due
        cursor.execute("""
            UPDATE bills 
            SET total_price = %s, cash_received = %s, change_due = %s 
            WHERE id = %s
        """, (total_price, cash_received, change_due, bill_id))

        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        print(f"Error occurred: {e}")
        return jsonify({'success': False, 'message': 'Failed to generate bill'}), 500
    finally:
        cursor.close()

    return redirect(url_for('desi_confirm_bill', bill_id=bill_id))


@app.route('/desi_confirm_bill/<string:bill_id>', methods=['GET', 'POST'])
def desi_confirm_bill(bill_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch bill details
    cursor.execute("SELECT * FROM bills WHERE id = %s AND status = 'draft'", (bill_id,))
    bill = cursor.fetchone()

    if not bill:
        return jsonify({'success': False, 'message': 'Bill not found or already confirmed/canceled'}), 404

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'confirm':
            cursor.execute("UPDATE bills SET status = 'confirmed' WHERE id = %s", (bill_id,))
            mysql.connection.commit()
            pdf_url = url_for('view_desi_food_bill', bill_id=bill_id)
            return jsonify({'success': True, 'pdf_url': pdf_url})

        elif action == 'cancel':
            cursor.execute("UPDATE bills SET status = 'canceled' WHERE id = %s", (bill_id,))
            mysql.connection.commit()
            return jsonify({'success': True, 'message': 'Bill canceled'})

    return render_template('Desi_food/desi_confirm_bill.html', bill=bill)

@app.route('/view_desi_food_bill/<string:bill_id>')
@role_required('desi_food_man', 'admin')
def view_desi_food_bill(bill_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch bill details
    cursor.execute("SELECT * FROM bills WHERE id = %s AND status = 'confirmed'", (bill_id,))
    bill = cursor.fetchone()

    if not bill:
        return "Bill not confirmed or not found", 404

    # Fetch items related to this bill, including category
    query = """
        SELECT s.section, s.item_id, s.quantity, s.total_price, i.name, i.price, i.category
        FROM sales s
        JOIN coffee_shop i ON s.item_id = i.id AND s.section = 'coffee_shop'
        WHERE s.bill_id = %s
        UNION ALL
        SELECT s.section, s.item_id, s.quantity, s.total_price, i.name, i.price, i.category
        FROM sales s
        JOIN desi_food i ON s.item_id = i.id AND s.section = 'desi_food'
        WHERE s.bill_id = %s
        UNION ALL
        SELECT s.section, s.item_id, s.quantity, s.total_price, i.name, i.price, i.category
        FROM sales s
        JOIN fast_food i ON s.item_id = i.id AND s.section = 'fast_food'
        WHERE s.bill_id = %s
    """
    cursor.execute(query, (bill_id, bill_id, bill_id))
    items = cursor.fetchall()
    cursor.close()

    # Calculate dynamic height
    row_height = 8 * mm
    header_height = 50 * mm  # Adjusted header height for additional category info
    num_rows = len(items)
    table_height = header_height + (num_rows * row_height)

    pdf_width = 80 * mm
    pdf_height = table_height + 80 * mm
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(pdf_width, pdf_height))

    # Header Section
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(pdf_width / 2, pdf_height - 15 * mm, "Coffee Shop Bill")

    c.setFont("Helvetica", 8)
    c.drawString(5 * mm, pdf_height - 25 * mm, f"Bill ID: {bill_id}")
    c.drawString(5 * mm, pdf_height - 30 * mm, f"Date: {bill['sale_date']}")
    c.drawString(5 * mm, pdf_height - 35 * mm, f"Total Price: {float(bill['total_price']):.2f}")
    c.drawString(5 * mm, pdf_height - 40 * mm, f"Cash Received: {float(bill['cash_received']):.2f}")
    c.drawString(5 * mm, pdf_height - 45 * mm, f"Change Due: {float(bill['change_due']):.2f}")

    # Body Section (Table)
    data = [['Category', 'Item', 'Qty', 'Price']]
    for item in items:
        data.append([item['category'], item['name'], str(item['quantity']), f"{float(item['total_price']):.2f}"])

    table = Table(data, colWidths=[16 * mm, 16 * mm, 15 * mm, 25 * mm])

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])
    table.setStyle(table_style)

    # Position Table
    table.wrapOn(c, pdf_width, pdf_height)
    table.drawOn(c, 5 * mm, pdf_height - 15 * mm - table_height)

    # Footer Section
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(pdf_width / 2, 25 * mm, "** UOS CAFETERIA ONE ***")

    # Finish PDF
    c.save()

    pdf_buffer.seek(0)
    return Response(pdf_buffer, mimetype='application/pdf', headers={'Content-Disposition': f'inline; filename="bill_{bill_id}.pdf"'})







##################################################### Tuck Shop ##############################################################




@app.route('/tuck_shop_dasboard')
@role_required('tuck_shop_man', 'admin')
def tuck_shop_dasboard():
    return render_template('Tuck_shop/tuck_shop_dasboard.html')


@app.route('/tuck_shop_items')
@role_required('tuck_shop_man', 'admin')
def tuck_shop_items():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, name, price, category FROM tuck_shop")
    items = cursor.fetchall()
    cursor.close()
    return render_template('Tuck_shop/tuck_shop_items.html', items=items)

@app.route('/add_tuck_shop_items', methods=['GET', 'POST'])
@role_required('tuck_shop_man', 'admin')
def add_tuck_shop_items():
    if request.method == 'POST':
        # Handle form submission for multiple items
        names = request.form.getlist('name')   # Get list of names
        prices = request.form.getlist('price') # Get list of prices
        categories = request.form.getlist('category')  # Get list of categories (can be empty)

        cur = mysql.connection.cursor()

        # Insert each item into the database, checking for an optional category
        for name, price, category in zip(names, prices, categories):
            if category.strip():  # If category is provided
                cur.execute("INSERT INTO tuck_shop (name, price, category) VALUES (%s, %s, %s)", 
                            (name.strip(), price.strip(), category.strip()))
            else:  # If no category is provided, set it to NULL
                cur.execute("INSERT INTO tuck_shop (name, price, category) VALUES (%s, %s, NULL)", 
                            (name.strip(), price.strip()))
        
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('tuck_shop_items'))

    return render_template('Tuck_shop/add_tuck_shop_items.html')


@app.route('/update_tuck_shop_items/<int:id>', methods=['GET', 'POST'])
@role_required('tuck_shop_man', 'admin')
def update_tuck_shop_items(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch the existing item details
    cursor.execute("SELECT id, name, price, category FROM tuck_shop WHERE id = %s", [id])
    item = cursor.fetchone()
    
    if request.method == 'POST':
        new_name = request.form['name']
        new_price = request.form['price']
        new_category = request.form.get('category', '')  # Fetch category (empty string if not provided)
        
        # Update the item in the database
        cursor.execute("""
            UPDATE tuck_shop
            SET name = %s, price = %s, category = %s
            WHERE id = %s
        """, (new_name, new_price, new_category if new_category.strip() else None, id))
        
        mysql.connection.commit()
        cursor.close()
        
        return redirect(url_for('tuck_shop_items'))
    
    cursor.close()
    return render_template('Tuck_shop/update_tuck_shop_items.html', item=item)


@app.route('/delete_tuck_shop_items/<int:id>', methods=['GET'])
@role_required('tuck_shop_man', 'admin')
def delete_tuck_shop_items(id):
    cursor = mysql.connection.cursor()
    
    # Delete the item from the database
    cursor.execute("DELETE FROM tuck_shop WHERE id = %s", [id])
    mysql.connection.commit()
    cursor.close()
    
    return redirect(url_for('tuck_shop_items'))



@app.route('/generate_tuck_Shop_bill')
@role_required('tuck_shop_man', 'admin' )
def generate_tuck_Shop_bill():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT id, name, price FROM tuck_shop")
    tuck_shop_items = cursor.fetchall()

    cursor.close()

    return render_template('Tuck_shop/generate_tuck_Shop_bill.html', 
                           tuck_shop_items=tuck_shop_items)



@app.route('/tuck_shop_bill', methods=['POST'])
@role_required('tuck_shop_man', 'admin')
def tuck_shop_bill():
    items = request.form.getlist('items')
    quantities = request.form.getlist('quantities')

    total_price = 0.0
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Generate a new bill ID
    bill_id = generate3_random_bill_id()
    bill_type = request.form.get('bill_type', 'student')

    try:
        # Create a new bill entry
        cursor.execute("""
            INSERT INTO bills (id, sale_date, status, bill_type) 
            VALUES (%s, NOW(), 'draft', %s)
        """, (bill_id, bill_type))

        for item, quantity in zip(items, quantities):
            section, item_id = item.split('|')
            quantity = int(quantity)

            # Fetch item price from the relevant section table
            cursor.execute(f"SELECT price FROM {section} WHERE id = %s", (item_id,))
            result = cursor.fetchone()
            if result:
                price = float(result['price'])
                item_total_price = price * quantity
                total_price += item_total_price

                # Insert sales record
                cursor.execute("""
                    INSERT INTO sales (bill_id, section, item_id, quantity, total_price, sale_date) 
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (bill_id, section, item_id, quantity, item_total_price))
            else:
                print(f"Item with ID {item_id} not found in section {section}")

        cash_received = request.form.get('cash_received', type=float, default=0.0)
        change_due = cash_received - total_price

        # Update bill with total price, cash received, and change due
        cursor.execute("""
            UPDATE bills 
            SET total_price = %s, cash_received = %s, change_due = %s 
            WHERE id = %s
        """, (total_price, cash_received, change_due, bill_id))

        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        print(f"Error occurred: {e}")
        return jsonify({'success': False, 'message': 'Failed to generate bill'}), 500
    finally:
        cursor.close()

    return redirect(url_for('tuck_confirm_bill', bill_id=bill_id))


@app.route('/tuck_confirm_bill/<string:bill_id>', methods=['GET', 'POST'])
def tuck_confirm_bill(bill_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch bill details
    cursor.execute("SELECT * FROM bills WHERE id = %s AND status = 'draft'", (bill_id,))
    bill = cursor.fetchone()

    if not bill:
        return jsonify({'success': False, 'message': 'Bill not found or already confirmed/canceled'}), 404

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'confirm':
            cursor.execute("UPDATE bills SET status = 'confirmed' WHERE id = %s", (bill_id,))
            mysql.connection.commit()
            pdf_url = url_for('view_tuck_shop_bill', bill_id=bill_id)
            return jsonify({'success': True, 'pdf_url': pdf_url})

        elif action == 'cancel':
            cursor.execute("UPDATE bills SET status = 'canceled' WHERE id = %s", (bill_id,))
            mysql.connection.commit()
            return jsonify({'success': True, 'message': 'Bill canceled'})

    return render_template('Tuck_Shop/tuck_confirm_bill.html', bill=bill)


@app.route('/view_tuck_shop_bill/<string:bill_id>')
@role_required('tuck_shop_man', 'admin')
def view_tuck_shop_bill(bill_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch bill details
    cursor.execute("SELECT * FROM bills WHERE id = %s AND status = 'confirmed'", (bill_id,))
    bill = cursor.fetchone()

    if not bill:
        return "Bill not confirmed or not found", 404

    # Fetch items related to this bill, including section, item details, and category
    query = """
        SELECT s.section, s.item_id, s.quantity, s.total_price, i.name, i.price, i.category
        FROM sales s
        JOIN tuck_shop i ON s.item_id = i.id
        WHERE s.bill_id = %s AND s.section = 'tuck_shop'
    """
    # Correct the way you're passing parameters (ensure it's a tuple)
    cursor.execute(query, (bill_id,))
    items = cursor.fetchall()
    cursor.close()


    # Calculate dynamic height
    row_height = 8 * mm
    header_height = 50 * mm  # Adjusted header height for additional category info
    num_rows = len(items)
    table_height = header_height + (num_rows * row_height)

    pdf_width = 80 * mm
    pdf_height = table_height + 80 * mm
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(pdf_width, pdf_height))

    # Header Section
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(pdf_width / 2, pdf_height - 15 * mm, "Coffee Shop Bill")

    c.setFont("Helvetica", 8)
    c.drawString(5 * mm, pdf_height - 25 * mm, f"Bill ID: {bill_id}")
    c.drawString(5 * mm, pdf_height - 30 * mm, f"Date: {bill['sale_date']}")
    c.drawString(5 * mm, pdf_height - 35 * mm, f"Total Price: {float(bill['total_price']):.2f}")
    c.drawString(5 * mm, pdf_height - 40 * mm, f"Cash Received: {float(bill['cash_received']):.2f}")
    c.drawString(5 * mm, pdf_height - 45 * mm, f"Change Due: {float(bill['change_due']):.2f}")

    # Body Section (Table)
    data = [['Category', 'Item', 'Qty', 'Price']]
    for item in items:
        data.append([item['category'], item['name'], str(item['quantity']), f"{float(item['total_price']):.2f}"])

    table = Table(data, colWidths=[16 * mm, 16 * mm, 15 * mm, 25 * mm])

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])
    table.setStyle(table_style)

    # Position Table
    table.wrapOn(c, pdf_width, pdf_height)
    table.drawOn(c, 5 * mm, pdf_height - 15 * mm - table_height)

    # Footer Section
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(pdf_width / 2, 25 * mm, "** UOS CAFETERIA ONE ***")

    # Finish PDF
    c.save()

    pdf_buffer.seek(0)
    return Response(pdf_buffer, mimetype='application/pdf', headers={'Content-Disposition': f'inline; filename="bill_{bill_id}.pdf"'})



############################################ Stocks #################################################################


@app.route('/show_stocks')
@role_required('admin')
def show_stocks():
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id, section, item_name, person_delivering, person_receiving, delivery_date, delivery_time FROM stocks;")
        items = cursor.fetchall()
    except Exception as e:
        print(f"Error fetching data: {e}")
        items = []  # Empty list in case of error
    finally:
        cursor.close()
    
    return render_template('Stocks/show_stocks.html', items=items)


@app.route('/add_new_stock', methods=['GET', 'POST'])
@role_required('admin')
def add_new_stock():
    if request.method == 'POST':
        # Handle form submission for multiple items
        section = request.form.getlist('section')   
        item_name = request.form.getlist('item_name') 
        person_delivering = request.form.getlist('person_delivering') 
        person_receiving = request.form.getlist('person_receiving')  

        cur = mysql.connection.cursor()
        for i in range(len(section)):
            # Automatically set delivery_date and delivery_time
            delivery_date = datetime.now().strftime('%Y-%m-%d')
            delivery_time = datetime.now().strftime('%H:%M:%S')

            cur.execute("""
                INSERT INTO stocks (section, item_name, person_delivering, person_receiving, delivery_date, delivery_time)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (section[i], item_name[i], person_delivering[i], person_receiving[i], delivery_date, delivery_time))

        mysql.connection.commit()
        cur.close()

        return redirect(url_for('show_stocks'))

    return render_template('Stocks/add_new_stocks.html')






@app.route('/update_stock/<int:id>', methods=['GET', 'POST'])
@role_required('admin')
def update_stock(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        section = request.form['section']
        item_name = request.form['item_name']
        person_delivering = request.form['person_delivering']
        person_receiving = request.form['person_receiving']

        cur.execute("""
            UPDATE stocks
            SET section = %s, item_name = %s, person_delivering = %s, person_receiving = %s
            WHERE id = %s
        """, (section, item_name, person_delivering, person_receiving, id))

        mysql.connection.commit()
        cur.close()

        return redirect(url_for('show_stocks'))

    cur.execute("SELECT * FROM stocks WHERE id = %s", (id,))
    stock = cur.fetchone()
    cur.close()

    return render_template('Stocks/update_stocks.html', stock=stock)




@app.route('/delete_stock/<int:id>', methods=['POST'])
@role_required('admin')
def delete_stock(id):
    cur = mysql.connection.cursor()
    
    try:
        # Execute SQL DELETE command
        cur.execute("DELETE FROM stocks WHERE id = %s", (id,))
        mysql.connection.commit()
        flash('Stock item deleted successfully!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error deleting stock item: {e}', 'error')
    finally:
        cur.close()

    return redirect(url_for('show_stocks'))





##################################################Randomly generating uniqe id's for every section##################################################################

def generate_random_bill_id():
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"C{random_part}"

def generate1_random_bill_id():
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"F{random_part}"

def generate2_random_bill_id():
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"D{random_part}"

def generate3_random_bill_id():
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"T{random_part}"


if __name__ == '__main__':
    app.run(debug=True)

