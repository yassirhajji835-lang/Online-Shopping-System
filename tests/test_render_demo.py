"""Render demo safety and disposable database checks."""
import pytest
import app as shop


def test_render_demo_requires_custom_credentials(monkeypatch):
    monkeypatch.setenv("SHOP_RENDER_DEMO", "1")
    monkeypatch.setenv("SHOP_SECRET", "x" * 40)
    monkeypatch.setenv("SHOP_HTTPS", "1")
    monkeypatch.setenv("SHOP_ADMIN_EMAIL", "admin@demo.shop")
    monkeypatch.setenv("SHOP_ADMIN_PASSWORD", "DemoAdmin123!")
    with pytest.raises(RuntimeError, match="SHOP_ADMIN_EMAIL"):
        shop.validate_render_demo_settings()
    monkeypatch.setenv("SHOP_ADMIN_EMAIL", "class-demo@example.org")
    with pytest.raises(RuntimeError, match="SHOP_ADMIN_PASSWORD"):
        shop.validate_render_demo_settings()
    monkeypatch.setenv("SHOP_ADMIN_PASSWORD", "long-unique-test-password-123")
    monkeypatch.delenv("SHOP_SECRET")
    with pytest.raises(RuntimeError, match="SHOP_SECRET"):
        shop.validate_render_demo_settings()
    monkeypatch.setenv("SHOP_SECRET", "x" * 40)
    monkeypatch.setenv("SHOP_HTTPS", "0")
    with pytest.raises(RuntimeError, match="SHOP_HTTPS"):
        shop.validate_render_demo_settings()
    monkeypatch.setenv("SHOP_HTTPS", "1")
    shop.validate_render_demo_settings()


def test_local_development_does_not_require_render_settings(monkeypatch):
    monkeypatch.delenv("SHOP_RENDER_DEMO", raising=False)
    monkeypatch.delenv("SHOP_SECRET", raising=False)
    monkeypatch.delenv("SHOP_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("SHOP_ADMIN_PASSWORD", raising=False)
    shop.validate_render_demo_settings()


def test_temporary_database_reseeds_after_file_loss(monkeypatch, tmp_path):
    monkeypatch.setattr(shop, "DB_PATH", tmp_path / "shop.sqlite3")
    monkeypatch.setenv("SHOP_ADMIN_EMAIL", "class-demo@example.org")
    monkeypatch.setenv("SHOP_ADMIN_PASSWORD", "long-unique-test-password-123")
    shop.init_db(seed=True)
    with shop.connect() as db:
        db.execute("UPDATE products SET stock=1 WHERE name='Wireless Mouse'")
        assert db.execute("SELECT stock FROM products WHERE name='Wireless Mouse'").fetchone()[0] == 1
    shop.DB_PATH.unlink()  # Models Render losing its temporary SQLite file.
    shop.init_db(seed=True)
    with shop.connect() as db:
        assert db.execute("SELECT stock FROM products WHERE name='Wireless Mouse'").fetchone()[0] == 18
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
