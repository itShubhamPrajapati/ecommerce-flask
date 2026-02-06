from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import ast
import random
import string
from datetime import datetime
import razorpay
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'mysecretkey12345')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///shop.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Razorpay Setup
razorpay_client = razorpay.Client(auth=(
    os.getenv('RAZORPAY_KEY_ID', 'rzp_test_SCpmnAZ9GWccsN'),
    os.getenv('RAZORPAY_KEY_SECRET', '1oNsRbN7NVSs7shL5dw4cePP')
))

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    phone = db.Column(db.String(15))
    address = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    discount_price = db.Column(db.Float)
    category = db.Column(db.String(50))
    image = db.Column(db.String(500))
    stock = db.Column(db.Integer, default=10)
    rating = db.Column(db.Float, default=4.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), unique=True)
    user_id = db.Column(db.Integer)
    user_email = db.Column(db.String(100))
    items = db.Column(db.Text)  # JSON string of cart items
    total = db.Column(db.Float)
    payment_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Helper functions
def get_cart():
    return session.get('cart', {})

def get_cart_count():
    cart = get_cart()
    return sum(cart.values())

def get_cart_total():
    cart = get_cart()
    total = 0
    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            price = product.discount_price if product.discount_price else product.price
            total += price * quantity
    return total

def get_cart_items():
    cart = get_cart()
    items = []
    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            price = product.discount_price if product.discount_price else product.price
            items.append({
                'id': str(product.id),
                'name': product.name,
                'price': price,
                'image': product.image,
                'quantity': quantity,
                'total': price * quantity
            })
    return items

def parse_order_items(items_string):
    """Parse order items from string to Python list"""
    if not items_string:
        return []
    
    try:
        # Try JSON parsing first
        return json.loads(items_string)
    except json.JSONDecodeError:
        try:
            # Try ast.literal_eval for Python string representation
            return ast.literal_eval(items_string)
        except:
            return []
    except Exception:
        return []

def is_logged_in():
    return 'user_id' in session

def is_admin():
    return session.get('is_admin', False)

def generate_order_id():
    """Generate unique order ID"""
    return 'ORD' + ''.join(random.choices(string.digits, k=10))

# Initialize database with sample data
def init_database():
    with app.app_context():
        # Drop all tables and recreate (for development)
        db.drop_all()
        db.create_all()
        
        # Create admin user
        admin = User(
            name='Admin',
            email='admin@shop.com',
            password=generate_password_hash('admin123'),
            phone='1234567890',
            is_admin=True
        )
        db.session.add(admin)
        print("✅ Admin user created: admin@shop.com / admin123")
        
        # Add sample products
        sample_products = [
            Product(
                name='iPhone 15 Pro',
                description='Latest iPhone with A17 Pro chip',
                price=134900,
                discount_price=129900,
                category='Electronics',
                image='https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=500&auto=format&fit=crop',
                stock=50,
                rating=4.8
            ),
            Product(
                name='MacBook Air M2',
                description='Supercharged by M2 chip',
                price=99900,
                category='Electronics',
                image='https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=500&auto=format&fit=crop',
                stock=30,
                rating=4.7
            ),
            Product(
                name='Sony Headphones',
                description='Noise cancelling headphones',
                price=29990,
                discount_price=26990,
                category='Electronics',
                image='https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&auto=format&fit=crop',
                stock=100,
                rating=4.6
            ),
            Product(
                name='Nike Air Max',
                description='Comfortable sports shoes',
                price=11995,
                category='Fashion',
                image='https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500&auto=format&fit=crop',
                stock=200,
                rating=4.5
            ),
            Product(
                name='Samsung 4K TV',
                description='55-inch Smart Television',
                price=54990,
                discount_price=49990,
                category='Electronics',
                image='https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=500&auto=format&fit=crop',
                stock=25,
                rating=4.4
            ),
            Product(
                name='The Lean Startup',
                description='Business book by Eric Ries',
                price=499,
                category='Books',
                image='https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=500&auto=format&fit=crop',
                stock=500,
                rating=4.6
            ),
            Product(
                name='Apple Watch Series 9',
                description='Smart watch with health features',
                price=45900,
                discount_price=42900,
                category='Electronics',
                image='https://images.unsplash.com/photo-1579586337278-3fbd4c400cfa?w=500&auto=format&fit=crop',
                stock=40,
                rating=4.7
            ),
            Product(
                name='Canon EOS R5',
                description='Professional mirrorless camera',
                price=329999,
                category='Electronics',
                image='https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=500&auto=format&fit=crop',
                stock=15,
                rating=4.9
            )
        ]
        db.session.add_all(sample_products)
        print("✅ 8 sample products added")
        
        db.session.commit()
        print("✅ Database initialized successfully!")

