from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)

# --- CONFIGURATION ---
# Use a strong secret key for session encryption
app.secret_key = "trader_pro_secret_2026_x99" 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///terminal_v2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- SECURE CREDENTIALS ---
# We store the hash so the actual password is never visible in the code
ADMIN_USER = "admin"
ADMIN_PASS_HASH = generate_password_hash("admin123") # Change "admin123" to your preferred password

# --- DATABASE MODEL ---
class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.Integer)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    meet_link = db.Column(db.String(200))
    image_url = db.Column(db.String(500))

# Initialize Database
with app.app_context():
    db.create_all()

# --- AUTHENTICATION DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash("REJECTED: Unauthorized Access detected.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- PUBLIC ROUTES ---

@app.route('/')
def index():
    schedules = Schedule.query.order_by(Schedule.day).all()
    return render_template('index.html', schedules=schedules)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form.get('username')
        pass_input = request.form.get('password')

        # Securely check credentials
        if user_input == ADMIN_USER and check_password_hash(ADMIN_PASS_HASH, pass_input):
            session['logged_in'] = True
            session['username'] = user_input
            return redirect(url_for('admin_dashboard'))
        
        flash('Invalid Access Key: Identification Failed')
    return render_template('login.html')


# --- PROTECTED ADMIN ROUTES ---

@app.route('/admin')
@login_required
def admin_dashboard():
    schedules = Schedule.query.order_by(Schedule.day).all()
    return render_template('admin.html', schedules=schedules)

@app.route('/add', methods=['POST'])
@login_required
def add_schedule():
    try:
        new_s = Schedule(
            day=int(request.form.get('day')),
            title=request.form.get('title'),
            description=request.form.get('description'),
            meet_link=request.form.get('meet_link'),
            image_url=request.form.get('image_url')
        )
        db.session.add(new_s)
        db.session.commit()
        flash("DATABASE_UPDATE: Node added successfully.")
    except Exception as e:
        flash(f"SYSTEM_ERROR: {str(e)}")
        
    return redirect(url_for('admin_dashboard'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_schedule(id):
    schedule = Schedule.query.get_or_404(id)
    if request.method == 'POST':
        schedule.day = int(request.form.get('day'))
        schedule.title = request.form.get('title')
        schedule.description = request.form.get('description')
        schedule.meet_link = request.form.get('meet_link')
        schedule.image_url = request.form.get('image_url')
        db.session.commit()
        flash("NODE_MODIFIED: Changes committed.")
        return redirect(url_for('admin_dashboard'))
    return render_template('edit.html', schedule=schedule)

@app.route('/delete/<int:id>')
@login_required
def delete_schedule(id):
    s = Schedule.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    flash("NODE_PURGED: Data removed from cluster.")
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- ERROR HANDLERS ---
@app.errorhandler(404)
def page_not_found(e):
    return "404: Node not found in current sector.", 404

