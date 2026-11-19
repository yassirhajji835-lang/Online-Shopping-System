# JSON REST API Reference — v1

The Online Shopping System includes server-rendered pages **and** a versioned JSON API using FastAPI.

- Base URL: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/api-docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`
- The API shares the existing SQLite database and the same customer/admin accounts.
- Public read requests do not require login. Private endpoints use the website's signed session cookie.
- JSON write operations require an **administrator login** and a CSRF token sent via `X-CSRF-Token`.
- **No external payment, logistics, or banking API is integrated**; checkout remains a simulated cash-on-delivery flow.

| HTTP method | Endpoint | Purpose | Permission |
|---|---|---|---|
| GET | `/health` | Check server/database connectivity | Public |
| GET | `/api/v1/categories` | List product categories | Public |
| GET | `/api/v1/products` | Paginated product list; query filters `q`, `category_id`, `page`, `page_size` | Public |
| GET | `/api/v1/products/{id}` | Retrieve a visible product | Public |
| GET | `/api/v1/me` | Current user's details | Signed-in user |
| GET | `/api/v1/csrf` | Retrieve CSRF header token | Signed-in user |
| GET | `/api/v1/orders` | List own orders | Customer |
| GET | `/api/v1/orders/{id}` | Order and line items; owner or admin | Owner / admin |
| GET | `/api/v1/admin/dashboard` | Product/order/customer counts | Admin |
| GET | `/api/v1/admin/orders` | All orders | Admin |
| POST | `/api/v1/admin/products` | Create a new product | Admin + CSRF |
| PUT | `/api/v1/admin/products/{id}` | Update a product's full details | Admin + CSRF |
| PATCH | `/api/v1/admin/orders/{id}/status` | Move an order to a legal next status | Admin + CSRF |

## Demo instructions

1. Install the dependencies and start `python app.py`.
2. Open `/api-docs`; use **Try it out** on `GET /api/v1/products` to see JSON data.
3. Sign into the website as a demonstration administrator (`admin@demo.shop` / `DemoAdmin123!`, *local demo only*).
4. Call `GET /api/v1/csrf` from the same browser session, copy its `csrf_token`.
5. For mutating endpoints, supply the header `X-CSRF-Token` with that token and use the documented JSON request bodies.
6. Run `python -m pytest -q` for integration and API security tests.

**Example public request:**

```bash
curl "http://127.0.0.1:8000/api/v1/products?q=hoodie&page_size=5"
```

**Example admin product body (POST or PUT):**

```json
{
  "name": "Study Notebook",
  "category_id": 3,
  "description": "A notebook for daily study",
  "price_cents": 1250,
  "stock": 15,
  "image_url": "📓",
  "is_active": true
}
```

Use a **real category ID** from `GET /api/v1/categories` instead of assuming that category 3 exists in every database. All monetary values use integer cents. A signed-in session from the browser must accompany protected requests; the browser's API documentation page may not propagate session cookies on every browser configuration.

## Security model and boundaries

- Prepared SQL parameters and schema constraints protect database writes.
- API endpoints enforce customer/admin privileges on the server, not only in the UI.
- Only order owners or admins can request order details.
- Product write endpoints require a valid anti-CSRF token in addition to administrator authentication.
- Order status transitions are validated and cancellation restores stock at most once.
- This is a **classroom/local development project**, not a production-ready public e-commerce API. Additional work would be necessary for production hardening, real payments, and operational deployment.