# Initialize database on startup
init_database()

# Custom Jinja2 filters
@app.template_filter('from_json')
def from_json_filter(value):
    """Custom filter to parse JSON strings in templates"""
    return parse_order_items(value)

@app.template_filter('format_price')
def format_price_filter(price):
    """Format price with Indian Rupee symbol"""
    return f"₹{price:,.2f}"

@app.template_filter('calculate_discount')
def calculate_discount_filter(original, discounted):
    """Calculate discount percentage"""
    if not discounted:
        return 0
    return int(((original - discounted) / original) * 100)

# Context processor for template variables - FIXED
@app.context_processor
def inject_utilities():
    """Make these functions available in all templates"""
    return {
        'parse_order_items': parse_order_items,
        'is_logged_in': is_logged_in,
        'is_admin': is_admin,
        'get_cart_count': get_cart_count,
        'cart_count': get_cart_count()  # This is the fix - call the function
    }

# Routes
@app.route('/')
def home():
    products = Product.query.limit(8).all()
    featured = Product.query.filter(Product.discount_price.isnot(None)).limit(4).all()
    return render_template('home.html', 
                         products=products, 
                         featured=featured)

@app.route('/products')
def products():
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    
    query = Product.query
    
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Product.name.contains(search))
    
    products = query.all()
    categories = ['Electronics', 'Fashion', 'Home', 'Books', 'Sports', 'Beauty']
    
    return render_template('products.html', 
                         products=products,
                         categories=categories,
                         selected_category=category)

@app.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get_or_404(id)
    related = Product.query.filter(Product.category == product.category, Product.id != id).limit(4).all()
    return render_template('products/product_detail.html', 
                         product=product, 
                         related=related)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_logged_in():
        return redirect('/')
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        
        # Validation
        if not name or not email or not password:
            flash('Please fill in all required fields', 'error')
            return redirect('/register')
        
        # Check if user exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered! Please login instead.', 'error')
            return redirect('/register')
        
        # Check if email is valid
        if '@' not in email or '.' not in email:
            flash('Please enter a valid email address', 'error')
            return redirect('/register')
        
        # Check password length
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return redirect('/register')
        
        # Create new user
        try:
            hashed_password = generate_password_hash(password)
            user = User(
                name=name,
                email=email,
                password=hashed_password,
                phone=phone,
                is_admin=False
            )
            
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect('/login')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Registration failed: {str(e)}', 'error')
            return redirect('/register')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect('/')
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please enter email and password', 'error')
            return redirect('/login')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_email'] = user.email
            session['is_admin'] = user.is_admin
            
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect('/')
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect('/')

@app.route('/profile')
def profile():
    if not is_logged_in():
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    orders = Order.query.filter_by(user_email=user.email).order_by(Order.created_at.desc()).all()
    
    # Parse order items for each order
    for order in orders:
        order.parsed_items = parse_order_items(order.items)
    
    return render_template('profile.html', 
                         user=user, 
                         orders=orders)

@app.route('/add-to-cart/<int:product_id>')
def add_to_cart(product_id):
    product = Product.query.get(product_id)
    if not product:
        flash('Product not found', 'error')
        return redirect('/')
    
    if product.stock <= 0:
        flash('Product is out of stock', 'error')
        return redirect(request.referrer or '/')
    
    cart = get_cart()
    current_qty = cart.get(str(product_id), 0)
    
    if current_qty >= product.stock:
        flash(f'Only {product.stock} items available in stock', 'error')
    else:
        cart[str(product_id)] = current_qty + 1
        session['cart'] = cart
        flash('Product added to cart!', 'success')
    
    return redirect(request.referrer or '/')

@app.route('/cart')
def cart():
    items = get_cart_items()
    total = get_cart_total()
    return render_template('cart.html', 
                         items=items, 
                         total=total)

@app.route('/update-cart', methods=['POST'])
def update_cart():
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Please login first'})
    
    product_id = request.form.get('product_id')
    action = request.form.get('action')
    
    if not product_id or not action:
        return jsonify({'success': False, 'message': 'Invalid request'})
    
    cart = get_cart()
    
    if action == 'increase':
        product = Product.query.get(int(product_id))
        if product and cart.get(product_id, 0) < product.stock:
            cart[product_id] = cart.get(product_id, 0) + 1
        else:
            return jsonify({'success': False, 'message': 'Product out of stock'})
    elif action == 'decrease':
        if cart.get(product_id, 0) > 1:
            cart[product_id] -= 1
        else:
            cart.pop(product_id, None)
    elif action == 'remove':
        cart.pop(product_id, None)
    else:
        return jsonify({'success': False, 'message': 'Invalid action'})
    
    session['cart'] = cart
    
    # Calculate new totals
    items = get_cart_items()
    total = get_cart_total()
    
    return jsonify({
        'success': True,
        'cart_count': get_cart_count(),
        'cart_total': total,
        'items': items
    })

