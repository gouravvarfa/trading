from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv

# ---------------- LOAD ENV VARIABLES ----------------
load_dotenv()

app = Flask(__name__)

# ---------------- SECURITY CONFIG ----------------
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not set")

app.secret_key = SECRET_KEY

# ---------------- DATABASE CONFIG (NEON ONLY) ----------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

# Fix postgres:// issue if present
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------------- ADMIN AUTH ----------------
ADMIN_USER = "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD not set")

ADMIN_PASS_HASH = generate_password_hash(ADMIN_PASSWORD)

# ---------------- DATABASE MODEL ----------------
class Schedule(db.Model):
    __tablename__ = "schedule"

    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    meet_link = db.Column(db.String(200))
    image_url = db.Column(db.String(500))

# ---------------- CREATE TABLES ----------------
with app.app_context():
    db.create_all()
    print("✅ USING DATABASE:", db.engine.url)

# ---------------- LOGIN REQUIRED DECORATOR ----------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Unauthorized access")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    schedules = Schedule.query.order_by(Schedule.day).all()
    return render_template("index.html", schedules=schedules)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USER and check_password_hash(ADMIN_PASS_HASH, password):
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("admin_dashboard"))

        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/admin")
@login_required
def admin_dashboard():
    schedules = Schedule.query.order_by(Schedule.day).all()
    return render_template("admin.html", schedules=schedules)

@app.route("/add", methods=["POST"])
@login_required
def add_schedule():
    try:
        schedule = Schedule(
            day=int(request.form.get("day")),
            title=request.form.get("title"),
            description=request.form.get("description"),
            meet_link=request.form.get("meet_link"),
            image_url=request.form.get("image_url")
        )
        db.session.add(schedule)
        db.session.commit()
        flash("Schedule added successfully")
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {e}")
    return redirect(url_for("admin_dashboard"))

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_schedule(id):
    schedule = Schedule.query.get_or_404(id)
    if request.method == "POST":
        schedule.day = int(request.form.get("day"))
        schedule.title = request.form.get("title")
        schedule.description = request.form.get("description")
        schedule.meet_link = request.form.get("meet_link")
        schedule.image_url = request.form.get("image_url")
        db.session.commit()
        flash("Schedule updated")
        return redirect(url_for("admin_dashboard"))
    return render_template("edit.html", schedule=schedule)

@app.route("/delete/<int:id>")
@login_required
def delete_schedule(id):
    schedule = Schedule.query.get_or_404(id)
    db.session.delete(schedule)
    db.session.commit()
    flash("Schedule deleted")
    return redirect(url_for("admin_dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- ERROR HANDLER ----------------
@app.errorhandler(404)
def not_found(e):
    return "404 - Page not found", 404

# ---------------- LOCAL RUN ONLY ----------------
if __name__ == "__main__":
    app.run(debug=False)
