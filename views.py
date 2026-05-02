import os
from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from google import genai

from app import app
from extensions import db
from models import User, Listing, Favorite, Message

# ---------------- Gemini client ----------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY in .env")
client = genai.Client(api_key=GEMINI_API_KEY)

# ---------------- Constants ----------------

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

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

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- Routes ----------------

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    cat = request.args.get("category", "")
    query = Listing.query
    if q:
        query = query.filter(Listing.title.ilike(f"%{q}%"))
    if cat:
        query = query.filter(Listing.category == cat)
    listings = query.order_by(Listing.created_at.desc()).all()
    return render_template("index.html", listings=listings, q=q,
                           selected_cat=cat, categories=CATEGORIES)


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
        image = request.files["image"]
        filename = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        listing = Listing(
            title=request.form["title"],
            description=request.form["description"],
            price=float(request.form["price"]),
            category=request.form["category"],
            image=filename,
            user_id=current_user.id
        )
        db.session.add(listing)
        db.session.commit()
        flash("Listing posted successfully!", "success")
        return redirect(url_for("index"))
    return render_template("create_listing.html", categories=CATEGORIES)


@app.route("/listing/<int:id>")
def listing_detail(id):
    listing = Listing.query.get_or_404(id)
    seller = User.query.get(listing.user_id)
    already_saved = False
    if current_user.is_authenticated:
        already_saved = Favorite.query.filter_by(
            user_id=current_user.id, listing_id=id).first() is not None
    return render_template("listing_detail.html", listing=listing,
                           seller=seller, already_saved=already_saved)


@app.route("/my_listings")
@login_required
def my_listings():
    listings = Listing.query.filter_by(user_id=current_user.id)\
                            .order_by(Listing.created_at.desc()).all()
    return render_template("my_listings.html", listings=listings, categories=CATEGORIES)


@app.route("/listing/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_listing(id):
    listing = Listing.query.get_or_404(id)
    if listing.user_id != current_user.id:
        flash("You can only edit your own listings.", "error")
        return redirect(url_for("index"))
    if request.method == "POST":
        listing.title = request.form["title"]
        listing.description = request.form["description"]
        listing.price = float(request.form["price"])
        listing.category = request.form["category"]
        image = request.files.get("image")
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            listing.image = filename
        db.session.commit()
        flash("Listing updated.", "success")
        return redirect(url_for("my_listings"))
    return render_template("edit_listing.html", listing=listing, categories=CATEGORIES)


@app.route("/listing/<int:id>/delete", methods=["POST"])
@login_required
def delete_listing(id):
    listing = Listing.query.get_or_404(id)
    if listing.user_id != current_user.id:
        flash("You can only delete your own listings.", "error")
        return redirect(url_for("index"))
    Favorite.query.filter_by(listing_id=id).delete()
    db.session.delete(listing)
    db.session.commit()
    flash("Listing deleted.", "success")
    return redirect(url_for("my_listings"))


@app.route("/favorite/<int:id>")
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
    listings = [Listing.query.get(f.listing_id) for f in favs]
    return render_template("favorites.html", listings=listings)


@app.route("/messages", methods=["GET", "POST"])
@login_required
def messages():
    if request.method == "POST":
        msg = Message(
            sender_id=current_user.id,
            receiver_id=request.form["receiver_id"],
            listing_id=request.form["listing_id"],
            text=request.form["text"]
        )
        db.session.add(msg)
        db.session.commit()
        flash("Message sent!", "success")
        listing_id = request.form.get("listing_id")
        if listing_id:
            return redirect(url_for("listing_detail", id=listing_id))
    inbox = Message.query.filter(
        (Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id)
    ).order_by(Message.timestamp.desc()).all()
    users = {u.id: u for u in User.query.all()}
    listings_map = {l.id: l for l in Listing.query.all()}
    return render_template("messages.html", messages=inbox,
                           users=users, listings_map=listings_map)


@app.route("/chatbot")
@login_required
def chatbot_page():
    return render_template("chatbot.html")


@app.route("/chat", methods=["POST"])
@login_required
def chat():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415
    data = request.get_json()
    user_msg = (data or {}).get("message", "").strip()
    if not user_msg:
        return jsonify({"reply": "Please type a message."})
    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=user_msg
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        print("Gemini Error:", e)
        return jsonify({"error": "AI service unavailable"}), 500
