from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models.models import db, User
from datetime import datetime
import re

auth_bp = Blueprint('auth', __name__)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    return True, ""

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        remember = data.get('remember', False)
        
        # Validation
        if not email or not password:
            error = 'Email and password are required'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 400
            flash(error, 'error')
            return render_template('auth/login.html')
        
        if not validate_email(email):
            error = 'Please enter a valid email address'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 400
            flash(error, 'error')
            return render_template('auth/login.html')
        
        # Find user and verify password
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=remember)
            
            if request.is_json:
                redirect_url = url_for('admin.dashboard') if user.is_admin else url_for('user.dashboard')
                return jsonify({
                    'success': True, 
                    'message': 'Login successful',
                    'redirect_url': redirect_url,
                    'is_admin': user.is_admin
                })
            
            flash('Welcome back!', 'success')
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('user.dashboard'))
        else:
            error = 'Invalid email or password'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 401
            flash(error, 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        track = data.get('track', '')
        
        # Validation
        errors = []
        
        if not name:
            errors.append('Full name is required')
        elif len(name) < 2:
            errors.append('Name must be at least 2 characters long')
        
        if not email:
            errors.append('Email is required')
        elif not validate_email(email):
            errors.append('Please enter a valid email address')
        elif User.query.filter_by(email=email).first():
            errors.append('Email already registered')
        
        if not password:
            errors.append('Password is required')
        else:
            valid, error_msg = validate_password(password)
            if not valid:
                errors.append(error_msg)
        
        if password != confirm_password:
            errors.append('Passwords do not match')
        
        if not track or track not in ['Medical', 'Nursing', 'Pharmacy']:
            errors.append('Please select a valid track')
        
        if errors:
            if request.is_json:
                return jsonify({'success': False, 'message': '; '.join(errors)}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('auth/login.html')
        
        # Create new user
        try:
            user = User(
                name=name,
                email=email,
                track=track,
                is_admin=False
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            # Auto-login after registration
            login_user(user)
            
            if request.is_json:
                return jsonify({
                    'success': True, 
                    'message': 'Registration successful! Welcome to TAMSA Library.',
                    'redirect_url': url_for('user.dashboard')
                })
            
            flash('Registration successful! Welcome to TAMSA Library.', 'success')
            return redirect(url_for('user.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            error = 'Registration failed. Please try again.'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 500
            flash(error, 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email or not validate_email(email):
            flash('Please enter a valid email address', 'error')
            return render_template('auth/forgot_password.html')
        
        user = User.query.filter_by(email=email).first()
        if user:
            # In a real application, you would send a password reset email here
            # For now, we'll just show a success message
            flash('If an account with that email exists, password reset instructions have been sent.', 'info')
        else:
            flash('If an account with that email exists, password reset instructions have been sent.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')

@auth_bp.route('/check-email')
def check_email():
    """AJAX endpoint to check if email is available"""
    email = request.args.get('email', '').strip().lower()
    
    if not email or not validate_email(email):
        return jsonify({'available': False, 'message': 'Invalid email format'})
    
    user = User.query.filter_by(email=email).first()
    if user:
        return jsonify({'available': False, 'message': 'Email already registered'})
    
    return jsonify({'available': True, 'message': 'Email is available'})
