"""Online Shopping System: educational browser/server project.

Run with `python app.py` after installing requirements.
Flask is not required: FastAPI provides the Python backend and Jinja2 renders HTML.
Only a simulated Cash on Delivery checkout is implemented.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import sys
from contextlib import contextmanager, asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import FastAPI, Form, Request, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("SHOP_DB", BASE / "shop.sqlite3"))
BASE.mkdir(parents=True, exist_ok=True)
SECRET = os.getenv("SHOP_SECRET", "")
if not SECRET:
    secret_path = BASE / ".session_secret"
    if secret_path.exists():
        SECRET = secret_path.read_text(encoding="utf-8").strip()
    else:
        SECRET = secrets.token_urlsafe(48)
        secret_path.write_text(SECRET, encoding="utf-8")
        try: secret_path.chmod(0o600)
        except OSError: pass
signer = URLSafeTimedSerializer(SECRET, salt="onlineshop-session-v1")
@asynccontextmanager
async def lifespan(application: FastAPI):
    init_db(seed=True)
    yield

app = FastAPI(title="Online Shopping System", docs_url="/api-docs", redoc_url=None, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))

CATEGORIES = ["Clothing", "Electronics", "Books", "Accessories"]
SEED_PRODUCTS = [
    ("Everyday Hoodie", "Clothing", "A comfortable unisex hoodie for everyday wear.", 4490, 30, "hoodie", "👕"),
    ("Classic Cotton Tee", "Clothing", "Soft cotton shirt with a relaxed fit.", 2290, 45, "tee", "👕"),
    ("Wireless Headphones", "Electronics", "Over-ear headphones with comfortable ear pads.", 7990, 16, "headphones", "🎧"),
    ("Study Desk Lamp", "Electronics", "Minimal lamp with adjustable angle.", 3490, 20, "lamp", "💡"),
    ("Python Study Guide", "Books", "An introductory guide to Python programming.", 2690, 22, "book", "📖"),
    ("Canvas Tote Bag", "Accessories", "Reusable everyday tote with inner pocket.", 1990, 37, "bag", "👜"),
    ("Wireless Mouse", "Electronics", "Wireless computer mouse for daily use.", 2599, 18, "mouse", "🖱️"),
    ("Test Notebook", "Books", "Simple notebook for study notes and planning.", 999, 5, "notebook", "📓"),
]
STATUS_NEXT = {"Pending": {"Confirmed", "Cancelled"}, "Confirmed": {"Shipped", "Cancelled"}, "Shipped": {"Delivered"}, "Delivered": set(), "Cancelled": set()}

# Curated free-to-use Unsplash demonstration photography. URLs are loaded in the
# visitor's browser (no API keys or server-side scraping). Offline SVG fallbacks
# are bundled with the project. Photos illustrate the *type* of product; they
# are not photos of specific items being sold.
DEMO_PHOTOS = {
    "mouse": ("https://images.unsplash.com/photo-1772531606450-0dd023c265d7?auto=format&fit=crop&w=900&q=82", "Fer Troulik"),
    "headphones": ("https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=82", "Unsplash contributor"),
    "hoodie": ("https://images.unsplash.com/photo-1721111260412-5541dc8fbec5?auto=format&fit=crop&w=900&q=82", "Urban Minimals"),
    "tee": ("https://images.unsplash.com/photo-1620799139507-2a76f79a2f4d?auto=format&fit=crop&w=900&q=82", "Mediamodifier"),
    "lamp": ("https://images.unsplash.com/photo-1731762524352-b5663f83a830?auto=format&fit=crop&w=900&q=82", "Aashish Chandra"),
    "book": ("https://images.unsplash.com/photo-1565229284535-2cbbe3049123?auto=format&fit=crop&w=900&q=82", "Rick Muigo"),
    "bag": ("https://images.unsplash.com/photo-1772890753143-24991d807710?auto=format&fit=crop&w=900&q=82", "JIN Qin"),
    "notebook": ("https://images.unsplash.com/photo-1646808910032-2b18a6821eb7?auto=format&fit=crop&w=900&q=82", "aceofnet"),
}


def product_visual_key(name: str) -> str:
    n = name.lower()
    if "headphone" in n or "headset" in n: return "headphones"
    if "mouse" in n: return "mouse"
    if "hoodie" in n or "sweatshirt" in n: return "hoodie"
    if "t-shirt" in n or "tshirt" in n or "cotton tee" in n: return "tee"
    if "lamp" in n or "light" in n: return "lamp"
    if "notebook" in n or "journal" in n: return "notebook"
    if "book" in n or "guide" in n: return "book"
    if "tote" in n or "bag" in n: return "bag"
    return "generic"


def valid_product_image(value: str) -> bool:
    # Backwards-compatible with the existing emoji field; restrict external
    # images to HTTPS so URLs cannot inject javascript: or insecure resources.
    return (not value or (len(value) <= 12 and ":" not in value and "/" not in value)
            or (value.startswith("https://") and len(value) <= 500 and not any(c.isspace() for c in value)))


def with_visual(product):
    if product is None: return None
    p = dict(product)
    key = product_visual_key(p["name"])
    original = (p.get("image_url") or "").strip()
    demo_photo, photographer = DEMO_PHOTOS.get(key, ("", ""))
    p["photo_url"] = original if original.startswith("https://") else demo_photo
    p["photo_credit"] = "Custom image" if original.startswith("https://") else photographer
    p["visual_key"] = key
    p["fallback_url"] = f"/static/illustrations/{key}.svg"
    return p

@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout=15000")
    try:
        yield conn
    finally:
        conn.close()


def init_db(seed: bool = True):
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY, name TEXT NOT NULL CHECK(length(trim(name)) > 0),
          email TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL,
          role TEXT NOT NULL DEFAULT 'customer' CHECK(role IN ('customer','admin')),
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS categories (
          id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE
        );
        CREATE TABLE IF NOT EXISTS products (
          id INTEGER PRIMARY KEY, category_id INTEGER NOT NULL REFERENCES categories(id),
          name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
          price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
          stock INTEGER NOT NULL CHECK(stock >= 0), image_url TEXT NOT NULL DEFAULT '',
          is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS cart_items (
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          product_id INTEGER NOT NULL REFERENCES products(id),
          quantity INTEGER NOT NULL CHECK(quantity > 0),
          UNIQUE(user_id, product_id)
        );
        CREATE TABLE IF NOT EXISTS orders (
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
          recipient TEXT NOT NULL, phone TEXT NOT NULL, address TEXT NOT NULL,
          total_cents INTEGER NOT NULL CHECK(total_cents >= 0),
          status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Confirmed','Shipped','Delivered','Cancelled')),
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS order_items (
          id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id),
          product_id INTEGER NOT NULL REFERENCES products(id),
          quantity INTEGER NOT NULL CHECK(quantity > 0),
          unit_price_cents INTEGER NOT NULL CHECK(unit_price_cents >= 0)
        );
        CREATE INDEX IF NOT EXISTS ix_products_category ON products(category_id);
        CREATE INDEX IF NOT EXISTS ix_orders_user ON orders(user_id);
        """)
        if seed:
            for cat in CATEGORIES:
                db.execute("INSERT OR IGNORE INTO categories(name) VALUES (?)", (cat,))
            count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            if count == 0:
                for name, category, desc, cents, stock, image, emoji in SEED_PRODUCTS:
                    cid = db.execute("SELECT id FROM categories WHERE name=?", (category,)).fetchone()[0]
                    db.execute("INSERT INTO products(category_id,name,description,price_cents,stock,image_url) VALUES (?,?,?,?,?,?)", (cid, name, desc, cents, stock, emoji))
            # This fixed demo account is LOCAL ONLY; change before any deployment.
            email = os.getenv("SHOP_ADMIN_EMAIL", "admin@demo.shop")
            password = os.getenv("SHOP_ADMIN_PASSWORD", "DemoAdmin123!")
            if not db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
                db.execute("INSERT INTO users(name,email,password_hash,role) VALUES (?,?,?,'admin')", ("Demo Administrator", email, hash_password(password)))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    return f"pbkdf2_sha256$310000${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, rounds, salt, expected = stored.split("$")
        if scheme != "pbkdf2_sha256": return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


