"""Regression checks for visual-only upgrade and product photo input."""
import re
from fastapi.testclient import TestClient
import app as shop


def token(page):
    return re.search(r'name="csrf"\s+value="([^"]+)"', page.text).group(1)


def test_storefront_photos_and_fallbacks(tmp_path, monkeypatch):
    monkeypatch.setattr(shop, 'DB_PATH', tmp_path / 'visual.sqlite3')
    with TestClient(shop.app) as c:
        page = c.get('/')
        assert page.status_code == 200
        assert 'hero-stage' in page.text
        assert 'showroom.js' in page.text
        assert 'images.unsplash.com' in page.text
        assert 'illustrations/headphones.svg' in page.text
        assert 'Test Notebook' in page.text
        assert 'Wireless Mouse' in page.text
        assert c.get('/static/illustrations/notebook.svg').status_code == 200
        assert 'gallery-choice' in c.get('/products/1').text


def test_admin_accepts_https_photo_url_and_rejects_unsafe_url(tmp_path, monkeypatch):
    monkeypatch.setattr(shop, 'DB_PATH', tmp_path / 'visual.sqlite3')
    with TestClient(shop.app) as c:
        login_page = c.get('/login')
        c.post('/login', data={'csrf': token(login_page), 'email': 'admin@demo.shop', 'password': 'DemoAdmin123!'})
        form = c.get('/admin/products/new')
        assert 'Product image URL' in form.text
        url = 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e'
        data = {'csrf': token(form), 'name': 'Photo Demo Item', 'description': 'A demo', 'category_id': '1', 'price': '11.25', 'stock': '3', 'image_url': url, 'is_active': '1'}
        response = c.post('/admin/products/save', data=data)
        assert response.status_code == 200
        with shop.connect() as db:
            item = db.execute("SELECT * FROM products WHERE name='Photo Demo Item'").fetchone()
            assert item['image_url'] == url
        data['name'] = 'Unsafe Demo Item'
        data['image_url'] = 'javascript:alert(1)'
        response = c.post('/admin/products/save', data=data)
        assert response.status_code == 400
        with shop.connect() as db:
            assert db.execute("SELECT COUNT(*) FROM products WHERE name='Unsafe Demo Item'").fetchone()[0] == 0
