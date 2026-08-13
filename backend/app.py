import os
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from config import Config
except ModuleNotFoundError:  # pragma: no cover
    from backend.config import Config

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, 'frontend', 'templates')
STATIC_DIR = os.path.join(PROJECT_ROOT, 'frontend', 'static')

app = FastAPI(title='CampusBites')
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')
templates = Jinja2Templates(directory=TEMPLATE_DIR)


def template_url_for(name: str, **params: Any):
    route_aliases = {
        'admin_add_food': '/admin/menu/add',
        'admin_edit_food': '/admin/menu/edit/{item_id}',
        'admin_dashboard': '/admin/dashboard',
        'manage_items': '/manage_items',
        'manage_slots': '/manage-slots',
        'toggle_item_status': '/admin/menu/toggle-status/{item_id}',
        'toggle_slot_status': '/admin/slots/toggle-status/{slot_id}',
        'user_menu': '/user-menu',
        'login': '/login',
        'register': '/register',
        'index': '/',
        'orders': '/orders',
        'cart': '/cart',
        'logout': '/logout',
    }

    path_params: Dict[str, Any] = {}
    query_params: Dict[str, Any] = {}
    for key, value in params.items():
        if value is None or value == '':
            continue
        if key in {'next', 'category', 'q', 'status', 'break_time', 'sort', 'page'}:
            query_params[key] = value
        elif key == 'food_id':
            path_params['item_id'] = value
        else:
            path_params[key] = value

    if name in route_aliases:
        url = route_aliases[name]
        for key, value in list(path_params.items()):
            url = url.replace('{' + key + '}', str(value))
        if query_params:
            separator = '&' if '?' in url else '?'
            url = f"{url}{separator}{'&'.join(f'{k}={v}' for k, v in query_params.items())}"
        return url

    url = '/' if name == 'index' else f"/{name.replace('_', '-') or ''}"
    if query_params:
        separator = '&' if '?' in url else '?'
        url = f"{url}{separator}{'&'.join(f'{k}={v}' for k, v in query_params.items())}"
    return url


templates.env.globals['get_flashed_messages'] = lambda with_categories=False: []
templates.env.globals['flash'] = lambda *args, **kwargs: None
templates.env.globals['url_for'] = template_url_for

mongo_client = None
mongo_db = None
mongo_error = None
try:
    mongo_client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=2000)
    mongo_db = mongo_client[Config.MONGO_DB_NAME]
    mongo_db.command('ping')
    print(f'INFO: Connected to MongoDB at {Config.MONGO_URI}')
except Exception as exc:  # pragma: no cover
    mongo_error = str(exc)
    mongo_client = None
    mongo_db = None
    print(f'INFO: MongoDB not active locally ({exc}). Using in-memory fallback store.')

IN_MEMORY_DB: Dict[str, Any] = {
    'users': [],
    'menu': [],
    'time_slots': [],
    'orders': [],
}


class InMemoryCursor:
    def __init__(self, documents: List[Dict[str, Any]]):
        self._documents = documents

    def __iter__(self):
        return iter(self._documents)

    def __len__(self):
        return len(self._documents)

    def __getitem__(self, index):
        return self._documents[index]

    def limit(self, count: int):
        return self._documents[:count]


class InMemoryCollection:
    def __init__(self, documents: List[Dict[str, Any]]):
        self._documents = documents

    def __iter__(self):
        return iter(self._documents)

    def _matches(self, document: Dict[str, Any], query: Optional[Dict[str, Any]]):
        if not query:
            return True
        if '$or' in query:
            return any(self._matches(document, clause) for clause in query['$or'])
        if '$and' in query:
            return all(self._matches(document, clause) for clause in query['$and'])
        for key, value in query.items():
            if key == '$or' or key == '$and':
                continue
            if isinstance(value, dict):
                if '$in' in value and document.get(key) in value['$in']:
                    continue
                if '$ne' in value and document.get(key) != value['$ne']:
                    continue
                if '$gte' in value and document.get(key, 0) < value['$gte']:
                    continue
                if '$lte' in value and document.get(key, 0) > value['$lte']:
                    continue
            if document.get(key) != value:
                return False
        return True

    def find(self, query: Optional[Dict[str, Any]] = None):
        matches = [doc for doc in self._documents if self._matches(doc, query or {})]
        return InMemoryCursor(matches)

    def find_one(self, query: Optional[Dict[str, Any]] = None):
        matches = self.find(query)
        return matches[0] if len(matches) > 0 else None

    def count_documents(self, query: Optional[Dict[str, Any]] = None):
        return len(self.find(query))

    def insert_one(self, document: Dict[str, Any]):
        if '_id' not in document:
            document['_id'] = f'generated-{len(self._documents) + 1}'
        self._documents.append(document)
        return SimpleNamespace(inserted_id=document['_id'])

    def insert_many(self, documents: List[Dict[str, Any]]):
        inserted_ids = []
        for document in documents:
            if '_id' not in document:
                document['_id'] = f'generated-{len(self._documents) + 1}'
            self._documents.append(document)
            inserted_ids.append(document['_id'])
        return SimpleNamespace(inserted_ids=inserted_ids)

    def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        for document in self._documents:
            if self._matches(document, query):
                if '$set' in update:
                    document.update(update['$set'])
                return SimpleNamespace(modified_count=1)
        return SimpleNamespace(modified_count=0)


