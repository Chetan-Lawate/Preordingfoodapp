# ⚡ CampusBites - Food Pre-Ordering Web Application

A full-stack mobile-first **Food Pre-Ordering Web Application** designed for students and employees to pre-order meals and beverages before their scheduled break slots (e.g., 10:30 AM, 1:00 PM, 3:30 PM) to skip long cafeteria queues.

Built with **Python Flask**, **Flask-SQLAlchemy**, **Flask-Login**, **MySQL** (with SQLite fallback), **Tailwind CSS**, and **Vanilla JavaScript**.

---

## 📁 Repository Folder Structure

```
preorderfoodapp/
├── backend/
│   ├── app.py                  # Core Flask application, auth & API endpoints
│   ├── config.py               # Database configuration (MySQL connection & SQLite fallback)
│   ├── models.py               # SQLAlchemy ORM Models (User, FoodItem, Order, OrderItem)
│   ├── schema.sql              # MySQL database setup script & seed SQL
│   ├── seed.py                 # Automatic database seeder for initial food items & demo users
│   └── requirements.txt        # Python backend dependencies
└── frontend/
    ├── static/
    │   ├── css/
    │   │   └── custom.css      # Modern UberEats styling, animations, toasts & glassmorphic nav
    │   └── js/
    │       ├── main.js         # Cart state, LocalStorage persistence, toast system & checkout AJAX
    │       └── admin.js        # Admin real-time order status updates & food availability toggles
    └── templates/
        ├── base.html           # Main layout template with navbar, toasts, and floating cart
        ├── index.html          # Hero landing page & featured food showcase
        ├── menu.html           # Categorized food menu with category pills & search
        ├── cart.html           # Cart review & break slot checkout
        ├── orders.html         # User pre-order history & live status tracker
        ├── login.html          # User login page with quick demo buttons
        ├── register.html       # User/Admin registration page
        ├── admin_dashboard.html# Admin panel for order fulfillment & menu CRUD operations
        └── admin_food_form.html# Add/Edit food item form template
```

---

## 🛢️ MySQL Database Schema

The database uses the following MySQL relational schema (defined in `backend/schema.sql` and `backend/models.py`):

1. **`users`**: `id`, `username`, `email`, `password_hash`, `role` (`'admin'`, `'user'`), `created_at`
2. **`food_items`**: `id`, `name`, `description`, `price`, `category`, `image_url`, `availability`, `created_at`
3. **`orders`**: `id`, `user_id`, `total_price`, `break_time`, `status` (`'pending'`, `'ready'`, `'completed'`), `created_at`
4. **`order_items`**: `id`, `order_id`, `food_id`, `quantity`

---

## 🔑 Demo Account Credentials

Default pre-seeded accounts available for instant testing:

- **Student / Employee Account**:
  - Email: `student@cafeteria.com`
  - Password: `user123`
  - Role: `user`

- **Cafeteria Admin Account**:
  - Email: `admin@cafeteria.com`
  - Password: `admin123`
  - Role: `admin`

---

## 🚀 Getting Started & Local Setup

### 1. Prerequisites
- Python 3.9+
- (Optional) MySQL Server 8.0+ running on `localhost:3306`

### 2. Environment Setup
```bash
# Clone or navigate to the project folder
cd preorderfoodapp

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Database Configuration (MySQL / SQLite)
By default, the application connects to MySQL using the connection string in `backend/config.py`:
- Host: `localhost`
- User: `root`
- Password: `` (empty by default)
- Database: `food_preorder`

To configure your custom MySQL credentials, set environment variables:
```bash
set MYSQL_USER=your_user
set MYSQL_PASSWORD=your_password
set MYSQL_DB=food_preorder
```

> ℹ️ **Automatic Fallback**: If MySQL is not running on your local machine, `seed.py` and `app.py` automatically fall back to local `sqlite:///food_preorder.db` so the app works seamlessly out-of-the-box!

### 4. Seed Database & Run
```bash
# Seed initial users & food items
python backend/seed.py

# Start the Flask web application
python backend/app.py
```
Open your browser at **`http://127.0.0.1:5000`**.

---

## ✨ Features Highlights

- **Mobile-First UX**: Responsive design optimized for smartphone ordering during busy campus breaks.
- **Categorized Menu**: Instant category pills (Breakfast, Meals, Snacks, Beverages, Desserts) & live search bar.
- **Cart & Break Slot Checkout**: LocalStorage-persisted cart allowing customers to select specific break time slots (`10:30 AM`, `01:00 PM`, `03:30 PM`, `05:00 PM`).
- **Live Status Tracking**: Status badge updates (`Pending` → `Ready for Pickup` with glowing green animation → `Completed`).
- **Admin Dashboard**: Comprehensive order fulfillment board sorted by break time and order status, plus full CRUD operations for cafeteria menu items.
