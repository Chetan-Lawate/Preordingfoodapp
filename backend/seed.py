import os
from app import app
from models import db, User, MenuItem, TimeSlot, Order, OrderItem
from werkzeug.security import generate_password_hash

def seed_database():
    with app.app_context():
        db.create_all()
        print("Database schema verified.")

        # Seed Admin User
        admin = User.query.filter_by(email='admin@cafeteria.com').first()
        if not admin:
            admin = User(
                username='Cafeteria Admin',
                email='admin@cafeteria.com',
                password_hash=generate_password_hash('admin123'),
                role='Admin'
            )
            db.session.add(admin)
            print("Created Admin user: admin@cafeteria.com / admin123")
        else:
            admin.password_hash = generate_password_hash('admin123')
            admin.role = 'Admin'

        # Seed Student User
        student = User.query.filter_by(email='student@cafeteria.com').first()
        if not student:
            student = User(
                username='Alex Johnson',
                email='student@cafeteria.com',
                password_hash=generate_password_hash('student123'),
                role='Student'
            )
            db.session.add(student)
            print("Created Student user: student@cafeteria.com / student123")
        else:
            student.password_hash = generate_password_hash('student123')
            student.role = 'Student'

        # Seed Default Time Slots
        sample_slots = [
            {'slot_name': 'Morning Break', 'start_time': '10:00 AM', 'end_time': '10:45 AM', 'is_active': True},
            {'slot_name': 'Lunch Break', 'start_time': '01:00 PM', 'end_time': '02:00 PM', 'is_active': True},
            {'slot_name': 'Tea Break', 'start_time': '03:30 PM', 'end_time': '04:15 PM', 'is_active': True},
            {'slot_name': 'Evening Break', 'start_time': '05:00 PM', 'end_time': '05:45 PM', 'is_active': True}
        ]
        for slot in sample_slots:
            existing_slot = TimeSlot.query.filter_by(slot_name=slot['slot_name']).first()
            if not existing_slot:
                db.session.add(TimeSlot(**slot))

        # Seed Menu Items with Active and Deleted status
        sample_menu = [
            {
                'item_name': 'Classic Club Sandwich',
                'description': 'Triple-decker toasted sourdough filled with smoked turkey breast, crispy bacon, cheddar, lettuce, & honey mustard.',
                'price': 140.00,
                'category': 'Snacks',
                'image_url': 'https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600&auto=format&fit=crop&q=80',
                'status': 'Active'
            },
            {
                'item_name': 'Crispy Chicken & Avocado Wrap',
                'description': 'Seasoned crispy tenderloins wrapped in a spinach tortilla with fresh sliced avocado, tomato, and garlic aioli.',
                'price': 160.00,
                'category': 'Meals',
                'image_url': 'https://images.unsplash.com/photo-1626700051175-6818013e1d4f?w=600&auto=format&fit=crop&q=80',
                'status': 'Active'
            },
            {
                'item_name': 'Artisan Margherita Pizza Slice',
                'description': 'Fresh mozzarella, vine-ripened tomato sauce, and sweet basil leaves on fermented sourdough crust.',
                'price': 99.00,
                'category': 'Meals',
                'image_url': 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=600&auto=format&fit=crop&q=80',
                'status': 'Active'
            },
            {
                'item_name': 'Iced Caramel Macchiato',
                'description': 'Rich double-shot espresso poured over iced whole milk, finished with handcrafted caramel drizzle.',
                'price': 120.00,
                'category': 'Beverages',
                'image_url': 'https://images.unsplash.com/photo-1517701604599-bb29b565090c?w=600&auto=format&fit=crop&q=80',
                'status': 'Active'
            },
            {
                'item_name': 'Fresh Acai & Berry Smoothie Bowl',
                'description': 'Blended organic acai and mixed forest berries, topped with crunchy coconut granola and fresh banana slices.',
                'price': 150.00,
                'category': 'Breakfast',
                'image_url': 'https://images.unsplash.com/photo-1590301157890-4810ed352733?w=600&auto=format&fit=crop&q=80',
                'status': 'Active'
            },
            {
                'item_name': 'Molten Chocolate Lava Muffin',
                'description': 'Decadent dark chocolate muffin with a warm gooey chocolate center, baked fresh daily.',
                'price': 80.00,
                'category': 'Desserts',
                'image_url': 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=600&auto=format&fit=crop&q=80',
                'status': 'Active'
            },
            {
                'item_name': 'Special Seasonal Masala Chai',
                'description': 'Spiced Indian ginger cardamom milk tea brewed fresh (Soft Deleted Item demo).',
                'price': 35.00,
                'category': 'Beverages',
                'image_url': 'https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=600&auto=format&fit=crop&q=80',
                'status': 'Deleted'
            },
            {
                'item_name': 'Double Cheese Nachos',
                'description': 'Crispy corn tortilla chips loaded with melted cheddar, jalapeños, and salsa (Soft Deleted Item demo).',
                'price': 110.00,
                'category': 'Snacks',
                'image_url': 'https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?w=600&auto=format&fit=crop&q=80',
                'status': 'Deleted'
            }
        ]

        for data in sample_menu:
            existing = MenuItem.query.filter_by(item_name=data['item_name']).first()
            if existing:
                existing.price = data['price']
                existing.description = data['description']
                existing.category = data['category']
                existing.image_url = data['image_url']
                existing.status = data['status']
            else:
                db.session.add(MenuItem(**data))

        db.session.commit()
        print("Database items & time slots seeded successfully!")

if __name__ == '__main__':
    seed_database()
