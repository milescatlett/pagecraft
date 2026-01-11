"""Authentication blueprint"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.extensions import limiter
from app.utils.security import validate_redirect_url

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=['POST'])
def login():
    """Login page with CSRF protection and rate limiting"""
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('cms.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=bool(remember))

            # Validate next parameter to prevent open redirect vulnerability
            next_page = request.args.get('next')
            if next_page:
                # Only allow relative URLs or URLs to localhost
                if validate_redirect_url(next_page, ['localhost', '127.0.0.1']):
                    return redirect(next_page)

            return redirect(url_for('cms.index'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    """Logout and redirect to login page"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
