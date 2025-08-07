from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import current_user, login_required
from app.models.models import db, Course, NewsArticle, WordOfTheDay, QuizOfTheDay, FAQ, ContactMessage, Resource, Topic
from datetime import date, datetime
import json

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Redirect unauthenticated users to login page
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    # Get featured content for home page
    featured_courses = Course.query.filter_by(is_active=True).limit(3).all()
    latest_news = NewsArticle.query.filter_by(is_published=True)\
        .order_by(NewsArticle.published_at.desc()).limit(3).all()
    
    # Get word of the day
    today = date.today()
    word_of_day = WordOfTheDay.query.filter_by(date=today).first()
    
    # Get popular resources
    popular_resources = Resource.query.filter_by(is_active=True)\
        .order_by(Resource.view_count.desc()).limit(6).all()
    
    # Statistics for the homepage
    stats = {
        'total_courses': Course.query.filter_by(is_active=True).count(),
        'total_topics': Topic.query.filter_by(is_active=True).count(),
        'total_resources': Resource.query.filter_by(is_active=True).count(),
        'active_users': db.session.query(db.func.count(db.distinct(db.text('user_progress.user_id'))))\
            .select_from(db.text('user_progress')).scalar() or 0
    }
    
    return render_template('main/index.html',
                         featured_courses=featured_courses,
                         latest_news=latest_news,
                         word_of_day=word_of_day,
                         popular_resources=popular_resources,
                         stats=stats)

@main_bp.route('/home')
@login_required
def home():
    # Alternative route for home page (authenticated users only)
    return redirect(url_for('main.index'))

@main_bp.route('/about')
def about():
    # Team members data (in a real app, this would come from database)
    team_members = [
        {
            'name': 'Dr. Sarah Johnson',
            'position': 'Chief Medical Officer',
            'bio': 'Leading expert in medical education with 15+ years of experience.',
            'image': 'team-1.jpg',
            'linkedin': '#',
            'email': 'sarah@medicore.com'
        },
        {
            'name': 'Prof. Michael Chen',
            'position': 'Director of Pharmacy Education',
            'bio': 'Renowned pharmacologist and educator specializing in clinical pharmacy.',
            'image': 'team-2.jpg',
            'linkedin': '#',
            'email': 'michael@medicore.com'
        },
        {
            'name': 'Dr. Emily Rodriguez',
            'position': 'Head of Nursing Programs',
            'bio': 'Experienced nurse educator with expertise in evidence-based practice.',
            'image': 'team-3.jpg',
            'linkedin': '#',
            'email': 'emily@medicore.com'
        }
    ]
    
    # Partners data
    partners = [
        {'name': 'University of Medical Sciences', 'logo': 'partner-1.png'},
        {'name': 'Global Health Institute', 'logo': 'partner-2.png'},
        {'name': 'Medical Publishers Alliance', 'logo': 'partner-3.png'},
        {'name': 'Healthcare Innovation Hub', 'logo': 'partner-4.png'}
    ]
    
    return render_template('main/about.html', 
                         team_members=team_members, 
                         partners=partners)

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        subject = data.get('subject', '').strip()
        message = data.get('message', '').strip()
        
        errors = []
        
        if not name:
            errors.append('Name is required')
        if not email:
            errors.append('Email is required')
        if not subject:
            errors.append('Subject is required')
        if not message:
            errors.append('Message is required')
        
        if errors:
            if request.is_json:
                return jsonify({'success': False, 'message': '; '.join(errors)}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('main/contact.html')
        
        try:
            contact_message = ContactMessage(
                name=name,
                email=email,
                subject=subject,
                message=message
            )
            db.session.add(contact_message)
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Message sent successfully! We\'ll get back to you soon.'})
            
            flash('Message sent successfully! We\'ll get back to you soon.', 'success')
            return redirect(url_for('main.contact'))
            
        except Exception as e:
            db.session.rollback()
            error = 'Failed to send message. Please try again.'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 500
            flash(error, 'error')
    
    return render_template('main/contact.html')

@main_bp.route('/faq')
def faq():
    # Get FAQs organized by category
    faq_categories = {}
    faqs = FAQ.query.filter_by(is_active=True).order_by(FAQ.order_index, FAQ.id).all()
    
    for faq in faqs:
        category = faq.category or 'general'
        if category not in faq_categories:
            faq_categories[category] = []
        faq_categories[category].append(faq)
    
    return render_template('main/faq.html', faq_categories=faq_categories)

