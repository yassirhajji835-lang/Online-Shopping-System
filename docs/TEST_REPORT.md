# Implementation & Test Report (Internal Draft)

**Application:** Online Shopping System
**Test environment:** Python 3.13; FastAPI 0.128.2; SQLite; pytest 8+; local FastAPI TestClient.
**Execution:** `python -m pytest -q`
**Result:** **11 automated test cases passed** during package preparation. Tests use an isolated temporary database.

| Test ID | Test scenario | Result |
|---|---|---|
| T01 | Health endpoint, product browsing, keyword filtering, missing product | Pass |
| T02 | Registration, duplicate email, invalid password, customer vs admin permissions | Pass |
| T03 | CSRF rejection for forged mutation | Pass |
| T04 | Cart, checkout, stock deduction, order price snapshot, order isolation, admin progress | Pass |
| T05 | Product creation and order cancellation restores stock only once | Pass |
| T06 | Stock depletion after cart selection blocks checkout; no partial order | Pass |
| T07 | Negative product price is rejected and not saved | Pass |
| T08 | JSON product/category endpoints, pagination, missing records, OpenAPI schema | Pass |
| T09 | JSON authentication and customer/admin access control | Pass |
| T10 | Admin product creation/editing via JSON; invalid CSRF and input rejected | Pass |
| T11 | JSON order isolation, valid transitions, single inventory restoration | Pass |

## Manual test checklist to run on your own laptop

- [ ] Open home page in desktop browser and verify six sample products.
- [ ] Resize browser to mobile width and confirm that product cards and navigation adapt.
- [ ] Register a user, log in, add item, change quantity, place demo order.
- [ ] Verify order history shows the order and correct total.
- [ ] Log in as administrator and update a product, stock, and order status.
- [ ] Confirm customer cannot reach `/admin` and another customer's order detail.
- [ ] Restart the server and confirm committed orders remain in the database.
- [ ] Check any teacher-specific performance tests against the acceptance targets in the Week 1 SRS.

This report does not claim to be a teacher-issued Week 2 or Week 3 lab report. Replace internal draft with the exact instructions when the teacher releases them.
