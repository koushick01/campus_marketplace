# Campus Marketplace — Project Guide

## Project Overview

A Flask-based student marketplace web app for a final year academic project. Campus users can post, browse, and buy/sell items. Features user auth, listings with categories and condition/negotiable fields, sold status toggling, favorites, flat messaging with unread counts, a seller profile page, and a Gemini-powered AI chatbot.

**Purpose:** Final year academic project — not production. Prioritize clean, demonstrable features over production hardening.

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3 / Flask |
| ORM | Flask-SQLAlchemy |
| Auth | Flask-Login + Werkzeug password hashing (scrypt) |
| Database | SQLite (`instance/marketplace.db`) |
| Frontend | Jinja2 templates + Bootstrap 5.3.2 (CDN) + vanilla JS |
| Icons | Bootstrap Icons 1.11.3 (CDN) |
| AI | Google Gemini 2.5 Flash via `google-genai` package |
| File storage | Local filesystem (`static/uploads/`) |
| Config | `python-dotenv` (`.env` file) |
| Deployment target | PythonAnywhere (recommended) or Render |

---

## Project Structure

```
campus_marketplace/
├── main.py                 # Entry point: imports app, runs on port 5001
├── app.py                  # App factory: creates Flask app, binds extensions, imports views
├── config.py               # Config class (SECRET_KEY, DB URI, UPLOAD_FOLDER, MAX_CONTENT_LENGTH)
├── extensions.py           # Unbound db + login_manager instances (avoids circular imports)
├── views.py                # All route handlers (imported by app.py at the bottom)
├── constants.py            # CATEGORIES list, CONDITIONS list
├── requirements.txt
├── .env                    # SECRET_KEY, GEMINI_API_KEY — never commit
├── .gitignore              # Excludes .env, instance/, static/uploads/, __pycache__
├── models/
│   ├── __init__.py         # Re-exports User, Listing, Favorite, Message
│   ├── user.py
│   ├── listing.py
│   ├── favorite.py
│   └── message.py
├── instance/
│   └── marketplace.db      # SQLite database (auto-created by db.create_all on startup)
├── static/
│   ├── uploads/            # User-uploaded listing images (UUID-prefixed filenames)
│   └── css/
│       └── style.css       # Full custom CSS (red palette, component classes)
└── templates/
    ├── base.html           # Bootstrap shell: navbar, flash messages, footer
    ├── index.html          # Home: listing grid + search + filters
    ├── register.html       # Registration form (username + email + password)
    ├── login.html          # Login form (username OR email)
    ├── create_listing.html # Post listing: title, category, condition, price, negotiable, image
    ├── edit_listing.html   # Edit own listing (same fields as create)
    ├── listing_detail.html # Single listing: sold banner, condition, negotiable, message form
    ├── my_listings.html    # Own listings table: status, mark sold/relist, edit, delete
    ├── favorites.html      # Saved listings with sold indicators
    ├── messages.html       # Flat inbox: sent/received, unread, reply links
    ├── chatbot.html        # Gemini AI chat UI (aria-live, disable during fetch)
    └── profile.html        # Seller profile: avatar initial, member since, listing grid
```

---

## Architecture: App Factory + Circular Import Solution

The project uses a deferred-import pattern to prevent circular imports:

```
extensions.py   →   defines db, login_manager (unbound, no app reference)
models/*.py     →   imports db from extensions
app.py          →   creates Flask app → binds extensions via init_app()
                    → imports models (for user_loader)
                    → imports views at the BOTTOM (registers routes onto app)
views.py        →   imports app from app.py (app already exists by this point)
main.py         →   imports app from app.py, calls app.run()
```

`db.create_all()` is called inside `with app.app_context()` directly in `app.py` so it runs whether you use `python main.py` or `flask run`.

---

## Database Models

### User (`models/user.py`)
| Field | Type | Notes |
|-------|------|-------|
| id | Integer PK | |
| username | String(80) | unique, not null |
| email | String(120) | unique, not null |
| password_hash | String(200) | scrypt via Werkzeug |
| created_at | DateTime | default utcnow |

