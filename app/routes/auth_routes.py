from flask import Blueprint, render_template, request, redirect, session

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_type = request.form.get('username')
        session['role'] = 'admin' if user_type == 'admin' else 'user'
        return redirect('/dashboard')
    return render_template('auth/login.html')
