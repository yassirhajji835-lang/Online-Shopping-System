# PostgreSQL deployment

Set DATABASE_URL to the internal connection URL from the existing Render PostgreSQL database. Never commit this secret. The app initializes six relational tables and demo seed data at startup. Existing SQLite data is not copied automatically. Without DATABASE_URL, local development uses SQLite. The health endpoint reports the active database engine. Verify registration, login, cart, checkout, admin users and orders, and persistence after redeployment before submission. The free database expires December 25, 2026. Export a backup before expiry.
