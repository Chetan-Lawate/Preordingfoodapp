import os
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, MenuItem, FoodItem, TimeSlot, Order, OrderItem

# Set paths for frontend templates and static files
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, 'frontend', 'templates')
STATIC_DIR = os.path.join(PROJECT_ROOT, 'frontend', 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Admin Access Decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('user_menu'))
        return f(*args, **kwargs)
    return decorated_function

# Context Processor for global template variables
@app.context_processor
def inject_global_vars():
    categories = ['All', 'Breakfast', 'Meals', 'Snacks', 'Beverages', 'Desserts']
    
    # Dynamically fetch active time slots from database
    try:
        active_slots_db = TimeSlot.query.filter_by(is_active=True).order_by(TimeSlot.id).all()
        if active_slots_db:
            break_times = [f"{slot.start_time} - {slot.end_time} ({slot.slot_name})" for slot in active_slots_db]
        else:
            break_times = ['10:00 AM - 10:45 AM (Morning Break)', '01:00 PM - 02:00 PM (Lunch Break)', '03:30 PM - 04:15 PM (Tea Break)']
    except Exception:
        break_times = ['10:00 AM - 10:45 AM (Morning Break)', '01:00 PM - 02:00 PM (Lunch Break)', '03:30 PM - 04:15 PM (Tea Break)']

    return dict(categories=categories, break_times=break_times, current_year=datetime.now().year)

# ----------------------------
# PUBLIC / STUDENT ROUTES
# ----------------------------

@app.route('/')
def index():
    # If Admin is logged in, redirect directly to Kitchen Live Orders
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))

    featured_items = MenuItem.query.filter_by(status='Active').limit(6).all()
    return render_template('index.html', featured_items=featured_items)

@app.route('/menu', endpoint='menu')
@app.route('/user_menu', endpoint='user_menu')
@app.route('/user-menu', endpoint='user-menu')
def user_menu():
    category = request.args.get('category', 'All')
    search_query = request.args.get('q', '').strip()
    
    # Students strictly view ONLY Active items
    query = MenuItem.query.filter_by(status='Active')
    if category != 'All':
        query = query.filter_by(category=category)
    if search_query:
        query = query.filter(MenuItem.item_name.ilike(f'%{search_query}%'))
        
    items = query.all()
    return render_template('user_menu.html', items=items, selected_category=category, search_query=search_query)

@app.route('/api/food')
def api_food():
    items = MenuItem.query.filter_by(status='Active').all()
    return jsonify([item.to_dict() for item in items])

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/checkout', methods=['POST'])
def checkout():
    if not current_user.is_authenticated:
        return jsonify({
            'success': False, 
            'message': 'Please sign in to your account to place an order.',
            'redirect': url_for('login', next='/cart')
        }), 401

    data = request.get_json(silent=True) or request.form
    if not data or 'items' not in data or not data['items']:
        return jsonify({'success': False, 'message': 'Your cart is empty.'}), 400
    
    break_time = data.get('break_time')
    if not break_time:
        return jsonify({'success': False, 'message': 'Please select a valid break time for pickup.'}), 400

    items_data = data['items'] # Array of {id, quantity}
    total_price = 0.0
    order_items_to_create = []

    for item_info in items_data:
        menu_id = item_info.get('id')
        qty = item_info.get('quantity', 1)
        menu_item = db.session.get(MenuItem, int(menu_id)) if menu_id else None
        
        if not menu_item or menu_item.status != 'Active':
            return jsonify({'success': False, 'message': f'Item "{menu_item.item_name if menu_item else "Unknown"}" is currently unavailable.'}), 400
        
        item_total = menu_item.price * qty
        total_price += item_total
        order_items_to_create.append((menu_id, qty))

    new_order = Order(
        user_id=current_user.id,
        total_price=total_price,
        break_time=break_time,
        status='Pending'
    )
    db.session.add(new_order)
    db.session.flush()

    for menu_id, qty in order_items_to_create:
        order_item = OrderItem(
            order_id=new_order.id,
            menu_id=menu_id,
            quantity=qty
        )
        db.session.add(order_item)

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Order #{new_order.id} placed successfully for pickup at {break_time}!',
        'order_id': new_order.id
    })

@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=user_orders)

