"""Integration checks for core user stories and authorization."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
import app as shop


def csrf_from(page):
    m = re.search(r'name="csrf"\s+value="([^"]+)"', page.text)
    assert m, f"No CSRF token found in {page.url}: {page.text[:300]}"
    return m.group(1)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(shop, "DB_PATH", tmp_path / "test.sqlite3")
    monkeypatch.setenv("SHOP_ADMIN_EMAIL", "admin@demo.shop")
    monkeypatch.setenv("SHOP_ADMIN_PASSWORD", "DemoAdmin123!")
    with TestClient(shop.app, follow_redirects=True) as client:
        yield client


def register(client, name, email, password="password123"):
    page = client.get("/register")
    return client.post("/register", data={"name": name, "email": email, "password": password, "csrf": csrf_from(page)})


def login(client, email, password):
    page = client.get("/login")
    return client.post("/login", data={"email": email, "password": password, "csrf": csrf_from(page)})


def logout(client):
    page = client.get("/")
    return client.post("/logout", data={"csrf": csrf_from(page)})


def checkout(client, recipient="Demo Customer"):
    p = client.get("/checkout")
    return client.post("/checkout", data={"csrf": csrf_from(p), "recipient": recipient, "phone": "1234567890", "address": "123 Test Street, Example City"})


def test_health_and_catalog(client):
    assert client.get("/health").json()["status"] == "ok"
    assert "Everyday Hoodie" in client.get("/").text
    assert "Wireless Headphones" in client.get("/?q=wireless").text
    assert "Everyday Hoodie" not in client.get("/?q=wireless").text
    assert "No matching products" in client.get("/?q=unfindablething").text
    assert client.get("/products/9999").status_code == 404


def test_customer_auth_and_access_control(client):
    assert "Account created" in register(client, "Demo User", "demo@example.com").text
    assert "already registered" in register(client, "Another User", "DEMO@example.com").text
    assert login(client, "demo@example.com", "wrongpass").status_code == 401
    assert "Signed in successfully" in login(client, "demo@example.com", "password123").text
    assert client.get("/admin").status_code == 403
    assert client.get("/admin/products").status_code == 403
    assert "You have signed out" in logout(client).text
    assert client.get("/orders").url.path == "/login"


def test_csrf_rejection(client):
    # Even without a user account, a forged mutation must fail.
    assert client.post("/register", data={"name": "A User", "email": "user@test.com", "password": "abc123456", "csrf": "incorrect"}).status_code == 403


def test_order_inventory_snapshot_and_permissions(client):
    register(client, "First Buyer", "first@test.com")
    login(client, "first@test.com", "password123")
    with shop.connect() as db:
        hoodie = db.execute("SELECT id,stock,price_cents FROM products WHERE name=?", ("Everyday Hoodie",)).fetchone()
    product_id, original_stock, price = hoodie["id"], hoodie["stock"], hoodie["price_cents"]
    product_page = client.get(f"/products/{product_id}")
    add = client.post(f"/cart/add/{product_id}", data={"quantity": "2", "csrf": csrf_from(product_page)})
    assert "Added to your cart" in add.text
    assert "Everyday Hoodie" in client.get("/cart").text
    complete = checkout(client)
    assert "Order placed" in complete.text
    with shop.connect() as db:
        created = db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 1").fetchone()
        lines = db.execute("SELECT * FROM order_items WHERE order_id=?", (created["id"],)).fetchall()
        left = db.execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()[0]
    assert created["status"] == "Pending"
    assert created["total_cents"] == 2 * price
    assert len(lines) == 1 and lines[0]["unit_price_cents"] == price
    assert left == original_stock - 2
    assert "Your cart is empty" in client.get("/cart").text
    oid = created["id"]
    logout(client)
    register(client, "Second Buyer", "second@test.com")
    login(client, "second@test.com", "password123")
    assert client.get(f"/orders/{oid}").status_code == 404
    logout(client)
    login(client, "admin@demo.shop", "DemoAdmin123!")
    assert "Administrator dashboard" in client.get("/admin").text
    assert "First Buyer" in client.get("/admin/orders").text
    # Only a valid transition is allowed.
    page = client.get(f"/orders/{oid}")
    invalid = client.post(f"/admin/orders/{oid}/status", data={"csrf": csrf_from(page), "status": "Delivered"})
    assert invalid.status_code == 400
    with shop.connect() as db:
        assert db.execute("SELECT status FROM orders WHERE id=?", (oid,)).fetchone()[0] == "Pending"
    for next_status in ["Confirmed", "Shipped", "Delivered"]:
        page = client.get(f"/orders/{oid}")
        response = client.post(f"/admin/orders/{oid}/status", data={"csrf": csrf_from(page), "status": next_status})
        assert response.status_code == 200 and next_status in response.text
    page = client.get(f"/orders/{oid}")
    assert client.post(f"/admin/orders/{oid}/status", data={"csrf": csrf_from(page), "status": "Pending"}).status_code == 400
    with shop.connect() as db:
        assert db.execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()[0] == original_stock-2


def test_admin_product_and_cancellation_restores_once(client):
    register(client, "A Customer", "customer@test.com")
    login(client, "customer@test.com", "password123")
    with shop.connect() as db:
        pid = db.execute("SELECT id FROM products WHERE name='Classic Cotton Tee'").fetchone()[0]
        original = db.execute("SELECT stock FROM products WHERE id=?", (pid,)).fetchone()[0]
    page = client.get(f"/products/{pid}")
    client.post(f"/cart/add/{pid}", data={"csrf": csrf_from(page), "quantity": "3"})
    checkout(client)
    with shop.connect() as db: oid = db.execute("SELECT max(id) FROM orders").fetchone()[0]
    logout(client)
    login(client, "admin@demo.shop", "DemoAdmin123!")
    form = client.get("/admin/products/new")
    with shop.connect() as db: catid = db.execute("SELECT id FROM categories LIMIT 1").fetchone()[0]
    add = client.post("/admin/products/save", data={"csrf": csrf_from(form), "name": "Sample Notebook", "category_id": str(catid), "price": "12.50", "stock": "10", "description": "Demo item", "image_url": "📕", "is_active": "1"})
    assert "Sample Notebook" in add.text
    with shop.connect() as db:
        assert db.execute("SELECT price_cents FROM products WHERE name='Sample Notebook'").fetchone()[0] == 1250
    page = client.get(f"/orders/{oid}")
    success = client.post(f"/admin/orders/{oid}/status", data={"csrf": csrf_from(page), "status": "Cancelled"})
    assert "Cancelled" in success.text
    again = client.post(f"/admin/orders/{oid}/status", data={"csrf": csrf_from(page), "status": "Cancelled"})
    assert again.status_code == 400
    with shop.connect() as db:
        assert db.execute("SELECT stock FROM products WHERE id=?", (pid,)).fetchone()[0] == original


def test_insufficient_stock_aborts_checkout(client):
    register(client, "Test Customer", "stock@test.com")
    login(client, "stock@test.com", "password123")
    with shop.connect() as db:
        product = db.execute("SELECT id,stock FROM products LIMIT 1").fetchone()
        pid = product["id"]
    product_page = client.get(f"/products/{pid}")
    client.post(f"/cart/add/{pid}", data={"quantity": "1", "csrf": csrf_from(product_page)})
    # Another process (admin) adjusts inventory after the product was added.
    with shop.connect() as db: db.execute("UPDATE products SET stock=0 WHERE id=?", (pid,))
    before = client.get("/checkout")
    result = client.post("/checkout", data={"csrf": csrf_from(before), "recipient": "Valid Name", "phone": "12345678", "address": "My full test address"})
    assert result.status_code == 400
    with shop.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM cart_items").fetchone()[0] == 1


def test_bad_product_price_rejected(client):
    login(client, "admin@demo.shop", "DemoAdmin123!")
    page = client.get("/admin/products/new")
    with shop.connect() as db: catid = db.execute("SELECT id FROM categories LIMIT 1").fetchone()[0]
    resp = client.post("/admin/products/save", data={"csrf": csrf_from(page), "name": "Invalid Product", "category_id": str(catid), "price": "-1", "stock": "10", "is_active": "1"})
    assert resp.status_code == 400
    with shop.connect() as db: assert db.execute("SELECT COUNT(*) FROM products WHERE name='Invalid Product'").fetchone()[0] == 0


def test_json_api_catalog_and_openapi(client):
    docs = client.get('/openapi.json')
    assert docs.status_code == 200
    assert '/api/v1/products' in docs.json()['paths']
    assert client.get('/api-docs').status_code == 200
    cats = client.get('/api/v1/categories').json()['categories']
    assert len(cats) == 4 and all('name' in c for c in cats)
    result = client.get('/api/v1/products', params={'q': 'hoodie', 'page_size': 5})
    assert result.status_code == 200 and result.json()['total'] == 1
    product = result.json()['items'][0]
    assert product['name'] == 'Everyday Hoodie'
    assert client.get(f"/api/v1/products/{product['id']}").json()['stock'] == 30
    assert client.get('/api/v1/products/999999').status_code == 404
    assert client.get('/api/v1/products?page_size=101').status_code == 422


def test_json_api_requires_auth_and_correct_roles(client):
    assert client.get('/api/v1/me').status_code == 401
    assert client.get('/api/v1/csrf').status_code == 401
    assert client.get('/api/v1/orders').status_code == 401
    assert client.get('/api/v1/admin/dashboard').status_code == 401
    register(client, 'Buyer', 'buyer@test.com')
    login(client, 'buyer@test.com', 'password123')
    assert client.get('/api/v1/me').json()['user']['role'] == 'customer'
    assert client.get('/api/v1/orders').json()['orders'] == []
    assert client.get('/api/v1/admin/dashboard').status_code == 403
    payload = {'name': 'Test', 'category_id': 1, 'price_cents': 100, 'stock': 2}
    assert client.post('/api/v1/admin/products', json=payload).status_code == 403


def test_json_api_admin_product_create_update_and_csrf(client):
    login(client, 'admin@demo.shop', 'DemoAdmin123!')
    with shop.connect() as db:
        category_id = db.execute('SELECT id FROM categories LIMIT 1').fetchone()[0]
    payload = {'name': 'REST API Test Item', 'category_id': category_id, 'price_cents': 1850, 'stock': 5}
    assert client.post('/api/v1/admin/products', json=payload).status_code == 403
    csrf = client.get('/api/v1/csrf').json()['csrf_token']
    headers = {'X-CSRF-Token': csrf}
    assert client.post('/api/v1/admin/products', json={**payload,'price_cents':-1}, headers=headers).status_code == 422
    assert client.post('/api/v1/admin/products', json={**payload,'category_id':9999999}, headers=headers).status_code == 422
    created = client.post('/api/v1/admin/products', json=payload, headers=headers)
    assert created.status_code == 201
    pid = created.json()['product']['id']
    assert client.get(f'/api/v1/products/{pid}').json()['price_cents'] == 1850
    updated = client.put(f'/api/v1/admin/products/{pid}', json={**payload,'stock':9,'is_active':False}, headers=headers)
    assert updated.status_code == 200 and updated.json()['product']['stock'] == 9
    assert client.get(f'/api/v1/products/{pid}').status_code == 404
    assert client.put('/api/v1/admin/products/8888888', json=payload, headers=headers).status_code == 404
    with shop.connect() as db:
        assert db.execute('SELECT stock,is_active FROM products WHERE id=?', (pid,)).fetchone()[:] == (9,0)


def test_json_api_order_ownership_and_admin_status_changes(client):
    register(client, 'Buyer One', 'buyer1@test.com')
    login(client, 'buyer1@test.com', 'password123')
    with shop.connect() as db:
        product = db.execute('SELECT id,stock FROM products LIMIT 1').fetchone()
    pid, original = product['id'], product['stock']
    page = client.get(f'/products/{pid}')
    client.post(f'/cart/add/{pid}', data={'csrf':csrf_from(page),'quantity':'2'})
    checkout(client)
    result = client.get('/api/v1/orders')
    assert result.status_code == 200 and len(result.json()['orders']) == 1
    oid = result.json()['orders'][0]['id']
    detail = client.get(f'/api/v1/orders/{oid}')
    assert detail.status_code == 200 and len(detail.json()['items']) == 1
    logout(client)
    register(client, 'Buyer Two', 'buyer2@test.com')
    login(client, 'buyer2@test.com', 'password123')
    assert client.get(f'/api/v1/orders/{oid}').status_code == 404
    logout(client)
    login(client, 'admin@demo.shop', 'DemoAdmin123!')
    assert len(client.get('/api/v1/admin/orders').json()['orders']) == 1
    csrf = client.get('/api/v1/csrf').json()['csrf_token']
    headers = {'X-CSRF-Token':csrf}
    assert client.patch(f'/api/v1/admin/orders/{oid}/status',json={'status':'Delivered'},headers=headers).status_code == 409
    move = client.patch(f'/api/v1/admin/orders/{oid}/status',json={'status':'Cancelled'},headers=headers)
    assert move.status_code == 200 and move.json()['status'] == 'Cancelled'
    assert client.patch(f'/api/v1/admin/orders/{oid}/status',json={'status':'Cancelled'},headers=headers).status_code == 409
    with shop.connect() as db:
        assert db.execute('SELECT stock FROM products WHERE id=?',(pid,)).fetchone()[0] == original
