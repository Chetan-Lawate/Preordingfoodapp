from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app as app_module
from app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_in_memory_store(monkeypatch):
    monkeypatch.setattr(app_module, 'mongo_db', None)
    for documents in app_module.IN_MEMORY_DB.values():
        documents.clear()
    app_module.ensure_seed_data()
    client.cookies.clear()


def register_user(role='Student'):
    suffix = uuid4().hex
    response = client.post('/register', data={
        'username': f'Test User {suffix}',
        'email': f'test.{suffix}@example.com',
        'password': 'strong-password',
        'role': role,
    }, follow_redirects=False)
    user = app_module.IN_MEMORY_DB['users'][-1]
    client.cookies.set('user_id', user['_id'])
    return response, user


def test_root_route():
    response = client.get('/')
    assert response.status_code == 200


def test_food_api():
    response = client.get('/api/food')
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_health_endpoint():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_public_pages_render():
    for path in ('/menu', '/user-menu', '/cart', '/login', '/register'):
        response = client.get(path)
        assert response.status_code == 200


def test_authenticated_pages_redirect_guests():
    for path in ('/orders', '/admin/dashboard', '/manage_items', '/manage-slots'):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303


def test_login_rejects_unknown_user():
    response = client.post('/login', data={'email': 'unknown@example.com', 'password': 'invalid'}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == '/login'


def test_registration_creates_student_session():
    email = f'new.student.{uuid4().hex}@example.com'
    response = client.post(
        '/register',
        data={'username': f'New Student {uuid4().hex}', 'email': email, 'password': 'strong-password'},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers['location'] == '/user_menu'
    assert 'user_id=' in response.headers['set-cookie']


def test_template_url_for_maps_paths_and_queries():
    url = app_module.template_url_for('admin_edit_food', food_id='menu-1', q='club sandwich')
    assert url == '/admin/menu/edit/menu-1?q=club sandwich'


def test_in_memory_collection_supports_query_operators():
    collection = app_module.InMemoryCollection([
        {'name': 'active', 'score': 10, 'tag': 'food'},
        {'name': 'inactive', 'score': 2, 'tag': 'drink'},
    ])
    assert len(collection.find({'score': {'$gte': 5}})) == 1
    assert len(collection.find({'tag': {'$in': ['food']}})) == 1
    assert len(collection.find({'tag': {'$ne': 'food'}})) == 1
    assert len(collection.find({'score': {'$lte': 2}})) == 1
    assert len(collection.find({'$or': [{'tag': 'food'}, {'score': 2}]})) == 2
    assert len(collection.find({'$and': [{'tag': 'food'}, {'score': 10}]})) == 1

    collection.insert_one({'name': 'new'})
    collection.update_one({'name': 'new'}, {'$set': {'score': 7}})
    assert collection.find_one({'name': 'new'})['score'] == 7


def test_normalize_template_values_adds_aliases():
    normalized = app_module.normalize_template_value({'_id': 'item-1', 'item_name': 'Sandwich'})
    assert normalized['id'] == 'item-1'
    assert normalized['item_id'] == 'item-1'
    assert normalized['name'] == 'Sandwich'
    assert app_module.normalize_template_value([{'slot_name': 'Lunch'}])[0]['name'] == 'Lunch'


def test_payload_and_persistence_helpers():
    assert app_module.parse_checkbox_flag('off') is False
    slot = app_module.build_slot_payload('Break', '10:00', '10:30', '1')
    app_module.save_slot('', slot)
    slot_id = app_module.IN_MEMORY_DB['time_slots'][-1]['_id']
    app_module.save_slot(slot_id, {'slot_name': 'Updated'})
    assert app_module.IN_MEMORY_DB['time_slots'][-1]['slot_name'] == 'Updated'

    item = app_module.build_menu_payload('Tea', '', 'Hot', 20, 'Beverages', '', '1')
    app_module.save_menu_item('', item)
    item_id = app_module.IN_MEMORY_DB['menu'][-1]['_id']
    app_module.save_menu_item(item_id, {'item_name': 'Iced Tea'})
    assert app_module.IN_MEMORY_DB['menu'][-1]['item_name'] == 'Iced Tea'


def test_in_memory_cursor_and_empty_collection_paths():
    cursor = app_module.InMemoryCursor([{'id': 1}, {'id': 2}])
    assert len(cursor) == 2
    assert cursor[0]['id'] == 1
    assert cursor.limit(1) == [{'id': 1}]
    collection = app_module.InMemoryCollection([])
    assert collection.find_one({'id': 1}) is None
    assert collection.count_documents({}) == 0
    assert collection.update_one({'id': 1}, {'$set': {'name': 'missing'}}).modified_count == 0
    collection.insert_many([{}, {}])
    assert len(collection.find()) == 2


def test_normalization_and_lookup_fallbacks():
    assert app_module.get_user_by_id(None) is None
    assert app_module.get_user_by_id('missing') is None
    assert app_module.get_menu_by_id(None) is None
    assert app_module.get_menu_by_id('missing') is None
    assert app_module.get_current_user(type('Request', (), {'cookies': {}})()) is None

    menu = app_module.normalize_menu_record({'_id': 'menu-1', 'item_name': 'Soup'})
    assert menu['availability'] is False
    assert menu['status'] == 'Active'
    assert menu['description'] == ''
    slot = app_module.normalize_slot_record({'_id': 'slot-1', 'slot_name': 'Lunch'})
    assert slot['id'] == 'slot-1'
    assert slot['name'] == 'Lunch'
    assert slot['is_active'] is True


def test_order_view_handles_missing_menu_item():
    order = {
        '_id': 'order-1',
        'user_id': 'missing',
        'items': [{'id': 'missing', 'food_name': 'Removed', 'price': 10, 'quantity': 2}],
    }
    view = app_module.build_order_view(order)
    assert view.user.username == 'Unknown User'
    assert view.items[0].food_name == 'Removed'
    assert view.items[0].subtotal == 20


def test_template_url_fallbacks_and_mapping_defaults():
    assert app_module.template_url_for('custom_page') == '/custom-page'
    assert app_module.template_url_for('custom_page', page=2) == '/custom-page?page=2'
    assert app_module.template_url_for('login') == '/login'
    assert app_module.append_query_params('/search?existing=1', {'page': 2}) == '/search?existing=1&page=2'
    assert app_module.normalize_mapping({'item_id': 'item-2'})['id'] == 'item-2'
    assert app_module.normalize_mapping({'slot_name': 'Morning'})['name'] == 'Morning'


def test_context_and_normalization_existing_values():
    user = app_module.make_user_context({'id': 'user-1', 'username': 'Student', 'role': 'Student'})
    assert user.id == 'user-1'
    assert user.is_admin is False
    client.cookies.set('user_id', user.id)
    app_module.IN_MEMORY_DB['users'].append({'_id': user.id, 'username': 'Student', 'role': 'Student'})
    assert app_module.get_current_user(type('Request', (), {'cookies': {'user_id': user.id}})()).username == 'Student'
    assert app_module.get_collection('custom').find_one() is None

    menu = app_module.normalize_menu_record({
        'id': 'menu-1', 'name': 'Soup', 'availability': True, 'status': 'Active',
        'description': 'Hot', 'image_url': '/soup.jpg', 'price': 10, 'category': 'Meals',
    })
    assert menu['name'] == 'Soup'
    slot = app_module.normalize_slot_record({'id': 'slot-1', 'name': 'Lunch', 'is_active': False})
    assert slot['name'] == 'Lunch'
    assert slot['is_active'] is False


def test_authenticated_and_invalid_request_branches():
    _, student = register_user()
    session = {'user_id': student['_id']}
    assert client.get('/login', cookies=session, follow_redirects=False).status_code == 303
    assert client.get('/register', cookies=session, follow_redirects=False).status_code == 303
    assert client.get('/menu?category=Meals&q=wrap').status_code == 200
    assert client.post('/checkout', data='not-json', headers={'content-type': 'application/json'}).status_code == 400
    assert client.post('/checkout', json={'items': [{'id': 'missing'}]}).status_code == 400

    _, admin = register_user('Admin')
    assert client.get('/', cookies={'user_id': admin['_id']}, follow_redirects=False).status_code == 303
    assert client.get('/admin/dashboard?break_time=Lunch&status=Ready').status_code == 200
    assert client.post('/manage-slots', data={'slot_name': 'Incomplete'}).status_code == 200
    assert client.post('/admin/slots/edit/missing', data={'slot_name': 'Incomplete'}).status_code == 200
    assert client.post('/admin/menu/add', data={'name': '', 'price': '0'}).status_code == 200
    assert client.post('/admin/menu/edit/missing', data={'name': '', 'price': '0'}).status_code == 200
    assert client.post('/admin/orders/missing/status', data={}).status_code == 400


def test_admin_dashboard_and_menu_crud():
    response, _ = register_user('Admin')
    assert response.headers['location'] == '/admin/dashboard'
    assert client.get('/admin/dashboard').status_code == 200
    assert client.get('/manage_items').status_code == 200
    assert client.get('/admin/menu/add').status_code == 200

    response = client.post('/admin/menu/add', data={
        'name': 'Test Wrap', 'description': 'Fresh wrap', 'price': '125',
        'category': 'Meals', 'availability': '1',
    }, follow_redirects=False)
    assert response.headers['location'] == '/manage_items'
    item = app_module.IN_MEMORY_DB['menu'][-1]
    item_id = item['_id']
    assert client.get(f'/admin/menu/edit/{item_id}').status_code == 200
    response = client.post(f'/admin/menu/edit/{item_id}', data={
        'name': 'Updated Wrap', 'description': 'Updated', 'price': '135',
        'category': 'Meals', 'availability': '1',
    }, follow_redirects=False)
    assert response.headers['location'] == '/manage_items'
    assert app_module.get_menu_by_id(item_id)['item_name'] == 'Updated Wrap'
    assert client.post(f'/admin/menu/toggle-status/{item_id}', follow_redirects=False).status_code == 303


def test_admin_slot_crud_and_toggle():
    register_user('Admin')
    assert client.get('/manage-slots').status_code == 200
    response = client.post('/manage-slots', data={
        'slot_name': 'Test Break', 'start_time': '09:00 AM', 'end_time': '09:30 AM', 'is_active': '1',
    }, follow_redirects=False)
    assert response.headers['location'] == '/manage-slots'
    slot_id = app_module.IN_MEMORY_DB['time_slots'][-1]['_id']
    assert client.get(f'/admin/slots/edit/{slot_id}', follow_redirects=False).status_code == 303
    response = client.post(f'/admin/slots/edit/{slot_id}', data={
        'slot_name': 'Updated Break', 'start_time': '09:15 AM', 'end_time': '09:45 AM', 'is_active': '1',
    }, follow_redirects=False)
    assert response.headers['location'] == '/manage-slots'
    assert client.post(f'/admin/slots/toggle-status/{slot_id}', follow_redirects=False).status_code == 303


def test_checkout_orders_and_status():
    register_user()
    item_id = app_module.IN_MEMORY_DB['menu'][0]['_id']
    response = client.post('/checkout', json={
        'items': [{'id': item_id, 'quantity': 2}],
        'break_time': '10:00 AM - 10:45 AM (Morning Break)',
    })
    assert response.status_code == 200
    order_id = response.json()['order_id']
    assert client.get('/orders').status_code == 200
    response = client.get(f'/api/orders/{order_id}/status')
    assert response.status_code == 200
    assert response.json()['status'] == 'Pending'


def test_checkout_rejects_invalid_payloads():
    register_user()
    assert client.post('/checkout', json={}).status_code == 400
    assert client.post('/checkout', json={'items': [{'id': 'missing'}]}).status_code == 400


def test_admin_can_update_order_status():
    _, student = register_user()
    item_id = app_module.IN_MEMORY_DB['menu'][0]['_id']
    checkout = client.post('/checkout', json={
        'items': [{'id': item_id, 'quantity': 1}], 'break_time': 'Lunch',
    })
    order_id = checkout.json()['order_id']
    client.cookies.set('user_id', student['_id'])
    _, admin = register_user('Admin')
    client.cookies.set('user_id', admin['_id'])
    response = client.post(f'/admin/orders/{order_id}/status', json={'status': 'Ready'})
    assert response.status_code == 200
    assert app_module.IN_MEMORY_DB['orders'][0]['status'] == 'Ready'