def get_collection(name: str):
    if mongo_db is not None:
        return mongo_db[name]
    return InMemoryCollection(IN_MEMORY_DB.setdefault(name, []))


def make_user_context(user_doc: Dict[str, Any]) -> SimpleNamespace:
    role = user_doc.get('role', 'Student')
    user = SimpleNamespace(
        id=str(user_doc.get('_id', user_doc.get('id', ''))),
        username=user_doc.get('username', ''),
        email=user_doc.get('email', ''),
        role=role,
        is_authenticated=True,
    )
    user.is_admin = role == 'Admin'
    return user


def get_current_user(request: Request) -> Optional[SimpleNamespace]:
    user_id = request.cookies.get('user_id')
    if not user_id:
        return None
    try:
        if mongo_db is not None:
            user_doc = mongo_db.users.find_one({'_id': ObjectId(user_id)})
        else:
            user_doc = next((u for u in IN_MEMORY_DB['users'] if str(u.get('_id', u.get('id'))) == str(user_id)), None)
        if not user_doc:
            return None
        return make_user_context(user_doc)
    except Exception:
        return None


def get_user_by_id(user_id: Any) -> Optional[Dict[str, Any]]:
    if not user_id:
        return None
    if mongo_db is not None:
        try:
            return mongo_db.users.find_one({'_id': ObjectId(str(user_id))})
        except Exception:
            return mongo_db.users.find_one({'_id': str(user_id)})
    return next((u for u in IN_MEMORY_DB['users'] if str(u.get('_id', u.get('id'))) == str(user_id)), None)


def get_menu_by_id(menu_id: Any) -> Optional[Dict[str, Any]]:
    if menu_id is None:
        return None
    menu_id = str(menu_id)
    if mongo_db is not None:
        try:
            return mongo_db.menu.find_one({'_id': ObjectId(menu_id)})
        except Exception:
            return mongo_db.menu.find_one({'_id': menu_id})
    return next((item for item in IN_MEMORY_DB['menu'] if str(item.get('_id', item.get('id'))) == menu_id), None)


def build_order_view(order: Dict[str, Any]) -> SimpleNamespace:
    order_id = str(order.get('_id', order.get('id', '')))
    user_doc = get_user_by_id(order.get('user_id'))
    display_items = []
    for item in order.get('items', []):
        menu_id = item.get('menu_id') or item.get('id')
        quantity = int(item.get('quantity', 0) or 0)
        menu_item = get_menu_by_id(menu_id)
        if menu_item is None:
            food_name = item.get('food_name') or 'Unknown Item'
            unit_price = float(item.get('price', 0) or 0)
        else:
            food_name = menu_item.get('item_name', 'Unknown Item')
            unit_price = float(menu_item.get('price', 0) or 0)
        subtotal = unit_price * quantity
        display_items.append(SimpleNamespace(
            food_name=food_name,
            quantity=quantity,
            subtotal=subtotal,
            price=unit_price,
        ))
    return SimpleNamespace(
        id=order_id,
        user=SimpleNamespace(username=user_doc.get('username', 'Unknown User') if user_doc else 'Unknown User'),
        status=order.get('status', 'Pending'),
        break_time=order.get('break_time', ''),
        total_price=float(order.get('total_price', 0) or 0),
        created_at=order.get('created_at', datetime.utcnow()),
        items=display_items,
    )


