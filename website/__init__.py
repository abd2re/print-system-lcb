from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from os import path, environ
from flask_login import LoginManager
import sqlalchemy as sa
from os import getenv
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
load_dotenv()

db = SQLAlchemy()
debug_mode = True

SECRET_KEY = getenv("SECRET_KEY")
SQLALCHEMY_DATABASE_URI = getenv("SQLALCHEMY_DATABASE_URI")
CONVERTAPI_SECRET = getenv("CONVERTAPI_SECRET")
DBX_APP_KEY = getenv("DBX_APP_KEY")
DBX_APP_SECRET = getenv("DBX_APP_SECRET")
REFRESH_TOKEN = getenv("REFRESH_TOKEN")
SENDER_EMAIL = getenv("SENDER_EMAIL")
SENDER_PASSWORD = getenv("SENDER_PASSWORD")
EMAIL = getenv("EMAIL")
PASSWORD = getenv("PASSWORD")
DEFAULT_PASSWORD = getenv("DEFAULT_PASSWORD")
WEBSITE = getenv("WEBSITE")


def init_app():    
    app = Flask(__name__, static_url_path='/static')
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    
    db.init_app(app)
    
    from .views import views
    from .auth import auth

    @app.route('/static/<path:path>')
    def serve_static(path):
        return send_from_directory('static', path)
    
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    
    if debug_mode:
        create_database(app)
    from .models import User
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))
    
    return app

def create_database(app):
    db.create_all(app=app)
    print('Created Database!')


