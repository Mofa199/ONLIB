from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, abort
from flask_login import login_required, current_user
from app.models.models import db, Course, Module, Topic, Resource, UserProgress, Quiz, QuizAttempt, Flashcard, WordOfTheDay, QuizOfTheDay
from datetime import date, datetime
import json

course_bp = Blueprint('course', __name__)

@course_bp.route('/')
@login_required
def index():
    # Get all available tracks
    tracks = ['Medical', 'Nursing', 'Pharmacy']
    
    # Get courses for each track
    courses_by_track = {}
    for track in tracks:
        courses_by_track[track] = Course.query.filter_by(track=track, is_active=True).all()
    
    # Get user's current track
    user_track = current_user.track
    
    # Get word of the day and quiz of the day
    today = date.today()
    word_of_day = WordOfTheDay.query.filter_by(date=today).first()
    quiz_of_day = QuizOfTheDay.query.filter_by(date=today).first()
    
    return render_template('courses/index.html',
                         courses_by_track=courses_by_track,
                         user_track=user_track,
                         tracks=tracks,
                         word_of_day=word_of_day,
                         quiz_of_day=quiz_of_day)

@course_bp.route('/track/<track>')
@login_required
def track_courses(track):
    if track not in ['Medical', 'Nursing', 'Pharmacy']:
        abort(404)
    
    # Get courses for the selected track
    courses = Course.query.filter_by(track=track, is_active=True).all()
    
    # Get user's progress for this track
    progress_data = []
    for course in courses:
        total_topics = Topic.query.join(Module).filter(Module.course_id == course.id).count()
        completed_topics = UserProgress.query.join(Topic).join(Module)\
            .filter(Module.course_id == course.id,
                    UserProgress.user_id == current_user.id,
                    UserProgress.completed == True).count()
        
        progress_percentage = (completed_topics / total_topics * 100) if total_topics > 0 else 0
        
        progress_data.append({
            'course': course,
            'total_topics': total_topics,
            'completed_topics': completed_topics,
            'progress_percentage': progress_percentage
        })
    
    # Get word of the day and quiz of the day
    today = date.today()
    word_of_day = WordOfTheDay.query.filter_by(date=today, category=track.lower()).first()
    if not word_of_day:
        word_of_day = WordOfTheDay.query.filter_by(date=today).first()
    
    quiz_of_day = QuizOfTheDay.query.filter_by(date=today, category=track.lower()).first()
    if not quiz_of_day:
        quiz_of_day = QuizOfTheDay.query.filter_by(date=today).first()
    
    return render_template('courses/track.html',
                         track=track,
                         progress_data=progress_data,
                         word_of_day=word_of_day,
                         quiz_of_day=quiz_of_day)

@course_bp.route('/course/<int:course_id>')
@login_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if user has access to this course (based on track)
    if course.track != current_user.track and not current_user.is_admin:
        flash('You don\'t have access to this course.', 'error')
        return redirect(url_for('course.index'))
    
    # Get modules with their topics
    modules = Module.query.filter_by(course_id=course_id, is_active=True)\
        .order_by(Module.order_index).all()
    
    # Get user's progress for each module
    module_progress = {}
    for module in modules:
        total_topics = len(module.topics)
        completed_topics = UserProgress.query.join(Topic)\
            .filter(Topic.module_id == module.id,
                    UserProgress.user_id == current_user.id,
                    UserProgress.completed == True).count()
        
        progress_percentage = (completed_topics / total_topics * 100) if total_topics > 0 else 0
        
        module_progress[module.id] = {
            'total_topics': total_topics,
            'completed_topics': completed_topics,
            'progress_percentage': progress_percentage
        }
    
    # Get recent activity for this course
    recent_activity = UserProgress.query.join(Topic).join(Module)\
        .filter(Module.course_id == course_id,
                UserProgress.user_id == current_user.id)\
        .order_by(UserProgress.last_accessed.desc()).limit(5).all()
    
    # Get word of the day and quiz of the day
    today = date.today()
    word_of_day = WordOfTheDay.query.filter_by(date=today, category=course.track.lower()).first()
    quiz_of_day = QuizOfTheDay.query.filter_by(date=today, category=course.track.lower()).first()
    
    return render_template('courses/course_detail.html',
                         course=course,
                         modules=modules,
                         module_progress=module_progress,
                         recent_activity=recent_activity,
                         word_of_day=word_of_day,
                         quiz_of_day=quiz_of_day)

