from flask import render_template, url_for, flash, redirect, request, jsonify
from app import app, db, bcrypt, mail
from app.forms import RegistrationForm, LoginForm, RequestResetForm, ResetPasswordForm
from app.models import User, Request 
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message

@app.route("/")
@app.route("/home")
def home():
    all_users = User.query.all()
    all_requests = Request.query.order_by(Request.date_posted.desc()).all()
    return render_template('home.html', title='Home', profiles=all_users, requests=all_requests)

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
        flash('Account created! Please check your email to verify your account.', 'info')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

def send_verification_email(user):
    token = user.get_reset_token() 
    link = url_for('confirm_email', token=token, _external=True)
    
    msg = Message('Skills Exchange: Verify your account', 
                  sender=app.config['MAIL_USERNAME'], 
                  recipients=[user.email])
    
    # Plain text version
    msg.body = f"Hey {user.username}! Verify your account here: {link}"
    
    # GitHub-style HTML version
    msg.html = f'''
        <div style="font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif; padding: 24px; color: #24292e; line-height: 1.5;">
            <h2 style="font-size: 20px; font-weight: 600; margin-bottom: 16px;">Hey {user.username}!</h2>
            
            <p style="margin-bottom: 16px;">A sign in attempt requires further verification because we did not recognize your device. To complete the sign in and verify your account, click the link below:</p>
            
            <div style="background-color: #f6f8fa; border: 1px solid #e1e4e8; padding: 20px; border-radius: 6px; margin-bottom: 16px; text-align: center;">
                <p style="margin: 0 0 10px 0; color: #586069; font-size: 12px; text-align: left;">Device: Chrome on Windows</p>
                <a href="{link}" 
                   style="display: inline-block; background-color: #2ea44f; color: #ffffff; padding: 12px 24px; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 6px;">
                   Verify Account & Device
                </a>
                <p style="margin-top: 15px; font-size: 12px; color: #586069;">This link will expire in 30 minutes.</p>
            </div>

            <p style="font-size: 14px; color: #586069; margin-bottom: 16px;">
                If you did not attempt to sign in to your account, your password may be compromised. Visit the Skills Exchange security settings to create a new, strong password.
            </p>

            <p style="font-size: 14px; color: #586069; margin-bottom: 24px;">
                If you'd like to automatically verify devices in the future, consider enabling two-factor authentication on your account.
            </p>

            <p style="border-top: 1px solid #e1e4e8; padding-top: 16px; color: #586069; font-size: 14px;">
                Thanks,<br>
                <strong>The Skills Exchange Team</strong>
            </p>
        </div>
    '''
    mail.send(msg)
    token = user.get_reset_token() 
    msg = Message('Verify your account on Skills Exchange', 
                  sender=app.config['MAIL_USERNAME'], 
                  recipients=[user.email])
    link = url_for('confirm_email', token=token, _external=True)
    msg.body = f"Please verify your account using this link: {link}"
    msg.html = f'''
        <div style="font-family: sans-serif; padding: 20px; border: 1px solid #2a7a58;">
            <h2 style="color: #2a7a58;">Skills Exchange</h2>
            <p>Please verify your account using this link: <a href="{link}">Verify Now</a></p>
            <p><small>Ignore this email if it wasn't you.</small></p>
        </div>
    '''
    mail.send(msg)

@app.route("/confirm_email/<token>")
def confirm_email(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired verification link.', 'warning')
        return redirect(url_for('register'))
    if not user.confirmed:
        user.confirmed = True
        db.session.commit()
        flash('Verification successful! You can now log in.', 'success')
    else:
        flash('Account already verified.', 'info')
    return redirect(url_for('login'))

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request', sender=app.config['MAIL_USERNAME'], recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
'''
    mail.send(msg)

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

@app.route("/create_profile", methods=['GET', 'POST'])
@login_required 
def create_profile():
    if request.method == 'POST':
        current_user.headline = request.form.get('headline')
        current_user.bio = request.form.get('bio')
        current_user.skill_cat = request.form.get('skill_cat')
        current_user.skill_level = request.form.get('level')
        current_user.phone = request.form.get('phone')
        db.session.commit()
        flash('Your profile has been completed!', 'success')
        return redirect(url_for('home'))
    full_name = f"{current_user.first_name} {current_user.last_name}"
    return render_template('create_profile.html', title='Complete Profile', user=current_user, full_name=full_name)

@app.route('/save-profile', methods=['POST'])
@login_required
def save_profile():
    headline = request.form.get('headline')
    bio = request.form.get('bio')
    skill_cat = request.form.get('skill_cat')
    if headline: current_user.headline = headline
    if bio: current_user.bio = bio
    if skill_cat: current_user.skill_cat = skill_cat
    db.session.commit()
    return jsonify({"status": "success", "message": "Saved successfully!"}), 200

@app.route('/post-request', methods=['POST'])
@login_required
def post_request():
    title = request.form.get('req_title')
    category = request.form.get('req_category')
    offer = request.form.get('req_offer')
    details = request.form.get('req_details')
    new_request = Request(title=title, category=category, offer=offer, details=details, author=current_user)
    db.session.add(new_request)
    db.session.commit()
    return jsonify({"status": "success"}), 200

    