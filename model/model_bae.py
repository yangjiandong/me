# -*- coding: utf-8 -*-
# Copyright 2013 Gully Chen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from sqlalchemy.orm import object_session

from flask.ext.sqlalchemy import SQLAlchemy


db = SQLAlchemy(session_options={"expire_on_commit": False})

import common

def bind_app(app):
    db.app = app
    db.init_app(app)
    init_database(app)
    app.teardown_request(clean_cache)
    return app


def drop_all():
    db.drop_all()


def create_all():
    db.create_all()


def create_default_settings(app):
    title = app.config["SiteTitle"]

    settings = DBSiteSettings(title=title,
                              subtitle=app.config["SiteSubTitle"],
                              owner=app.config["OwnerEmail"],
                              version=DBSiteSettings.VERSION)
    settings.id = 1

    from apis import User, Post, Category

    home = Category.default_category()

    owner = User.get_user_by_email(app.config["OwnerEmail"])
    if not owner:
        owner = User.create_user(email=app.config["OwnerEmail"],
                                 password=app.config["DefaultPassword"],
                                 role="Owner")

    post = Post.get_by_id(1)
    if not post:
        Post.create_post(owner, home, title=common.Welcome_Title % title,
                         body=common.Welcome_Post % title)

    settings.inited = True
    settings.save()
    return settings


def init_database(app):
    try:
        settings = DBSiteSettings.get_site_settings()

        if not settings or not settings.inited:
            raise Exception("Can not get site settings")

        if settings.version < DBSiteSettings.VERSION:
            raise Exception("Database expired")
    except:
        from alembic import command

        command.upgrade(app.config["MIGRATE_CFG"], "head")
        settings = create_default_settings(app)

    app.config["SiteTitle"] = settings.title
    app.config["SiteSubTitle"] = settings.subtitle
    app.config["OwnerEmail"] = settings.owner


__db_get_cache = {}


def clean_cache(*args, **kwargs):
    __db_get_cache.clear()


def _norm_key(cls, id):
    return "%s_%s" % (cls.__name__, id)


def _get(cls, ids):
    multiple = isinstance(ids, (list, tuple, set))
    if not multiple:
        ids = [ids]

    results = []
    for id in ids:
        if id is None:
            results.append(None)
            continue
        key = _norm_key(cls, id)

        if key not in __db_get_cache:
            db_object = cls.query.get(id)
            __db_get_cache[key] = db_object
        else:
            db_object = __db_get_cache[key]

        if (db_object is not None) and (db_object not in db.session):
            session = object_session(db_object)
            if session is not None:
                session.expunge(db_object)
            try:
                db.session.add(db_object)
            except:
                db_object = db.session.merge(db_object)
                __db_get_cache[key] = db_object

        results.append(db_object)

    if multiple:
        return results
    else:
        return results[0]


def _remove(cls, ids):
    multiple = isinstance(ids, (list, tuple, set))
    if not multiple:
        ids = [ids]

    keys = [_norm_key(cls, id) for id in ids]
    results = [__db_get_cache.pop(k, None) for k in keys]

    if multiple:
        return results
    else:
        return results[0]


def _update(cls, objs):
    multiple = isinstance(objs, (list, tuple, set))
    if not multiple:
        objs = [objs]

    keys = []
    for obj in objs:
        if hasattr(obj, "id"):
            key = _norm_key(cls, obj.id)
            __db_get_cache[key] = obj
            keys.append(key)
        else:
            keys.append(None)

    if multiple:
        return keys
    else:
        return keys[0]


class ModelMixin(object):
    protect_attrs = []

    @classmethod
    def get_by_id(cls, id):
        return _get(cls, id)

    @classmethod
    def get_by_ids(cls, ids):
        return _get(cls, ids)

    @classmethod
    def get_all(cls, order=None):
        query = cls.query
        if order is not None:
            query = query.order_by(order)
        return query.all()

    @classmethod
    def check_exist(cls, **kwargs):
        return cls.query.filter_by(**kwargs).count() > 0

    @classmethod
    def filter_one(cls, **filters):
        return cls.query.filter_by(**filters).first()

    @classmethod
    def create(cls, *args, **kwargs):
        obj = cls(*args, **kwargs)
        return obj

    def to_dict(self):
        _res = {}
        if hasattr(self, "stats"):
            _res["stats"] = self.stats.to_dict()
        res = dict([(k, getattr(self, k)) for k in self.__dict__.keys() if
                    (not k.startswith("_") and k not in self.protect_attrs)])
        res.update(_res)
        return res

    def save(self, commit=True):
        db.session.add(self)
        if commit:
            self.commit()

        _update(self.__class__, self)

    def delete(self, commit=True):
        if hasattr(self, "stats"):

            from stats import DBStats

            dbstats = DBStats.get_by_id(self._stats_id)
            _remove(DBStats, self._stats_id)
            if dbstats:
                db.session.delete(dbstats)

        _remove(self.__class__, self.id)
        db.session.delete(self)
        if commit:
            self.commit()
        return self

    def commit(self):
        ModelMixin.commit()

    def update(self, commit=True, **kwargs):
        need_save = False
        for attr, val in kwargs.iteritems():
            if getattr(self, attr, None) != val:
                if (not attr.startswith("_")) and (attr != "id") and (attr in self.__dict__):
                    need_save = True
                    setattr(self, attr, val)
                    if attr == "public" and hasattr(self, "stats"):
                        self.stats.public = val
                        self.stats.save()

        if need_save:
            self.save(commit)

    @staticmethod
    def commit():
        try:
            db.session.commit()
        except:
            db.session.rollback()
            raise


class StatsMixin(object):
    @property
    def stats(self):

        from stats import DBStats

        dbstats = DBStats.get_by_id(self._stats_id)
        if not dbstats:
            dbstats = DBStats.create()
            dbstats.target_type = self.__class__.__name__
            dbstats.target_id = self.id
            if hasattr(self, "public"):
                dbstats.public = self.public
            dbstats.save()
            self._stats_id = dbstats.id
            self.save()
        return dbstats


########################################
## Data Models
########################################
class DBSiteSettings(db.Model, ModelMixin):
    VERSION = 1.2  # update this if tables changed

    id = db.Column(db.Integer, primary_key=True)

    version = db.Column(db.Float, default=0.0)
    title = db.Column(db.String(512))
    subtitle = db.Column(db.String(128))
    copyright = db.Column(db.String(512), default="")
    ga_tracking_id = db.Column(db.String(128))
    owner = db.Column(db.String(256))
    inited = db.Column(db.Boolean, default=False)

    def __init__(self, title, subtitle, owner, version):
        self.title = title
        self.subtitle = subtitle
        self.owner = owner
        self.version = version

    @property
    def categories(self):
        from post import DBCategory

        return DBCategory.get_all(order=DBCategory.sort)

    @property
    def UserRoles(self):
        from user import DBUser

        return DBUser.UserRoles

    @property
    def Templates(self):
        from post import DBCategory

        return DBCategory.Templates

    @property
    def Orders(self):
        from post import DBCategory

        return DBCategory.Orders

    @classmethod
    def get_site_settings(cls):
        return cls.get_by_id(1)

