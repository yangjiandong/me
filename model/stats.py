from model_bae import ModelMixin, db


class DBStats(db.Model, ModelMixin):
    __tablename__ = "db_stats"

    id = db.Column(db.Integer, primary_key=True)

    target_type = db.Column(db.String(128))
    target_id = db.Column(db.Integer)
    public = db.Column(db.Boolean, default=True)

    view_count = db.Column(db.Integer, default=0)
    share_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    unlike_count = db.Column(db.Integer, default=0)

    post_count = db.Column(db.Integer, default=0)
    photo_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)

    def increase(self, name, delta=1, commit=True):
        val = getattr(self, name)
        val += delta
        setattr(self, name, val)
        if commit:
            self.save()

    def decrease(self, name, delta=1, commit=True):
        val = getattr(self, name)
        val -= delta
        if val < 0:
            val = 0
        setattr(self, name, val)
        if commit:
            self.save()

    def set(self, name, value, commit=True):
        setattr(self, name, value)
        if commit:
            self.save()
