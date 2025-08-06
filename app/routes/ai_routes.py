from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from app.models.models import db, SearchLog, Topic, Resource, Drug, DrugClass
import requests
import json
from datetime import datetime

ai_bp = Blueprint('ai', __name__)

def get_deepseek_response(prompt, context="", max_tokens=500):
    """
    Get response from DeepSeek API
    This is a placeholder implementation - you'll need to replace with actual DeepSeek API
    """
    api_key = current_app.config.get('DEEPSEEK_API_KEY')
    
    if not api_key:
        return {
            'success': False,
            'message': 'AI service not configured'
        }
    
    try:
        # This is a placeholder for DeepSeek API integration
        # Replace with actual DeepSeek API endpoint and authentication
        
        # For now, we'll simulate AI responses based on the prompt
        if 'search' in prompt.lower():
            return simulate_search_response(prompt, context)
        elif 'summarize' in prompt.lower():
            return simulate_summary_response(context)
        elif 'explain' in prompt.lower():
            return simulate_explanation_response(prompt, context)
        else:
            return simulate_general_response(prompt, context)
            
    except Exception as e:
        return {
            'success': False,
            'message': 'AI service temporarily unavailable'
        }

def simulate_search_response(prompt, context):
    """Simulate AI search response"""
    return {
        'success': True,
        'response': f"I found several relevant resources based on your query. Here are the most relevant matches from our medical library. Would you like me to help you explore any specific topic in more detail?",
        'suggestions': [
            'Show me more details about this topic',
            'Find related resources',
            'Explain this concept simply'
        ]
    }

def simulate_summary_response(context):
    """Simulate AI summarization response"""
    return {
        'success': True,
        'response': "Here's a concise summary of the key points: This medical content covers important concepts that are essential for understanding the topic. The main takeaways include fundamental principles, clinical applications, and practical considerations for medical professionals.",
        'key_points': [
            'Key concept 1: Fundamental principles',
            'Key concept 2: Clinical applications', 
            'Key concept 3: Practical considerations'
        ]
    }

def simulate_explanation_response(prompt, context):
    """Simulate AI explanation response"""
    return {
        'success': True,
        'response': "Let me explain this medical concept in simple terms. This topic involves several important aspects that work together to create the overall understanding. I can break this down into more digestible parts if needed.",
        'follow_up': 'Would you like me to explain any specific part in more detail?'
    }

def simulate_general_response(prompt, context):
    """Simulate general AI response"""
    return {
        'success': True,
        'response': "I'm here to help you with your medical studies! I can assist with searching for resources, explaining complex concepts, summarizing content, and answering questions about medical topics. What would you like to explore?",
        'capabilities': [
            'Search medical resources',
            'Explain medical concepts',
            'Summarize content',
            'Answer medical questions'
        ]
    }

@ai_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    """Main AI chat endpoint"""
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({
            'success': False,
            'message': 'Message is required'
        }), 400
    
    user_message = data.get('message', '').strip()
    context = data.get('context', '')
    chat_type = data.get('type', 'general')  # general, search, explain, summarize
    
    if not user_message:
        return jsonify({
            'success': False,
            'message': 'Message cannot be empty'
        }), 400
    
    # Prepare prompt based on chat type
    if chat_type == 'search':
        prompt = f"Help me search for medical resources about: {user_message}"
    elif chat_type == 'explain':
        prompt = f"Please explain this medical concept: {user_message}"
    elif chat_type == 'summarize':
        prompt = f"Please summarize this medical content: {user_message}"
    else:
        prompt = f"Medical assistant question: {user_message}"
    
    # Get AI response
    ai_response = get_deepseek_response(prompt, context)
    
    # Log the interaction
    if current_user.is_authenticated:
        try:
            search_log = SearchLog(
                user_id=current_user.id,
                query=user_message,
                search_type='ai'
            )
            db.session.add(search_log)
            db.session.commit()
        except:
            pass  # Don't fail if logging fails
    
    return jsonify(ai_response)