def money(value: int): return f"${value / 100:,.2f}"
templates.env.filters["money"] = money


def current_user(request: Request):
    tok = request.cookies.get("shop_session")
    if not tok: return None
    try:
        data = signer.loads(tok, max_age=60 * 60 * 12)
    except (BadSignature, SignatureExpired):
        return None
    with connect() as db:
        u = db.execute("SELECT id,name,email,role FROM users WHERE id=?", (data.get("uid"),)).fetchone()
    return dict(u) if u else None


def get_csrf(request: Request):
    tok = request.cookies.get("shop_session")
    if tok:
        try:
            data = signer.loads(tok, max_age=60 * 60 * 12)
            if data.get("csrf"): return data["csrf"]
        except (BadSignature, SignatureExpired): pass
    csrf_cookie = request.cookies.get("shop_guest_csrf")
    if csrf_cookie:
        try: return signer.loads(csrf_cookie, max_age=60 * 60 * 12)["csrf"]
        except (BadSignature, SignatureExpired, KeyError): pass
    return secrets.token_urlsafe(32)


def csrf_valid(request: Request, token: str) -> bool:
    expected = get_csrf(request)
    return bool(token and hmac.compare_digest(token, expected))


def render(request: Request, page: str, **context):
    user = current_user(request)
    csrf = get_csrf(request)
    response = templates.TemplateResponse(request, page, {"user": user, "csrf": csrf, **context})
    if not request.cookies.get("shop_session") and not request.cookies.get("shop_guest_csrf"):
        response.set_cookie("shop_guest_csrf", signer.dumps({"csrf": csrf}), httponly=True, samesite="lax", max_age=43200)
    return response


