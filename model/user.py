from datetime import datetime
import hashlib

from model_bae import ModelMixin, StatsMixin,db
import common
from stats import DBStats


#db = SQLAlchemy(session_options={"expire_on_commit": False})

class DBUser(db.Model, ModelMixin, StatsMixin):
    __tablename__ = "db_user"

    UserRoles = common.UserRoles

    id = db.Column(db.Integer, primary_key=True)

    protect_attrs = ["password", "posts",  "email"]

    email = db.Column(db.String(128), unique=True, index=True)
    password = db.Column(db.String(256))
    nickname = db.Column(db.String(40), unique=True, index=True)
    active = db.Column(db.Boolean, default=True)
    avatar = db.Column(db.String(512), default="")
    role = db.Column(db.Enum(*UserRoles), default="User")
    joined_date = db.Column(db.DateTime, default=datetime.utcnow)

    _stats_id = db.Column(db.Integer, db.ForeignKey(DBStats.__tablename__ + '.id', ondelete="SET NULL"))

    def __init__(self, email,
                 nickname="", avatar="", role="User", active=True):
        self.email = email
        self.nickname = nickname or self.email.split("@")[0]
        self.avatar = avatar
        self.role = role
        self.active = active

    def __repr__(self):
        return '<DBUser %r : %s>' % (self.nickname, self.email)

    @property
    def avatar_url(self):
        if not self.avatar:
            return "http://www.gravatar.com/avatar/%s?s=64" % (
                hashlib.md5(self.email.lower().strip()).hexdigest())
        return self.avatar

    @classmethod
    def get_user_by_email(cls, email):
        return cls.filter_one(email=email)

    def to_dict(self):
        res = ModelMixin.to_dict(self)
        res["avatar_url"] = self.avatar_url
        return res
