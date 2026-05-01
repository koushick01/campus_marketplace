# Campus Marketplace — Project Guide

## Project Overview

A Flask-based student marketplace web app for a final year project. Campus users can post, browse, and buy/sell items. Includes user auth, listings with categories, favorites, direct messaging, and a Gemini-powered AI chatbot.

**Purpose:** Final year academic project — not production. Prioritize clean features and good design over production hardening.

## Tech Stack

- **Backend:** Python / Flask, Flask-SQLAlchemy, Flask-Login
- **Database:** SQLite (`instance/marketplace.db`)
- **Frontend:** Jinja2 templates + Bootstrap 5.3.2 (CDN) + vanilla JS
- **AI:** Google Gemini 2.5 Flash (`google-generativeai`)
- **Auth:** Flask-Login with Werkzeug password hashing
- **File storage:** Local filesystem (`static/uploads/`)
- **Deployment target:** Render or PythonAnywhere

## Project Structure

```
campus_marketplace/
├── app.py                  # All routes, models, app factory
├── config.py               # Config class (SECRET_KEY, DB URI, upload settings)
├── requirements.txt
├── .env                    # SECRET_KEY, GEMINI_API_KEY (never commit)
├── .gitignore
├── instance/
│   └── marketplace.db      # SQLite database
├── static/
│   ├── uploads/            # User-uploaded listing images
│   └── css/
│       └── style.css       # Custom CSS (red color palette, modern Bootstrap overrides)
└── templates/
    ├── base.html           # Navbar + Bootstrap layout shell
    ├── index.html          # Home — listing grid + search + category filter
    ├── register.html       # Registration form
    ├── login.html          # Login form
    ├── create_listing.html # Post a new listing (category dropdown)
    ├── listing_detail.html # Single listing view + message seller
    ├── favorites.html      # Saved listings list
    ├── messages.html       # All messages (flat list inbox)
    ├── chatbot.html        # Gemini AI chat UI
    └── my_listings.html    # User's own listings (edit/delete)
```

## Database Models

| Model     | Key Fields |
|-----------|-----------|
| `User`    | id, username, password_hash |
| `Listing` | id, title, description, price, category, image, user_id (FK), created_at |
| `Favorite`| id, user_id, listing_id |
| `Message` | id, sender_id, receiver_id, listing_id, text, timestamp |

## Routes

| Route | Methods | Auth | Notes |
|-------|---------|------|-------|
| `/` | GET | No | Home; search by title; filter by category |
| `/register` | GET, POST | No | Open to any username (no email restriction) |
| `/login` | GET, POST | No | |
| `/logout` | GET | Yes | |
| `/create` | GET, POST | Yes | Image upload (PNG/JPG, max 500 KB); category dropdown |
| `/listing/<id>` | GET | No | View + message seller |
| `/listing/<id>/edit` | GET, POST | Yes | Edit own listing |
| `/listing/<id>/delete` | POST | Yes | Delete own listing |
| `/favorite/<id>` | GET | Yes | Toggle-add favorite |
| `/unfavorite/<id>` | POST | Yes | Remove from favorites |
| `/favorites` | GET | Yes | View saved listings |
| `/messages` | GET, POST | Yes | Flat inbox + send |
| `/my_listings` | GET | Yes | User's own listings |
| `/chatbot` | GET | Yes | Chatbot UI |
| `/chat` | POST | Yes | Gemini API call |

## Listing Categories (Fixed Dropdown)

```python
CATEGORIES = [
    "Books & Notes",
    "Electronics",
    "Clothing & Accessories",
    "Furniture & Dorm",
    "Sports & Fitness",
    "Stationery & Supplies",
    "Bikes & Transport",
    "Food & Meal Plans",
    "Services & Tutoring",
    "Other",
]
```

## Design System

**Color Palette (Red theme):**
```css
--primary:     #C0392B   /* deep red — primary actions, navbar */
--primary-dark: #922B21  /* darker red — hover states */
--accent:      #E74C3C   /* bright red — highlights, badges */
--surface:     #FDFDFD   /* off-white card backgrounds */
--bg:          #F5F5F5   /* page background */
--text:        #212121   /* primary text */
--muted:       #757575   /* secondary text */
```

**UI Direction:**
- Modern, stylish Bootstrap 5 with custom CSS overrides
- Cards with subtle shadows and hover lift effects
- Consistent red accent throughout navbar, buttons, badges
- Clean typography, good whitespace
- Responsive grid for listings

## Feature Decisions

| Feature | Decision |
|---------|----------|
| Registration | Open — any username, no email restriction |
| Payments | None — connect buyers & sellers only |
| Messaging | Flat list (no threading) |
| Search | Title only |
| Filters | Category dropdown filter on home page |
| My Listings | Yes — view, edit, delete own listings |
| Favorites | Add and remove |
| Database | SQLite (no migration to PostgreSQL needed) |
| Real-time | No WebSockets — standard HTTP |

## Known Gaps to Fix

- `my_listings.html` is empty; `/my_listings`, `/listing/<id>/edit`, `/listing/<id>/delete` routes missing
- No CSRF protection (can add Flask-WTF if time permits)
- No "remove from favorites" feature
- No pagination (add if listing count grows)
- Search is case-sensitive (fix with `ilike` or `.lower()`)
- `OPENAI_API_KEY` in `.env` is unused — remove
- `/list_models` debug route should be removed before demo

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server
python app.py
# App runs at http://127.0.0.1:5000 in debug mode
```

## Environment Variables (`.env`)

```
SECRET_KEY=...
GEMINI_API_KEY=...
```

Never commit `.env` to version control.

## Deployment Notes

**Recommended: PythonAnywhere** (better than Render for Flask/SQLite final year projects)
- Free tier supports Flask + SQLite with zero config
- No build pipeline or Dockerfile needed
- Persistent filesystem (SQLite file and uploads survive restarts)
- Simple WSGI config pointing to `app.py`

**Render alternative:**
- Requires `gunicorn` added to `requirements.txt`
- SQLite data is wiped on each deploy (ephemeral disk on free tier) — workaround: use Render's persistent disk add-on or switch to PostgreSQL
- Add a `render.yaml` or configure manually via dashboard

## Coding Conventions

- All models and routes in `app.py` — keep co-located (project is small enough)
- Templates extend `base.html` via `{% extends 'base.html' %}` + `{% block content %}`
- Use `@login_required` for all authenticated routes
- Images saved with `secure_filename` + UUID prefix
- `CATEGORIES` list defined once at top of `app.py` and passed to templates that need it
- Bootstrap classes + custom `style.css` overrides — no inline styles
