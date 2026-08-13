from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_root_route():
    response = client.get('/')
    assert response.status_code == 200


def test_food_api():
    response = client.get('/api/food')
    assert response.status_code == 200
    assert isinstance(response.json(), list)
