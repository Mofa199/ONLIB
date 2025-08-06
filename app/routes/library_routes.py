from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file, abort, current_app
from flask_login import login_required, current_user
from app.models.models import db, Resource, ResourceRating, Topic, Module, Course, User
from datetime import datetime
import os
from werkzeug.utils import secure_filename

library_bp = Blueprint('library', __name__)

@library_bp.route('/')
@login_required
def index():
    # Get filter parameters
    resource_type = request.args.get('type', 'all')
    author = request.args.get('author', '')
    year = request.args.get('year', '')
    search_query = request.args.get('q', '')
    sort_by = request.args.get('sort', 'created_at')
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = Resource.query.filter_by(is_active=True)
    
    # Apply filters
    if resource_type != 'all':
        query = query.filter(Resource.resource_type == resource_type)
    
    if author:
        query = query.filter(Resource.author.contains(author))
    
    if year:
        query = query.filter(Resource.year_published == int(year))
    
    if search_query:
        query = query.filter(
            db.or_(
                Resource.title.contains(search_query),
                Resource.description.contains(search_query),
                Resource.author.contains(search_query)
            )
        )
    
    # Apply sorting
    if sort_by == 'title':
        query = query.order_by(Resource.title)
    elif sort_by == 'author':
        query = query.order_by(Resource.author)
    elif sort_by == 'year':
        query = query.order_by(Resource.year_published.desc())
    elif sort_by == 'popular':
        query = query.order_by(Resource.view_count.desc())
    elif sort_by == 'rating':
        # This would require a more complex query with joins
        query = query.order_by(Resource.created_at.desc())
    else:  # created_at
        query = query.order_by(Resource.created_at.desc())
    
    # Paginate results
    resources = query.paginate(page=page, per_page=12, error_out=False)
    
    # Get filter options
    resource_types = db.session.query(Resource.resource_type.distinct()).filter(Resource.is_active == True).all()
    resource_types = [rt[0] for rt in resource_types if rt[0]]
    
    authors = db.session.query(Resource.author.distinct()).filter(Resource.is_active == True, Resource.author != None).all()
    authors = [author[0] for author in authors if author[0]][:50]  # Limit to top 50 authors
    
    years = db.session.query(Resource.year_published.distinct()).filter(Resource.is_active == True, Resource.year_published != None).order_by(Resource.year_published.desc()).all()
    years = [year[0] for year in years if year[0]]
    
    # Get featured/recommended resources
    featured_resources = Resource.query.filter_by(is_active=True)\
        .order_by(Resource.view_count.desc()).limit(6).all()
    
    return render_template('library/index.html',
                         resources=resources,
                         resource_types=resource_types,
                         authors=authors,
                         years=years,
                         featured_resources=featured_resources,
                         current_filters={
                             'type': resource_type,
                             'author': author,
                             'year': year,
                             'q': search_query,
                             'sort': sort_by
                         })

