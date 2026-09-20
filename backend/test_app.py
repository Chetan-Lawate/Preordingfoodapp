from uuid import uuid4

from fastapi.testclient import TestClient

import app as app_module
from app import app

client = TestClient(app)


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


def test_normalize_template_values_adds_aliases():
    normalized = app_module.normalize_template_value({'_id': 'item-1', 'item_name': 'Sandwich'})
    assert normalized['id'] == 'item-1'
    assert normalized['item_id'] == 'item-1'
    assert normalized['name'] == 'Sandwich'
