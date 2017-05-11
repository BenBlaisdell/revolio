import flask_sqlalchemy
import sqlalchemy.dialects.postgresql


db = flask_sqlalchemy.SQLAlchemy()


class SubscriptionOrm(db.Model):
    __tablename__ = 'subscription'

    id = db.Column(db.String, primary_key=True)
    state = db.Column(db.String)
    bucket = db.Column(db.String)
    prefix = db.Column(db.String)
    data = db.Column(sqlalchemy.dialects.postgresql.JSONB)


class NotificationOrm(db.Model):
    __tablename__ = 'notification'

    id = db.Column(db.String, primary_key=True)
    bucket = db.Column(db.String)
    prefix = db.Column(db.String)
    config_id = db.Column(db.String)
    data = db.Column(sqlalchemy.dialects.postgresql.JSONB)


class ElementOrm(db.Model):
    __tablename__ = 'element'

    id = db.Column(db.String, primary_key=True)
    state = db.Column(db.String)
    bucket = db.Column(db.String)
    key = db.Column(db.String)
    subscription_id = db.Column(db.String)
    data = db.Column(sqlalchemy.dialects.postgresql.JSONB)
