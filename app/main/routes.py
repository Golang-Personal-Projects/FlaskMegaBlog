from datetime import datetime, timezone
from flask_login import current_user, login_required
from flask import render_template, flash, url_for, request, current_app
from sqlalchemy import select
from werkzeug.utils import redirect
from app.main.forms import EditProfile, EmptyForm, PostForm
from app import db
from app.models import User, Post
from app.main import bp


@bp.route("/", methods=["GET", "POST"])
@bp.route("/index", methods=["GET", "POST"])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash("Your post is now live!!")
        return redirect(url_for("main.index"))
    page = request.args.get("page", 1, type=int)
    posts = db.paginate(current_user.following_posts(), page=page, per_page=current_app.config["POSTS_PER_PAGE"],
                        error_out=False)
    next_url = url_for("main.index", page=posts.next_num) if posts.has_next else None
    prev_url = url_for("main.index", page=posts.prev_num) if posts.prev_num else None
    return render_template("index.html", title="Home Page", form=form, posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(tz=timezone.utc)
        db.session.commit()


@bp.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfile(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Changes have been saved!")
        return redirect(url_for("main.index"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template("edit.html", title="Edit Profile", form=form)


@bp.route("/follow/<username>", methods=["POST"])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(select(User).where(User.username == username))
        if user is None:
            flash(f"User {username} not found.")
            return redirect(url_for("main.index"))
        if user == current_user:
            flash("You cannot follow yourself!")
            return redirect(url_for("main.user", username=username))
        current_user.follow(user)
        db.session.commit()
        flash(f"You are following {username}")
        return redirect(url_for("main.user", username=username))
    else:
        return redirect(url_for("main.index"))


@bp.route("/unfollow/<username>", methods=["POST"])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(select(User).where(User.username == username))
        if user is None:
            flash(f"User {username} not found.")
            return redirect(url_for("main.index"))
        if user == current_user:
            flash("You cannot unfollow yourself!")
            return redirect(url_for("main.user", username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(f"You are not following {username}")
        return redirect(url_for("main.user", username=username))
    else:
        return redirect(url_for("main.index"))


@bp.route("/explore")
@login_required
def explore():
    page = request.args.get("page", 1, type=int)
    query = select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(query, error_out=False, page=page, per_page=current_app.config["POSTS_PER_PAGE"])
    next_url = url_for("main.explore", page=posts.next_num) if posts.has_next else None
    prev_url = url_for("main.explore", page=posts.prev_num) if posts.prev_num else None
    return render_template("index.html", title="Explore", posts=posts.items, next_url=next_url, prev_url=prev_url)


@bp.route("/user/<username>")
@login_required
def user(username):
    user = db.first_or_404(select(User).where(User.username == username))
    page = request.args.get("next")
    query = user.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page, per_page=current_app.config["POSTS_PER_PAGE"], error_out=False)
    next_url = url_for("user", username=user.username, page=posts.next_num) if posts.next_num else None
    prev_url = url_for("user", username=user.username, page=posts.prev_num) if posts.prev_num else None
    form = EmptyForm()
    return render_template("user.html", user=user, posts=posts, form=form, prev_url=prev_url, next_url=next_url)
