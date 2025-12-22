from flask import Blueprint, render_template, session, redirect, url_for

traveller_bp = Blueprint('traveller', __name__)

@traveller_bp.route('/traveller/dashboard')
def dashboard():
    if session.get('role') != 'traveller':
        return redirect(url_for('auth.login'))
    return render_template('travellerDashboard.html')
