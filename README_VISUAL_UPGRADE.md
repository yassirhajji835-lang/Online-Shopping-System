# ONLINE SHOP — Visual Upgrade (2026)

This version preserves the existing FastAPI/SQLite customer, admin, cart, checkout, inventory, and order workflows. The visual layer adds an editorial homepage, demo product photography from Unsplash, interactive 3D-style parallax/tilt, a photo/illustration product gallery, mobile layout, and bundled SVG fallback illustrations.

## Start on Windows

1. Extract the ZIP file (do not run Python from inside the ZIP).
2. Open the extracted `Online_Shopping_System_Project` folder.
3. Double-click `START_WINDOWS.bat`, or run `python -m pip install -r requirements.txt` followed by `python app.py`.
4. Open **http://127.0.0.1:8000/**.
5. Admin login for a NEW, local demo database: **admin@demo.shop** / **DemoAdmin123!**. Change these before deploying; this is not a production-ready login.

## Keep your existing products, orders, and accounts

The **clean** ZIP deliberately excludes `shop.sqlite3` and `.session_secret` so it is safer to share for class. To keep your previous data, **stop the server**, copy the `shop.sqlite3` file from your ORIGINAL project folder into this upgraded folder, and then start the upgraded version. Do not overwrite your old project; keep a backup. The server will create a new `.session_secret`, so sign in again. Your original password hashes remain in your existing database.

The **with-data** ZIP (if provided) already includes the original database, which contains your customer accounts and simulated order details. **Do not share that ZIP publicly.**

## How product photographs work

- Built-in demo products are automatically matched to curated Unsplash image URLs. Images load directly in the browser and need internet access.
- When the browser is offline or a photo fails to load, a bundled SVG product illustration is shown. These are original local fallback graphics, not photographs.
- To set a custom product picture, sign in as administrator, go to **Products → Edit**, and paste a direct **HTTPS** image URL in **Product image URL**. You can leave the field empty to use the matching demo photo.
- The photo/illustration toggle on product pages is a gallery between a reference photo and a designed illustration, **not** multiple real camera angles or a 3D product model.
- Photos are illustrative placeholders only; they are not evidence of actual stock, brands, or product specifications. See `docs/IMAGE_CREDITS.md`.

## Design and performance

- `static/visual-upgrade.css`: responsive layout, typography, perspective, hover and lighting.
- `static/showroom.js`: lightweight pointer-driven parallax, product tilt, gallery switch, offline image fallbacks, and gentle reveal.
- `static/illustrations/`: 9 original SVG fallback images.
- No Three.js or heavy 3D libraries required. Honors reduced-motion preferences.
- All existing forms and stock calculations remain server-side; the new JavaScript changes only presentation.

## Verify

Run `python -m pytest -q` in the project folder. Test a new customer checkout, inventory deduction, and administrator edits in your browser before submission.

## Security / submission

This is a **classroom demonstration** with simulated Cash on Delivery only. It is not hardened for public deployment. Never commit or share `.session_secret`, `shop.sqlite3`, `.env`, or real customer data. Update the project presentation screenshots if your professor requires screenshots of the final interface.