@course_bp.route('/module/<int:module_id>')
@login_required
def module_detail(module_id):
    module = Module.query.get_or_404(module_id)
    course = module.course
    
    # Check access
    if course.track != current_user.track and not current_user.is_admin:
        flash('You don\'t have access to this module.', 'error')
        return redirect(url_for('course.index'))
    
    # Get topics with user progress
    topics = Topic.query.filter_by(module_id=module_id, is_active=True)\
        .order_by(Topic.order_index).all()
    
    topic_progress = {}
    for topic in topics:
        progress = UserProgress.query.filter_by(user_id=current_user.id, topic_id=topic.id).first()
        topic_progress[topic.id] = {
            'completed': progress.completed if progress else False,
            'progress_percentage': progress.progress_percentage if progress else 0,
            'last_accessed': progress.last_accessed if progress else None
        }
    
    return render_template('courses/module_detail.html',
                         module=module,
                         course=course,
                         topics=topics,
                         topic_progress=topic_progress)

@course_bp.route('/topic/<int:topic_id>')
@login_required
def topic_detail(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    module = topic.module
    course = module.course
    
    # Check access
    if course.track != current_user.track and not current_user.is_admin:
        flash('You don\'t have access to this topic.', 'error')
        return redirect(url_for('course.index'))
    
    # Get or create user progress
    progress = UserProgress.query.filter_by(user_id=current_user.id, topic_id=topic_id).first()
    if not progress:
        progress = UserProgress(user_id=current_user.id, topic_id=topic_id)
        db.session.add(progress)
        db.session.commit()
    
    # Update last accessed
    progress.last_accessed = datetime.utcnow()
    db.session.commit()
    
    # Get resources for this topic
    resources = Resource.query.filter_by(topic_id=topic_id, is_active=True).all()
    
    # Organize resources by type
    resources_by_type = {}
    for resource in resources:
        if resource.resource_type not in resources_by_type:
            resources_by_type[resource.resource_type] = []
        resources_by_type[resource.resource_type].append(resource)
    
    # Get flashcards for this topic
    flashcards = Flashcard.query.filter_by(topic_id=topic_id, is_active=True).all()
    
    # Get quizzes for this topic
    quizzes = Quiz.query.filter_by(topic_id=topic_id, is_active=True).all()
    
    # Get quiz attempts for this user
    quiz_attempts = {}
    for quiz in quizzes:
        attempts = QuizAttempt.query.filter_by(user_id=current_user.id, quiz_id=quiz.id)\
            .order_by(QuizAttempt.started_at.desc()).all()
        quiz_attempts[quiz.id] = attempts
    
    # Parse illustrations if they exist
    illustrations = []
    if topic.illustrations:
        try:
            illustrations = json.loads(topic.illustrations)
        except:
            illustrations = []
    
    # Get navigation (previous/next topics)
    all_topics = Topic.query.filter_by(module_id=module.id, is_active=True)\
        .order_by(Topic.order_index).all()
    
    current_index = next((i for i, t in enumerate(all_topics) if t.id == topic_id), -1)
    prev_topic = all_topics[current_index - 1] if current_index > 0 else None
    next_topic = all_topics[current_index + 1] if current_index < len(all_topics) - 1 else None
    
    return render_template('courses/topic_detail.html',
                         topic=topic,
                         module=module,
                         course=course,
                         progress=progress,
                         resources_by_type=resources_by_type,
                         flashcards=flashcards,
                         quizzes=quizzes,
                         quiz_attempts=quiz_attempts,
                         illustrations=illustrations,
                         prev_topic=prev_topic,
                         next_topic=next_topic)

@course_bp.route('/quiz/<int:quiz_id>')
@login_required
def quiz_detail(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    topic = quiz.topic
    
    # Check access
    if topic.module.course.track != current_user.track and not current_user.is_admin:
        abort(403)
    
    # Check if user has exceeded max attempts
    attempts_count = QuizAttempt.query.filter_by(user_id=current_user.id, quiz_id=quiz_id).count()
    if attempts_count >= quiz.max_attempts:
        flash('You have exceeded the maximum number of attempts for this quiz.', 'error')
        return redirect(url_for('course.topic_detail', topic_id=topic.id))
    
    # Get questions
    questions = quiz.questions
    
    return render_template('courses/quiz_detail.html',
                         quiz=quiz,
                         topic=topic,
                         questions=questions,
                         attempts_count=attempts_count)

@course_bp.route('/quiz/<int:quiz_id>/start', methods=['POST'])
@login_required
def start_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Check access and attempts
    topic = quiz.topic
    if topic.module.course.track != current_user.track and not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    attempts_count = QuizAttempt.query.filter_by(user_id=current_user.id, quiz_id=quiz_id).count()
    if attempts_count >= quiz.max_attempts:
        return jsonify({'success': False, 'message': 'Maximum attempts exceeded'}), 400
    
    # Create new attempt
    attempt = QuizAttempt(
        user_id=current_user.id,
        quiz_id=quiz_id,
        started_at=datetime.utcnow()
    )
    
    try:
        db.session.add(attempt)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'attempt_id': attempt.id,
            'message': 'Quiz started successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to start quiz'}), 500

