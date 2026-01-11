"""User management blueprint (admin only)"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required
from app.models import User
from app.extensions import db, limiter
from app.utils.decorators import admin_required
from app.utils.validators import validate_username, validate_password

bp = Blueprint('users', __name__)


@bp.route('/users')
@login_required
@admin_required
def users_list():
    """List all users (admin only)"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('cms/users.html', users=users)


@bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
@limiter.limit("5 per minute")
def users_create():
    """Create a new user (admin only) with CSRF protection and validation"""
    data = request.get_json() if request.is_json else request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')
    is_admin = data.get('is_admin', False)

    # Validate username
    is_valid, error = validate_username(username)
    if not is_valid:
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 400
        flash(error, 'danger')
        return redirect(url_for('users.users_list'))

    # Validate password
    is_valid, error = validate_password(password)
    if not is_valid:
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 400
        flash(error, 'danger')
        return redirect(url_for('users.users_list'))

    # Check if username already exists
    if User.query.filter_by(username=username).first():
        if request.is_json:
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        flash('Username already exists', 'danger')
        return redirect(url_for('users.users_list'))

    user = User(username=username, is_admin=bool(is_admin))
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True, 'user_id': user.id})
    flash(f'User "{username}" created successfully', 'success')
    return redirect(url_for('users.users_list'))


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
@limiter.limit("5 per minute")
def users_delete(user_id):
    """Delete a user (admin only) with CSRF protection"""
    user = User.query.get_or_404(user_id)

    # Prevent deleting yourself
    from flask_login import current_user
    if user.id == current_user.id:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Cannot delete yourself'}), 400
        flash('Cannot delete yourself', 'danger')
        return redirect(url_for('users.users_list'))

    username = user.username
    db.session.delete(user)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True})
    flash(f'User "{username}" deleted successfully', 'success')
    return redirect(url_for('users.users_list'))


@bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
@limiter.limit("5 per minute")
def users_toggle_admin(user_id):
    """Toggle admin status (admin only) with CSRF protection"""
    user = User.query.get_or_404(user_id)

    # Prevent removing your own admin status
    from flask_login import current_user
    if user.id == current_user.id:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Cannot modify your own admin status'}), 400
        flash('Cannot modify your own admin status', 'danger')
        return redirect(url_for('users.users_list'))

    user.is_admin = not user.is_admin
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True, 'is_admin': user.is_admin})
    status = 'granted' if user.is_admin else 'revoked'
    flash(f'Admin privileges {status} for "{user.username}"', 'success')
    return redirect(url_for('users.users_list'))


@bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
@limiter.limit("5 per minute")
def users_reset_password(user_id):
    """Reset user password (admin only) with CSRF protection"""
    user = User.query.get_or_404(user_id)
    data = request.get_json() if request.is_json else request.form
    new_password = data.get('password', '')

    # Validate password
    is_valid, error = validate_password(new_password)
    if not is_valid:
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 400
        flash(error, 'danger')
        return redirect(url_for('users.users_list'))

    user.set_password(new_password)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True})
    flash(f'Password reset for "{user.username}"', 'success')
    return redirect(url_for('users.users_list'))