### Listing (`models/listing.py`)
| Field | Type | Notes |
|-------|------|-------|
| id | Integer PK | |
| title | String(120) | not null |
| description | Text | nullable |
| price | Numeric(10,2) | not null — use Numeric not Float |
| category | String(50) | not null |
| image | String(200) | nullable, UUID-prefixed filename |
| user_id | Integer FK → user.id | not null |
| created_at | DateTime | default utcnow |
| status | String(20) | 'available' or 'sold', default 'available' |
| condition | String(20) | nullable (New/Like New/Good/Fair/Poor) |
| is_negotiable | Boolean | default False |

Relationship: `user = db.relationship("User", backref="listings")`

### Favorite (`models/favorite.py`)
| Field | Type | Notes |
|-------|------|-------|
| id | Integer PK | |
| user_id | Integer FK → user.id | not null |
| listing_id | Integer FK → listing.id | not null |
| UniqueConstraint | (user_id, listing_id) | prevents duplicate saves |

### Message (`models/message.py`)
| Field | Type | Notes |
|-------|------|-------|
| id | Integer PK | |
| sender_id | Integer FK → user.id | not null |
| receiver_id | Integer FK → user.id | not null |
| listing_id | Integer FK → listing.id | nullable |
| text | Text | not null |
| timestamp | DateTime | default utcnow |
| is_read | Boolean | default False |

Relationships use `foreign_keys=[...]` due to multiple FKs to user:
```python
sender   = db.relationship("User", foreign_keys=[sender_id])
receiver = db.relationship("User", foreign_keys=[receiver_id])
listing  = db.relationship("Listing", foreign_keys=[listing_id])
```

> **Schema change rule:** SQLite has no ALTER TABLE support for adding columns. When the schema changes, delete `instance/marketplace.db` and let `db.create_all()` recreate it on next startup.

---

## Routes

| Route | Methods | Auth | Description |
|-------|---------|------|-------------|
| `/` | GET | No | Home: search by title, filter by category/price/sold |
| `/register` | GET, POST | No | Creates user with username + email |
| `/login` | GET, POST | No | Login by username OR email |
| `/logout` | GET | Yes | |
| `/create` | GET, POST | Yes | Post new listing (with condition, negotiable) |
| `/listing/<id>` | GET | No | Detail view: sold banner, message form, mark-sold for owner |
| `/listing/<id>/edit` | GET, POST | Yes | Edit own listing |
| `/listing/<id>/delete` | POST | Yes | Delete own listing + cascade favorites/messages |
| `/listing/<id>/mark_sold` | POST | Yes | Toggle status available ↔ sold |
| `/favorite/<id>` | POST | Yes | Save to favorites |
| `/unfavorite/<id>` | POST | Yes | Remove from favorites |
| `/favorites` | GET | Yes | View saved listings |
| `/messages` | GET, POST | Yes | Flat inbox (marks received as read on open) |
| `/my_listings` | GET | Yes | Own listings with status, sold/relist button |
| `/user/<username>` | GET | No | Seller profile page |
| `/chatbot` | GET | Yes | AI chat UI |
| `/chat` | POST | Yes | Gemini API call with system prompt + listing context |

---

## Key Feature Details

### Sold System
- `Listing.status` field: `'available'` (default) or `'sold'`
- Owner toggles via `/listing/<id>/mark_sold` (POST) — works from both detail page and my_listings
- Home page hides sold listings by default; "Show sold" checkbox reveals them with greyed cards + ribbon
- Sold listings show a banner on detail page and disable the message/favorite actions for buyers

### Unread Messages
- `Message.is_read` is `False` by default
- `@app.context_processor` injects `unread_count` into every template
- Navbar shows a white badge on "Messages" when `unread_count > 0`
- Opening `/messages` marks all received unread messages as read

### Chatbot
- Gemini client is lazily initialised — app works fine with no API key (returns 503)
- System prompt is injected with the 10 most recent available listings for context
- Input and send button are disabled during fetch to prevent double-sends

### Image Upload
- Max 500 KB enforced server-side (`MAX_CONTENT_LENGTH = 500 * 1024`) and client-side (JS file size check)
- Filename collision prevention: `uuid4().hex + "." + ext` — original filename discarded
- Allowed types: PNG, JPG, JPEG only

### Index Filters
- `q` — title substring search (case-insensitive `ilike`)
- `category` — exact category match
- `min_price` / `max_price` — numeric range filters
- `show_sold=1` — include sold listings (default: excluded)

---

## Constants (`constants.py`)

