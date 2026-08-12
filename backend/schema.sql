-- Database schema for College Canteen Pre-Ordering System
-- MySQL Script

CREATE DATABASE IF NOT EXISTS food_preorder;
USE food_preorder;

-- Users Table (Roles: Admin, Student)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('Admin', 'Student') DEFAULT 'Student' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Menu Table (Status: Active, Deleted - Soft Delete)
CREATE TABLE IF NOT EXISTS menu (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(120) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(50) NOT NULL,
    image_url VARCHAR(500),
    status ENUM('Active', 'Deleted') DEFAULT 'Active' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Time Slots Table
CREATE TABLE IF NOT EXISTS time_slots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slot_name VARCHAR(80) NOT NULL,
    start_time VARCHAR(20) NOT NULL,
    end_time VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Orders Table (Status: Pending, Cooking, Ready, Completed)
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    break_time VARCHAR(50) NOT NULL,
    status ENUM('Pending', 'Cooking', 'Ready', 'Completed') DEFAULT 'Pending' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Order Items Table
CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    menu_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (menu_id) REFERENCES menu(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Seed Data (Passwords: admin123 for Admin, student123 for Student)
INSERT INTO users (username, email, password_hash, role) VALUES
('Cafeteria Manager', 'admin@cafeteria.com', 'scrypt:32768:8:1$uH3GvQxX3D1b4$d2e67f7bbba6471b0521e1bf699df899b8d0034ba23381a17950c411ca7192f155fa8ea9aa5eb461ec4682054ffcf475b6d51cbbf57aa210214a1a5b81a8c9b3', 'Admin'),
('Alex Johnson', 'student@cafeteria.com', 'scrypt:32768:8:1$YxR0L6Jz6P0k4$f10d297920ab67c6999335ef00ea1eebcc755cbce68260d753b879632ebcaefc2edabcf2b704c356e9c9cf5b9d316e61f22aa5d6fdb0c3e66bbf8e5c83bc56c5', 'Student')
ON DUPLICATE KEY UPDATE username=VALUES(username);

INSERT INTO time_slots (slot_name, start_time, end_time, is_active) VALUES
('Morning Break', '10:00 AM', '10:45 AM', 1),
('Lunch Break', '01:00 PM', '02:00 PM', 1),
('Tea Break', '03:30 PM', '04:15 PM', 1),
('Evening Break', '05:00 PM', '05:45 PM', 1)
ON DUPLICATE KEY UPDATE slot_name=VALUES(slot_name);

INSERT INTO menu (item_name, description, price, category, image_url, status) VALUES
('Classic Club Sandwich', 'Triple-decker toasted bread filled with grilled chicken, cheese, lettuce, & mustard.', 140.00, 'Snacks', 'https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600&auto=format&fit=crop&q=80', 'Active'),
('Crispy Chicken Wrap', 'Seasoned crispy tenderloins wrapped in tortilla with fresh avocado and garlic aioli.', 160.00, 'Meals', 'https://images.unsplash.com/photo-1626700051175-6818013e1d4f?w=600&auto=format&fit=crop&q=80', 'Active'),
('Cheesy Margherita Pizza Slice', 'Fresh mozzarella, vine-ripened tomato sauce, and basil on sourdough crust.', 99.00, 'Meals', 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=600&auto=format&fit=crop&q=80', 'Active'),
('Iced Caramel Macchiato', 'Rich espresso layered with creamy cold milk and drizzled with caramel syrup.', 120.00, 'Beverages', 'https://images.unsplash.com/photo-1517701604599-bb29b565090c?w=600&auto=format&fit=crop&q=80', 'Active'),
('Fresh Berry Smoothie Bowl', 'Blended acai, mixed berries, topped with crunchy granola, chia seeds, and honey.', 150.00, 'Breakfast', 'https://images.unsplash.com/photo-1590301157890-4810ed352733?w=600&auto=format&fit=crop&q=80', 'Active'),
('Chocolate Lava Muffin', 'Decadent warm chocolate muffin with a molten fudge core.', 80.00, 'Desserts', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=600&auto=format&fit=crop&q=80', 'Active'),
('Special Seasonal Chai', 'Spiced Indian ginger cardamom milk tea brewed fresh.', 35.00, 'Beverages', 'https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=600&auto=format&fit=crop&q=80', 'Deleted')
ON DUPLICATE KEY UPDATE item_name=VALUES(item_name);
