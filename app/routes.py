import os
import secrets
from datetime import datetime
from urllib.parse import urlparse
from flask import render_template, url_for, flash, redirect, request, jsonify
from app import app, db, bcrypt, mail
from app.forms import RegistrationForm, LoginForm, RequestResetForm, ResetPasswordForm
from app.models import User, Request, Message, Rating
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message as MailMessage

# --- Context Processors ---

@app.context_processor
def inject_notifications():
    if current_user.is_authenticated:
        count = Request.query.filter_by(user_id=current_user.id).count()
        return dict(notification_count=count)
    return dict(notification_count=0)

# --- Helper Functions ---

def save_file(form_file, folder):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_file.filename)
    filename = random_hex + f_ext
    filepath = os.path.join(app.root_path, 'static', folder, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    form_file.save(filepath)
    return filename

def send_verification_email(user):
    token = user.get_reset_token() 
    confirm_url = url_for('confirm_email', token=token, _external=True)
    
    msg = MailMessage(
        'Verify your account on Skills Exchange', 
        sender=app.config['MAIL_USERNAME'], 
        recipients=[user.email]
    )
    
    msg.html = f"""
        <div style="font-family: sans-serif; padding: 20px; color: #333; max-width: 600px; border: 1px solid #eee;">
            <h2 style="color: #2a7a58;">Welcome, {user.username}!</h2>
            <p>Thanks for joining the Skills Exchange community. Please verify your email to get started:</p>
            <div style="margin: 30px 0;">
                <a href="{confirm_url}" 
                   style="background-color: #2a7a58; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                    Verify My Account
                </a>
            </div>
            <p style="font-size: 11px; color: #aaa;">This link will expire in 30 minutes.</p>
        </div>
    """
    mail.send(msg)

# --- Authentication & Core Routes ---

@app.route("/")
@app.route("/home")
def home():
    if current_user.is_authenticated:
        all_users = User.query.filter(User.headline != None, User.id != current_user.id).all()
    else:
        all_users = User.query.filter(User.headline != None).all()
        
    all_requests = Request.query.order_by(Request.date_posted.desc()).all()
    return render_template('home.html', title='Home', profiles=all_users, requests=all_requests)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(
                first_name=form.first_name.data, 
                last_name=form.last_name.data, 
                username=form.username.data, 
                email=form.email.data, 
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()
            send_verification_email(user)
            flash('Account created! Please check your email to verify.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')
            
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            if not user.confirmed:
                flash('Please verify your email address before logging in.', 'warning')
                return render_template('login.html', title='Login', form=form)
            
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/confirm_email/<token>")
def confirm_email(token):
    user = User.verify_reset_token(token)
    if user is None:
        flash('Invalid or expired verification link.', 'warning')
        return redirect(url_for('register'))
    if not user.confirmed:
        user.confirmed = True
        db.session.commit()
        flash('Verification successful! You can now log in.', 'success')
    else:
        flash('Account already verified.', 'info')
    return redirect(url_for('login'))

# --- User Profile Management ---

@app.route("/create_profile", methods=['GET', 'POST'])
@login_required 
def create_profile():
    if request.method == 'POST':
        current_user.headline = request.form.get('headline')
        current_user.bio = request.form.get('bio')
        current_user.phone = request.form.get('phone')
        current_user.skill_cat = request.form.get('skill_cat')
        current_user.skill_level = request.form.get('level')
        current_user.help_text = request.form.get('help_text')
        current_user.skills_learn = request.form.get('skills_learn')
        current_user.time_commit = request.form.get('time_commit')
        current_user.languages = request.form.get('languages')
        current_user.linkedin = request.form.get('linkedin')
        current_user.instagram = request.form.get('instagram')
        current_user.method_zoom = request.form.get('method_zoom') == 'on'
        current_user.method_inperson = request.form.get('method_inperson') == 'on'

        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '':
                current_user.profile_pic = save_file(file, 'profile_pics')

        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('home'))
        
    full_name = f"{current_user.first_name} {current_user.last_name}"
    return render_template('create_profile.html', title='Edit Profile', user=current_user, full_name=full_name)

# --- POST REQUEST (UPDATED WITH FLASH & REDIRECT) ---
@app.route('/post-request', methods=['POST'])
@login_required
def post_request():
    title = request.form.get('req_title')
    category = request.form.get('req_category')
    offer = request.form.get('req_offer')
    details = request.form.get('req_details')

    if not details:
        flash("The description (details) is required.", "danger")
        return redirect(url_for('home'))

    new_request = Request(
        title=title,
        category=category,
        offer=offer,
        details=details,
        author=current_user
    )
    
    try:
        db.session.add(new_request)
        db.session.commit()
        flash("Community request posted successfully!", "success")
        return redirect(url_for('home'))
    except Exception as e:
        db.session.rollback()
        flash(f"Error posting request: {str(e)}", "danger")
        return redirect(url_for('home'))

@app.route("/delete-request/<int:request_id>", methods=['POST'])
@login_required
def delete_request(request_id):
    req = Request.query.get_or_404(request_id)
    if req.author.id != current_user.id:
        flash('Permission denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    db.session.delete(req)
    db.session.commit()
    flash('Request removed.', 'success')
    return redirect(url_for('dashboard'))

# --- Password Reset ---

@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.get_reset_token()
            msg = MailMessage('Password Reset Request', sender=app.config['MAIL_USERNAME'], recipients=[user.email])
            msg.body = f"To reset your password, visit: {url_for('reset_token', token=token, _external=True)}"
            mail.send(msg)
        flash('Instructions have been sent to your email.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)

@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('Invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated!', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)

@app.route("/dashboard")
@login_required
def dashboard():
    my_requests = Request.query.filter_by(user_id=current_user.id).order_by(Request.date_posted.desc()).all()
    return render_template('dashboard.html', title='My Dashboard', requests=my_requests)

@app.route("/vouch/<int:user_id>", methods=['POST'])
@login_required
def vouch_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id != current_user.id:
        user.vouch_count += 1
        db.session.commit()
    return jsonify({"new_count": user.vouch_count})

# --- Chat & Rating Routes ---

@app.route("/user/<int:user_id>", methods=['GET', 'POST'])
@login_required
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == user.id)) |
        ((Message.sender_id == user.id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()

    return render_template('user_profile.html', user=user, messages=messages)

@app.route("/send_message/<int:recipient_id>", methods=['POST'])
@login_required
def send_message(recipient_id):
    body = request.form.get('body')
    if body:
        msg = Message(sender_id=current_user.id, recipient_id=recipient_id, body=body)
        db.session.add(msg)
        db.session.commit()
    return redirect(url_for('user_profile', user_id=recipient_id))

@app.route("/rate_user/<int:user_id>", methods=['POST'])
@login_required
def rate_user(user_id):
    score = request.form.get('rating')
    if score:
        existing = Rating.query.filter_by(author_id=current_user.id, rated_user_id=user_id).first()
        if existing:
            existing.score = int(score)
        else:
            new_rating = Rating(score=int(score), author_id=current_user.id, rated_user_id=user_id)
            db.session.add(new_rating)
        db.session.commit()
        flash('Rating submitted!', 'success')
    return redirect(url_for('user_profile', user_id=user_id))

@app.route('/delete_user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": f"User {user_id} deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error deleting user", "error": str(e)}), 500