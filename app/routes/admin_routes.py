from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from app.models.models import (db, User, Course, Module, Topic, Resource, Quiz, QuizQuestion, 
                              Flashcard, DrugClass, Drug, NewsArticle, WordOfTheDay, QuizOfTheDay, 
                              FAQ, ContactMessage, Badge, UserProgress)
from datetime import datetime, date
from werkzeug.utils import secure_filename
import os
import json

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin access"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get statistics
    stats = {
        'total_users': User.query.count(),
        'total_courses': Course.query.count(),
        'total_modules': Module.query.count(),
        'total_topics': Topic.query.count(),
        'total_resources': Resource.query.count(),
        'active_users': User.query.filter(User.last_login.isnot(None)).count(),
        'pending_messages': ContactMessage.query.filter_by(is_read=False).count()
    }
    
    # Get recent activities
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_resources = Resource.query.order_by(Resource.created_at.desc()).limit(5).all()
    recent_messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(5).all()
    
    # Get user distribution by track
    user_distribution = db.session.query(User.track, db.func.count(User.id))\
        .group_by(User.track).all()
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_users=recent_users,
                         recent_resources=recent_resources,
                         recent_messages=recent_messages,
                         user_distribution=user_distribution)

# User Management
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    track = request.args.get('track', '')
    
    query = User.query
    
    if search:
        query = query.filter(
            db.or_(
                User.name.contains(search),
                User.email.contains(search)
            )
        )
    
    if track:
        query = query.filter_by(track=track)
    
    users = query.order_by(User.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    
    tracks = ['Medical', 'Nursing', 'Pharmacy']
    
    return render_template('admin/users.html',
                         users=users,
                         tracks=tracks,
                         current_search=search,
                         current_track=track)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        track = data.get('track', '')
        is_admin = data.get('is_admin', False)
        
        errors = []
        
        if not name:
            errors.append('Name is required')
        if not email:
            errors.append('Email is required')
        if User.query.filter_by(email=email).first():
            errors.append('Email already exists')
        if not password:
            errors.append('Password is required')
        if not track or track not in ['Medical', 'Nursing', 'Pharmacy']:
            errors.append('Valid track is required')
        
        if errors:
            if request.is_json:
                return jsonify({'success': False, 'message': '; '.join(errors)}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('admin/add_user.html')
        
        try:
            user = User(
                name=name,
                email=email,
                track=track,
                is_admin=bool(is_admin)
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'User created successfully'})
            
            flash('User created successfully!', 'success')
            return redirect(url_for('admin.users'))
            
        except Exception as e:
            db.session.rollback()
            error = 'Failed to create user'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 500
            flash(error, 'error')
    
    return render_template('admin/add_user.html')

# Course Management
@admin_bp.route('/courses')
@login_required
@admin_required
def courses():
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('admin/courses.html', courses=courses)

@admin_bp.route('/courses/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_course():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        track = data.get('track', '')
        color = data.get('color', '#1a6ac3')
        icon = data.get('icon', 'fas fa-book')
        
        errors = []
        
        if not name:
            errors.append('Course name is required')
        if not track or track not in ['Medical', 'Nursing', 'Pharmacy']:
            errors.append('Valid track is required')
        
        if errors:
            if request.is_json:
                return jsonify({'success': False, 'message': '; '.join(errors)}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('admin/add_course.html')
        
        try:
            course = Course(
                name=name,
                description=description,
                track=track,
                color=color,
                icon=icon
            )
            
            db.session.add(course)
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Course created successfully'})
            
            flash('Course created successfully!', 'success')
            return redirect(url_for('admin.courses'))
            
        except Exception as e:
            db.session.rollback()
            error = 'Failed to create course'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 500
            flash(error, 'error')
    
    return render_template('admin/add_course.html')

@admin_bp.route('/courses/<int:course_id>/modules')
@login_required
@admin_required
def course_modules(course_id):
    course = Course.query.get_or_404(course_id)
    modules = Module.query.filter_by(course_id=course_id).order_by(Module.order_index).all()
    return render_template('admin/course_modules.html', course=course, modules=modules)

@admin_bp.route('/modules/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_module():
    course_id = request.args.get('course_id', type=int)
    course = Course.query.get_or_404(course_id) if course_id else None
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        course_id = data.get('course_id', type=int)
        order_index = data.get('order_index', 0, type=int)
        
        if not name or not course_id:
            error = 'Module name and course are required'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 400
            flash(error, 'error')
            return render_template('admin/add_module.html', course=course)
        
        try:
            module = Module(
                name=name,
                description=description,
                course_id=course_id,
                order_index=order_index
            )
            
            db.session.add(module)
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Module created successfully'})
            
            flash('Module created successfully!', 'success')
            return redirect(url_for('admin.course_modules', course_id=course_id))
            
        except Exception as e:
            db.session.rollback()
            error = 'Failed to create module'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 500
            flash(error, 'error')
    
    courses = Course.query.all()
    return render_template('admin/add_module.html', courses=courses, course=course)

@admin_bp.route('/modules/<int:module_id>/topics')
@login_required
@admin_required
def module_topics(module_id):
    module = Module.query.get_or_404(module_id)
    topics = Topic.query.filter_by(module_id=module_id).order_by(Topic.order_index).all()
    return render_template('admin/module_topics.html', module=module, topics=topics)

@admin_bp.route('/topics/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_topic():
    module_id = request.args.get('module_id', type=int)
    module = Module.query.get_or_404(module_id) if module_id else None
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        summary = data.get('summary', '').strip()
        youtube_link = data.get('youtube_link', '').strip()
        mnemonic = data.get('mnemonic', '').strip()
        module_id = data.get('module_id', type=int)
        order_index = data.get('order_index', 0, type=int)
        estimated_time = data.get('estimated_time', type=int)
        difficulty_level = data.get('difficulty_level', 'beginner')
        
        if not title or not module_id:
            error = 'Topic title and module are required'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 400
            flash(error, 'error')
            return render_template('admin/add_topic.html', module=module)
        
        try:
            topic = Topic(
                title=title,
                content=content,
                summary=summary,
                youtube_link=youtube_link,
                mnemonic=mnemonic,
                module_id=module_id,
                order_index=order_index,
                estimated_time=estimated_time,
                difficulty_level=difficulty_level
            )
            
            db.session.add(topic)
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Topic created successfully'})
            
            flash('Topic created successfully!', 'success')
            return redirect(url_for('admin.module_topics', module_id=module_id))
            
        except Exception as e:
            db.session.rollback()
            error = 'Failed to create topic'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 500
            flash(error, 'error')
    
    modules = Module.query.all()
    return render_template('admin/add_topic.html', modules=modules, module=module)

# Resource Management
@admin_bp.route('/resources')
@login_required
@admin_required
def resources():
    page = request.args.get('page', 1, type=int)
    resource_type = request.args.get('type', '')
    
    query = Resource.query
    
    if resource_type:
        query = query.filter_by(resource_type=resource_type)
    
    resources = query.order_by(Resource.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    
    resource_types = ['book', 'article', 'magazine', 'pdf', 'video', 'image', 'link']
    
    return render_template('admin/resources.html',
                         resources=resources,
                         resource_types=resource_types,
                         current_type=resource_type)

@admin_bp.route('/resources/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_resource():
    if request.method == 'POST':
        data = request.form  # Handle file uploads with form data
        
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        resource_type = data.get('resource_type', '')
        external_url = data.get('external_url', '').strip()
        author = data.get('author', '').strip()
        year_published = data.get('year_published', type=int)
        topic_id = data.get('topic_id', type=int)
        
        file = request.files.get('file')
        
        errors = []
        
        if not title:
            errors.append('Title is required')
        if not resource_type:
            errors.append('Resource type is required')
        if not file and not external_url:
            errors.append('Either file or external URL is required')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            topics = Topic.query.all()
            return render_template('admin/add_resource.html', topics=topics)
        
        try:
            resource = Resource(
                title=title,
                description=description,
                resource_type=resource_type,
                external_url=external_url,
                author=author,
                year_published=year_published,
                topic_id=topic_id,
                uploaded_by=current_user.id
            )
            
            # Handle file upload
            if file and file.filename:
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                resource.file_path = filename
                resource.file_size = os.path.getsize(file_path)
            
            db.session.add(resource)
            db.session.commit()
            
            flash('Resource added successfully!', 'success')
            return redirect(url_for('admin.resources'))
            
        except Exception as e:
            db.session.rollback()
            flash('Failed to add resource', 'error')
    
    topics = Topic.query.all()
    resource_types = ['book', 'article', 'magazine', 'pdf', 'video', 'image', 'link']
    return render_template('admin/add_resource.html', topics=topics, resource_types=resource_types)

# News Management
@admin_bp.route('/news')
@login_required
@admin_required
def news():
    articles = NewsArticle.query.order_by(NewsArticle.created_at.desc()).all()
    return render_template('admin/news.html', articles=articles)

@admin_bp.route('/news/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_news():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        summary = data.get('summary', '').strip()
        category = data.get('category', '')
        is_published = data.get('is_published', False)
        is_featured = data.get('is_featured', False)
        
        if not title or not content:
            error = 'Title and content are required'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 400
            flash(error, 'error')
            return render_template('admin/add_news.html')
        
        try:
            article = NewsArticle(
                title=title,
                content=content,
                summary=summary,
                author_id=current_user.id,
                category=category,
                is_published=bool(is_published),
                is_featured=bool(is_featured),
                published_at=datetime.utcnow() if is_published else None
            )
            
            db.session.add(article)
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Article created successfully'})
            
            flash('Article created successfully!', 'success')
            return redirect(url_for('admin.news'))
            
        except Exception as e:
            db.session.rollback()
            error = 'Failed to create article'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 500
            flash(error, 'error')
    
    categories = ['announcement', 'update', 'news', 'event']
    return render_template('admin/add_news.html', categories=categories)

# Daily Content Management
@admin_bp.route('/daily-content')
@login_required
@admin_required
def daily_content():
    today = date.today()
    
    word_today = WordOfTheDay.query.filter_by(date=today).first()
    quiz_today = QuizOfTheDay.query.filter_by(date=today).first()
    
    recent_words = WordOfTheDay.query.order_by(WordOfTheDay.date.desc()).limit(10).all()
    recent_quizzes = QuizOfTheDay.query.order_by(QuizOfTheDay.date.desc()).limit(10).all()
    
    return render_template('admin/daily_content.html',
                         word_today=word_today,
                         quiz_today=quiz_today,
                         recent_words=recent_words,
                         recent_quizzes=recent_quizzes)

@admin_bp.route('/daily-content/word', methods=['POST'])
@login_required
@admin_required
def add_word_of_day():
    data = request.get_json() if request.is_json else request.form
    
    word = data.get('word', '').strip()
    definition = data.get('definition', '').strip()
    pronunciation = data.get('pronunciation', '').strip()
    example = data.get('example', '').strip()
    category = data.get('category', 'medical')
    word_date = data.get('date')
    
    if not word or not definition:
        error = 'Word and definition are required'
        if request.is_json:
            return jsonify({'success': False, 'message': error}), 400
        flash(error, 'error')
        return redirect(url_for('admin.daily_content'))
    
    try:
        if word_date:
            word_date = datetime.strptime(word_date, '%Y-%m-%d').date()
        else:
            word_date = date.today()
        
        # Check if word already exists for this date
        existing = WordOfTheDay.query.filter_by(date=word_date).first()
        if existing:
            existing.word = word
            existing.definition = definition
            existing.pronunciation = pronunciation
            existing.example = example
            existing.category = category
        else:
            word_entry = WordOfTheDay(
                word=word,
                definition=definition,
                pronunciation=pronunciation,
                example=example,
                category=category,
                date=word_date
            )
            db.session.add(word_entry)
        
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Word of the day saved successfully'})
        
        flash('Word of the day saved successfully!', 'success')
        return redirect(url_for('admin.daily_content'))
        
    except Exception as e:
        db.session.rollback()
        error = 'Failed to save word of the day'
        if request.is_json:
            return jsonify({'success': False, 'message': error}), 500
        flash(error, 'error')
        return redirect(url_for('admin.daily_content'))

# Contact Messages
@admin_bp.route('/messages')
@login_required
@admin_required
def messages():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    
    query = ContactMessage.query
    
    if status == 'unread':
        query = query.filter_by(is_read=False)
    elif status == 'read':
        query = query.filter_by(is_read=True)
    
    messages = query.order_by(ContactMessage.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    
    return render_template('admin/messages.html', messages=messages, current_status=status)

@admin_bp.route('/messages/<int:message_id>/mark-read', methods=['POST'])
@login_required
@admin_required
def mark_message_read(message_id):
    message = ContactMessage.query.get_or_404(message_id)
    message.is_read = True
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except:
        db.session.rollback()
        return jsonify({'success': False}), 500

# FAQ Management
@admin_bp.route('/faq')
@login_required
@admin_required
def faq_admin():
    faqs = FAQ.query.order_by(FAQ.order_index, FAQ.id).all()
    return render_template('admin/faq.html', faqs=faqs)

@admin_bp.route('/faq/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_faq():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        question = data.get('question', '').strip()
        answer = data.get('answer', '').strip()
        category = data.get('category', 'general')
        order_index = data.get('order_index', 0, type=int)
        
        if not question or not answer:
            error = 'Question and answer are required'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 400
            flash(error, 'error')
            return render_template('admin/add_faq.html')
        
        try:
            faq = FAQ(
                question=question,
                answer=answer,
                category=category,
                order_index=order_index
            )
            
            db.session.add(faq)
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'FAQ added successfully'})
            
            flash('FAQ added successfully!', 'success')
            return redirect(url_for('admin.faq_admin'))
            
        except Exception as e:
            db.session.rollback()
            error = 'Failed to add FAQ'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 500
            flash(error, 'error')
    
    categories = ['general', 'account', 'resources', 'technical']
    return render_template('admin/add_faq.html', categories=categories)