def normalize_menu_record(item: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(item)
    if '_id' in normalized and 'id' not in normalized:
        normalized['id'] = str(normalized['_id'])
    if 'item_name' in normalized and 'name' not in normalized:
        normalized['name'] = normalized['item_name']
    if 'availability' not in normalized:
        normalized['availability'] = normalized.get('status') == 'Active'
    if 'status' not in normalized:
        normalized['status'] = 'Active'
    normalized.setdefault('description', '')
    normalized.setdefault('image_url', '')
    normalized.setdefault('price', 0.0)
    normalized.setdefault('category', 'Meals')
    return normalized


def normalize_slot_record(slot: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(slot)
    if '_id' in normalized and 'id' not in normalized:
        normalized['id'] = str(normalized['_id'])
    if 'slot_name' in normalized and 'name' not in normalized:
        normalized['name'] = normalized['slot_name']
    normalized.setdefault('is_active', True)
    return normalized


def parse_checkbox_flag(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() not in {'', '0', 'false', 'off', 'no'}


def normalize_template_value(value: Any):
    if isinstance(value, list):
        return [normalize_template_value(item) for item in value]
    if isinstance(value, dict):
        normalized = dict(value)
        if '_id' in normalized and 'id' not in normalized:
            normalized['id'] = str(normalized['_id'])
        if 'item_id' in normalized and 'id' not in normalized:
            normalized['id'] = str(normalized['item_id'])
        if 'item_name' in normalized and 'name' not in normalized:
            normalized['name'] = normalized['item_name']
        if 'slot_name' in normalized and 'name' not in normalized:
            normalized['name'] = normalized['slot_name']
        if 'item_name' in normalized and 'item_id' not in normalized and '_id' in normalized:
            normalized['item_id'] = str(normalized['_id'])
        return normalized
    return value


def render_template(request: Request, template_name: str, **context: Any):
    user = get_current_user(request)
    guest_user = SimpleNamespace(
        id='',
        username='',
        email='',
        role='Student',
        is_authenticated=False,
        is_admin=False,
    )
    categories = ['All', 'Breakfast', 'Meals', 'Snacks', 'Beverages', 'Desserts']
    time_slots = list(get_collection('time_slots').find())
    if time_slots:
        break_times = [
            f"{slot.get('start_time')} - {slot.get('end_time')} ({slot.get('slot_name')})"
            for slot in time_slots
            if slot.get('is_active') is not False
        ]
    else:
        break_times = [
            '10:00 AM - 10:45 AM (Morning Break)',
            '01:00 PM - 02:00 PM (Lunch Break)',
            '03:30 PM - 04:15 PM (Tea Break)',
        ]
    template_context = {
        'request': request,
        'request_args': dict(request.query_params),
        'current_user': user or guest_user,
        'categories': categories,
        'break_times': break_times,
        'current_year': datetime.now().year,
        **{key: normalize_template_value(value) for key, value in context.items()},
    }
    return templates.TemplateResponse(request, template_name, template_context)


def require_admin(request: Request):
    current_user = get_current_user(request)
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, detail='Admin access required')
    return current_user


def ensure_seed_data():
    if mongo_db is not None:
        if mongo_db.users.count_documents({}) == 0:
            mongo_db.users.insert_many([
                {
                    'username': 'Cafeteria Admin',
                    'email': 'admin@cafeteria.com',
                    'password_hash': generate_password_hash('admin123'),
                    'role': 'Admin',
                    'created_at': datetime.utcnow(),
                },
                {
                    'username': 'Alex Johnson',
                    'email': 'student@cafeteria.com',
                    'password_hash': generate_password_hash('student123'),
                    'role': 'Student',
                    'created_at': datetime.utcnow(),
                },
            ])
        if mongo_db.menu.count_documents({}) == 0:
            mongo_db.menu.insert_many([
                {
                    'item_name': 'Classic Club Sandwich',
                    'description': 'Triple-decker toasted sourdough filled with smoked turkey breast, crispy bacon, cheddar, lettuce, & honey mustard.',
                    'price': 140.0,
                    'category': 'Snacks',
                    'image_url': 'https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600&auto=format&fit=crop&q=80',
                    'status': 'Active',
                    'created_at': datetime.utcnow(),
                },
                {
                    'item_name': 'Crispy Chicken & Avocado Wrap',
                    'description': 'Seasoned crispy tenderloins wrapped in a spinach tortilla with fresh sliced avocado, tomato, and garlic aioli.',
                    'price': 160.0,
                    'category': 'Meals',
                    'image_url': 'https://images.unsplash.com/photo-1626700051175-6818013e1d4f?w=600&auto=format&fit=crop&q=80',
                    'status': 'Active',
                    'created_at': datetime.utcnow(),
                },
                {
                    'item_name': 'Molten Chocolate Lava Muffin',
                    'description': 'Decadent dark chocolate muffin with a warm gooey chocolate center, baked fresh daily.',
                    'price': 80.0,
                    'category': 'Desserts',
                    'image_url': 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=600&auto=format&fit=crop&q=80',
                    'status': 'Active',
                    'created_at': datetime.utcnow(),
                },
            ])
        if mongo_db.time_slots.count_documents({}) == 0:
            mongo_db.time_slots.insert_many([
                {'slot_name': 'Morning Break', 'start_time': '10:00 AM', 'end_time': '10:45 AM', 'is_active': True, 'created_at': datetime.utcnow()},
                {'slot_name': 'Lunch Break', 'start_time': '01:00 PM', 'end_time': '02:00 PM', 'is_active': True, 'created_at': datetime.utcnow()},
                {'slot_name': 'Tea Break', 'start_time': '03:30 PM', 'end_time': '04:15 PM', 'is_active': True, 'created_at': datetime.utcnow()},
            ])
    else:
        if not IN_MEMORY_DB['users']:
            IN_MEMORY_DB['users'] = [
                {'_id': 'admin-user', 'username': 'Cafeteria Admin', 'email': 'admin@cafeteria.com', 'password_hash': generate_password_hash('admin123'), 'role': 'Admin'},
                {'_id': 'student-user', 'username': 'Alex Johnson', 'email': 'student@cafeteria.com', 'password_hash': generate_password_hash('student123'), 'role': 'Student'},
            ]
        if not IN_MEMORY_DB['menu']:
            IN_MEMORY_DB['menu'] = [
                {'_id': '1', 'item_name': 'Classic Club Sandwich', 'description': 'Classic sandwich', 'price': 140.0, 'category': 'Snacks', 'image_url': 'https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600&auto=format&fit=crop&q=80', 'status': 'Active'},
                {'_id': '2', 'item_name': 'Crispy Chicken & Avocado Wrap', 'description': 'Wrap description', 'price': 160.0, 'category': 'Meals', 'image_url': 'https://images.unsplash.com/photo-1626700051175-6818013e1d4f?w=600&auto=format&fit=crop&q=80', 'status': 'Active'},
                {'_id': '3', 'item_name': 'Molten Chocolate Lava Muffin', 'description': 'Dessert', 'price': 80.0, 'category': 'Desserts', 'image_url': 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=600&auto=format&fit=crop&q=80', 'status': 'Active'},
            ]
        if not IN_MEMORY_DB['time_slots']:
            IN_MEMORY_DB['time_slots'] = [
                {'_id': '1', 'slot_name': 'Morning Break', 'start_time': '10:00 AM', 'end_time': '10:45 AM', 'is_active': True},
                {'_id': '2', 'slot_name': 'Lunch Break', 'start_time': '01:00 PM', 'end_time': '02:00 PM', 'is_active': True},
            ]


ensure_seed_data()


@app.get('/', name='index')
async def index(request: Request):
    current = get_current_user(request)
    if current and current.is_admin:
        return RedirectResponse(url='/admin/dashboard', status_code=status.HTTP_303_SEE_OTHER)
    menu_items = list(get_collection('menu').find({'status': 'Active'}).limit(6))
    return render_template(request, 'index.html', featured_items=menu_items)


@app.get('/menu', name='menu')
@app.get('/user_menu', name='user_menu')
@app.get('/user-menu', name='user_menu_hyphen')
async def user_menu(request: Request):
    category = request.query_params.get('category', 'All')
    search_query = (request.query_params.get('q', '') or '').strip()
    items = list(get_collection('menu').find({'status': 'Active'})) if mongo_db is not None else IN_MEMORY_DB['menu']
    if category != 'All':
        items = [item for item in items if item.get('category') == category]
    if search_query:
        items = [item for item in items if search_query.lower() in (item.get('item_name', '') or '').lower()]
    return render_template(request, 'user_menu.html', items=items, selected_category=category, search_query=search_query)


@app.get('/cart', name='cart')
async def cart(request: Request):
    return render_template(request, 'cart.html')


@app.get('/orders', name='orders')
async def orders(request: Request):
    current = get_current_user(request)
    if not current:
        return RedirectResponse(url='/login', status_code=status.HTTP_303_SEE_OTHER)
    raw_orders = list(get_collection('orders').find({'user_id': current.id})) if mongo_db is not None else [order for order in IN_MEMORY_DB['orders'] if order.get('user_id') == current.id]
    orders_list = [build_order_view(order) for order in raw_orders]
    return render_template(request, 'orders.html', orders=orders_list)


@app.get('/api/food', name='api_food')
async def api_food():
    items = list(get_collection('menu').find({'status': 'Active'})) if mongo_db is not None else [item for item in IN_MEMORY_DB['menu'] if item.get('status') == 'Active']
    return JSONResponse([{
        'id': str(item.get('_id', item.get('id', ''))),
        'item_name': item.get('item_name'),
        'name': item.get('item_name'),
        'description': item.get('description'),
        'price': item.get('price'),
        'category': item.get('category'),
        'image_url': item.get('image_url'),
        'status': item.get('status'),
    } for item in items])


@app.get('/login', name='login')
async def login_page(request: Request):
    current = get_current_user(request)
    if current:
        return RedirectResponse(url='/admin/dashboard' if current.is_admin else '/user_menu', status_code=status.HTTP_303_SEE_OTHER)
    return render_template(request, 'login.html')


@app.post('/login', name='login_post')
async def login_post(request: Request, email: str = Form(...), password: str = Form(...), remember: str = Form(default='')):
    user_doc = None
    if mongo_db is not None:
        user_doc = mongo_db.users.find_one({'email': email})
    else:
        user_doc = next((u for u in IN_MEMORY_DB['users'] if u.get('email') == email), None)
    if not user_doc or not check_password_hash(user_doc.get('password_hash', ''), password):
        return RedirectResponse('/login', status_code=status.HTTP_303_SEE_OTHER)

    response = RedirectResponse(url='/admin/dashboard' if user_doc.get('role') == 'Admin' else '/user_menu', status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie('user_id', str(user_doc.get('_id', user_doc.get('id'))), httponly=True, samesite='lax')
    return response


@app.get('/register', name='register')
async def register_page(request: Request):
    current = get_current_user(request)
    if current:
        return RedirectResponse(url='/admin/dashboard' if current.is_admin else '/user_menu', status_code=status.HTTP_303_SEE_OTHER)
    return render_template(request, 'register.html')


@app.post('/register', name='register_post')
async def register_post(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...), role: str = Form('Student')):
    if role not in ['Student', 'Admin']:
        role = 'Student'
    if mongo_db is not None:
        existing = mongo_db.users.find_one({'$or': [{'email': email}, {'username': username}]})
        if existing:
            return RedirectResponse('/register', status_code=status.HTTP_303_SEE_OTHER)
        user_doc = {'username': username, 'email': email, 'password_hash': generate_password_hash(password), 'role': role, 'created_at': datetime.utcnow()}
        result = mongo_db.users.insert_one(user_doc)
        user_doc['_id'] = result.inserted_id
    else:
        existing = next((u for u in IN_MEMORY_DB['users'] if u.get('email') == email or u.get('username') == username), None)
        if existing:
            return RedirectResponse('/register', status_code=status.HTTP_303_SEE_OTHER)
        user_doc = {'_id': f'user-{len(IN_MEMORY_DB["users"]) + 1}', 'username': username, 'email': email, 'password_hash': generate_password_hash(password), 'role': role}
        IN_MEMORY_DB['users'].append(user_doc)
    response = RedirectResponse(url='/admin/dashboard' if user_doc.get('role') == 'Admin' else '/user_menu', status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie('user_id', str(user_doc.get('_id', user_doc.get('id'))), httponly=True, samesite='lax')
    return response


@app.get('/logout', name='logout')
async def logout(request: Request):
    response = RedirectResponse(url='/user_menu', status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie('user_id')
    return response


@app.post('/checkout', name='checkout')
async def checkout(request: Request):
    current = get_current_user(request)
    if not current:
        return JSONResponse({'success': False, 'message': 'Please sign in to your account to place an order.', 'redirect': '/login'}, status_code=401)

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({'success': False, 'message': 'Invalid checkout payload.'}, status_code=400)

    if not payload or not payload.get('items'):
        return JSONResponse({'success': False, 'message': 'Your cart is empty.'}, status_code=400)
    break_time = payload.get('break_time')
    if not break_time:
        return JSONResponse({'success': False, 'message': 'Please select a valid break time for pickup.'}, status_code=400)
    total_price = 0.0
    order_items = []
    menu_items = list(get_collection('menu').find()) if mongo_db is not None else IN_MEMORY_DB['menu']
    menu_lookup = {str(item.get('_id', item.get('id'))): item for item in menu_items}
    for item_info in payload['items']:
        menu_id = str(item_info.get('id'))
        qty = int(item_info.get('quantity', 1))
        menu_item = menu_lookup.get(menu_id)
        if not menu_item or menu_item.get('status') != 'Active':
            return JSONResponse({'success': False, 'message': f'Item "{menu_item.get("item_name") if menu_item else "Unknown"}" is currently unavailable.'}, status_code=400)
        total_price += float(menu_item.get('price', 0)) * qty
        order_items.append({'menu_id': menu_id, 'quantity': qty})
    order_doc = {'user_id': current.id, 'total_price': total_price, 'break_time': break_time, 'status': 'Pending', 'created_at': datetime.utcnow(), 'items': order_items}
    if mongo_db is not None:
        insert_result = mongo_db.orders.insert_one(order_doc)
        order_id = str(insert_result.inserted_id)
    else:
        order_id = f'order-{len(IN_MEMORY_DB["orders"]) + 1}'
        order_doc['_id'] = order_id
        IN_MEMORY_DB['orders'].append(order_doc)
    return JSONResponse({'success': True, 'message': f'Order #{order_id} placed successfully for pickup at {break_time}!', 'order_id': order_id})


@app.get('/api/orders/{order_id}/status', name='order_status_api')
async def order_status_api(request: Request, order_id: str):
    current = get_current_user(request)
    if not current:
        return JSONResponse({'error': 'Unauthorized'}, status_code=401)
    if mongo_db is not None:
        order = mongo_db.orders.find_one({'_id': ObjectId(order_id)})
    else:
        order = next((o for o in IN_MEMORY_DB['orders'] if str(o.get('_id')) == str(order_id)), None)
    if not order:
        return JSONResponse({'error': 'Order not found'}, status_code=404)
    if str(order.get('user_id')) != str(current.id) and not current.is_admin:
        return JSONResponse({'error': 'Unauthorized'}, status_code=403)
    return JSONResponse({'order_id': str(order.get('_id', order_id)), 'status': order.get('status'), 'break_time': order.get('break_time')})


@app.get('/admin/dashboard', name='admin_dashboard')
async def admin_dashboard(request: Request):
    current = get_current_user(request)
    if not current or not current.is_admin:
        return RedirectResponse(url='/user_menu', status_code=status.HTTP_303_SEE_OTHER)
    filter_time = request.query_params.get('break_time', 'All')
    filter_status = request.query_params.get('status', 'All')
    raw_orders = list(get_collection('orders').find()) if mongo_db is not None else IN_MEMORY_DB['orders']
    orders_list = [build_order_view(order) for order in raw_orders]
    time_slots = list(get_collection('time_slots').find()) if mongo_db is not None else IN_MEMORY_DB['time_slots']
    break_times = [
        f"{slot.get('start_time')} - {slot.get('end_time')} ({slot.get('slot_name')})"
        for slot in time_slots
        if slot.get('is_active') is not False
    ]
    if filter_time != 'All':
        orders_list = [order for order in orders_list if getattr(order, 'break_time', '') == filter_time]
    if filter_status != 'All':
        orders_list = [order for order in orders_list if getattr(order, 'status', '') == filter_status]
    counts = {
        'total_orders': len(orders_list),
        'pending_orders': sum(1 for o in orders_list if getattr(o, 'status', None) == 'Pending'),
        'cooking_orders': sum(1 for o in orders_list if getattr(o, 'status', None) == 'Cooking'),
        'ready_orders': sum(1 for o in orders_list if getattr(o, 'status', None) == 'Ready'),
        'completed_orders': sum(1 for o in orders_list if getattr(o, 'status', None) == 'Completed'),
    }
    return render_template(request, 'admin_dashboard.html', orders=orders_list, **counts, selected_time=filter_time, selected_status=filter_status, break_times=break_times)


@app.get('/manage_items', name='manage_items')
@app.get('/manage-items', name='manage_items_alt')
async def manage_items(request: Request):
    current = get_current_user(request)
    if not current or not current.is_admin:
        return RedirectResponse(url='/user_menu', status_code=status.HTTP_303_SEE_OTHER)
    menu_items = list(get_collection('menu').find()) if mongo_db is not None else IN_MEMORY_DB['menu']
    active_items = [normalize_menu_record(item) for item in menu_items if item.get('status') == 'Active']
    deleted_items = [normalize_menu_record(item) for item in menu_items if item.get('status') == 'Deleted']
    return render_template(request, 'manage_items.html', active_items=active_items, deleted_items=deleted_items, active_count=len(active_items), deleted_count=len(deleted_items))


@app.get('/manage-slots', name='manage_slots')
@app.get('/manage_slots', name='manage_slots_alt')
async def manage_slots(request: Request):
    current = get_current_user(request)
    if not current or not current.is_admin:
        return RedirectResponse(url='/user_menu', status_code=status.HTTP_303_SEE_OTHER)
    slots = list(get_collection('time_slots').find()) if mongo_db is not None else IN_MEMORY_DB['time_slots']
    normalized_slots = [normalize_slot_record(slot) for slot in slots]
    return render_template(request, 'manage_slots.html', slots=normalized_slots)


@app.post('/manage-slots', name='manage_slots_post')
async def manage_slots_post(
    request: Request,
    slot_id: str = Form(default=''),
    slot_name: str = Form(default=''),
    start_time: str = Form(default=''),
    end_time: str = Form(default=''),
    is_active: Optional[str] = Form(default=None)
):
    current = get_current_user(request)
    if not current or not current.is_admin:
        return RedirectResponse(url='/user_menu', status_code=status.HTTP_303_SEE_OTHER)

    if not slot_name or not start_time or not end_time:
        return RedirectResponse('/manage-slots', status_code=status.HTTP_303_SEE_OTHER)

    payload = {
        'slot_name': slot_name,
        'start_time': start_time,
        'end_time': end_time,
        'is_active': parse_checkbox_flag(is_active),
    }

    if slot_id:
        if mongo_db is not None:
            mongo_db.time_slots.update_one({'_id': ObjectId(slot_id)}, {'$set': payload})
        else:
            for slot in IN_MEMORY_DB['time_slots']:
                if str(slot.get('_id')) == str(slot_id):
                    slot.update(payload)
                    break
    else:
        if mongo_db is not None:
            mongo_db.time_slots.insert_one(payload)
        else:
            payload['_id'] = f'slot-{len(IN_MEMORY_DB["time_slots"]) + 1}'
            IN_MEMORY_DB['time_slots'].append(payload)
    return RedirectResponse('/manage-slots', status_code=status.HTTP_303_SEE_OTHER)


@app.get('/admin/slots/edit/{slot_id}', name='admin_edit_slot_get')
@app.post('/admin/slots/edit/{slot_id}', name='admin_edit_slot_post')
async def admin_edit_slot(request: Request, slot_id: str, slot_name: str = Form(default=''), start_time: str = Form(default=''), end_time: str = Form(default=''), is_active: Optional[str] = Form(default=None)):
    current = get_current_user(request)
    if not current or not current.is_admin:
        return RedirectResponse(url='/user_menu', status_code=status.HTTP_303_SEE_OTHER)
    if request.method == 'GET':
        slots = list(get_collection('time_slots').find()) if mongo_db is not None else IN_MEMORY_DB['time_slots']
        slot = next((item for item in slots if str(item.get('_id')) == str(slot_id)), None)
        if slot:
            return RedirectResponse('/manage-slots', status_code=status.HTTP_303_SEE_OTHER)
        return RedirectResponse('/manage-slots', status_code=status.HTTP_303_SEE_OTHER)
    if not slot_name or not start_time or not end_time:
        return RedirectResponse('/manage-slots', status_code=status.HTTP_303_SEE_OTHER)
    payload = {
        'slot_name': slot_name,
        'start_time': start_time,
        'end_time': end_time,
        'is_active': parse_checkbox_flag(is_active),
    }
    if mongo_db is not None:
        mongo_db.time_slots.update_one({'_id': ObjectId(slot_id)}, {'$set': payload})
    else:
        for slot in IN_MEMORY_DB['time_slots']:
            if str(slot.get('_id')) == str(slot_id):
                slot.update(payload)
                break
    return RedirectResponse('/manage-slots', status_code=status.HTTP_303_SEE_OTHER)


@app.post('/admin/slots/toggle-status/{slot_id}', name='toggle_slot_status')
async def toggle_slot_status(request: Request, slot_id: str):
    current = get_current_user(request)
    if not current or not current.is_admin:
        return RedirectResponse('/user_menu', status_code=status.HTTP_303_SEE_OTHER)
    if mongo_db is not None:
        slot = mongo_db.time_slots.find_one({'_id': ObjectId(slot_id)})
        if not slot:
            return RedirectResponse('/manage-slots', status_code=status.HTTP_303_SEE_OTHER)
        mongo_db.time_slots.update_one({'_id': ObjectId(slot_id)}, {'$set': {'is_active': not bool(slot.get('is_active', True))}})
    else:
        for slot in IN_MEMORY_DB['time_slots']:
            if str(slot.get('_id')) == str(slot_id):
                slot['is_active'] = not bool(slot.get('is_active', True))
                break
    return RedirectResponse('/manage-slots', status_code=status.HTTP_303_SEE_OTHER)


@app.get('/admin/menu/add', name='admin_add_food_get')
@app.post('/admin/menu/add', name='admin_add_food_post')
async def admin_add_food(
    request: Request,
    item_name: str = Form(default=''),
    name: str = Form(default=''),
    description: str = Form(default=''),
    price: float = Form(default=0.0),
    category: str = Form(default='Meals'),
    image_url: str = Form(default=''),
    item_status: str = Form(default='Active'),
    availability: str = Form(default='1')
):
    current = get_current_user(request)
    if not current or not current.is_admin:
        return RedirectResponse(url='/user_menu', status_code=status.HTTP_303_SEE_OTHER)
    resolved_name = (name or item_name or '').strip()
    if request.method == 'GET':
        return render_template(request, 'admin_food_form.html', action='Add', food=None)
    if not resolved_name or price <= 0:
        return RedirectResponse('/manage_items', status_code=status.HTTP_303_SEE_OTHER)
    item = {
        'item_name': resolved_name,
        'description': description,
        'price': price,
        'category': category,
        'image_url': image_url or 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&auto=format&fit=crop&q=80',
        'status': 'Active' if availability not in ['', '0', 'false', 'False', 'FALSE'] else 'Deleted',
        'created_at': datetime.utcnow(),
    }
    if mongo_db is not None:
        mongo_db.menu.insert_one(item)
    else:
        item['_id'] = f'menu-{len(IN_MEMORY_DB["menu"]) + 1}'
        IN_MEMORY_DB['menu'].append(item)
    return RedirectResponse('/manage_items', status_code=status.HTTP_303_SEE_OTHER)


@app.get('/admin/menu/edit/{item_id}', name='admin_edit_food_get')
@app.post('/admin/menu/edit/{item_id}', name='admin_edit_food_post')
async def admin_edit_food(
    request: Request,
    item_id: str,
    item_name: str = Form(default=''),
    name: str = Form(default=''),
    description: str = Form(default=''),
    price: float = Form(default=0.0),
    category: str = Form(default='Meals'),
    image_url: str = Form(default=''),
    item_status: str = Form(default='Active'),
    availability: str = Form(default='1')
):
    current = get_current_user(request)
    if not current or not current.is_admin:
        return RedirectResponse(url='/user_menu', status_code=status.HTTP_303_SEE_OTHER)
    resolved_name = (name or item_name or '').strip()
    if request.method == 'GET':
        item = None
        if mongo_db is not None:
            item = mongo_db.menu.find_one({'_id': ObjectId(item_id)})
        else:
            item = next((itm for itm in IN_MEMORY_DB['menu'] if str(itm.get('_id')) == str(item_id)), None)
        if item is not None:
            item = normalize_menu_record(item)
        return render_template(request, 'admin_food_form.html', action='Edit', food=item)
    if not resolved_name or price <= 0:
        return RedirectResponse('/manage_items', status_code=status.HTTP_303_SEE_OTHER)
    resolved_status = 'Active' if availability not in ['', '0', 'false', 'False', 'FALSE'] else 'Deleted'
    if mongo_db is not None:
        mongo_db.menu.update_one({'_id': ObjectId(item_id)}, {'$set': {'item_name': resolved_name, 'description': description, 'price': price, 'category': category, 'image_url': image_url, 'status': resolved_status}})
    else:
        for item in IN_MEMORY_DB['menu']:
            if str(item.get('_id')) == str(item_id):
                item['item_name'] = resolved_name
                item['description'] = description
                item['price'] = price
                item['category'] = category
                item['image_url'] = image_url
                item['status'] = resolved_status
                break
    return RedirectResponse('/manage_items', status_code=status.HTTP_303_SEE_OTHER)


@app.post('/admin/orders/{order_id}/status', name='update_order_status')
async def update_order_status(request: Request, order_id: str):
    current = get_current_user(request)
    if not current or not current.is_admin:
        return JSONResponse({'success': False, 'message': 'Admin access required.'}, status_code=403)

    try:
        content_type = request.headers.get('content-type', '')
        if 'application/json' in content_type:
            payload = await request.json()
            status_value = payload.get('status') or payload.get('status_value')
        else:
            form = await request.form()
            status_value = form.get('status') or form.get('status_value')
    except Exception:
        return JSONResponse({'success': False, 'message': 'Invalid status payload.'}, status_code=400)

    if not status_value:
        return JSONResponse({'success': False, 'message': 'A valid status is required.'}, status_code=400)

    if mongo_db is not None:
        mongo_db.orders.update_one({'_id': ObjectId(order_id)}, {'$set': {'status': status_value}})
    else:
        for order in IN_MEMORY_DB['orders']:
            if str(order.get('_id')) == str(order_id):
                order['status'] = status_value
                break
    return JSONResponse({'success': True, 'message': f'Order status updated to {status_value}.'})


@app.post('/admin/menu/toggle-status/{item_id}', name='toggle_item_status')
async def toggle_item_status(request: Request, item_id: str):
    current = get_current_user(request)
    if not current or not current.is_admin:
        return RedirectResponse('/user_menu', status_code=status.HTTP_303_SEE_OTHER)
    if mongo_db is not None:
        item = mongo_db.menu.find_one({'_id': ObjectId(item_id)})
        new_status = 'Deleted' if item.get('status') == 'Active' else 'Active'
        mongo_db.menu.update_one({'_id': ObjectId(item_id)}, {'$set': {'status': new_status}})
    else:
        for item in IN_MEMORY_DB['menu']:
            if str(item.get('_id')) == str(item_id):
                item['status'] = 'Deleted' if item.get('status') == 'Active' else 'Active'
                break
    return RedirectResponse('/manage_items', status_code=status.HTTP_303_SEE_OTHER)


def seed_database():
    ensure_seed_data()
    print('Database seed complete.')


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=5000, reload=False)