@ai_bp.route('/search-assist', methods=['POST'])
@login_required
def search_assist():
    """AI-powered search assistance"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({
            'success': False,
            'message': 'Search query is required'
        }), 400
    
    # Perform actual search in database
    results = []
    
    # Search topics
    topics = Topic.query.filter(
        db.or_(
            Topic.title.contains(query),
            Topic.content.contains(query),
            Topic.summary.contains(query)
        ),
        Topic.is_active == True
    ).limit(5).all()
    
    for topic in topics:
        results.append({
            'type': 'topic',
            'title': topic.title,
            'summary': topic.summary or (topic.content[:200] + '...' if topic.content else ''),
            'url': url_for('course.topic_detail', topic_id=topic.id),
            'module': topic.module.name,
            'course': topic.module.course.name
        })
    
    # Search resources
    resources = Resource.query.filter(
        db.or_(
            Resource.title.contains(query),
            Resource.description.contains(query),
            Resource.author.contains(query)
        ),
        Resource.is_active == True
    ).limit(5).all()
    
    for resource in resources:
        results.append({
            'type': 'resource',
            'title': resource.title,
            'summary': resource.description or 'No description available',
            'url': url_for('library.resource_detail', resource_id=resource.id),
            'author': resource.author,
            'resource_type': resource.resource_type
        })
    
    # Search drugs if query seems pharmacology-related
    drugs = Drug.query.filter(
        db.or_(
            Drug.name.contains(query),
            Drug.generic_name.contains(query),
            Drug.description.contains(query)
        )
    ).limit(3).all()
    
    for drug in drugs:
        results.append({
            'type': 'drug',
            'title': drug.name,
            'summary': drug.description or 'No description available',
            'url': url_for('pharma.drug_detail', drug_id=drug.id),
            'generic_name': drug.generic_name,
            'drug_class': drug.drug_class.name
        })
    
    # Get AI-enhanced search suggestions
    ai_response = get_deepseek_response(f"search for {query}", json.dumps(results[:3]))
    
    return jsonify({
        'success': True,
        'results': results,
        'ai_suggestion': ai_response.get('response', ''),
        'total_results': len(results)
    })

@ai_bp.route('/summarize', methods=['POST'])
@login_required
def summarize():
    """AI content summarization"""
    data = request.get_json()
    content = data.get('content', '').strip()
    content_type = data.get('type', 'text')  # text, topic, resource
    content_id = data.get('id')
    
    if not content and not content_id:
        return jsonify({
            'success': False,
            'message': 'Content or content ID is required'
        }), 400
    
    # Get content from database if ID provided
    if content_id:
        if content_type == 'topic':
            topic = Topic.query.get(content_id)
            if topic and topic.is_active:
                content = f"Title: {topic.title}\n\nContent: {topic.content or ''}\n\nSummary: {topic.summary or ''}"
            else:
                return jsonify({'success': False, 'message': 'Topic not found'}), 404
                
        elif content_type == 'resource':
            resource = Resource.query.get(content_id)
            if resource and resource.is_active:
                content = f"Title: {resource.title}\n\nDescription: {resource.description or ''}\n\nAuthor: {resource.author or ''}"
            else:
                return jsonify({'success': False, 'message': 'Resource not found'}), 404
    
    if not content:
        return jsonify({
            'success': False,
            'message': 'No content to summarize'
        }), 400
    
    # Get AI summary
    ai_response = get_deepseek_response("summarize", content)
    
    return jsonify(ai_response)

@ai_bp.route('/explain', methods=['POST'])
@login_required
def explain():
    """AI concept explanation"""
    data = request.get_json()
    concept = data.get('concept', '').strip()
    context = data.get('context', '')
    level = data.get('level', 'intermediate')  # beginner, intermediate, advanced
    
    if not concept:
        return jsonify({
            'success': False,
            'message': 'Concept to explain is required'
        }), 400
    
    # Prepare prompt based on level
    level_prompts = {
        'beginner': f"Explain this medical concept in simple terms for a beginner: {concept}",
        'intermediate': f"Explain this medical concept for a medical student: {concept}",
        'advanced': f"Provide an advanced explanation of this medical concept: {concept}"
    }
    
    prompt = level_prompts.get(level, level_prompts['intermediate'])
    
    # Get AI explanation
    ai_response = get_deepseek_response(prompt, context)
    
    return jsonify(ai_response)

@ai_bp.route('/recommendations', methods=['POST'])
@login_required
def recommendations():
    """AI-powered content recommendations"""
    data = request.get_json()
    user_track = current_user.track
    current_topic_id = data.get('topic_id')
    current_resource_id = data.get('resource_id')
    
    recommendations = []
    
    # Get user's recent activity
    recent_progress = current_user.progress_records[-5:] if current_user.progress_records else []
    
    # Base recommendations on user's track
    if user_track:
        # Get topics from user's track
        track_topics = Topic.query.join(Topic.module).join(Topic.module.property.mapper.class_.course)\
            .filter_by(track=user_track, is_active=True).limit(5).all()
        
        for topic in track_topics:
            if not current_topic_id or topic.id != current_topic_id:
                recommendations.append({
                    'type': 'topic',
                    'title': topic.title,
                    'description': topic.summary or 'No description available',
                    'url': url_for('course.topic_detail', topic_id=topic.id),
                    'reason': f'Recommended for {user_track} students'
                })
    
    # Get AI-enhanced recommendations
    context = {
        'user_track': user_track,
        'recent_topics': [p.topic.title for p in recent_progress] if recent_progress else [],
        'current_topic_id': current_topic_id,
        'current_resource_id': current_resource_id
    }
    
    ai_response = get_deepseek_response(
        "recommend study materials", 
        json.dumps(context)
    )
    
    return jsonify({
        'success': True,
        'recommendations': recommendations[:6],
        'ai_insight': ai_response.get('response', ''),
        'study_tips': ai_response.get('suggestions', [])
    })

@ai_bp.route('/study-assistant', methods=['POST'])
@login_required
def study_assistant():
    """AI study planning and assistance"""
    data = request.get_json()
    request_type = data.get('type', 'general')  # plan, tips, quiz, review
    topic_id = data.get('topic_id')
    
    response_data = {'success': True}
    
    if request_type == 'plan':
        # Generate study plan
        response_data.update({
            'study_plan': [
                'Review key concepts and definitions',
                'Practice with flashcards',
                'Take practice quizzes',
                'Review difficult topics',
                'Apply knowledge with case studies'
            ],
            'estimated_time': '2-3 hours',
            'difficulty': 'Intermediate'
        })
        
    elif request_type == 'tips':
        # Get study tips
        response_data.update({
            'tips': [
                'Use active recall techniques',
                'Space out your study sessions',
                'Create visual aids and diagrams',
                'Teach concepts to others',
                'Practice with real-world examples'
            ]
        })
        
    elif request_type == 'quiz':
        # Generate practice questions
        response_data.update({
            'questions': [
                {
                    'question': 'What is the primary function of this concept?',
                    'type': 'multiple_choice',
                    'options': ['Option A', 'Option B', 'Option C', 'Option D']
                },
                {
                    'question': 'Explain the mechanism of action.',
                    'type': 'short_answer'
                }
            ]
        })
    
    # Add AI-generated insights
    ai_response = get_deepseek_response(f"study assistant {request_type}", json.dumps(data))
    response_data['ai_insight'] = ai_response.get('response', '')
    
    return jsonify(response_data)

@ai_bp.route('/voice-search', methods=['POST'])
@login_required
def voice_search():
    """Process voice search queries"""
    data = request.get_json()
    transcript = data.get('transcript', '').strip()
    
    if not transcript:
        return jsonify({
            'success': False,
            'message': 'Voice transcript is required'
        }), 400
    
    # Process the voice query similar to text search
    return search_assist()

@ai_bp.route('/feedback', methods=['POST'])
@login_required
def feedback():
    """Collect AI interaction feedback"""
    data = request.get_json()
    interaction_id = data.get('interaction_id')
    rating = data.get('rating')  # 1-5 stars
    feedback_text = data.get('feedback', '').strip()
    
    # In a real application, you'd store this feedback for AI improvement
    # For now, we'll just acknowledge it
    
    return jsonify({
        'success': True,
        'message': 'Thank you for your feedback! This helps us improve the AI assistant.'
    })

@ai_bp.route('/status')
@login_required
def status():
    """Check AI service status"""
    api_key = current_app.config.get('DEEPSEEK_API_KEY')
    
    return jsonify({
        'available': bool(api_key),
        'service': 'DeepSeek AI',
        'features': [
            'Smart search assistance',
            'Content summarization',
            'Concept explanations',
            'Study recommendations',
            'Voice search support'
        ]
    })