@app.route('/api/orders/<int:order_id>/status')
@login_required
def order_status_api(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    if order.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify({'order_id': order.id, 'status': order.status, 'break_time': order.break_time})

# ----------------------------
# AUTHENTICATION ROUTES
# ----------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard') if current_user.is_admin else url_for('user_menu'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Invalid email or password. Please try again.', 'danger')
            return redirect(url_for('login'))
            
        login_user(user, remember=remember)
        flash(f'Welcome back, {user.username}!', 'success')
        
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('admin_dashboard') if user.is_admin else url_for('user_menu'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard') if current_user.is_admin else url_for('user_menu'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'Student')
        if role not in ['Student', 'Admin']:
            role = 'Student'

        if not username or not email or not password:
            flash('Please fill out all required fields.', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
        if existing_user:
            flash('Email or username already registered.', 'warning')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash('Account registered successfully! Welcome to College Canteen.', 'success')
        return redirect(url_for('admin_dashboard') if new_user.is_admin else url_for('user_menu'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('user_menu'))

# ----------------------------
# ADMIN DASHBOARD, TIME SLOTS & MENU CRUD
# ----------------------------

@app.route('/admin', endpoint='admin')
@app.route('/admin/dashboard', endpoint='admin_dashboard')
@app.route('/kitchen-live-orders', endpoint='kitchen_live_orders')
@admin_required
def admin_dashboard():
    filter_time = request.args.get('break_time', 'All')
    filter_status = request.args.get('status', 'All')

    query = Order.query
    if filter_time != 'All':
        query = query.filter_by(break_time=filter_time)
    if filter_status != 'All':
        query = query.filter_by(status=filter_status)

    orders = query.order_by(Order.created_at.desc()).all()

    # Statistics summary
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='Pending').count()
    cooking_orders = Order.query.filter_by(status='Cooking').count()
    ready_orders = Order.query.filter_by(status='Ready').count()
    completed_orders = Order.query.filter_by(status='Completed').count()

    return render_template(
        'admin_dashboard.html',
        orders=orders,
        total_orders=total_orders,
        pending_orders=pending_orders,
        cooking_orders=cooking_orders,
        ready_orders=ready_orders,
        completed_orders=completed_orders,
        selected_time=filter_time,
        selected_status=filter_status
    )

# Manage Time Slots (GET & POST)
@app.route('/manage-slots', methods=['GET', 'POST'], endpoint='manage_slots')
@app.route('/manage_slots', methods=['GET', 'POST'])
@admin_required
def manage_slots():
    if request.method == 'POST':
        slot_name = request.form.get('slot_name', '').strip()
        start_time = request.form.get('start_time', '').strip()
        end_time = request.form.get('end_time', '').strip()
        is_active = True if request.form.get('is_active') else False

        if not slot_name or not start_time or not end_time:
            flash('Slot name, start time, and end time are required.', 'danger')
            return redirect(url_for('manage_slots'))

        new_slot = TimeSlot(
            slot_name=slot_name,
            start_time=start_time,
            end_time=end_time,
            is_active=is_active
        )
        db.session.add(new_slot)
        db.session.commit()

        flash(f'Time slot "{new_slot.slot_name}" added successfully.', 'success')
        return redirect(url_for('manage_slots'))

    slots = TimeSlot.query.order_by(TimeSlot.id).all()
    return render_template('manage_slots.html', slots=slots)

@app.route('/admin/slots/toggle/<int:slot_id>', methods=['POST'])
@admin_required
def toggle_slot_status(slot_id):
    slot = db.session.get(TimeSlot, slot_id)
    if not slot:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Slot not found'}), 404
        flash('Time slot not found.', 'danger')
        return redirect(url_for('manage_slots'))

    slot.is_active = not slot.is_active
    db.session.commit()
    status_str = "Active" if slot.is_active else "Inactive"

    if request.is_json:
        return jsonify({'success': True, 'is_active': slot.is_active, 'status': status_str})

    flash(f'Time slot "{slot.slot_name}" is now marked as {status_str}.', 'success')
    return redirect(url_for('manage_slots'))

@app.route('/admin/slots/edit/<int:slot_id>', methods=['POST'])
@admin_required
def edit_slot(slot_id):
    slot = db.session.get(TimeSlot, slot_id)
    if not slot:
        flash('Time slot not found.', 'danger')
        return redirect(url_for('manage_slots'))

    slot.slot_name = request.form.get('slot_name', slot.slot_name).strip()
    slot.start_time = request.form.get('start_time', slot.start_time).strip()
    slot.end_time = request.form.get('end_time', slot.end_time).strip()
    slot.is_active = True if request.form.get('is_active') else False

    db.session.commit()
    flash(f'Time slot "{slot.slot_name}" updated successfully.', 'success')
    return redirect(url_for('manage_slots'))

@app.route('/manage_items', endpoint='manage_items')
@app.route('/manage-items')
@admin_required
def manage_items():
    active_items = MenuItem.query.filter_by(status='Active').order_by(MenuItem.category, MenuItem.item_name).all()
    deleted_items = MenuItem.query.filter_by(status='Deleted').order_by(MenuItem.category, MenuItem.item_name).all()
    
    return render_template(
        'manage_items.html',
        active_items=active_items,
        deleted_items=deleted_items,
        active_count=len(active_items),
        deleted_count=len(deleted_items)
    )

@app.route('/admin/menu/toggle-status/<int:item_id>', methods=['POST'])
@app.route('/admin/food/toggle-status/<int:item_id>', methods=['POST'])
@admin_required
def toggle_item_status(item_id):
    item = db.session.get(MenuItem, item_id)
    if not item:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Item not found'}), 404
        flash('Menu item not found.', 'danger')
        return redirect(url_for('manage_items'))

    # Soft Delete Toggle Logic
    if item.status == 'Active':
        item.status = 'Deleted'
        action_msg = f'Item "{item.item_name}" moved to Deleted/Archived Menu.'
    else:
        item.status = 'Active'
        action_msg = f'Item "{item.item_name}" restored to Active Menu.'

    db.session.commit()

    if request.is_json:
        return jsonify({
            'success': True,
            'status': item.status,
            'message': action_msg
        })

    flash(action_msg, 'success')
    return redirect(url_for('manage_items'))

@app.route('/admin/menu/add', methods=['GET', 'POST'])
@app.route('/admin/food/add', methods=['GET', 'POST'])
@admin_required
def admin_add_food():
    if request.method == 'POST':
        item_name = request.form.get('item_name') or request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = float(request.form.get('price', 0.0))
        category = request.form.get('category', 'Meals')
        image_url = request.form.get('image_url', '').strip()
        status = request.form.get('status', 'Active')

        if not item_name or price <= 0:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Food name and valid price required.'}), 400
            flash('Food name and a valid positive price are required.', 'danger')
            return redirect(url_for('manage_items'))

        if not image_url:
            image_url = 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&auto=format&fit=crop&q=80'

        item = MenuItem(
            item_name=item_name,
            description=description,
            price=price,
            category=category,
            image_url=image_url,
            status=status
        )
        db.session.add(item)
        db.session.commit()

        if request.is_json:
            return jsonify({'success': True, 'message': f'Food item "{item.item_name}" added to menu.', 'item': item.to_dict()})

        flash(f'Food item "{item.item_name}" added to menu.', 'success')
        return redirect(url_for('manage_items'))

    return render_template('admin_food_form.html', action='Add', food=None)

@app.route('/admin/menu/edit/<int:item_id>', methods=['GET', 'POST'])
@app.route('/admin/food/edit/<int:item_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_food(item_id):
    food = db.session.get(MenuItem, item_id)
    if not food:
        flash('Item not found.', 'danger')
        return redirect(url_for('manage_items'))

    if request.method == 'POST':
        food.item_name = request.form.get('item_name') or request.form.get('name', food.item_name).strip()
        food.description = request.form.get('description', food.description).strip()
        food.price = float(request.form.get('price', food.price))
        food.category = request.form.get('category', food.category)
        food.image_url = request.form.get('image_url', food.image_url).strip()
        if request.form.get('status'):
            food.status = request.form.get('status')

        db.session.commit()

        if request.is_json:
            return jsonify({'success': True, 'message': f'Food item "{food.item_name}" updated.', 'item': food.to_dict()})

        flash(f'Food item "{food.item_name}" updated.', 'success')
        return redirect(url_for('manage_items'))

    return render_template('admin_food_form.html', action='Edit', food=food)

@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@admin_required
def update_order_status(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Order not found'}), 404
        flash('Order not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    new_status = request.form.get('status') or (request.get_json() or {}).get('status')
    
    if new_status in ['Pending', 'Cooking', 'Ready', 'Completed']:
        order.status = new_status
        db.session.commit()
        if request.is_json:
            return jsonify({'success': True, 'order_id': order.id, 'status': order.status})
        flash(f'Order #{order.id} status updated to "{new_status}".', 'success')
    else:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        flash('Invalid status update.', 'danger')

    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
        except Exception:
            pass
    app.run(debug=True, port=5000)
