from datetime import datetime, timezone
from flask_babel import get_locale
from flask_login import current_user, login_required
from flask import render_template, flash, url_for, request, current_app, g
from langdetect import detect, LangDetectException
from sqlalchemy import select
from werkzeug.utils import redirect
from app.main.forms import EditProfile, EmptyForm, PostForm, MessageForm
from app import db
from app.models import User, Post, Message, Notification
from app.main import bp
from app.translate import translate
from app.main.forms import SearchForm
from flask_babel import _


@bp.route("/", methods=["GET", "POST"])
@bp.route("/index", methods=["GET", "POST"])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        try:
            language = detect(form.post.data)
        except LangDetectException:
            language = ""
        post = Post(body=form.post.data, author=current_user, language=language)
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
        g.search_form = SearchForm()
    g.locale = str(get_locale())


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
    next_url = url_for("main.user", username=user.username, page=posts.next_num) if posts.next_num else None
    prev_url = url_for("main.user", username=user.username, page=posts.prev_num) if posts.prev_num else None
    form = EmptyForm()
    return render_template("user.html", user=user, posts=posts, form=form, prev_url=prev_url, next_url=next_url)


@bp.route("/translate", methods=["POST"])
@login_required
def translate_text():
    data = request.get_json()
    return {
        "text": translate(data['text'],
                          data['source_language'],
                          data['dest_language'])
    }


@bp.route("/search")
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for("main.explore"))
    page = request.args.get("page", 1, type=int)
    posts, total = Post.search(g.search_form.q.data, page, current_app.config["POSTS_PER_PAGE"])
    next_url = url_for("main.search", q=g.search_form.q.data, page=page - 1) \
        if total > page * current_app.config["POSTS_PER_PAGE"] else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('search.html', title=_('Search'), posts=posts,
                           next_url=next_url, prev_url=prev_url)


@bp.route("/user/<username>/popup")
def user_popup(username):
    user = db.first_or_404(select(User).where(User.username == username))
    form = EmptyForm()
    return render_template("user_popup.html", user=user, form=form)


@bp.route("/send_message/<recipient>", methods=["GET", "POST"])
@login_required
def send_message(recipient):
    user = db.first_or_404(select(User).where(User.username == recipient))
    form = MessageForm()
    if form.validate_on_submit():
        user.add_notification('unread_message_count', user.unread_message_count())
        msg = Message(author=current_user, recipient=user, body=form.message.data)
        db.session.add(msg)
        db.session.commit()
        flash(_("Your message has been sent."))
        return redirect(url_for("main.user", username=recipient))
    return render_template("send_message.html", title=_("Send Message"), form=form, recipient=recipient)


@bp.route("/messages")
@login_required
def messages():
    current_user.last_message_read_time = datetime.now(tz=timezone.utc)
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    page = request.args.get("page", 1, type=int)
    query = current_user.messages_received.select().order_by(Message.timestamp.desc())
    messages = db.paginate(query, page=page, per_page=current_app.config["POSTS_PER_PAGE"], error_out=False)
    next_url = url_for('main.messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num) \
        if messages.has_prev else None
    return render_template('messages.html', messages=messages.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    query = current_user.notifications.select().where(Notification.timestamp > since).order_by(
        Notification.timestamp.asc())
    notifications = db.session.scalars(query)
    return [{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications]

@bp.route('/export_posts')
@login_required
def export_posts():
    if current_user.get_task_in_progress('export_posts'):
        flash('An export task is currently in progress')
    else:
        current_user.launch_task('export_posts', _('Exporting posts...'))
        db.session.commit()
    return redirect(url_for('main.user', username=current_user.username))