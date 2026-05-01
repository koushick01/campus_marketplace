import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from google import genai
from config import Config
from datetime import datetime

load_dotenv()


app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY in .env")

client = genai.Client(api_key=GEMINI_API_KEY)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

# ---------------- Models ----------------

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    category = db.Column(db.String(50))
    image = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    listing_id = db.Column(db.Integer)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer)
    receiver_id = db.Column(db.Integer)
    listing_id = db.Column(db.Integer)
    text = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- Utils ----------------

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- Routes ----------------

@app.route("/")
def index():
    q = request.args.get("q", "")
    if q:
        listings = Listing.query.filter(Listing.title.contains(q)).all()
    else:
        listings = Listing.query.order_by(Listing.created_at.desc()).all()
    return render_template("index.html", listings=listings)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = User(username=request.form["username"],
                    password_hash=generate_password_hash(request.form["password"]))
        db.session.add(user)
        db.session.commit()
        flash("Registered successfully!")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password_hash, request.form["password"]):
            login_user(user)
            return redirect(url_for("index"))
        flash("Invalid credentials")
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
        return redirect(url_for("index"))
    return render_template("create_listing.html")

@app.route("/listing/<int:id>")
def listing_detail(id):
    listing = Listing.query.get_or_404(id)
    return render_template("listing_detail.html", listing=listing)

@app.route("/favorite/<int:id>")
@login_required
def favorite(id):
    db.session.add(Favorite(user_id=current_user.id, listing_id=id))
    db.session.commit()
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
        msg = Message(sender_id=current_user.id,
                      receiver_id=request.form["receiver_id"],
                      listing_id=request.form["listing_id"],
                      text=request.form["text"])
        db.session.add(msg)
        db.session.commit()
    inbox = Message.query.filter(
        (Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id)
    ).order_by(Message.timestamp.desc()).all()
    return render_template("messages.html", messages=inbox)

@app.route("/chatbot", methods=["GET"])
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
    
    
@app.route("/list_models")
@login_required
def list_models():
    try:
        models = client.models.list()
        names = [m.name for m in models]
        return jsonify({"available_models": names})
        

    except Exception as e:
        return jsonify({"error": str(e)}), 500




# ---------------- Init ----------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