@app.route('/checkout')
def checkout():
    if not is_logged_in():
        flash('Please login to checkout', 'error')
        return redirect('/login')
    
    items = get_cart_items()
    if not items:
        flash('Your cart is empty', 'error')
        return redirect('/cart')
    
    # Check stock availability
    for item in items:
        product = Product.query.get(int(item['id']))
        if product and product.stock < item['quantity']:
            flash(f'{product.name} has only {product.stock} items in stock', 'error')
            return redirect('/cart')
    
    total = get_cart_total()
    user = User.query.get(session['user_id'])
    
    return render_template('checkout.html',
                         items=items,
                         total=total,
                         user=user)

@app.route('/create-order', methods=['POST'])
def create_order():
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Please login'})
    
    user = User.query.get(session['user_id'])
    items = get_cart_items()
    total = get_cart_total()
    
    if not items:
        return jsonify({'success': False, 'message': 'Cart is empty'})
    
    # Check stock again before creating order
    for item in items:
        product = Product.query.get(int(item['id']))
        if product and product.stock < item['quantity']:
            return jsonify({'success': False, 'message': f'{product.name} is out of stock'})
    
    # Generate order ID
    order_id = generate_order_id()
    
    # Save order to database
    try:
        order = Order(
            order_id=order_id,
            user_id=user.id,
            user_email=user.email,
            items=json.dumps(items),  # Convert list to JSON string
            total=total,
            status='Created'
        )
        db.session.add(order)
        
        # Update product stock
        for item in items:
            product = Product.query.get(int(item['id']))
            if product:
                product.stock -= item['quantity']
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Failed to create order: {str(e)}'})
    
    # Create Razorpay order
    try:
        razorpay_order = razorpay_client.order.create({
            'amount': int(total * 100),  # Convert to paise
            'currency': 'INR',
            'payment_capture': 1,
            'receipt': order_id
        })
        
        # Update order with Razorpay order ID
        order.razorpay_order_id = razorpay_order['id']
        db.session.commit()
        
        return jsonify({
            'success': True,
            'order_id': razorpay_order['id'],
            'amount': total * 100,
            'currency': 'INR',
            'key': os.getenv('RAZORPAY_KEY_ID'),
            'name': 'Modern Shop',
            'description': 'Order Payment',
            'receipt': order_id,
            'user': {
                'name': user.name,
                'email': user.email,
                'phone': user.phone or '9999999999'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Payment gateway error: {str(e)}'})

@app.route('/payment-success', methods=['POST'])
def payment_success():
    payment_id = request.form.get('razorpay_payment_id')
    order_id = request.form.get('razorpay_order_id')
    signature = request.form.get('razorpay_signature')
    
    try:
        # Find order by Razorpay order ID
        order = Order.query.filter_by(razorpay_order_id=order_id).first()
        if order:
            order.payment_id = payment_id
            order.status = 'Paid'
            db.session.commit()
        
        # Clear cart
        session.pop('cart', None)
        
        flash('Payment successful! Your order has been placed.', 'success')
        return redirect('/orders')
        
    except Exception as e:
        flash('Payment verification failed. Please contact support.', 'error')
        return redirect('/orders')

@app.route('/payment-failed')
def payment_failed():
    flash('Payment failed. Please try again.', 'error')
    return redirect('/checkout')

@app.route('/orders')
def orders():
    if not is_logged_in():
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    user_orders = Order.query.filter_by(user_email=user.email).order_by(Order.created_at.desc()).all()
    
    # Parse order items for each order
    for order in user_orders:
        order.parsed_items = parse_order_items(order.items)
    
    return render_template('orders.html', 
                         orders=user_orders)

@app.route('/order/<string:order_id>')
def order_detail(order_id):
    if not is_logged_in():
        return redirect('/login')
    
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    if order.user_email != session.get('user_email') and not is_admin():
        flash('Access denied', 'error')
        return redirect('/')
    
    # Parse order items
    items = parse_order_items(order.items)
    
    return render_template('order_detail.html', 
                         order=order,
                         items=items)

# Admin Routes
@app.route('/admin')
def admin_dashboard():
    if not is_logged_in() or not is_admin():
        flash('Access denied', 'error')
        return redirect('/')
    
    total_orders = Order.query.count()
    total_products = Product.query.count()
    total_users = User.query.count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    # Parse order items for recent orders
    for order in recent_orders:
        order.parsed_items = parse_order_items(order.items)
    
    return render_template('admin/dashboard.html',
                         total_orders=total_orders,
                         total_products=total_products,
                         total_users=total_users,
                         recent_orders=recent_orders)

@app.route('/admin/products')
def admin_products():
    if not is_logged_in() or not is_admin():
        flash('Access denied', 'error')
        return redirect('/')
    
    products = Product.query.all()
    return render_template('admin/products.html', 
                         products=products)

@app.route('/admin/add-product', methods=['GET', 'POST'])
def add_product():
    if not is_logged_in() or not is_admin():
        flash('Access denied', 'error')
        return redirect('/')
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            price = request.form.get('price', '0')
            discount_price = request.form.get('discount_price', '')
            category = request.form.get('category', 'Electronics')
            image = request.form.get('image', '').strip()
            stock = request.form.get('stock', '10')
            
            # Validation
            if not name or not description or not image:
                flash('Please fill in all required fields', 'error')
                return redirect('/admin/add-product')
            
            # Convert values
            price = float(price)
            discount_price = float(discount_price) if discount_price else None
            stock = int(stock)
            
            product = Product(
                name=name,
                description=description,
                price=price,
                discount_price=discount_price,
                category=category,
                image=image,
                stock=stock
            )
            
            db.session.add(product)
            db.session.commit()
            
            flash('Product added successfully!', 'success')
            return redirect('/admin/products')
        except Exception as e:
            flash(f'Error adding product: {str(e)}', 'error')
            return redirect('/admin/add-product')
    
    categories = ['Electronics', 'Fashion', 'Home', 'Books', 'Sports', 'Beauty']
    return render_template('admin/add_product.html', categories=categories)

@app.route('/admin/edit-product/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    if not is_logged_in() or not is_admin():
        flash('Access denied', 'error')
        return redirect('/')
    
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            product.name = request.form.get('name', '').strip()
            product.description = request.form.get('description', '').strip()
            product.price = float(request.form.get('price', '0'))
            
            discount_price = request.form.get('discount_price', '')
            product.discount_price = float(discount_price) if discount_price else None
            
            product.category = request.form.get('category', 'Electronics')
            product.image = request.form.get('image', '').strip()
            product.stock = int(request.form.get('stock', '10'))
            
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect('/admin/products')
        except Exception as e:
            flash(f'Error updating product: {str(e)}', 'error')
    
    categories = ['Electronics', 'Fashion', 'Home', 'Books', 'Sports', 'Beauty']
    return render_template('admin/edit_product.html', product=product, categories=categories)

@app.route('/admin/delete-product/<int:id>')
def delete_product(id):
    if not is_logged_in() or not is_admin():
        flash('Access denied', 'error')
        return redirect('/')
    
    try:
        product = Product.query.get_or_404(id)
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting product: {str(e)}', 'error')
    
    return redirect('/admin/products')

@app.route('/admin/orders')
def admin_orders():
    if not is_logged_in() or not is_admin():
        flash('Access denied', 'error')
        return redirect('/')
    
    orders = Order.query.order_by(Order.created_at.desc()).all()
    
    # Parse order items for each order
    for order in orders:
        order.parsed_items = parse_order_items(order.items)
    
    return render_template('admin/orders.html', 
                         orders=orders)

@app.route('/admin/update-order-status/<string:order_id>', methods=['POST'])
def update_order_status(order_id):
    if not is_logged_in() or not is_admin():
        return jsonify({'success': False, 'message': 'Access denied'})
    
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    new_status = request.json.get('status')
    
    if new_status in ['Pending', 'Paid', 'Shipped', 'Delivered', 'Cancelled']:
        order.status = new_status
        db.session.commit()
        return jsonify({'success': True, 'message': 'Order status updated'})
    
    return jsonify({'success': False, 'message': 'Invalid status'})

# AJAX endpoints
@app.route('/api/cart-count')
def api_cart_count():
    return jsonify({'count': get_cart_count()})

@app.route('/api/clear-cart')
def clear_cart():
    if 'cart' in session:
        session.pop('cart')
    return jsonify({'success': True})

# Health check endpoint
@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting Modern Shop E-commerce Website...")
    print("=" * 60)
    print(f"📁 Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("🌐 Server running at: http://localhost:5000")
    print("🔑 Admin login: admin@shop.com / admin123")
    print("=" * 60)
    app.run(debug=True, port=5000)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
