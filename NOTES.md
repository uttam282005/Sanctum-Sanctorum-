# Sanctum Sanctorum Bookstore — Project Notes

- **GitHub Repository**: [https://github.com/uttam282005/Sanctum-Sanctorum-](https://github.com/uttam282005/Sanctum-Sanctorum-) (Public)
- **Deployment URL**: Live deployment link (e.g. on Render / Vercel / Fly.io)
- **Seeded Demo Accounts**:
  - ID 1: Wong Li (`wong@example.com`, tier: `supreme`)
  - ID 2: Christine Palmer (`christine@example.com`, tier: `master`)
  - ID 3: Jonathan Pangborn (`jonathan@example.com`, tier: `adept`)
  - ID 4: Sara Lin (`sara@example.com`, tier: `apprentice`)

### Deployment Options Included in Repository:
1. **Render (Recommended — Free & No Credit Card Required)**:
   - Connect `https://github.com/uttam282005/Sanctum-Sanctorum-` on [render.com](https://render.com).
   - Render automatically detects `render.yaml` and `Dockerfile`.
   - Click **Deploy** to receive a public URL (e.g. `https://sanctum-sanctorum.onrender.com`).
2. **Vercel**:
   - `vercel.json` and `api/index.py` are configured for serverless Python deployment.
   - Import `uttam282005/Sanctum-Sanctorum-` in Vercel Dashboard to deploy.
3. **Docker**:
   - `docker build -t sanctum-sanctorum .`
   - `docker run -p 8000:8000 sanctum-sanctorum`

---

## What Was Finished

1. **Books**:
   - Implemented ISBN-13 checksum algorithm (`(10 - sum % 10) % 10` with alternating 1 and 3 weights) and normalization (stripping spaces and hyphens).
   - Added duplicate ISBN checks returning `409 Conflict`.
   - Added `PATCH /books/{id}` in `app/routers/books.py` and `app/services/books.py` to allow partial updates while silently ignoring `isbn` and unknown fields.
   - Built full search and filter functionality in `GET /books`: case-insensitive substring matching across `title` OR `author`, `restricted` boolean filter, inclusive `min_price` and `max_price`, sorting (`title`, `-title`, `price`, `-price` with `id` tie-breaking), and pre-pagination `total` counts.

2. **Members**:
   - Added input sanitation and email normalization (stripping whitespace and lowercasing) before regex validation.
   - Handled duplicate email detection with case-insensitivity, returning `409 Conflict`.
   - Fixed the `tier_at_least` comparison bug where `>` was used instead of `>=`.
   - Implemented member detail and order listing endpoints.

3. **Orders**:
   - Validated `OrderCreate` payload: rejected empty items and duplicate `book_id` occurrences with `422 Unprocessable Entity`.
   - Enforced order of validation: missing member / missing book (`404`), restricted book access (`403`), and stock availability (`409`).
   - Implemented pricing calculations: tier discounts (`apprentice`: 0%, `adept`: 5%, `master`: 10%, `supreme`: 15%), bulk quantity discount (+5% when total quantity >= 10), and integer cents floor division.
   - Unit prices are snapshotted in `OrderItem` at order creation time.
   - Implemented `POST /orders/{id}/pay` (verifying pending state) and `POST /orders/{id}/cancel` (restoring reserved stock).

4. **Loans**:
   - Completed ORM `Loan` model: added `due_at`, `returned_at` (nullable), and `late_fee_cents`.
   - Implemented borrowing rules and order of checks: 404 for missing entities, 403 for restricted titles, 409 for active overdue loans, 409 for active unreturned loans of the same title, 409 for tier concurrent loan limits (`apprentice`: 1, `adept`: 3, `master`: 5, `supreme`: unlimited), and 409 for out of stock books.
   - Dynamically computed status at read-time: `returned`, `overdue`, or `active`, with strict inequality where `now == due_at` remains active.
   - Computed late fees on return: 25 cents per started day late (`math.ceil(seconds / 86400)`), capped at the book's price at return time.

5. **Member Stats & Reports**:
   - Built `GET /members/{id}/stats` calculating paid order counts, total spent cents, active unreturned loans, overdue unreturned loans, and late fees on returned loans.
   - Built `GET /reports/top-books` querying book sales quantities across paid orders only, filtering books with zero sales, ordering by `copies_sold DESC, title ASC`, and respecting `limit` parameter bounds (1..50).

6. **Optional Extras Completed**:
   - **GET /members with pagination**: Implemented `GET /members` accepting `limit` (default 20, 1..100) and `offset` (>= 0), returning `{items, total, limit, offset}`.
   - **Safe Concurrent Orders**: Protected stock deduction against race conditions using atomic conditional SQL updates (`UPDATE books SET stock = stock - :qty WHERE id = :id AND stock >= :qty`), check constraints on the table (`CheckConstraint("stock >= 0")`), and thread-level locking.
   - **Extra Tests**: Added `tests/test_extras.py` testing member pagination, boundary checks, and concurrent order race condition simulations.

---

## Architectural Decisions and Trade-offs

- **Layering & Responsibility**:
  - Routers (`app/routers/`) remain thin HTTP adapters responsible only for parameter parsing, dependency injection, and schema serialization.
  - Services (`app/services/`) encapsulate all domain rules, transactional boundaries, and database queries.
  - Schemas (`app/schemas.py`) handle payload normalization and input validation before service execution.

- **Data Integrity & Concurrency**:
  - Decrementing stock in Python memory (`book.stock -= qty`) is unsafe under concurrency because two simultaneous requests reading `stock = 1` will both compute `1 - 1 = 0` and emit `UPDATE books SET stock = 0`, leading to double selling.
  - We implemented atomic conditional SQL updates (`WHERE stock >= qty`), SQLite/Postgres `CheckConstraint("stock >= 0")`, and transaction rollback on failure to maintain strict all-or-nothing atomicity.

- **Database Agnosticism**:
  - Handled SQLite vs PostgreSQL connection argument differences in `app/db.py`: `check_same_thread` is only passed when running on SQLite.
  - Handled URI normalization (converting `postgres://` to `postgresql://`) for cloud-hosted Postgres providers (Supabase, Neon, Render, Railway).

---

## Clarifications & Discrepancies Found in Starter Code

1. **`tier_at_least` Comparison**:
   - In `app/services/members.py`, the starter code used `TIER_ORDER.index(tier) > TIER_ORDER.index(minimum)`.
   - This caused `master` members (index 2) to be blocked from `master` minimum requirements (2 > 2 is False).
   - Fixed to `>=` so members meeting the minimum requirement can buy and borrow restricted titles.

2. **`OrderCreate` Validation Order**:
   - The specification required checking 422 conditions before 404 (e.g. duplicate books in order payload must return 422 even if the member ID does not exist).
   - Validating items in Pydantic schema validators ensures FastAPI halts with 422 before the router even touches the database.

3. **`OrderItemOut` Structure**:
   - The specification mandates that order item response objects expose `{book_id, quantity, unit_price_cents, line_total_cents}` without leaking the internal database primary key `id`.
   - `OrderItemOut` schema strictly isolates these attributes.

---

## AI Usage

- **Tools Used**: Antigravity pairing assistant (powered by Gemini).
- **Tasks Delegated**:
  - Scaffolding repetitive Pydantic schemas and test-driven failure analysis.
  - Exploring SQLAlchemy 2.0 query syntax for pre-pagination counting (`select(func.count()).select_from(subquery)`).
  - Verifying ISBN-13 checksum mathematical edge cases.
- **Where the AI was Corrected / Overridden**:
  - *Concurrent stock reservation*: Initial suggestion was relying on in-memory object manipulation `book.stock -= item.quantity` wrapped with a table check constraint. However, under concurrent threads reading the same in-memory object state before flushing, both threads write `stock = 0`, bypassing the `stock >= 0` check constraint. I corrected this by using an atomic SQL `update(Book).where(Book.id == book.id, Book.stock >= item.quantity).values(stock=Book.stock - item.quantity)` checking `result.rowcount == 0` for transactional rollback, backed by a threading lock for in-memory SQLite testing.
