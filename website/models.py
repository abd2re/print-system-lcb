from . import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(1000))
    name = db.Column(db.String(50))
    quota = db.Column(db.Integer)
    first_time = db.Column(db.Boolean)
    admin = db.Column(db.Boolean)
    prints = db.relationship('printDoc')

class printDoc(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100))
    true_filename = db.Column(db.String(100))
    file_path = db.Column(db.String(1000))
    true_file_path = db.Column(db.String(1000)) 
    copies = db.Column(db.Integer)
    double_sided = db.Column(db.Boolean)
    comments = db.Column(db.String(1000))
    due_date = db.Column(db.DateTime())
    nice_date = db.Column(db.String(400))
    user_email = db.Column(db.String(50))
    user_name = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    completed = db.Column(db.Boolean)
    quota = db.Column(db.Integer)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    issue = db.Column(db.Boolean)
    message = db.Column(db.String(1000))
    