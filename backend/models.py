from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Student') # 'Admin' or 'Student'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'Admin'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role
        }

class MenuItem(db.Model):
    __tablename__ = 'menu'
    
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False) # Breakfast, Meals, Snacks, Beverages, Desserts
    image_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default='Active', nullable=False) # 'Active' or 'Deleted'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def name(self):
        return self.item_name

    def to_dict(self):
        return {
            'id': self.id,
            'item_name': self.item_name,
            'name': self.item_name,
            'description': self.description,
            'price': self.price,
            'category': self.category,
            'image_url': self.image_url,
            'status': self.status
        }

FoodItem = MenuItem

class TimeSlot(db.Model):
    __tablename__ = 'time_slots'
    
    id = db.Column(db.Integer, primary_key=True)
    slot_name = db.Column(db.String(80), nullable=False)
    start_time = db.Column(db.String(20), nullable=False)
    end_time = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'slot_name': self.slot_name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'is_active': self.is_active,
            'formatted': f"{self.start_time} - {self.end_time} ({self.slot_name})"
        }

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    break_time = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending') # 'Pending', 'Cooking', 'Ready', 'Completed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else 'Unknown',
            'user_email': self.user.email if self.user else '',
            'total_price': self.total_price,
            'break_time': self.break_time,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'items': [item.to_dict() for item in self.items]
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey('menu.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    menu_item = db.relationship('MenuItem', lazy=True)

    @property
    def food_name(self):
        return self.menu_item.item_name if self.menu_item else 'Item Removed'

    @property
    def subtotal(self):
        return (self.menu_item.price * self.quantity) if self.menu_item else 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'menu_id': self.menu_id,
            'food_name': self.food_name,
            'food_price': self.menu_item.price if self.menu_item else 0.0,
            'quantity': self.quantity,
            'subtotal': self.subtotal
        }
