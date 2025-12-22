from flask import Blueprint, render_template, session, redirect, url_for

host_bp = Blueprint('host', __name__)

@host_bp.route('/host/profile')
def profile():
    if session.get('role') != 'host':
        return redirect(url_for('auth.login'))
    return render_template('hostProfile.html')
