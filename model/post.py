from datetime import datetime
from model_bae import ModelMixin, StatsMixin, db
# from category import DBCategory
from user import DBUser
from stats import DBStats
import common


class DBCategory(db.Model, ModelMixin, StatsMixin):
    __tablename__ = "db_category"

    Templates = common.Templates
    Orders = common.Orders

    protect_attrs = ["posts"]

    id = db.Column(db.Integer, primary_key=True)

    url = db.Column(db.String(64), unique=True, index=True)
    name = db.Column(db.String(64))
    sort = db.Column(db.Integer, default=0)
    posts_per_page = db.Column(db.Integer, default=5)

    order = db.Column(db.Enum(*Orders), default=Orders[1])
    template = db.Column(db.Enum(*Templates), default=Templates[0])
    content = db.Column(db.Text)  # for template "Text" only

    _stats_id = db.Column(db.Integer, db.ForeignKey(DBStats.__tablename__ + '.id', ondelete="SET NULL"))

    def __init__(self, url, name, sort=0, order=Orders[1], template=Templates[0]):
        self.url = url
        self.name = name
        self.sort = sort
        self.order = order
        self.template = template

    def __repr__(self):
        return '<DBCategory %r : %s>' % (self.url, self.name)

    @property
    def Posts(self):
        return self.posts

    def get_posts(self, page=1, per_page=10, include_no_published=False, start_cursor=""):
        if self.url == "":  # Home category
            query = DBPost.query
        else:
            query = self.Posts

        query = query.order_by("sticky desc").order_by("post_date " + self.order)

        if not include_no_published:
            query = query.filter_by(public=True)

        # return (items, cursor) for GAE compatibility
        return query.paginate(page, per_page, False).items, ""

    @classmethod
    def get_by_url(cls, category_url):
        return cls.filter_one(url=category_url)

class DBPost(db.Model, ModelMixin, StatsMixin):
    __tablename__ = "db_post"

    protect_attrs = ["_author", "author", "_category", "category", "photos", "comments",
                     "Comments", "stats", "tags", "_tag_list"]

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(128))
    body = db.Column(db.Text)

    public = db.Column(db.Boolean, default=True)
    sticky = db.Column(db.Boolean, default=False)

    post_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # post event datetime
    updated_date = db.Column(db.DateTime, onupdate=datetime.utcnow, index=True)  # updated datetime

    category_id = db.Column(db.Integer, db.ForeignKey(DBCategory.__tablename__ + '.id', ondelete="SET NULL"),
                            index=True)
    _category = db.relationship('DBCategory', backref=db.backref('posts', lazy='dynamic'))

    author_id = db.Column(db.Integer, db.ForeignKey(DBUser.__tablename__ + ".id", ondelete="SET NULL"), index=True)
    _author = db.relationship('DBUser', backref=db.backref('posts', lazy='dynamic'))

    _stats_id = db.Column(db.Integer, db.ForeignKey(DBStats.__tablename__ + '.id', ondelete="SET NULL"))
    _tag_list = db.Column(db.Text, default="")


    def __init__(self, author_id, category_id, title="", body="", post_date=None):
        self.title = title
        self.body = body
        self.author_id = author_id
        self.category_id = category_id
        if post_date is None:
            post_date = datetime.utcnow()
        self.post_date = post_date
        self.updated_date = datetime.utcnow()

    def __repr__(self):
        return '<Post %s>' % self.id

    @property
    def author(self):
        return DBUser.get_by_id(self.author_id)

    @property
    def category(self):
        return DBCategory.get_by_id(self.category_id)

    @property
    def Comments(self):
        return self.comments.order_by("created_date").all()

    @property
    def tags(self):
        if not self._tag_list:
            return []
        return [tag for tag in self._tag_list.split(",") if tag and tag.strip()]

    @tags.setter
    def tags(self, value):
        self._tag_list = ",".join(list(set(value)))

    def to_dict(self):
        res = ModelMixin.to_dict(self)
        res["author"] = self.author.to_dict() if self.author is not None else {}
        res["category"] = self.category.to_dict() if self.category is not None else {}
        res["photos"] = [photo.to_dict() for photo in self.photos if photo is not None]
        res["tags"] = self.tags
        return res

    @classmethod
    def hot_posts(cls, count=8, order="view_count desc"):
        query = DBStats.query.filter_by(public=True).filter_by(target_type=cls.__name__).order_by(order)
        ids = [stats.target_id for stats in query.limit(count).all()]
        return [post for post in cls.get_by_ids(ids) if post and post.public]

    @classmethod
    def latest_posts(cls, count=8, order="updated_date desc"):
        return cls.query.filter_by(public=True).order_by(order).limit(count).all()


class DBComment(db.Model, ModelMixin, StatsMixin):
    __tablename__ = "db_comment"

    protect_attrs = ["post", "_post"]

    id = db.Column(db.Integer, primary_key=True)

    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.Column(db.String(32), nullable=False)
    content = db.Column(db.Text, default="")
    deleted = db.Column(db.Boolean, default=False)

    parent_id = db.Column(db.Integer, default=-1)
    post_id = db.Column(db.Integer, db.ForeignKey(DBPost.__tablename__ + ".id", ondelete="SET NULL"), index=True)
    _post = db.relationship('DBPost', backref=db.backref('comments', lazy='dynamic'))

    _stats_id = db.Column(db.Integer, db.ForeignKey(DBStats.__tablename__ + '.id', ondelete="SET NULL"))

    def __init__(self, author, content, post_id, parent_id=-1):
        self.author = author
        self.content = content
        self.post_id = post_id
        self.parent_id = parent_id

    @property
    def post(self):
        return DBPost.get_by_id(self.post_id)

    def to_dict(self):
        res = ModelMixin.to_dict(self)
        if self.deleted:
            from settings import gettext

            res["content"] = gettext("Comment Deleted")
        return res


class DBPhoto(db.Model, ModelMixin, StatsMixin):
    __tablename__ = "db_photo"

    protect_attrs = ["post", "_post"]

    id = db.Column(db.Integer, primary_key=True)

    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    url = db.Column(db.String(1024), default="")
    url_thumb = db.Column(db.String(1024), default="")
    mime = db.Column(db.String(128), default="application/octet-stream")
    alt = db.Column(db.String(140), default="")
    real_file = db.Column(db.String(1024), default="")
    real_file_thumb = db.Column(db.String(1024), default="")

    public = db.Column(db.Boolean, default=True)

    post_id = db.Column(db.Integer, db.ForeignKey(DBPost.__tablename__ + ".id", ondelete="SET NULL"), index=True)
    _post = db.relationship('DBPost', backref=db.backref('photos', lazy='dynamic'))

    _stats_id = db.Column(db.Integer, db.ForeignKey(DBStats.__tablename__ + '.id', ondelete="SET NULL"))

    def __init__(self, url="", real_file="", alt="", mime="application/octet-stream"):
        self.url = url
        self.alt = alt
        self.mime = mime
        self.real_file = real_file

    @property
    def post(self):
        return DBPost.get_by_id(self.post_id)

    @classmethod
    def hot_photos(cls, count=12, order="like_count desc"):
        query = DBStats.query.filter_by(public=True).filter_by(target_type=cls.__name__).order_by(order)
        ids = [stats.target_id for stats in query.limit(count).all()]
        return [photo for photo in cls.get_by_ids(ids) if photo]

