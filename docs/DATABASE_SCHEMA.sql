-- SQLite Online Shopping System database schema
-- Automatically initialized by app.py on first launch.
PRAGMA foreign_keys = ON;
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
