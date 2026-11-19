# Render free demo deployment — temporary SQLite database

> **Classroom demonstration only. Not a production shop.** No real payments or
> delivery integration are implemented. Use fictional names, addresses and
> phone numbers. Do not store real customer information.

## What this configuration does

The root `render.yaml` configures one **Free** Python web service. It installs
`requirements.txt`, starts `uvicorn app:app --host 0.0.0.0 --port $PORT`, and
checks `/health`. The existing FastAPI lifespan initializes a fresh SQLite
file and seeds sample categories, products and one administrator account.

The database is explicitly located at **`/tmp/shop.sqlite3`** by `SHOP_DB`.
It is **not** the SQLite file on your Windows computer and is **not** stored
in GitHub. No persistent disk or external database is provisioned.

## Deploy using a Render Blueprint (recommended)

1. Open https://dashboard.render.com/ and sign in.
2. Select **New > Blueprint** and connect GitHub if requested.
3. Select the private repository
   `yassirhajji835-lang/Online-Shopping-System`, branch `main`.
4. Render should detect `render.yaml` at the repository root. Review that
   the service has `plan: free` and **no database or disk**.
5. When prompted for `SHOP_ADMIN_EMAIL` and `SHOP_ADMIN_PASSWORD`, supply a
   **new email address and a unique password of at least 12 characters**.
   Do **not** use `admin@demo.shop` / `DemoAdmin123!`. Do not place the
   password in GitHub, screenshots, or chat. Store it in your password manager.
6. Render generates `SHOP_SECRET` automatically. Confirm `SHOP_HTTPS=1`.
7. Deploy the Blueprint. Wait for the service to report **Live**. Your URL
   will look like `https://<your-service-name>.onrender.com`; use the actual
   URL Render provides, not a guessed address.
8. Visit `/health` on your Render URL. Expected JSON includes
   `"status":"ok"` and `"storage":"SQLite"`. Then visit `/` and
   `/api-docs`. Log in with your **new** administrator credentials.
9. Register a fictional test customer, add a product to the cart, place a
   Cash-on-Delivery *simulation* order, and check inventory in the admin page.

The `SHOP_RENDER_DEMO=1` guard prevents startup if the custom administrator
credentials, signing secret, or HTTPS cookie setting are missing. If the
service fails to start, check the Render Logs and Environment tab. Do not
turn off this guard to work around missing credentials.

## Alternative: manual Web Service

If you create a **New > Web Service** rather than a Blueprint, configure:

| Setting | Value |
| --- | --- |
| Repository | `yassirhajji835-lang/Online-Shopping-System` |
| Branch | `main` |
| Language / runtime | Python |
| Instance type | Free |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app:app --host 0.0.0.0 --port $PORT` |
| Health check | `/health` |

Set environment variables yourself:

| Key | Value |
| --- | --- |
| `SHOP_RENDER_DEMO` | `1` |
| `SHOP_DB` | `/tmp/shop.sqlite3` |
| `SHOP_HTTPS` | `1` |
| `SHOP_SECRET` | A unique random string, at least 32 characters |
| `SHOP_ADMIN_EMAIL` | Your custom demo administrator email |
| `SHOP_ADMIN_PASSWORD` | Unique password, at least 12 characters |

Keep secret values in Render's Environment settings, never in GitHub.

## Data loss: read this before using the demo

Render's Free web services have **ephemeral filesystems** and spin down after
15 minutes without inbound traffic. A cold start can take about a minute.
When the service spins down, restarts, or redeploys, **all changes in
`/tmp/shop.sqlite3` are lost**, including:

- New customer accounts and their passwords
- New or edited products, categories, prices, and inventory
- Cart contents, orders, delivery addresses, and order statuses
- The custom test orders you placed in the online demo

On startup, the application **recreates** the SQLite database, seeds the
original sample products and administrator account from environment variables,
and starts with **no customer orders**. Changes may also disappear after
unexpected service restarts. Refreshing the page *without* a restart does not
normally reset the database. This is not a reliable data store.

Your original local `shop.sqlite3` remains on your computer and is unaffected.
To preserve data, move to a persistent PostgreSQL service or a paid Render
service with a persistent disk and migrate the database deliberately. A free
Render PostgreSQL database is not a permanent solution: current free databases
expire after 30 days. Do not upload local database files to GitHub.

## Troubleshooting

- **Build failed:** Inspect Render Logs. Check the selected repo, branch,
  Python runtime and build command.
- **Startup failed / missing settings:** Fill in both `SHOP_ADMIN_*` values,
  check `SHOP_SECRET` exists, and keep `SHOP_HTTPS=1`.
- **Slow first page:** Free services can sleep after 15 minutes of inactivity;
  allow roughly a minute for a cold start.
- **Admin login stopped working after reset:** Log in with the administrator
  email and password stored in the Render environment. Your old local demo
  credentials are intentionally not used.
- **Orders/products disappeared:** Expected after a free instance spin-down,
  restart or redeploy. The SQLite file is disposable.
- **Product photo missing:** Unsplash demo images need internet access;
  bundled SVG illustrations provide offline fallbacks.

## References

- https://render.com/docs/free
- https://render.com/docs/blueprint-spec
- https://render.com/docs/infrastructure-as-code
- https://render.com/docs/your-first-deploy
