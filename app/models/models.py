# Placeholder for DB models
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    name = db.Column(db.String(100))
    password = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    modules = db.relationship('Module', backref='course', lazy=True)

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    topics = db.relationship('Topic', backref='module', lazy=True)

class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    content = db.Column(db.Text)
    summary = db.Column(db.Text)
    youtube_link = db.Column(db.String(200))
    pdf_path = db.Column(db.String(200))
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
