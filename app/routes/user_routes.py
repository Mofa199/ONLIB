from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.models.models import db, User, Course, Module, Topic, UserProgress, Badge, Resource, Quiz, QuizAttempt
from datetime import datetime
import json

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    
    # Get user's track-specific courses
    courses = Course.query.filter_by(track=current_user.track, is_active=True).all()
    
    # Get recent progress
    recent_progress = UserProgress.query.filter_by(user_id=current_user.id)\
        .order_by(UserProgress.last_accessed.desc()).limit(5).all()
    
    # Get user's badges
    user_badges = current_user.earned_badges
    
    # Calculate overall progress
    total_topics = Topic.query.join(Module).join(Course)\
        .filter(Course.track == current_user.track, Course.is_active == True).count()
    completed_topics = UserProgress.query.join(Topic).join(Module).join(Course)\
        .filter(Course.track == current_user.track, 
                UserProgress.user_id == current_user.id,
                UserProgress.completed == True).count()
    
    overall_progress = (completed_topics / total_topics * 100) if total_topics > 0 else 0
    
    # Get recommended resources
    recommended_resources = Resource.query.join(Topic).join(Module).join(Course)\
        .filter(Course.track == current_user.track)\
        .order_by(Resource.view_count.desc()).limit(6).all()
    
    # Get bookmarked resources
    bookmarked_resources = current_user.bookmarked_resources[:6]
    
    # Get quiz attempts stats
    quiz_attempts = QuizAttempt.query.filter_by(user_id=current_user.id, completed=True).all()
    avg_quiz_score = sum(attempt.score for attempt in quiz_attempts) / len(quiz_attempts) if quiz_attempts else 0
    
    return render_template('user/dashboard.html',
                         courses=courses,
                         recent_progress=recent_progress,
                         user_badges=user_badges,
                         overall_progress=overall_progress,
                         recommended_resources=recommended_resources,
                         bookmarked_resources=bookmarked_resources,
                         total_topics=total_topics,
                         completed_topics=completed_topics,
                         avg_quiz_score=avg_quiz_score,
                         total_points=current_user.total_points,
                         user_level=current_user.level)

@user_bp.route('/profile')
@login_required
def profile():
    return render_template('user/profile.html', user=current_user)

@user_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        name = data.get('name', '').strip()
        bio = data.get('bio', '').strip()
        track = data.get('track', '')
        
        errors = []
        
        if not name:
            errors.append('Name is required')
        elif len(name) < 2:
            errors.append('Name must be at least 2 characters long')
        
        if track and track not in ['Medical', 'Nursing', 'Pharmacy']:
            errors.append('Invalid track selected')
        
        if errors:
            if request.is_json:
                return jsonify({'success': False, 'message': '; '.join(errors)}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('user/edit_profile.html', user=current_user)
        
        try:
            current_user.name = name
            current_user.bio = bio
            if track:
                current_user.track = track
            
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Profile updated successfully'})
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('user.profile'))
            
        except Exception as e:
            db.session.rollback()
            error = 'Failed to update profile. Please try again.'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 500
            flash(error, 'error')
    
    return render_template('user/edit_profile.html', user=current_user)

@user_bp.route('/progress')
@login_required
def progress():
    # Get user's progress by course
    courses = Course.query.filter_by(track=current_user.track, is_active=True).all()
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
    
    # Get recent activity
    recent_activity = UserProgress.query.filter_by(user_id=current_user.id)\
        .order_by(UserProgress.last_accessed.desc()).limit(10).all()
    
    return render_template('user/progress.html',
                         progress_data=progress_data,
                         recent_activity=recent_activity)

@user_bp.route('/bookmarks')
@login_required
def bookmarks():
    bookmarked_resources = current_user.bookmarked_resources
    return render_template('user/bookmarks.html', resources=bookmarked_resources)

@user_bp.route('/bookmark/<int:resource_id>', methods=['POST'])
@login_required
def toggle_bookmark(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    
    if resource in current_user.bookmarked_resources:
        current_user.bookmarked_resources.remove(resource)
        action = 'removed'
    else:
        current_user.bookmarked_resources.append(resource)
        action = 'added'
    
    try:
        db.session.commit()
        return jsonify({
            'success': True, 
            'action': action,
            'message': f'Bookmark {action} successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'message': 'Failed to update bookmark'
        }), 500

@user_bp.route('/achievements')
@login_required
def achievements():
    # Get all available badges
    all_badges = Badge.query.filter_by(is_active=True).all()
    earned_badges = current_user.earned_badges
    
    # Separate earned and unearned badges
    earned_badge_ids = [badge.id for badge in earned_badges]
    unearned_badges = [badge for badge in all_badges if badge.id not in earned_badge_ids]
    
    return render_template('user/achievements.html',
                         earned_badges=earned_badges,
                         unearned_badges=unearned_badges,
                         total_points=current_user.total_points,
                         user_level=current_user.level)

@user_bp.route('/quiz-history')
@login_required
def quiz_history():
    quiz_attempts = QuizAttempt.query.filter_by(user_id=current_user.id)\
        .order_by(QuizAttempt.completed_at.desc()).all()
    
    # Calculate statistics
    completed_attempts = [attempt for attempt in quiz_attempts if attempt.completed]
    total_attempts = len(completed_attempts)
    avg_score = sum(attempt.score for attempt in completed_attempts) / total_attempts if total_attempts > 0 else 0
    best_score = max((attempt.score for attempt in completed_attempts), default=0)
    
    return render_template('user/quiz_history.html',
                         quiz_attempts=quiz_attempts,
                         total_attempts=total_attempts,
                         avg_score=avg_score,
                         best_score=best_score)

@user_bp.route('/settings')
@login_required
def settings():
    return render_template('user/settings.html', user=current_user)

@user_bp.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    data = request.get_json() if request.is_json else request.form
    
    # Update user preferences (these would be stored in the database)
    # For now, we'll just return success
    
    if request.is_json:
        return jsonify({'success': True, 'message': 'Settings updated successfully'})
    
    flash('Settings updated successfully!', 'success')
    return redirect(url_for('user.settings'))

@user_bp.route('/update-progress', methods=['POST'])
@login_required
def update_progress():
    """Update user's progress for a topic"""
    data = request.get_json()
    topic_id = data.get('topic_id')
    progress_percentage = data.get('progress_percentage', 0)
    time_spent = data.get('time_spent', 0)
    completed = data.get('completed', False)
    
    if not topic_id:
        return jsonify({'success': False, 'message': 'Topic ID is required'}), 400
    
    topic = Topic.query.get_or_404(topic_id)
    
    # Get or create progress record
    progress = UserProgress.query.filter_by(user_id=current_user.id, topic_id=topic_id).first()
    if not progress:
        progress = UserProgress(user_id=current_user.id, topic_id=topic_id)
        db.session.add(progress)
    
    # Update progress
    progress.progress_percentage = max(progress.progress_percentage, progress_percentage)
    progress.time_spent += time_spent
    progress.last_accessed = datetime.utcnow()
    
    # Check if topic is completed
    if completed and not progress.completed:
        progress.completed = True
        progress.completed_at = datetime.utcnow()
        progress.progress_percentage = 100
        
        # Award points for completion
        points_awarded = 10  # Base points for completing a topic
        current_user.total_points += points_awarded
        
        # Check for level up (every 100 points = 1 level)
        new_level = (current_user.total_points // 100) + 1
        if new_level > current_user.level:
            current_user.level = new_level
    
    try:
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Progress updated successfully',
            'new_level': current_user.level,
            'total_points': current_user.total_points
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to update progress'}), 500
