from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json
from app import db

# Association tables for many-to-many relationships
user_bookmarks = db.Table('user_bookmarks',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('resource_id', db.Integer, db.ForeignKey('resource.id'), primary_key=True)
)

user_badges = db.Table('user_badges',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('badge_id', db.Integer, db.ForeignKey('badge.id'), primary_key=True),
    db.Column('earned_at', db.DateTime, default=datetime.utcnow)
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    track = db.Column(db.String(50))  # Medical, Nursing, Pharmacy
    avatar_url = db.Column(db.String(200))
    bio = db.Column(db.Text)
    total_points = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    progress_records = db.relationship('UserProgress', backref='user', lazy=True, cascade='all, delete-orphan')
    bookmarked_resources = db.relationship('Resource', secondary=user_bookmarks, backref='bookmarked_by')
    earned_badges = db.relationship('Badge', secondary=user_badges, backref='earned_by')
    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_progress_percentage(self, course_id=None):
        """Calculate user's progress percentage"""
        if course_id:
            total_topics = Topic.query.join(Module).filter(Module.course_id == course_id).count()
            completed_topics = UserProgress.query.join(Topic).join(Module).filter(
                Module.course_id == course_id,
                UserProgress.user_id == self.id,
                UserProgress.completed == True
            ).count()
        else:
            total_topics = Topic.query.count()
            completed_topics = UserProgress.query.filter_by(user_id=self.id, completed=True).count()
        
        return (completed_topics / total_topics * 100) if total_topics > 0 else 0

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    track = db.Column(db.String(50), nullable=False)  # Medical, Nursing, Pharmacy
    color = db.Column(db.String(7), default='#1a6ac3')
    icon = db.Column(db.String(50))  # Font Awesome icon class
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    modules = db.relationship('Module', backref='course', lazy=True, cascade='all, delete-orphan')

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    order_index = db.Column(db.Integer, default=0)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    topics = db.relationship('Topic', backref='module', lazy=True, cascade='all, delete-orphan')

class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text)
    summary = db.Column(db.Text)
    illustrations = db.Column(db.Text)  # JSON array of image paths
    youtube_link = db.Column(db.String(200))
    mnemonic = db.Column(db.Text)
    order_index = db.Column(db.Integer, default=0)
    estimated_time = db.Column(db.Integer)  # in minutes
    difficulty_level = db.Column(db.String(20), default='beginner')
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    resources = db.relationship('Resource', backref='topic', lazy=True, cascade='all, delete-orphan')
    progress_records = db.relationship('UserProgress', backref='topic', lazy=True, cascade='all, delete-orphan')
    quizzes = db.relationship('Quiz', backref='topic', lazy=True, cascade='all, delete-orphan')
    flashcards = db.relationship('Flashcard', backref='topic', lazy=True, cascade='all, delete-orphan')

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    resource_type = db.Column(db.String(50), nullable=False)  # pdf, video, image, link, book, article, magazine
    file_path = db.Column(db.String(300))
    external_url = db.Column(db.String(500))
    file_size = db.Column(db.Integer)  # in bytes
    author = db.Column(db.String(100))
    year_published = db.Column(db.Integer)
    tags = db.Column(db.Text)  # JSON string of tags
    download_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    ratings = db.relationship('ResourceRating', backref='resource', lazy=True, cascade='all, delete-orphan')
    
    def get_average_rating(self):
        ratings = [r.rating for r in self.ratings]
        return sum(ratings) / len(ratings) if ratings else 0

class ResourceRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='resource_ratings')

class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    progress_percentage = db.Column(db.Integer, default=0)  # 0-100
    time_spent = db.Column(db.Integer, default=0)  # in minutes
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Unique constraint to prevent duplicate progress records
    __table_args__ = (db.UniqueConstraint('user_id', 'topic_id', name='unique_user_topic_progress'),)

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))  # Font Awesome icon class
    color = db.Column(db.String(7), default='#1a6ac3')
    criteria = db.Column(db.Text)  # JSON string describing criteria
    points_value = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    time_limit = db.Column(db.Integer)  # in minutes
    passing_score = db.Column(db.Integer, default=70)  # percentage
    max_attempts = db.Column(db.Integer, default=3)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('QuizQuestion', backref='quiz', lazy=True, cascade='all, delete-orphan')
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy=True, cascade='all, delete-orphan')

class QuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='multiple_choice')
    options = db.Column(db.Text)  # JSON string for multiple choice options
    correct_answer = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text)
    points = db.Column(db.Integer, default=1)
    order_index = db.Column(db.Integer, default=0)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)

class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    score = db.Column(db.Integer)  # percentage
    answers = db.Column(db.Text)  # JSON string of user answers
    time_taken = db.Column(db.Integer)  # in minutes
    completed = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    front_text = db.Column(db.Text, nullable=False)
    back_text = db.Column(db.Text, nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DrugClass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    mechanism_of_action = db.Column(db.Text)
    indications = db.Column(db.Text)
    contraindications = db.Column(db.Text)
    side_effects = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    drugs = db.relationship('Drug', backref='drug_class', lazy=True, cascade='all, delete-orphan')

class Drug(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    generic_name = db.Column(db.String(150))
    brand_names = db.Column(db.Text)  # JSON array
    description = db.Column(db.Text)
    mechanism_of_action = db.Column(db.Text)
    indications = db.Column(db.Text)
    contraindications = db.Column(db.Text)
    side_effects = db.Column(db.Text)
    dosage_forms = db.Column(db.Text)  # JSON array
    typical_dosage = db.Column(db.Text)
    drug_class_id = db.Column(db.Integer, db.ForeignKey('drug_class.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class NewsArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(50))  # announcement, update, news
    tags = db.Column(db.Text)  # JSON string
    featured_image = db.Column(db.String(300))
    is_published = db.Column(db.Boolean, default=False)
    is_featured = db.Column(db.Boolean, default=False)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime)
    
    # Relationships
    author = db.relationship('User', backref='articles')

class WordOfTheDay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False)
    definition = db.Column(db.Text, nullable=False)
    pronunciation = db.Column(db.String(100))
    example = db.Column(db.Text)
    category = db.Column(db.String(50))  # medical, pharmacy, nursing
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class QuizOfTheDay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=False)  # JSON array
    correct_answer = db.Column(db.String(200), nullable=False)
    explanation = db.Column(db.Text)
    category = db.Column(db.String(50))  # medical, pharmacy, nursing
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FAQ(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))  # general, account, resources, technical
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    replied = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SearchLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    query = db.Column(db.String(500), nullable=False)
    results_count = db.Column(db.Integer, default=0)
    clicked_result_id = db.Column(db.Integer)
    search_type = db.Column(db.String(20), default='general')  # general, ai
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='search_logs')
