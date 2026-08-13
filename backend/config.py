import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'cafeteria_preorder_secret_key_2026')

    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:3039/')
    MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'food_preorder')
    MONGO_COLLECTION_USERS = os.environ.get('MONGO_COLLECTION_USERS', 'users')
    MONGO_COLLECTION_MENU = os.environ.get('MONGO_COLLECTION_MENU', 'menu')
    MONGO_COLLECTION_TIME_SLOTS = os.environ.get('MONGO_COLLECTION_TIME_SLOTS', 'time_slots')
    MONGO_COLLECTION_ORDERS = os.environ.get('MONGO_COLLECTION_ORDERS', 'orders')

    @classmethod
    def mongo_url(cls):
        return cls.MONGO_URI

    @classmethod
    def db_name(cls):
        return cls.MONGO_DB_NAME