@main_bp.route('/news')
def news():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    
    query = NewsArticle.query.filter_by(is_published=True)
    
    if category:
        query = query.filter_by(category=category)
    
    news_articles = query.order_by(NewsArticle.published_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    
    # Get available categories
    categories = db.session.query(NewsArticle.category)\
        .filter(NewsArticle.is_published == True)\
        .distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    return render_template('main/news.html', 
                         news_articles=news_articles,
                         categories=categories,
                         current_category=category)

@main_bp.route('/news/<int:article_id>')
def news_article(article_id):
    article = NewsArticle.query.filter_by(id=article_id, is_published=True).first_or_404()
    
    # Increment view count
    article.view_count += 1
    db.session.commit()
    
    # Get related articles
    related_articles = NewsArticle.query\
        .filter(NewsArticle.id != article_id, NewsArticle.is_published == True)\
        .order_by(NewsArticle.published_at.desc()).limit(3).all()
    
    return render_template('main/news_article.html', 
                         article=article,
                         related_articles=related_articles)

@main_bp.route('/search')
def search():
    query = request.args.get('q', '').strip()
    category = request.args.get('category', 'all')
    page = request.args.get('page', 1, type=int)
    
    results = []
    total_results = 0
    
    if query:
        # Search in resources
        if category in ['all', 'resources']:
            resource_results = Resource.query.filter(
                db.or_(
                    Resource.title.contains(query),
                    Resource.description.contains(query),
                    Resource.author.contains(query)
                ),
                Resource.is_active == True
            ).all()
            
            for resource in resource_results:
                results.append({
                    'type': 'resource',
                    'title': resource.title,
                    'description': resource.description,
                    'url': url_for('library.resource_detail', resource_id=resource.id),
                    'author': resource.author,
                    'created_at': resource.created_at
                })
        
        # Search in topics
        if category in ['all', 'topics']:
            topic_results = Topic.query.filter(
                db.or_(
                    Topic.title.contains(query),
                    Topic.content.contains(query),
                    Topic.summary.contains(query)
                ),
                Topic.is_active == True
            ).all()
            
            for topic in topic_results:
                results.append({
                    'type': 'topic',
                    'title': topic.title,
                    'description': topic.summary or topic.content[:200] + '...' if topic.content else '',
                    'url': url_for('course.topic_detail', topic_id=topic.id),
                    'module': topic.module.name,
                    'created_at': topic.created_at
                })
        
        # Search in news articles
        if category in ['all', 'news']:
            news_results = NewsArticle.query.filter(
                db.or_(
                    NewsArticle.title.contains(query),
                    NewsArticle.content.contains(query),
                    NewsArticle.summary.contains(query)
                ),
                NewsArticle.is_published == True
            ).all()
            
            for article in news_results:
                results.append({
                    'type': 'news',
                    'title': article.title,
                    'description': article.summary or article.content[:200] + '...' if article.content else '',
                    'url': url_for('main.news_article', article_id=article.id),
                    'author': article.author.name,
                    'created_at': article.published_at or article.created_at
                })
        
        total_results = len(results)
        
        # Sort results by relevance (for now, just by date)
        results.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Log search for analytics (if user is logged in)
        if current_user.is_authenticated:
            from app.models.models import SearchLog
            search_log = SearchLog(
                user_id=current_user.id,
                query=query,
                results_count=total_results,
                search_type='general'
            )
            db.session.add(search_log)
            db.session.commit()
    
    return render_template('main/search.html',
                         query=query,
                         results=results,
                         total_results=total_results,
                         category=category)

@main_bp.route('/word-of-the-day')
def word_of_the_day():
    today = date.today()
    word = WordOfTheDay.query.filter_by(date=today).first()
    
    # Get previous words
    previous_words = WordOfTheDay.query.filter(WordOfTheDay.date < today)\
        .order_by(WordOfTheDay.date.desc()).limit(10).all()
    
    return render_template('main/word_of_the_day.html',
                         word=word,
                         previous_words=previous_words)

@main_bp.route('/quiz-of-the-day')
def quiz_of_the_day():
    today = date.today()
    quiz = QuizOfTheDay.query.filter_by(date=today).first()
    
    return render_template('main/quiz_of_the_day.html', quiz=quiz)

@main_bp.route('/privacy-policy')
def privacy_policy():
    return render_template('main/privacy_policy.html')

@main_bp.route('/terms-of-service')
def terms_of_service():
    return render_template('main/terms_of_service.html')

@main_bp.route('/api/stats')
def api_stats():
    """API endpoint for getting site statistics"""
    stats = {
        'total_courses': Course.query.filter_by(is_active=True).count(),
        'total_topics': Topic.query.filter_by(is_active=True).count(),
        'total_resources': Resource.query.filter_by(is_active=True).count(),
        'total_users': db.session.query(db.func.count(db.distinct(db.text('user.id'))))\
            .select_from(db.text('user')).scalar() or 0
    }
    
    return jsonify(stats)

@main_bp.route('/api/word-of-the-day')
def api_word_of_the_day():
    """API endpoint for getting word of the day"""
    today = date.today()
    word = WordOfTheDay.query.filter_by(date=today).first()
    
    if word:
        return jsonify({
            'word': word.word,
            'definition': word.definition,
            'pronunciation': word.pronunciation,
            'example': word.example,
            'category': word.category
        })
    
    return jsonify({'error': 'No word of the day found'}), 404