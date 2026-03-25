import os
import secrets
import random
from datetime import datetime
from urllib.parse import urlparse
from flask import render_template, url_for, flash, redirect, request, jsonify
from app import app, db, bcrypt, mail
from app.forms import RegistrationForm, LoginForm, RequestResetForm, ResetPasswordForm
from app.models import User, Request, Message, Rating
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message as MailMessage
from sqlalchemy import func

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
    code = f"{random.randint(100000, 999999)}"
    user.verification_code = code
    db.session.commit()
    
    msg = MailMessage(
        'Your Skills Exchange Verification Code',
        sender=app.config['MAIL_USERNAME'],
        recipients=[user.email]
    )
    msg.html = f"""
        <div style="font-family: sans-serif; padding: 20px; border: 1px solid #eee; max-width: 500px;">
            <h2 style="color: #2a7a58;">Verify Your Account</h2>
            <p>Thanks for joining the Skills Exchange community! Please use the code below to verify your email:</p>
            <div style="background: #f4f7f6; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #2a7a58; border-radius: 10px; margin: 20px 0;">
                {code}
            </div>
        </div>
    """
    mail.send(msg)

def send_reset_email(user):
    token = user.get_reset_token()
    msg = MailMessage('Password Reset Request',
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email.
'''
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
    member_count = User.query.count()
    avg_rating_value = db.session.query(func.avg(Rating.score)).scalar()
    avg_rating = round(float(avg_rating_value), 1) if avg_rating_value else 5.0 

    return render_template('home.html', title='Home', profiles=all_users, requests=all_requests, member_count=member_count, avg_rating=avg_rating)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(first_name=form.first_name.data, last_name=form.last_name.data, 
                    username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        send_verification_email(user)
        flash('Account created! We have sent a 6-digit code to your email.', 'success')
        return redirect(url_for('verify_code'))
    return render_template('register.html', title='Register', form=form)

@app.route("/verify_code", methods=['GET', 'POST'])
def verify_code():
    if request.method == 'POST':
        email = request.form.get('email')
        code = request.form.get('code')
        user = User.query.filter_by(email=email).first()
        if user and user.verification_code == code:
            user.confirmed = True
            user.verification_code = None
            db.session.commit()
            flash('Account verified! You can now log in.', 'success')
            return redirect(url_for('login'))
        flash('Invalid code or email.', 'danger')
    return render_template('verify_code.html', title='Verify Code')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            if not user.confirmed:
                flash('Please verify your email address.', 'warning')
                return redirect(url_for('verify_code'))
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            if next_page and urlparse(next_page).netloc == '':
                return redirect(next_page)
            return redirect(url_for('home'))
        flash('Login Unsuccessful. Check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- Password Reset Routes ---

@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)

@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated!', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)

# --- User Profile Management ---



@app.route("/user/<int:user_id>")
@login_required
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    # Fetch messages between current_user and this profile's user
    chat_history = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == user.id)) |
        ((Message.sender_id == user.id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()
    
    return render_template('user_profile.html', title=f"{user.username}'s Profile", 
                           user=user, chat_history=chat_history)

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

@app.route('/post-request', methods=['POST'])
@login_required
def post_request():
    new_request = Request(title=request.form.get('req_title'), 
                          category=request.form.get('req_category'), 
                          offer=request.form.get('req_offer'), 
                          details=request.form.get('req_details'), author=current_user)
    db.session.add(new_request)
    db.session.commit()
    flash("Request posted successfully!", "success")
    return redirect(url_for('home'))

@app.route("/dashboard")
@login_required
def dashboard():
    my_requests = Request.query.filter_by(user_id=current_user.id).order_by(Request.date_posted.desc()).all()
    return render_template('dashboard.html', title='My Dashboard', requests=my_requests)

@app.route("/send_message/<int:recipient_id>", methods=['POST'])
@login_required
def send_message(recipient_id):
    recipient = User.query.get_or_404(recipient_id)
    # Get the text from the HTML form input named 'message_content'
    message_body = request.form.get('message_content')
    
    if message_body:
        # We use 'body=' here because that is the column name in models.py
        msg = Message(
            sender_id=current_user.id, 
            recipient_id=recipient.id, 
            body=message_body
        )
        db.session.add(msg)
        db.session.commit()
        flash('Your message has been sent!', 'success')
    else:
        flash('Message cannot be empty.', 'danger')
        
    return redirect(url_for('user_profile', user_id=recipient_id))
@app.route("/inbox")
@login_required
def inbox():
    # Find all unique users the current user has messaged or received messages from
    sent_to = db.session.query(Message.recipient_id).filter(Message.sender_id == current_user.id)
    received_from = db.session.query(Message.sender_id).filter(Message.recipient_id == current_user.id)
    
    # Combine the IDs and get the User objects
    user_ids = sent_to.union(received_from).all()
    unique_ids = [uid[0] for uid in user_ids]
    
    chat_partners = User.query.filter(User.id.in_(unique_ids)).all()
    
    return render_template('inbox.html', title='My Messages', chat_partners=chat_partners)

@app.route("/delete_request/<int:request_id>", methods=['POST'])
@login_required
def delete_request(request_id):
    req = Request.query.get_or_404(request_id)
    if req.author != current_user:
        flash('You do not have permission to delete this.', 'danger')
        return redirect(url_for('dashboard'))
    db.session.delete(req)
    db.session.commit()
    flash('Your request has been deleted!', 'success')
    return redirect(url_for('dashboard'))