@library_bp.route('/resource/<int:resource_id>')
@login_required
def resource_detail(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    
    # Increment view count
    resource.view_count += 1
    db.session.commit()
    
    # Get user's rating for this resource
    user_rating = ResourceRating.query.filter_by(
        user_id=current_user.id,
        resource_id=resource_id
    ).first()
    
    # Get all ratings and reviews
    ratings = ResourceRating.query.filter_by(resource_id=resource_id)\
        .order_by(ResourceRating.created_at.desc()).all()
    
    # Calculate rating statistics
    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total_ratings = len(ratings)
    avg_rating = resource.get_average_rating()
    
    for rating in ratings:
        rating_counts[rating.rating] += 1
    
    # Get related resources (same topic or similar)
    related_resources = []
    if resource.topic_id:
        related_resources = Resource.query.filter(
            Resource.topic_id == resource.topic_id,
            Resource.id != resource_id,
            Resource.is_active == True
        ).limit(6).all()
    
    if len(related_resources) < 6:
        # Add more resources from same resource type
        additional_resources = Resource.query.filter(
            Resource.resource_type == resource.resource_type,
            Resource.id != resource_id,
            Resource.is_active == True
        ).limit(6 - len(related_resources)).all()
        related_resources.extend(additional_resources)
    
    # Check if resource is bookmarked by current user
    is_bookmarked = resource in current_user.bookmarked_resources
    
    return render_template('library/resource_detail.html',
                         resource=resource,
                         user_rating=user_rating,
                         ratings=ratings,
                         rating_counts=rating_counts,
                         total_ratings=total_ratings,
                         avg_rating=avg_rating,
                         related_resources=related_resources,
                         is_bookmarked=is_bookmarked)

@library_bp.route('/resource/<int:resource_id>/rate', methods=['POST'])
@login_required
def rate_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    
    data = request.get_json() if request.is_json else request.form
    rating_value = data.get('rating', type=int)
    comment = data.get('comment', '').strip()
    
    if not rating_value or rating_value < 1 or rating_value > 5:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Invalid rating value'}), 400
        flash('Invalid rating value', 'error')
        return redirect(url_for('library.resource_detail', resource_id=resource_id))
    
    # Check if user already rated this resource
    existing_rating = ResourceRating.query.filter_by(
        user_id=current_user.id,
        resource_id=resource_id
    ).first()
    
    try:
        if existing_rating:
            # Update existing rating
            existing_rating.rating = rating_value
            existing_rating.comment = comment
            existing_rating.created_at = datetime.utcnow()
        else:
            # Create new rating
            new_rating = ResourceRating(
                user_id=current_user.id,
                resource_id=resource_id,
                rating=rating_value,
                comment=comment
            )
            db.session.add(new_rating)
        
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Rating submitted successfully'})
        
        flash('Rating submitted successfully!', 'success')
        return redirect(url_for('library.resource_detail', resource_id=resource_id))
        
    except Exception as e:
        db.session.rollback()
        error_msg = 'Failed to submit rating'
        if request.is_json:
            return jsonify({'success': False, 'message': error_msg}), 500
        flash(error_msg, 'error')
        return redirect(url_for('library.resource_detail', resource_id=resource_id))

@library_bp.route('/resource/<int:resource_id>/download')
@login_required
def download_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    
    if not resource.file_path:
        flash('This resource is not available for download', 'error')
        return redirect(url_for('library.resource_detail', resource_id=resource_id))
    
    # Increment download count
    resource.download_count += 1
    db.session.commit()
    
    # Get file path
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], resource.file_path)
    
    if not os.path.exists(file_path):
        flash('File not found', 'error')
        return redirect(url_for('library.resource_detail', resource_id=resource_id))
    
    return send_file(file_path, as_attachment=True, 
                    download_name=f"{resource.title}.{resource.file_path.split('.')[-1]}")

@library_bp.route('/books')
@login_required
def books():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '')
    author = request.args.get('author', '')
    year = request.args.get('year', '')
    
    query = Resource.query.filter_by(resource_type='book', is_active=True)
    
    if search_query:
        query = query.filter(
            db.or_(
                Resource.title.contains(search_query),
                Resource.description.contains(search_query),
                Resource.author.contains(search_query)
            )
        )
    
    if author:
        query = query.filter(Resource.author.contains(author))
    
    if year:
        query = query.filter(Resource.year_published == int(year))
    
    books = query.order_by(Resource.created_at.desc())\
        .paginate(page=page, per_page=12, error_out=False)
    
    # Get filter options
    authors = db.session.query(Resource.author.distinct())\
        .filter(Resource.resource_type == 'book', Resource.is_active == True, Resource.author != None).all()
    authors = [author[0] for author in authors if author[0]]
    
    years = db.session.query(Resource.year_published.distinct())\
        .filter(Resource.resource_type == 'book', Resource.is_active == True, Resource.year_published != None)\
        .order_by(Resource.year_published.desc()).all()
    years = [year[0] for year in years if year[0]]
    
    return render_template('library/books.html',
                         books=books,
                         authors=authors,
                         years=years,
                         current_filters={
                             'q': search_query,
                             'author': author,
                             'year': year
                         })

@library_bp.route('/articles')
@login_required
def articles():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '')
    author = request.args.get('author', '')
    
    query = Resource.query.filter_by(resource_type='article', is_active=True)
    
    if search_query:
        query = query.filter(
            db.or_(
                Resource.title.contains(search_query),
                Resource.description.contains(search_query),
                Resource.author.contains(search_query)
            )
        )
    
    if author:
        query = query.filter(Resource.author.contains(author))
    
    articles = query.order_by(Resource.created_at.desc())\
        .paginate(page=page, per_page=12, error_out=False)
    
    return render_template('library/articles.html',
                         articles=articles,
                         current_filters={
                             'q': search_query,
                             'author': author
                         })

