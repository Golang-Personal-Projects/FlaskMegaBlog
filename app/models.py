from datetime import datetime, timezone
from typing import Optional
import jwt
from flask_login import UserMixin
from sqlalchemy.dialects.mysql import INTEGER
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from sqlalchemy import String, ForeignKey, Table, Column, func, select, or_
from sqlalchemy.orm import Mapped, mapped_column, relationship, WriteOnlyMapped, aliased
from app import login
from hashlib import md5
from time import time
from flask import current_app
from app.search import query_index
from app.search import add_to_index, remove_from_index, query_index

followers = Table(
    "followers",
    db.metadata,
    Column("follower_id", INTEGER, ForeignKey("user.id"), primary_key=True),
    Column("followed_id", INTEGER, ForeignKey("user.id"), primary_key=True)
)


class User(db.Model, UserMixin):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    email: Mapped[str] = mapped_column(String(120), index=True, unique=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(256))
    posts: WriteOnlyMapped["Post"] = relationship(back_populates="author")
    about_me: Mapped[Optional[str]] = mapped_column(String(140))
    last_seen: Mapped[Optional[datetime]] = mapped_column(default=lambda: datetime.now(tz=timezone.utc))
    following: WriteOnlyMapped["User"] = relationship(secondary=followers, primaryjoin=(followers.c.follower_id == id),
                                                      secondaryjoin=(followers.c.followed_id == id),
                                                      back_populates="followers")
    followers: WriteOnlyMapped["User"] = relationship(secondary=followers, primaryjoin=(followers.c.followed_id == id),
                                                      secondaryjoin=(followers.c.follower_id == id),
                                                      back_populates="following")

    def __repr__(self):
        return "User {}".format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode("utf-8")).hexdigest()
        return f"https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}"

    def follow(self, user):
        if not self.is_following(user):
            self.following.add(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.following.remove(user)

    def is_following(self, user):
        query = self.following.select().where(User.id == user.id)
        return db.session.scalar(query) is not None

    def followers_count(self):
        query = select(func.count()).select_from(
            self.followers.select().subquery())
        return db.session.scalar(query)

    def following_count(self):
        query = select(func.count()).select_from(
            self.following.select().subquery())
        return db.session.scalar(query)

    def following_posts(self):
        Author = aliased(User)
        Follower = aliased(User)
        return (
            select(Post)
            .join(Post.author.of_type(Author))
            .join(Author.followers.of_type(Follower), isouter=True)
            .where(or_(
                Follower.id == self.id,
                Author.id == self.id, ))
            .group_by(Post)
            .order_by(Post.timestamp.desc())
        )

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {"reset_password": self.id, "exp": time() + expires_in}, current_app.config["SECRET_KEY"], algorithm="HS256"
        )

    @staticmethod
    def verify_reset_password(token):
        try:
            id = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])["reset_password"]
        except:
            return
        return db.session.get(User, id)


@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))


class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return [], 0
        when = []
        for i in range(len(ids)):
            when.append(ids[i], i)
        query = select(cls).where(cls.id.in_(ids)).order_by(db.case(*when, value=cls.id))
        return db.session.scalars(query), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in db.session.scalars(sa.select(cls)):
            add_to_index(cls.__tablename__, obj)


db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


class Post(SearchableMixin, db.Model):
    __searchable__ = ['body']
    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str] = mapped_column(String(140))
    timestamp: Mapped[datetime] = mapped_column(index=True, default=lambda: datetime.now(tz=timezone.utc))
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), index=True)
    author: Mapped[User] = relationship(back_populates="posts")
    language: Mapped[Optional[str]] = mapped_column(String(5))

    def __repr__(self):
        return "<Post {}>".format(self.body)
