# routes/community.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.community import create_thread, get_all_threads, get_thread, add_comment, delete_thread, delete_comment as delete_comment_db

community_bp = Blueprint("traveller_community", __name__, url_prefix="/community")
#database theke threads ane and frontend e pathay 
@community_bp.route("/")
def community_home():
    threads = get_all_threads()
    return render_template("traveller/community/community_home.html", threads=threads)

@community_bp.route("/thread/<thread_id>")
def view_thread(thread_id):
    thread = get_thread(thread_id)
    if not thread:
        flash("Thread not found.", "danger")
        return redirect(url_for("traveller_community.community_home"))
    return render_template("traveller/community/thread.html", thread=thread)
# Show or create new thread
@community_bp.route("/new", methods=["GET", "POST"])
def new_thread():
    if "user_id" not in session:
        flash("You must be logged in to create a thread.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        role = session.get("role")

        create_thread(title, content, session["user_id"], role)
        flash("Thread created successfully!", "success")
        return redirect(url_for("traveller_community.community_home"))

    return render_template("traveller/community/new_post.html")
# sudhu post korar jonno
@community_bp.route("/thread/<thread_id>/comment", methods=["POST"])
def post_comment(thread_id):
    if "user_id" not in session:
        flash("You must be logged in to comment.", "danger")
        return redirect(url_for("auth.login"))

    comment_text = request.form.get("comment")
    role = session.get("role")
    add_comment(thread_id, comment_text, session["user_id"], role)
    flash("Comment added!", "success")
    return redirect(url_for("traveller_community.view_thread", thread_id=thread_id))
#thread delete korar jonno
@community_bp.route("/thread/<thread_id>/delete", methods=["POST"])
def delete_thread_route(thread_id):
    thread = get_thread(thread_id)
    if not thread or str(thread.get("user_id")) != str(session.get("user_id")):
        flash("You are not authorized to delete this thread.", "danger")
        return redirect(url_for("traveller_community.community_home"))
    delete_thread(thread_id)
    flash("Thread deleted successfully!", "success")
    return redirect(url_for("traveller_community.community_home"))
#delete comment korar jonno
@community_bp.route("/thread/<thread_id>/comment/<comment_id>/delete", methods=["POST"])
def delete_comment_route(thread_id, comment_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in.", "danger")
        return redirect(url_for("traveller_community.view_thread", thread_id=thread_id))
    result = delete_comment_db(thread_id, comment_id, user_id)
    if result.modified_count:
        flash("Comment deleted.", "success")
    else:
        flash("You are not authorized to delete this comment.", "danger")
    return redirect(url_for("traveller_community.view_thread", thread_id=thread_id))