@library_bp.route('/magazines')
@login_required
def magazines():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '')
    
    query = Resource.query.filter_by(resource_type='magazine', is_active=True)
    
    if search_query:
        query = query.filter(
            db.or_(
                Resource.title.contains(search_query),
                Resource.description.contains(search_query)
            )
        )
    
    magazines = query.order_by(Resource.created_at.desc())\
        .paginate(page=page, per_page=12, error_out=False)
    
    return render_template('library/magazines.html',
                         magazines=magazines,
                         current_filters={'q': search_query})

@library_bp.route('/recommendations')
@login_required
def recommendations():
    # Get user's track and recent activity
    user_track = current_user.track
    
    # Get resources from user's track
    track_resources = Resource.query.join(Topic).join(Module).join(Course)\
        .filter(Course.track == user_track, Resource.is_active == True)\
        .order_by(Resource.view_count.desc()).limit(12).all()
    
    # Get popular resources overall
    popular_resources = Resource.query.filter_by(is_active=True)\
        .order_by(Resource.view_count.desc()).limit(12).all()
    
    # Get recently added resources
    recent_resources = Resource.query.filter_by(is_active=True)\
        .order_by(Resource.created_at.desc()).limit(12).all()
    
    # Get highly rated resources
    # This is a simplified version - in a real app you'd use a more sophisticated query
    highly_rated = Resource.query.filter_by(is_active=True)\
        .order_by(Resource.created_at.desc()).limit(12).all()
    
    return render_template('library/recommendations.html',
                         track_resources=track_resources,
                         popular_resources=popular_resources,
                         recent_resources=recent_resources,
                         highly_rated=highly_rated,
                         user_track=user_track)

@library_bp.route('/collections')
@login_required
def collections():
    # Get curated collections (this would be more sophisticated in a real app)
    collections = [
        {
            'name': 'Essential Medical Textbooks',
            'description': 'Core textbooks every medical student should read',
            'resources': Resource.query.filter_by(resource_type='book', is_active=True)
                .join(Topic).join(Module).join(Course)
                .filter(Course.track == 'Medical').limit(6).all(),
            'color': '#213874'
        },
        {
            'name': 'Nursing Practice Guides',
            'description': 'Practical guides for nursing students and professionals',
            'resources': Resource.query.filter_by(resource_type='book', is_active=True)
                .join(Topic).join(Module).join(Course)
                .filter(Course.track == 'Nursing').limit(6).all(),
            'color': '#1a6ac3'
        },
        {
            'name': 'Pharmacy Reference Materials',
            'description': 'Essential references for pharmacy practice',
            'resources': Resource.query.filter_by(resource_type='book', is_active=True)
                .join(Topic).join(Module).join(Course)
                .filter(Course.track == 'Pharmacy').limit(6).all(),
            'color': '#f3ab1b'
        }
    ]
    
    return render_template('library/collections.html', collections=collections)

@library_bp.route('/api/search-suggestions')
@login_required
def api_search_suggestions():
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify([])
    
    # Search in resource titles and authors
    suggestions = []
    
    # Title suggestions
    title_matches = Resource.query.filter(
        Resource.title.contains(query),
        Resource.is_active == True
    ).limit(5).all()
    
    for resource in title_matches:
        suggestions.append({
            'type': 'title',
            'text': resource.title,
            'url': url_for('library.resource_detail', resource_id=resource.id)
        })
    
    # Author suggestions
    author_matches = db.session.query(Resource.author.distinct())\
        .filter(Resource.author.contains(query), Resource.is_active == True)\
        .limit(3).all()
    
    for author in author_matches:
        if author[0]:
            suggestions.append({
                'type': 'author',
                'text': f"By {author[0]}",
                'url': url_for('library.index', author=author[0])
            })
    
    return jsonify(suggestions[:8])  # Limit to 8 suggestions

@library_bp.route('/api/resource/<int:resource_id>/bookmark', methods=['POST'])
@login_required
def api_toggle_bookmark(resource_id):
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
            'bookmarked': action == 'added'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to update bookmark'}), 500