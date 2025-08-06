from flask import Blueprint
user_bp = Blueprint('user', __name__)

from flask import Blueprint, render_template

user_bp = Blueprint('user', __name__)

@user_bp.route('/courses')
def courses():
    return render_template('user/courses.html')

@user_bp.route('/topic/<string:topic_name>')
def topic(topic_name):
    return render_template('user/topic.html', topic_name=topic_name)