def redirect(path: str, *, notice: str | None = None, error: str | None = None):
    if notice: path += ("&" if "?" in path else "?") + "notice=" + quote(notice)
    if error: path += ("&" if "?" in path else "?") + "error=" + quote(error)
    return RedirectResponse(path, status_code=303)


def fail(request: Request, message: str, status: int = 400):
    result = render(request, "message.html", title="Request not completed", message=message)
    result.status_code = status
    return result


def user_or_redirect(request: Request, role: Optional[str] = None):
    user = current_user(request)
    return user if user and (not role or user["role"] == role) else None


def csrf_or_fail(request: Request, csrf: str):
    if not csrf_valid(request, csrf): return fail(request, "Security token missing or expired. Reload the page and try again.", 403)
    return None


def valid_int(value: str, minimum: int = 0) -> int | None:
    try:
        num = int(value)
        return num if str(num) == str(value).strip() and num >= minimum else None
    except (ValueError, TypeError): return None


def price_to_cents(value: str) -> int | None:
    try:
        v = Decimal(value)
        if not v.is_finite() or v < 0 or v.as_tuple().exponent < -2: return None
        return int(v * 100)
    except (InvalidOperation, ValueError): return None


@app.get("/", response_class=HTMLResponse)
def home(request: Request, q: str = "", category: str = "", page: int = 1, notice: str = "", error: str = ""):
    page = max(1, min(page, 9999)); q = q.strip()[:80]
    args = []
    filters = ["p.is_active=1"]
    if q: filters.append("(p.name LIKE ? OR p.description LIKE ?)"); args += ["%" + q + "%", "%" + q + "%"]
    if category and category.isdecimal(): filters.append("p.category_id=?"); args.append(int(category))
    clause = " AND ".join(filters)
    with connect() as db:
        count = db.execute(f"SELECT COUNT(*) FROM products p WHERE {clause}", args).fetchone()[0]
        rows = db.execute(f"SELECT p.*, c.name AS category FROM products p JOIN categories c ON c.id=p.category_id WHERE {clause} ORDER BY p.id DESC LIMIT 12 OFFSET ?", [*args, (page-1)*12]).fetchall()
        cats = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return render(request, "home.html", products=[with_visual(r) for r in rows], categories=cats, q=q, category=category, page_no=page, pages=max(1, (count + 11)//12), count=count, notice=notice, error=error, hero_photos=DEMO_PHOTOS)


@app.get("/products/{product_id}")
def detail(request: Request, product_id: int):
    with connect() as db:
        p = db.execute("SELECT p.*, c.name AS category FROM products p JOIN categories c ON c.id=p.category_id WHERE p.id=? AND p.is_active=1", (product_id,)).fetchone()
    return render(request, "product.html", product=with_visual(p)) if p else fail(request, "Product not found.", 404)


@app.get("/register")
def register_page(request: Request): return render(request, "auth.html", mode="register", title="Create account")


@app.post("/register")
def register(request: Request, name: str = Form(""), email: str = Form(""), password: str = Form(""), csrf: str = Form("")):
    if bad := csrf_or_fail(request, csrf): return bad
    name, email = name.strip(), email.strip().lower()
    if not (2 <= len(name) <= 70 and 3 <= len(email) <= 130 and "@" in email and "." in email.split("@")[-1] and len(password) >= 8):
        return fail(request, "Provide a name (2–70 characters), valid email and password (at least 8 characters).")
    with connect() as db:
        try:
            db.execute("INSERT INTO users(name,email,password_hash,role) VALUES (?,?,?,'customer')", (name, email, hash_password(password)))
        except sqlite3.IntegrityError:
            return fail(request, "That email is already registered.")
    return redirect("/login", notice="Account created. Please sign in.")


@app.get("/login")
def login_page(request: Request, notice: str = ""): return render(request, "auth.html", mode="login", title="Welcome back", notice=notice)


@app.post("/login")
def login(request: Request, email: str = Form(""), password: str = Form(""), csrf: str = Form("")):
    if bad := csrf_or_fail(request, csrf): return bad
    with connect() as db:
        u = db.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    if not u or not verify_password(password, u["password_hash"]):
        return fail(request, "Email or password is incorrect.", 401)
    token = signer.dumps({"uid": u["id"], "csrf": secrets.token_urlsafe(32)})
    resp = redirect("/admin" if u["role"] == "admin" else "/", notice="Signed in successfully.")
    resp.set_cookie("shop_session", token, httponly=True, samesite="lax", secure=os.getenv("SHOP_HTTPS", "0") == "1", max_age=43200)
    resp.delete_cookie("shop_guest_csrf")
    return resp


@app.post("/logout")
def logout(request: Request, csrf: str = Form("")):
    if bad := csrf_or_fail(request, csrf): return bad
    resp = redirect("/", notice="You have signed out.")
    resp.delete_cookie("shop_session")
    resp.delete_cookie("shop_guest_csrf")
    return resp


def cart_rows(uid):
    with connect() as db:
        rows = db.execute("SELECT ci.id, ci.quantity, p.id AS product_id, p.name, p.price_cents, p.stock, p.is_active, p.image_url FROM cart_items ci JOIN products p ON p.id=ci.product_id WHERE ci.user_id=? ORDER BY ci.id", (uid,)).fetchall()
    return rows


@app.get("/cart")
def cart(request: Request, notice: str = "", error: str = ""):
    u = user_or_redirect(request, "customer")
    if not u: return redirect("/login", error="Please sign in as a customer.")
    items = cart_rows(u["id"])
    return render(request, "cart.html", items=items, total=sum(r["price_cents"] * r["quantity"] for r in items), notice=notice, error=error)


@app.post("/cart/add/{product_id}")
def cart_add(request: Request, product_id: int, quantity: str = Form("1"), csrf: str = Form("")):
    if bad := csrf_or_fail(request, csrf): return bad
    u = user_or_redirect(request, "customer")
    if not u: return redirect("/login", error="Sign in before adding products.")
    qty = valid_int(quantity, 1)
    if qty is None: return fail(request, "Quantity must be a positive whole number.")
    with connect() as db:
        p = db.execute("SELECT stock,is_active FROM products WHERE id=?", (product_id,)).fetchone()
        if not p or not p["is_active"]: return fail(request, "Product is not available.", 404)
        old = db.execute("SELECT quantity FROM cart_items WHERE user_id=? AND product_id=?", (u["id"], product_id)).fetchone()
        new_qty = qty + (old[0] if old else 0)
        if new_qty > p["stock"]: return fail(request, "Not enough inventory for that quantity.")
        db.execute("INSERT INTO cart_items(user_id,product_id,quantity) VALUES (?,?,?) ON CONFLICT(user_id,product_id) DO UPDATE SET quantity=excluded.quantity", (u["id"], product_id, new_qty))
    return redirect("/cart", notice="Added to your cart.")


@app.post("/cart/update/{product_id}")
def cart_update(request: Request, product_id: int, quantity: str = Form("1"), csrf: str = Form("")):
    if bad := csrf_or_fail(request, csrf): return bad
    u = user_or_redirect(request, "customer")
    if not u: return redirect("/login")
    qty = valid_int(quantity, 0)
    if qty is None: return fail(request, "Quantity cannot be negative.")
    with connect() as db:
        if qty == 0:
            db.execute("DELETE FROM cart_items WHERE user_id=? AND product_id=?", (u["id"], product_id))
        else:
            p = db.execute("SELECT stock,is_active FROM products WHERE id=?", (product_id,)).fetchone()
            if not p or not p["is_active"] or qty > p["stock"]: return fail(request, "Insufficient stock or product no longer available.")
            db.execute("UPDATE cart_items SET quantity=? WHERE user_id=? AND product_id=?", (qty, u["id"], product_id))
    return redirect("/cart", notice="Cart updated.")


@app.post("/api/cart/quantity/{product_id}")
def cart_quantity_ajax(request: Request, product_id: int, quantity: str = Form(""), csrf: str = Form("")):
    if not csrf_valid(request, csrf):
        return JSONResponse({"error": "Session expired. Refresh the page."}, status_code=403)
    u = current_user(request)
    if not u or u["role"] != "customer":
        return JSONResponse({"error": "Please sign in again."}, status_code=401)
    qty = valid_int(quantity, 0)
    if qty is None:
        return JSONResponse({"error": "Enter a valid quantity."}, status_code=422)
    with connect() as db:
        p = db.execute("SELECT stock,is_active FROM products WHERE id=?", (product_id,)).fetchone()
        if not p or not p["is_active"] or qty > p["stock"]:
            return JSONResponse({"error": "Quantity exceeds available stock."}, status_code=409)
        if qty == 0:
            db.execute("DELETE FROM cart_items WHERE user_id=? AND product_id=?", (u["id"], product_id))
        else:
            existing = db.execute("SELECT 1 FROM cart_items WHERE user_id=? AND product_id=?", (u["id"], product_id)).fetchone()
            if not existing:
                return JSONResponse({"error": "Item is no longer in your cart."}, status_code=404)
            db.execute("UPDATE cart_items SET quantity=? WHERE user_id=? AND product_id=?", (qty, u["id"], product_id))
    return {"ok": True, "quantity": qty}


@app.get("/checkout")
def checkout_page(request: Request):
    u = user_or_redirect(request, "customer")
    if not u: return redirect("/login")
    items = cart_rows(u["id"])
    if not items: return redirect("/cart", error="Cart is empty.")
    return render(request, "checkout.html", items=items, total=sum(r["price_cents"]*r["quantity"] for r in items))


@app.post("/checkout")
def checkout(request: Request, recipient: str = Form(""), phone: str = Form(""), address: str = Form(""), csrf: str = Form("")):
    if bad := csrf_or_fail(request, csrf): return bad
    u = user_or_redirect(request, "customer")
    if not u: return redirect("/login")
    recipient, phone, address = recipient.strip(), phone.strip(), address.strip()
    if not (2 <= len(recipient) <= 100 and 5 <= len(phone) <= 30 and 8 <= len(address) <= 400):
        return fail(request, "Please fill in recipient name, phone and delivery address.")
    with connect() as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            items = db.execute("SELECT ci.product_id,ci.quantity,p.price_cents,p.stock,p.is_active FROM cart_items ci JOIN products p ON p.id=ci.product_id WHERE ci.user_id=?", (u["id"],)).fetchall()
            if not items: raise ValueError("Your cart is empty.")
            for item in items:
                if not item["is_active"] or item["quantity"] > item["stock"]:
                    raise ValueError("A product in your cart is unavailable or has insufficient stock. Please update your cart.")
            total = sum(item["quantity"] * item["price_cents"] for item in items)
            oid = db.execute("INSERT INTO orders(user_id,recipient,phone,address,total_cents,status) VALUES (?,?,?,?,?,'Pending')", (u["id"], recipient, phone, address, total)).lastrowid
            for it in items:
                changed = db.execute("UPDATE products SET stock=stock-? WHERE id=? AND stock>=?", (it["quantity"], it["product_id"], it["quantity"]))
                if changed.rowcount != 1: raise ValueError("Not enough stock to complete checkout.")
                db.execute("INSERT INTO order_items(order_id,product_id,quantity,unit_price_cents) VALUES (?,?,?,?)", (oid, it["product_id"], it["quantity"], it["price_cents"]))
            db.execute("DELETE FROM cart_items WHERE user_id=?", (u["id"],))
            db.execute("COMMIT")
        except (sqlite3.Error, ValueError) as exc:
            db.execute("ROLLBACK")
            return fail(request, str(exc) if isinstance(exc, ValueError) else "Could not place order. Try again.", 400)
    return redirect(f"/orders/{oid}", notice="Order placed. Payment is simulated (Cash on Delivery).")


@app.get("/orders")
def orders(request: Request):
    u = user_or_redirect(request, "customer")
    if not u: return redirect("/login")
    with connect() as db:
        data = db.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (u["id"],)).fetchall()
    return render(request, "orders.html", orders=data)


@app.get("/orders/{oid}")
def order_detail(request: Request, oid: int, notice: str = ""):
    u = user_or_redirect(request)
    if not u: return redirect("/login")
    with connect() as db:
        o = db.execute("SELECT o.*,u.name AS customer FROM orders o JOIN users u ON u.id=o.user_id WHERE o.id=?", (oid,)).fetchone()
        if not o or (u["role"] != "admin" and o["user_id"] != u["id"]):
            return fail(request, "Order not found or access denied.", 404)
        items = db.execute("SELECT oi.*,p.name FROM order_items oi JOIN products p ON p.id=oi.product_id WHERE oi.order_id=?", (oid,)).fetchall()
    return render(request, "order_detail.html", order=o, items=items, notice=notice)


@app.get("/admin")
def admin(request: Request, notice: str = "", error: str = ""):
    u = user_or_redirect(request, "admin")
    if not u: return fail(request, "Administrator access required.", 403)
    with connect() as db:
        totals = {k: db.execute(q).fetchone()[0] for k, q in {
          "products": "SELECT COUNT(*) FROM products", "orders": "SELECT COUNT(*) FROM orders", "pending": "SELECT COUNT(*) FROM orders WHERE status='Pending'", "customers": "SELECT COUNT(*) FROM users WHERE role='customer'"}.items()}
    return render(request, "admin.html", totals=totals, notice=notice, error=error)


@app.get("/admin/products")
def admin_products(request: Request, notice: str = "", error: str = ""):
    if not user_or_redirect(request, "admin"): return fail(request, "Administrator access required.", 403)
    with connect() as db:
        products = db.execute("SELECT p.*,c.name AS category FROM products p JOIN categories c ON c.id=p.category_id ORDER BY p.id DESC").fetchall()
        categories = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return render(request, "admin_products.html", products=products, categories=categories, notice=notice, error=error)


@app.post("/admin/categories")
def admin_category_add(request: Request, name: str = Form(""), csrf: str = Form("")):
    if bad := csrf_or_fail(request, csrf): return bad
    if not user_or_redirect(request, "admin"): return fail(request, "Administrator access required.", 403)
    name = name.strip()
    if not 2 <= len(name) <= 80: return fail(request, "Category name must be 2–80 characters.")
    with connect() as db:
        try: db.execute("INSERT INTO categories(name) VALUES (?)", (name,))
        except sqlite3.IntegrityError: return fail(request, "This category already exists.")
    return redirect("/admin/products", notice="Category added.")


@app.post("/admin/categories/{cid}/rename")
def admin_category_rename(request: Request, cid: int, name: str = Form(""), csrf: str = Form("")):
    if bad := csrf_or_fail(request, csrf): return bad
    if not user_or_redirect(request, "admin"): return fail(request, "Administrator access required.", 403)
    name = name.strip()
    if not 2 <= len(name) <= 80: return fail(request, "Category name must be 2–80 characters.")
    with connect() as db:
        try: db.execute("UPDATE categories SET name=? WHERE id=?", (name, cid))
        except sqlite3.IntegrityError: return fail(request, "This category already exists.")
    return redirect("/admin/products", notice="Category renamed.")


@app.get("/admin/products/new")
def admin_product_new(request: Request):
    if not user_or_redirect(request, "admin"): return fail(request, "Administrator access required.", 403)
    with connect() as db: categories = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return render(request, "admin_product_form.html", product=None, categories=categories, title="Add product")


@app.get("/admin/products/{pid}/edit")
def admin_product_edit(request: Request, pid: int):
    if not user_or_redirect(request, "admin"): return fail(request, "Administrator access required.", 403)
    with connect() as db:
        p = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        cats = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return render(request, "admin_product_form.html", product=p, categories=cats, title="Edit product") if p else fail(request, "Product not found.", 404)


@app.post("/admin/products/save")
def admin_product_save(request: Request, pid: str = Form(""), name: str = Form(""), description: str = Form(""), category_id: str = Form(""), price: str = Form(""), stock: str = Form(""), image_url: str = Form(""), is_active: str = Form("0"), csrf: str = Form("")):
    if bad := csrf_or_fail(request, csrf): return bad
    if not user_or_redirect(request, "admin"): return fail(request, "Administrator access required.", 403)
    price_cents = price_to_cents(price)
    stock_val = valid_int(stock, 0)
    catid = valid_int(category_id, 1)
    pid_val = valid_int(pid, 1) if pid else None
    name, description = name.strip(), description.strip()
    if not (2 <= len(name) <= 130 and len(description) <= 1500 and price_cents is not None and stock_val is not None and catid is not None and valid_product_image(image_url.strip())):
        return fail(request, "Invalid product details or image URL. Use a short emoji or HTTPS photo URL (max 500 characters); price must have at most 2 decimals.")
    with connect() as db:
        if not db.execute("SELECT 1 FROM categories WHERE id=?", (catid,)).fetchone(): return fail(request, "Category does not exist.")
        if pid_val:
            if not db.execute("SELECT 1 FROM products WHERE id=?", (pid_val,)).fetchone(): return fail(request, "Product not found.", 404)
            db.execute("UPDATE products SET category_id=?,name=?,description=?,price_cents=?,stock=?,image_url=?,is_active=? WHERE id=?", (catid,name,description,price_cents,stock_val,image_url,1 if is_active == "1" else 0,pid_val))
        else:
            db.execute("INSERT INTO products(category_id,name,description,price_cents,stock,image_url,is_active) VALUES (?,?,?,?,?,?,?)", (catid,name,description,price_cents,stock_val,image_url,1 if is_active == "1" else 0))
    return redirect("/admin/products", notice="Product saved.")


@app.get("/admin/orders")
def admin_orders(request: Request, notice: str = "", error: str = ""):
    if not user_or_redirect(request, "admin"): return fail(request, "Administrator access required.", 403)
    with connect() as db:
        data = db.execute("SELECT o.*, u.name AS customer FROM orders o JOIN users u ON u.id=o.user_id ORDER BY o.id DESC").fetchall()
    return render(request, "admin_orders.html", orders=data, notice=notice, error=error)


@app.post("/admin/orders/{oid}/status")
def admin_order_status(request: Request, oid: int, status: str = Form(""), csrf: str = Form("")):
    if bad := csrf_or_fail(request, csrf): return bad
    if not user_or_redirect(request, "admin"): return fail(request, "Administrator access required.", 403)
    with connect() as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            order = db.execute("SELECT status FROM orders WHERE id=?", (oid,)).fetchone()
            if not order: raise ValueError("Order not found.")
            if status not in STATUS_NEXT[order["status"]]: raise ValueError("Invalid status transition.")
            if status == "Cancelled":
                for item in db.execute("SELECT product_id, quantity FROM order_items WHERE order_id=?", (oid,)).fetchall():
                    db.execute("UPDATE products SET stock=stock+? WHERE id=?", (item["quantity"], item["product_id"]))
            db.execute("UPDATE orders SET status=? WHERE id=?", (status, oid))
            db.execute("COMMIT")
        except (sqlite3.Error, ValueError) as exc:
            db.execute("ROLLBACK")
            return fail(request, str(exc) if isinstance(exc, ValueError) else "Could not update order status.")
    return redirect(f"/orders/{oid}", notice=f"Order moved to {status}.")



# JSON REST API, version 1. Uses the same business database and session/role rules
# as the server-rendered shopping interface. Mutations additionally require the
# signed-in user's anti-CSRF token in X-CSRF-Token.

class APIProductInput(BaseModel):
    name: str = Field(min_length=2, max_length=130)
    category_id: int = Field(ge=1)
    description: str = Field(default="", max_length=1500)
    price_cents: int = Field(ge=0)
    stock: int = Field(ge=0)
    image_url: str = Field(default="", max_length=500)
    is_active: bool = True


class APIOrderStatusInput(BaseModel):
    status: str


def api_user(request: Request, role: str | None = None):
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    if role and user["role"] != role:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user


def api_check_csrf(request: Request, token: str):
    if not csrf_valid(request, token):
        raise HTTPException(status_code=403, detail="Missing or invalid X-CSRF-Token")


def api_product(db, product_id: int, *, allow_inactive: bool = False):
    where = "p.id=?" if allow_inactive else "p.id=? AND p.is_active=1"
    result = db.execute(
        f"SELECT p.*, c.name AS category FROM products p JOIN categories c ON c.id=p.category_id WHERE {where}",
        (product_id,),
    ).fetchone()
    return dict(result) if result else None


@app.get("/api/v1/categories", tags=["JSON API - Catalog"])
def api_categories():
    with connect() as db:
        return {"categories": [dict(r) for r in db.execute("SELECT id,name FROM categories ORDER BY name")]}


@app.get("/api/v1/products", tags=["JSON API - Catalog"])
def api_products(
    q: str = Query(default="", max_length=80),
    category_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
):
    filters = ["p.is_active=1"]
    args = []
    if q.strip():
        filters.append("(p.name LIKE ? OR p.description LIKE ?)")
        args += [f"%{q.strip()}%", f"%{q.strip()}%"]
    if category_id is not None:
        filters.append("p.category_id=?")
        args.append(category_id)
    where = " AND ".join(filters)
    with connect() as db:
        count = db.execute(f"SELECT COUNT(*) FROM products p WHERE {where}", args).fetchone()[0]
        rows = db.execute(
            f"SELECT p.*,c.name AS category FROM products p JOIN categories c ON c.id=p.category_id WHERE {where} ORDER BY p.id DESC LIMIT ? OFFSET ?",
            [*args, page_size, (page - 1) * page_size],
        ).fetchall()
    return {"items": [dict(r) for r in rows], "total": count, "page": page, "page_size": page_size}


@app.get("/api/v1/products/{product_id}", tags=["JSON API - Catalog"])
def api_product_detail(product_id: int):
    with connect() as db:
        result = api_product(db, product_id)
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@app.get("/api/v1/me", tags=["JSON API - Account"])
def api_profile(request: Request):
    return {"user": api_user(request)}


@app.get("/api/v1/csrf", tags=["JSON API - Account"])
def api_csrf(request: Request):
    api_user(request)
    return {"csrf_token": get_csrf(request), "header": "X-CSRF-Token"}


@app.get("/api/v1/orders", tags=["JSON API - Orders"])
def api_my_orders(request: Request):
    user = api_user(request, "customer")
    with connect() as db:
        rows = db.execute("SELECT id,total_cents,status,created_at FROM orders WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
    return {"orders": [dict(r) for r in rows]}


@app.get("/api/v1/orders/{order_id}", tags=["JSON API - Orders"])
def api_my_order_detail(request: Request, order_id: int):
    user = api_user(request)
    with connect() as db:
        row = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if not row or (user["role"] != "admin" and row["user_id"] != user["id"]):
            raise HTTPException(status_code=404, detail="Order not found")
        items = db.execute(
            "SELECT oi.id,oi.product_id,p.name,oi.quantity,oi.unit_price_cents FROM order_items oi JOIN products p ON p.id=oi.product_id WHERE oi.order_id=?",
            (order_id,),
        ).fetchall()
    return {"order": dict(row), "items": [dict(r) for r in items]}


@app.get("/api/v1/admin/dashboard", tags=["JSON API - Admin"])
def api_admin_dashboard(request: Request):
    api_user(request, "admin")
    with connect() as db:
        return {"products": db.execute("SELECT COUNT(*) FROM products").fetchone()[0],
                "orders": db.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
                "customers": db.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0]}


@app.get("/api/v1/admin/orders", tags=["JSON API - Admin"])
def api_admin_order_list(request: Request):
    api_user(request, "admin")
    with connect() as db:
        rows = db.execute("SELECT o.id,o.user_id,u.name AS customer,o.total_cents,o.status,o.created_at FROM orders o JOIN users u ON u.id=o.user_id ORDER BY o.id DESC").fetchall()
    return {"orders": [dict(r) for r in rows]}


@app.post("/api/v1/admin/products", status_code=201, tags=["JSON API - Admin"])
def api_create_product(request: Request, product: APIProductInput, x_csrf_token: str = Header(default="")):
    api_user(request, "admin")
    api_check_csrf(request, x_csrf_token)
    name = product.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Product name is too short")
    if not valid_product_image(product.image_url):
        raise HTTPException(status_code=422, detail="Use an HTTPS image URL or a short emoji")
    with connect() as db:
        if not db.execute("SELECT 1 FROM categories WHERE id=?", (product.category_id,)).fetchone():
            raise HTTPException(status_code=422, detail="Unknown category")
        cursor = db.execute(
            "INSERT INTO products(category_id,name,description,price_cents,stock,image_url,is_active) VALUES (?,?,?,?,?,?,?)",
            (product.category_id,name,product.description,product.price_cents,product.stock,product.image_url,int(product.is_active)),
        )
        created = api_product(db, cursor.lastrowid, allow_inactive=True)
    return {"product": created}


@app.put("/api/v1/admin/products/{product_id}", tags=["JSON API - Admin"])
def api_update_product(request: Request, product_id: int, product: APIProductInput, x_csrf_token: str = Header(default="")):
    api_user(request, "admin")
    api_check_csrf(request, x_csrf_token)
    name = product.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Product name is too short")
    if not valid_product_image(product.image_url):
        raise HTTPException(status_code=422, detail="Use an HTTPS image URL or a short emoji")
    with connect() as db:
        if not api_product(db, product_id, allow_inactive=True):
            raise HTTPException(status_code=404, detail="Product not found")
        if not db.execute("SELECT 1 FROM categories WHERE id=?", (product.category_id,)).fetchone():
            raise HTTPException(status_code=422, detail="Unknown category")
        db.execute(
            "UPDATE products SET category_id=?,name=?,description=?,price_cents=?,stock=?,image_url=?,is_active=? WHERE id=?",
            (product.category_id,name,product.description,product.price_cents,product.stock,product.image_url,int(product.is_active),product_id),
        )
        updated = api_product(db, product_id, allow_inactive=True)
    return {"product": updated}


@app.patch("/api/v1/admin/orders/{order_id}/status", tags=["JSON API - Admin"])
def api_change_order_status(request: Request, order_id: int, payload: APIOrderStatusInput, x_csrf_token: str = Header(default="")):
    api_user(request, "admin")
    api_check_csrf(request, x_csrf_token)
    with connect() as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            order = db.execute("SELECT status FROM orders WHERE id=?", (order_id,)).fetchone()
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
            if payload.status not in STATUS_NEXT[order["status"]]:
                raise HTTPException(status_code=409, detail="Invalid status transition")
            if payload.status == "Cancelled":
                for item in db.execute("SELECT product_id,quantity FROM order_items WHERE order_id=?", (order_id,)).fetchall():
                    db.execute("UPDATE products SET stock=stock+? WHERE id=?", (item["quantity"],item["product_id"]))
            db.execute("UPDATE orders SET status=? WHERE id=?", (payload.status,order_id))
            db.execute("COMMIT")
        except HTTPException:
            db.execute("ROLLBACK")
            raise
        except sqlite3.Error:
            db.execute("ROLLBACK")
            raise HTTPException(status_code=500, detail="Order update failed")
    return {"order_id": order_id, "status": payload.status}

@app.get("/health")
def health():
    with connect() as db: db.execute("SELECT 1").fetchone()
    return {"status": "ok", "system": "Online Shopping System", "storage": "SQLite"}


if __name__ == "__main__":
    if "--init" in sys.argv:
        init_db(seed=True)
        print("Database initialized. Local demo admin: admin@demo.shop / DemoAdmin123! (unless environment overrides).")
    else:
        import uvicorn
        print("Open http://127.0.0.1:8000. Local demo admin: admin@demo.shop / DemoAdmin123! (unless environment overrides).")
        uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8000")))
