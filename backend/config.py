import os
import pymysql

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'cafeteria_preorder_secret_key_2026')
    
    # MySQL Database Credentials
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'food_preorder')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    
    CUSTOM_DB_URI = os.environ.get('DATABASE_URL')
    
    if CUSTOM_DB_URI:
        SQLALCHEMY_DATABASE_URI = CUSTOM_DB_URI
    else:
        mysql_conn_str = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
        
        # Check MySQL server availability at startup
        try:
            conn = pymysql.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                port=MYSQL_PORT,
                connect_timeout=2
            )
            conn.close()
            SQLALCHEMY_DATABASE_URI = mysql_conn_str
            print(f"INFO: Successfully connected to MySQL database at {MYSQL_HOST}:{MYSQL_PORT}")
        except Exception as e:
            BASE_DIR = os.path.abspath(os.path.dirname(__file__))
            sqlite_path = os.path.join(BASE_DIR, 'food_preorder.db')
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{sqlite_path}"
            print(f"INFO: MySQL not active locally ({e}). Using local SQLite fallback database: {sqlite_path}")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
