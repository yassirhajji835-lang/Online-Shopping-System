# System Architecture and Database Design

## Architecture

```
Customer / Administrator
      |
      | browser GET / POST + HTML forms
      v
Jinja2 HTML/CSS frontend (responsive templates)
      |
      | FastAPI routes, CSRF checks, user session, role checks
      v
Python backend / business rules
      |
      | parameterized SQL and transaction-controlled writes
      v
SQLite database (six related tables)
```

### Core data relationships

```
users (1) -------- (N) orders (1) -------- (N) order_items
  |                                               |
  +-- (N) cart_items --------- (1) products ------+
                                   |
                             (N) products
                                   |
                              (1) categories
```

Explicit foreign keys:
- `products.category_id` → `categories.id`.
- `cart_items.user_id` → `users.id`; `cart_items.product_id` → `products.id`.
- `orders.user_id` → `users.id`.
- `order_items.order_id` → `orders.id`; `order_items.product_id` → `products.id`.

### Purchase algorithm

1. The customer signs in, adds available products to their cart, and supplies delivery details.
2. The backend acquires a SQLite write transaction with `BEGIN IMMEDIATE`.
3. Within the same transaction, it rechecks active product status and stock.
4. It saves an order, saves immutable unit prices on its order items, decrements stock, and clears the cart.
5. It commits all changes together or rolls them all back when any validation or database operation fails.

This prevents partially saved orders and ensures historical totals are preserved after catalog price changes.

### Security and validation

- PBKDF2-HMAC-SHA256 salted password hashes, not plaintext passwords.
- Signed, expiring HttpOnly session cookies; SameSite=Lax, optional Secure flag for HTTPS.
- Separate server-side authorization checks for customers and administrators.
- CSRF tokens checked for form mutations.
- Prepared SQL query parameters, escaped Jinja2 HTML output, SQLite CHECK/UNIQUE/FOREIGN KEY constraints.
- Administrative order state machine restricts transitions; cancelling an unshipped order restores inventory only once.

**Scope boundary:** This is an educational local demo. The fixed initial admin password must be changed before any public use. There is no real payment, courier, email API, production authentication audit, or cloud deployment.
