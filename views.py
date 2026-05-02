import os
import uuid
from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from google import genai

from app import app
from extensions import db
from models import User, Listing, Favorite, Message
from constants import CATEGORIES

# ---------------- Gemini client (lazy — app works even if key is missing) ----------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ---------------- Constants ----------------

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
CONDITIONS = ["New", "Like New", "Good", "Fair", "Poor"]

# ---------------- Helpers ----------------

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload_image(file):
    """Save uploaded image with a UUID prefix. Returns filename or None."""
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        return filename
    return None


# ---------------- Context processor ----------------

@app.context_processor
def inject_unread_count():
    if current_user.is_authenticated:
        count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
        return {"unread_count": count}
    return {"unread_count": 0}


# ---------------- Routes ----------------

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    cat = request.args.get("category", "")
    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()
    show_sold = request.args.get("show_sold", "") == "1"

    query = Listing.query
    if q:
        query = query.filter(Listing.title.ilike(f"%{q}%"))
    if cat:
        query = query.filter(Listing.category == cat)
    if not show_sold:
        query = query.filter(Listing.status == "available")
    if min_price:
        try:
            query = query.filter(Listing.price >= float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            query = query.filter(Listing.price <= float(max_price))
        except ValueError:
            pass

    listings = query.order_by(Listing.created_at.desc()).all()
    return render_template("index.html", listings=listings, q=q,
                           selected_cat=cat, categories=CATEGORIES,
                           min_price=min_price, max_price=max_price,
                           show_sold=show_sold)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip().lower()
        if User.query.filter_by(username=username).first():
            flash("Username already taken. Please choose another.", "error")
            return redirect(url_for("register"))
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
            return redirect(url_for("register"))
        user = User(username=username, email=email,
                    password_hash=generate_password_hash(request.form["password"]))
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form["identifier"].strip()
        if "@" in identifier:
            user = User.query.filter_by(email=identifier.lower()).first()
        else:
            user = User.query.filter_by(username=identifier).first()
        if user and check_password_hash(user.password_hash, request.form["password"]):
            login_user(user)
            return redirect(url_for("index"))
        flash("Invalid username/email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/create", methods=["GET", "POST"])
@login_required
def create_listing():
    if request.method == "POST":
        try:
            price = float(request.form["price"])
            if price < 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("Please enter a valid price.", "error")
            return render_template("create_listing.html", categories=CATEGORIES,
                                   conditions=CONDITIONS)

        filename = save_upload_image(request.files.get("image"))
        listing = Listing(
            title=request.form["title"],
            description=request.form["description"],
            price=price,
            category=request.form["category"],
            condition=request.form.get("condition") or None,
            is_negotiable=request.form.get("is_negotiable") == "on",
            image=filename,
            user_id=current_user.id
        )
        db.session.add(listing)
        db.session.commit()
        flash("Listing posted successfully!", "success")
        return redirect(url_for("index"))
    return render_template("create_listing.html", categories=CATEGORIES, conditions=CONDITIONS)


@app.route("/listing/<int:id>")
def listing_detail(id):
    listing = db.session.get(Listing, id)
    if listing is None:
        flash("Listing not found.", "error")
        return redirect(url_for("index"))
    already_saved = False
    if current_user.is_authenticated:
        already_saved = Favorite.query.filter_by(
            user_id=current_user.id, listing_id=id).first() is not None
    return render_template("listing_detail.html", listing=listing,
                           seller=listing.user, already_saved=already_saved)


@app.route("/listing/<int:id>/mark_sold", methods=["POST"])
@login_required
def mark_sold(id):
    listing = db.session.get(Listing, id)
    if listing is None:
        flash("Listing not found.", "error")
        return redirect(url_for("my_listings"))
    if listing.user_id != current_user.id:
        flash("You can only update your own listings.", "error")
        return redirect(url_for("index"))
    listing.status = "available" if listing.status == "sold" else "sold"
    db.session.commit()
    if listing.status == "sold":
        flash("Listing marked as sold.", "success")
    else:
        flash("Listing relisted as available.", "success")
    return redirect(url_for("my_listings"))


@app.route("/my_listings")
@login_required
def my_listings():
    listings = Listing.query.filter_by(user_id=current_user.id)\
                            .order_by(Listing.created_at.desc()).all()
    return render_template("my_listings.html", listings=listings, categories=CATEGORIES)


@app.route("/listing/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_listing(id):
    listing = db.session.get(Listing, id)
    if listing is None:
        flash("Listing not found.", "error")
        return redirect(url_for("index"))
    if listing.user_id != current_user.id:
        flash("You can only edit your own listings.", "error")
        return redirect(url_for("index"))
    if request.method == "POST":
        try:
            price = float(request.form["price"])
            if price < 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("Please enter a valid price.", "error")
            return render_template("edit_listing.html", listing=listing,
                                   categories=CATEGORIES, conditions=CONDITIONS)

        listing.title = request.form["title"]
        listing.description = request.form["description"]
        listing.price = price
        listing.category = request.form["category"]
        listing.condition = request.form.get("condition") or None
        listing.is_negotiable = request.form.get("is_negotiable") == "on"
        new_image = save_upload_image(request.files.get("image"))
        if new_image:
            listing.image = new_image
        db.session.commit()
        flash("Listing updated.", "success")
        return redirect(url_for("my_listings"))
    return render_template("edit_listing.html", listing=listing,
                           categories=CATEGORIES, conditions=CONDITIONS)


@app.route("/listing/<int:id>/delete", methods=["POST"])
@login_required
def delete_listing(id):
    listing = db.session.get(Listing, id)
    if listing is None:
        flash("Listing not found.", "error")
        return redirect(url_for("my_listings"))
    if listing.user_id != current_user.id:
        flash("You can only delete your own listings.", "error")
        return redirect(url_for("index"))
    Favorite.query.filter_by(listing_id=id).delete()
    Message.query.filter_by(listing_id=id).delete()
    db.session.delete(listing)
    db.session.commit()
    flash("Listing deleted.", "success")
    return redirect(url_for("my_listings"))


@app.route("/favorite/<int:id>", methods=["POST"])
@login_required
def favorite(id):
    if not Favorite.query.filter_by(user_id=current_user.id, listing_id=id).first():
        db.session.add(Favorite(user_id=current_user.id, listing_id=id))
        db.session.commit()
        flash("Saved to favorites.", "success")
    return redirect(url_for("listing_detail", id=id))


@app.route("/unfavorite/<int:id>", methods=["POST"])
@login_required
def unfavorite(id):
    fav = Favorite.query.filter_by(user_id=current_user.id, listing_id=id).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
        flash("Removed from favorites.", "success")
    return redirect(url_for("favorites"))


@app.route("/favorites")
@login_required
def favorites():
    favs = Favorite.query.filter_by(user_id=current_user.id).all()
    listing_ids = [f.listing_id for f in favs]
    listings = Listing.query.filter(Listing.id.in_(listing_ids)).all() if listing_ids else []
    return render_template("favorites.html", listings=listings)


@app.route("/messages", methods=["GET", "POST"])
@login_required
def messages():
    if request.method == "POST":
        try:
            receiver_id = int(request.form["receiver_id"])
            listing_id  = int(request.form["listing_id"])
        except (ValueError, TypeError):
            flash("Invalid message request.", "error")
            return redirect(url_for("index"))

        if receiver_id == current_user.id:
            flash("You cannot message yourself.", "error")
            return redirect(url_for("listing_detail", id=listing_id))

        msg = Message(
            sender_id=current_user.id,
            receiver_id=receiver_id,
            listing_id=listing_id,
            text=request.form["text"]
        )
        db.session.add(msg)
        db.session.commit()
        flash("Message sent!", "success")
        return redirect(url_for("listing_detail", id=listing_id))

    # Mark received messages as read
    Message.query.filter_by(receiver_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()

    inbox = Message.query.filter(
        (Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id)
    ).order_by(Message.timestamp.desc()).all()

    return render_template("messages.html", messages=inbox)


@app.route("/user/<username>")
def user_profile(username):
    seller = User.query.filter_by(username=username).first()
    if seller is None:
        flash("User not found.", "error")
        return redirect(url_for("index"))
    listings = Listing.query.filter_by(user_id=seller.id)\
                            .order_by(Listing.created_at.desc()).all()
    return render_template("profile.html", seller=seller, listings=listings)


@app.route("/chatbot")
@login_required
def chatbot_page():
    return render_template("chatbot.html")


@app.route("/chat", methods=["POST"])
@login_required
def chat():
    if not client:
        return jsonify({"error": "AI service is not configured."}), 503
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415
    data = request.get_json()
    user_msg = (data or {}).get("message", "").strip()
    if not user_msg:
        return jsonify({"reply": "Please type a message."})

    recent = Listing.query.filter_by(status="available")\
                          .order_by(Listing.created_at.desc()).limit(10).all()
    listing_context = "\n".join(
        f"- {l.title} (${l.price}, {l.category})" for l in recent
    ) or "No listings currently available."

    system_prompt = (
        "You are a helpful assistant for Campus Marketplace, a student buy-and-sell platform. "
        "Help users find items, understand how the platform works, and answer general questions. "
        "Keep responses concise and friendly.\n\n"
        f"Recent available listings on the platform:\n{listing_context}"
    )

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=f"{system_prompt}\n\nUser: {user_msg}"
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        print("Gemini Error:", e)
        return jsonify({"error": "AI service unavailable. Please try again."}), 500


@app.errorhandler(413)
def too_large(e):
    flash("Image is too large. Maximum size is 500 KB.", "error")
    return redirect(request.referrer or url_for("index"))
