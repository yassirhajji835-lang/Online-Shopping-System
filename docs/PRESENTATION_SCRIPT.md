# Final Group Presentation — Short Speaking Guide (Draft)

**Slide 1 — Title (Speaker 1, 15–20 seconds):** “Our project is an Online Shopping System, designed for the Introduction to Software Design course. The goal was to build a browser-based shopping application with two user roles and persistent data.”

**Slide 2 — Requirements (Speaker 1, 30–40 seconds):** “The teacher required a frontend and backend, a relational database with at least four tables, two roles, and a browser/server design. We implemented six tables and two separate roles: customer and administrator.”

**Slide 3 — Architecture (Speaker 3, 35–45 seconds):** “The user interacts with an HTML/CSS storefront. FastAPI validates input and manages role-based access. All products, cart data, and orders are saved in SQLite.”

**Slide 4 — Features (Speaker 2, 45–60 seconds):** “Customers can register, sign in, search the catalog, view products, edit the cart, complete a simulated checkout, and monitor their orders. Administrators can manage categories, products, stock, and order status.”

**Slide 5 — Database and checkout (Speaker 3, 45–60 seconds):** “Our six tables are users, categories, products, cart items, orders, and order items. Checkout uses one database transaction to avoid partially created orders, and it saves the item price at time of purchase.”

**Slide 6 — Live demo (All members, 2–3 minutes):** “We will register, add a product, create an order, then switch to administrator and update its status.”

**Slide 7 — Validation (Speaker 3, 30 seconds):** “We used automated tests covering authentication, authorization, stock handling, order integrity, cancellation, and invalid input. There were seven passing tests at the time this draft was prepared.”

**Slide 8 — Closing (Speaker 1, 15–20 seconds):** “We met the core design constraints and demonstrated the software engineering process from requirements to implementation and testing. Thank you; we welcome questions.”

**Do before presentation:** put all three passport names on slide 1; replace screenshots with your final interface; rehearse a demo with sample orders; bring printed official reports. The narrative is a draft, not proof of group presentation or official report completion.