```python
CATEGORIES = [
    "Books & Notes", "Electronics", "Clothing & Accessories",
    "Furniture & Dorm", "Sports & Fitness", "Stationery & Supplies",
    "Bikes & Transport", "Food & Meal Plans", "Services & Tutoring", "Other",
]

CONDITIONS = ["New", "Like New", "Good", "Fair", "Poor"]
```

`CONDITIONS` is defined in `views.py` and passed to create/edit templates.

---

## Design System

**CSS Variables (`static/css/style.css`):**
```css
--primary:      #C0392B   /* deep red — navbar, buttons, prices */
--primary-dark: #922B21   /* hover states */
--primary-light:#E74C3C   /* focus rings */
--accent:       #F1948A   /* highlights, category badges border */
--bg:           #F7F7F7   /* page background */
--surface:      #FFFFFF   /* card backgrounds */
--border:       #E0E0E0
--text:         #1A1A1A
--muted:        #6B7280
--success:      #27AE60
--radius:       10px
```

**Key CSS Classes:**
| Class | Purpose |
|-------|---------|
| `.listing-card` | Product card with hover lift |
| `.listing-card.sold` | Greyed-out image, muted title/price |
| `.sold-ribbon` | Diagonal "SOLD" ribbon on card corner |
| `.sold-banner` | Grey banner across top of detail page |
| `.form-card` | White box for create/edit forms |
| `.auth-card` | Centred auth form box |
| `.chat-window` | Responsive height chat area (min 400px, max 600px) |
| `.chat-bubble.user` | Red right-aligned bubble |
| `.chat-bubble.bot` | White left-aligned bubble |
| `.fav-card` | Favorites list row |
| `.fav-thumb` | 64×52px thumbnail in favorites |
| `.message-card` | Inbox message row (red left border) |
| `.message-card.sent` | Muted left border |
| `.unread-badge` | White pill on Messages nav link |
| `.profile-header` | Seller profile card |
| `.profile-avatar` | Circular letter avatar |
| `.empty-state` | Centred icon + text for empty pages |

---

## Context Processor

```python
@app.context_processor
def inject_unread_count():
    if current_user.is_authenticated:
        count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
        return {"unread_count": count}
    return {"unread_count": 0}
```

`unread_count` is available in every template automatically.

---

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server (port 5001)
python main.py
# App at http://127.0.0.1:5001

# Reset database (after schema changes)
# Delete instance/marketplace.db then restart — db.create_all() recreates it

# Check database contents
sqlite3 "instance/marketplace.db" "SELECT username, email FROM user;"
sqlite3 "instance/marketplace.db" ".tables"
sqlite3 "instance/marketplace.db" ".schema listing"
```

---

## Environment Variables (`.env`)

```
SECRET_KEY=your-secret-key-here
GEMINI_API_KEY=your-gemini-api-key-here
```

Never commit `.env`. The app runs without `GEMINI_API_KEY` (chatbot returns 503).

---

## Deployment Notes

**Recommended: PythonAnywhere**
- Free tier: Flask + SQLite, persistent filesystem, no Dockerfile needed
- WSGI config points to `app.py`, exposes the `app` object
- Upload `static/uploads/` separately or create it manually

**Render alternative:**
- Add `gunicorn` to `requirements.txt`
- Free tier has ephemeral disk — SQLite and uploads are wiped on redeploy
- Use Render's persistent disk add-on, or switch to PostgreSQL + Cloudinary for images

---

## Coding Conventions

- Routes live in `views.py`; models in `models/`; app wiring in `app.py`
- `@login_required` on all authenticated routes
- Post/Redirect/Get pattern throughout (no double-submit on refresh)
- `db.session.get(Model, id)` not deprecated `Model.query.get(id)`
- `db.Numeric(10, 2)` for price (not Float — avoids floating point errors)
- UUID prefix on upload filenames — original filename discarded
- `foreign_keys=[...]` on relationships where a model has multiple FKs to the same table
- `ilike` for case-insensitive search
- No inline styles in templates — use CSS classes from `style.css`
- No Flask-Migrate — schema changes require deleting `instance/marketplace.db`

---

## Known Remaining Gaps

- No CSRF protection (Flask-WTF would add this)
- No pagination (acceptable for project demo scale)
- Messages are flat (no threading) — by design
- No email verification on registration — by design (open campus platform)
- SQLite not suitable for concurrent writes at scale — fine for demo