@course_bp.route('/quiz-attempt/<int:attempt_id>/submit', methods=['POST'])
@login_required
def submit_quiz(attempt_id):
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    
    # Check ownership
    if attempt.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    if attempt.completed:
        return jsonify({'success': False, 'message': 'Quiz already completed'}), 400
    
    data = request.get_json()
    answers = data.get('answers', {})
    
    # Calculate score
    quiz = attempt.quiz
    questions = quiz.questions
    correct_answers = 0
    total_questions = len(questions)
    
    for question in questions:
        user_answer = answers.get(str(question.id), '')
        if user_answer.lower().strip() == question.correct_answer.lower().strip():
            correct_answers += 1
    
    score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    # Update attempt
    attempt.answers = json.dumps(answers)
    attempt.score = score
    attempt.completed = True
    attempt.completed_at = datetime.utcnow()
    attempt.time_taken = int((datetime.utcnow() - attempt.started_at).total_seconds() / 60)
    
    # Award points if passed
    if score >= quiz.passing_score:
        points_awarded = 20  # Base points for passing a quiz
        current_user.total_points += points_awarded
        
        # Check for level up
        new_level = (current_user.total_points // 100) + 1
        if new_level > current_user.level:
            current_user.level = new_level
    
    try:
        db.session.commit()
        
        return jsonify({
            'success': True,
            'score': score,
            'passed': score >= quiz.passing_score,
            'correct_answers': correct_answers,
            'total_questions': total_questions,
            'new_level': current_user.level,
            'total_points': current_user.total_points
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to submit quiz'}), 500

@course_bp.route('/flashcards/<int:topic_id>')
@login_required
def flashcards(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    
    # Check access
    if topic.module.course.track != current_user.track and not current_user.is_admin:
        abort(403)
    
    flashcards = Flashcard.query.filter_by(topic_id=topic_id, is_active=True).all()
    
    return render_template('courses/flashcards.html',
                         topic=topic,
                         flashcards=flashcards)

@course_bp.route('/api/modules/<int:course_id>')
@login_required
def api_course_modules(course_id):
    """API endpoint to get modules for a course"""
    course = Course.query.get_or_404(course_id)
    
    # Check access
    if course.track != current_user.track and not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    modules = Module.query.filter_by(course_id=course_id, is_active=True)\
        .order_by(Module.order_index).all()
    
    modules_data = []
    for module in modules:
        topics = Topic.query.filter_by(module_id=module.id, is_active=True)\
            .order_by(Topic.order_index).all()
        
        topics_data = []
        for topic in topics:
            progress = UserProgress.query.filter_by(user_id=current_user.id, topic_id=topic.id).first()
            topics_data.append({
                'id': topic.id,
                'title': topic.title,
                'completed': progress.completed if progress else False,
                'progress_percentage': progress.progress_percentage if progress else 0
            })
        
        modules_data.append({
            'id': module.id,
            'name': module.name,
            'description': module.description,
            'topics': topics_data
        })
    
    return jsonify(modules_data)

@course_bp.route('/api/topic/<int:topic_id>/resources')
@login_required
def api_topic_resources(topic_id):
    """API endpoint to get resources for a topic"""
    topic = Topic.query.get_or_404(topic_id)
    
    # Check access
    if topic.module.course.track != current_user.track and not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    resources = Resource.query.filter_by(topic_id=topic_id, is_active=True).all()
    
    resources_data = []
    for resource in resources:
        resources_data.append({
            'id': resource.id,
            'title': resource.title,
            'description': resource.description,
            'resource_type': resource.resource_type,
            'file_path': resource.file_path,
            'external_url': resource.external_url,
            'author': resource.author,
            'year_published': resource.year_published
        })
    
    return jsonify(resources_data)