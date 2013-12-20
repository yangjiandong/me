from datetime import datetime
from model_bae import ModelMixin, StatsMixin,db
from stats import DBStats
from post import DBPost

class DBTag(db.Model, ModelMixin, StatsMixin):
    __tablename__ = "db_tag"

    protect_attrs = ["_norm_name"]

    id = db.Column(db.Integer, primary_key=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    _norm_name = db.Column(db.String(64))

    name = db.Column(db.String(64))

    post_count = db.Column(db.Integer, default=0)

    _post_id_list = db.Column(db.Text, default="")

    _stats_id = db.Column(db.Integer, db.ForeignKey(DBStats.__tablename__ + '.id', ondelete="SET NULL"))

    def __init__(self, name):
        self.name = name.strip()
        self._norm_name = name.strip().lower()
        self.post_count = 0
        self._post_id_list = ""

    @property
    def post_ids(self):
        if not self._post_id_list:
            return []
        return [str(id) for id in self._post_id_list.split(",") if id and id.strip()]

    @post_ids.setter
    def post_ids(self, value):
        value = map(str, value)
        self._post_id_list = ",".join(value)

    def add_post_id(self, post_id):
        post_id = str(post_id)
        if post_id not in self.post_ids:
            self.post_count += 1
            self._post_id_list += "," + str(post_id)
            self.save()

    def remove_post_id(self, post_id):
        post_id = str(post_id)
        post_ids = self.post_ids
        if post_id in post_ids:
            post_ids.remove(post_id)
            self.post_count -= 1
            self.post_ids = post_ids
            self.save()

    def get_posts(self, page=1, per_page=10):
        posts_list = map(long, self.post_ids)
        posts_list = posts_list[::-1]
        ids = posts_list[(page-1)*per_page:page*per_page]
        return [post for post in DBPost.get_by_ids(ids) if post and post.public]

    @classmethod
    def hot_tags(cls, count=16):
        query = DBTag.query.order_by("post_count desc").filter(DBTag.post_count > 0)
        return query.limit(count).all()

    @classmethod
    def get_tag_by_name(cls, name):
        return DBTag.filter_one(_norm_name=name.strip().lower())




