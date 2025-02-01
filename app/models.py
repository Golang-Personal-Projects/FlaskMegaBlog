from datetime import datetime, timezone
from typing import Optional
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import  db
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship, WriteOnlyMapped
from app import login

class User(db.Model, UserMixin):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    email: Mapped[str] = mapped_column(String(120), index=True, unique=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(256))
    posts: WriteOnlyMapped["Post"] = relationship(back_populates="author")

    def __repr__(self):
        return "User {}".format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Post(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str] = mapped_column(String(140))
    timestamp: Mapped[datetime] = mapped_column(index=True, default=lambda: datetime.now(tz=timezone.utc))
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), index=True)
    author: Mapped[User] = relationship(back_populates="posts")

    def __repr__(self):
        return "<Post {}>".format(self.body)

@login.user_loader
def load_user(id):
    return db.session.get(User,int(id))
