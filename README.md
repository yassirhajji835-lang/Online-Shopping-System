> **Free Render demo:** The repository includes a `render.yaml` Blueprint for a free web service with **temporary SQLite storage**. All online accounts, orders, cart contents and stock changes disappear after spin-down, restart or redeploy. Use fake test data only. See [Render deployment guide](docs/RENDER_FREE_DEMO.md).

> **2026 visual upgrade:** New premium storefront, demo photos, CSS 3D/parallax, product image gallery, responsive layout, and offline illustrations. See [README_VISUAL_UPGRADE.md](README_VISUAL_UPGRADE.md).

# Online Shopping System — Software Design / Project Training

A working browser/server (B/S) classroom demo with a Python **FastAPI** backend (HTML routes + JSON REST API v1), HTML/CSS/Jinja2 frontend, SQLite relational database (6 tables), and two roles: **customer** and **administrator**. Built to match the Week 1 software requirements specification.

## Quick start (Windows/macOS/Linux)

1. Install Python 3.10+ and open a terminal in this folder.
2. Optional: `python -m venv .venv`, then activate the environment.
3. Install dependencies: `python -m pip install -r requirements.txt`
4. Start server: `python app.py`
5. Open **http://127.0.0.1:8000** in a browser.

On the first launch, the database, categories, sample products, and a local-demo administrator account are automatically created.

**Local demo administrator account:** `admin@demo.shop` / `DemoAdmin123!`

**Customer account:** Click **Register** and create your own account.

**Important:** The included admin credentials are for a classroom demo on your computer only. Set `SHOP_ADMIN_EMAIL` and `SHOP_ADMIN_PASSWORD` before *first* run if you need custom credentials. Never deploy this demo publicly with default credentials or without additional hardening. No payment gateway is connected: checkout is Cash on Delivery simulation.

## Requirements traceability

| Week 1 feature | Implemented location |
| --- | --- |
| F01/F02 Register, login, logout | `/register`, `/login`, `/logout` |
| F03/F04/F05 Catalog, filter, details | `/`, `/products/{id}` |
| F06 Cart edit | `/cart`, `/cart/add/{id}`, `/cart/update/{id}` |
| F07 Checkout, atomic inventory reduction | `/checkout` |
| F08 Customer order history and details | `/orders`, `/orders/{id}` |
| F09 Admin categories | `/admin/categories`, `/admin/categories/{id}/rename` |
| F10/F11 Admin product management and stock | `/admin/products`, `/admin/products/save` |
| F12 Status transitions and cancellation | `/admin/orders`, `/admin/orders/{id}/status` |
| F13/F14 Server role checks and validation | all protected routes, SQLite CHECK / FK constraints |

Database tables: `users`, `categories`, `products`, `cart_items`, `orders`, `order_items`.

## Versioned JSON API (new)

The application includes API endpoints, **not only HTML forms**. For example:

- `GET /api/v1/categories` — categories in JSON
- `GET /api/v1/products?q=hoodie` — filtered products in JSON
- `GET /api/v1/orders` — the signed-in customer's orders
- `GET /api/v1/admin/dashboard` — admin-only JSON counts
- `POST /api/v1/admin/products` and `PUT /api/v1/admin/products/{id}` — admin writes protected by CSRF
- `PATCH /api/v1/admin/orders/{id}/status` — controlled order state updates

Open **http://127.0.0.1:8000/api-docs** for interactive OpenAPI documentation, or read `docs/API_REFERENCE.md` for parameters and authentication details. See `docs/DATABASE_SCHEMA.sql` for the exact six-table SQL schema.

## Live demonstration script (5–7 minutes)

1. Launch the server and show the catalog; search for `hoodie` and filter by category.
2. Register a new customer and log in.
3. Open a product; add 2 units to cart; adjust the quantity.
4. Checkout using fake contact/address data; show the new order and its initial Pending status.
5. Log out; sign in as demo admin; show dashboard, create/edit a product or its stock.
6. View orders and move Pending → Confirmed → Shipped → Delivered.
7. Log out and return as customer to verify the updated order status.
8. Open `/api-docs`, execute `GET /api/v1/products` to show the JSON REST API.
9. Explain the six related database tables and why order creation uses one transaction.

## Testing

`python -m pytest -q`

The tests create a separate temporary SQLite database; they never touch your normal demo database.

## Directory guide

- `app.py` — backend routes, validation, database schema, business logic.
- `templates/` — rendered frontend pages for customer and admin.
- `static/styles.css` — responsive design, desktop and mobile.
- `tests/` — automated integration tests.
- `docs/` — architecture, SQL schema, API reference, diagrams, schedule, and test evidence.
- `shop.sqlite3` — automatically created when you first start the app (intentionally excluded from ZIP).

## Operational notes

- Run only locally for coursework. Optional environment values: `SHOP_DB` (database path), `SHOP_SECRET` (signing key), `SHOP_ADMIN_EMAIL`, `SHOP_ADMIN_PASSWORD`, `SHOP_HTTPS=1` (when behind HTTPS), and `PORT`.
- Save/backup SQLite by stopping the server and copying `shop.sqlite3`.
- For a clean demonstration, stop the server and remove `shop.sqlite3`, then restart (this removes all demo accounts and orders).
- Product photos now use curated Unsplash demo URLs, with bundled offline SVG illustrations as fallbacks. Admins can enter HTTPS image URLs (up to 500 characters) or keep an emoji; image upload/storage is not implemented. See `docs/IMAGE_CREDITS.md` and `README_VISUAL_UPGRADE.md`.
- You must still complete any additional Week 2/Week 3 lab report instructions once supplied by the teacher, add the three real student names, print three required lab reports, and attend the December 11 presentation.