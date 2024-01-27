from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User
from . import *
from flask_login import login_user, login_required, logout_user, current_user

auth = Blueprint('auth',__name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if db.session.query(User.id).first() is None:
        user = User(email=EMAIL,name="abd2re",
                    password=generate_password_hash(PASSWORD, method='sha256'),
                    quota=1000,first_time=False,admin=True)
        db.session.add(user)
        db.session.commit()
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash("Connexion réussie !",category="success")
                login_user(user, remember=True)
                if user.first_time:
                    return redirect(url_for('auth.change_password'))
                else:
                    return redirect(url_for('views.prints'))
            else:
                flash("Mot de passe incorrect, essayez à nouveau",category="error")
        else:
            flash("L'e-mail n'existe pas",category="error")
        
    return render_template("login.html", user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == "POST":
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        if password1 == password2:
            current_user.password = generate_password_hash(password1, method='sha256')
            current_user.first_time = False
            db.session.commit()
            flash("Le mot de passe a été mis à jour",category="success")
            return redirect(url_for('views.prints'))
        else:
            flash("Les mots de passe ne correspondent pas",category="error")
    return render_template("change_password.html", user=current_user)