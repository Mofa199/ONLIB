from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from .models import db, User, Topic, Module
from .forms import LoginForm, RegisterForm, TopicForm
from .auth import hash_password, verify_password
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['UPLOAD_FOLDER'] = 'uploads'

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data,
            email=form.email.data,
            password=hash_password(form.password.data),
            is_admin=False
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful')
        return redirect(url_for('login'))
    return render_template('auth/register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and verify_password(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid login')
    return render_template('auth/login.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return render_template('admin/dashboard.html')
    return render_template('user/dashboard.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin/add-topic', methods=['GET', 'POST'])
@login_required
def add_topic():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    form = TopicForm()
    if form.validate_on_submit():
        topic = Topic(
            title=form.title.data,
            content=form.content.data,
            summary=form.summary.data,
            youtube_link=form.youtube_link.data,
            module_id=1  # placeholder
        )
        # Handle PDF file
        pdf = request.files['pdf_file']
        if pdf:
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf.filename)
            pdf.save(pdf_path)
            topic.pdf_path = pdf.filename
        db.session.add(topic)
        db.session.commit()
        flash('Topic added!')
        return redirect(url_for('dashboard'))
    return render_template('admin/add_topic.html', form=form)
