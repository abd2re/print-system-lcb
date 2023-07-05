from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, printDoc, Notification
from . import *
from flask_login import login_user, login_required, logout_user, current_user
from io import BytesIO
from datetime import datetime
import random
from werkzeug.utils import secure_filename
import json
import os
import zipfile
import xml.dom.minidom
import PyPDF4
import convertapi
import dropbox
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


dbx = dropbox.Dropbox(
        app_key = DBX_APP_KEY,
        app_secret = DBX_APP_SECRET,
        oauth2_refresh_token = REFRESH_TOKEN
    )


def upload(filepath,filename):
    with open(filepath, "rb") as f:
        dbx.files_upload(f.read(),f"/uploads/{filename}")
              
def dropbox_get_link(filename):
    try:
        shared_link_metadata = dbx.sharing_create_shared_link_with_settings(f"/uploads/{filename}")
        shared_link = shared_link_metadata.url
        return shared_link.replace('?dl=0', '?dl=1').replace("www.dropbox","dl.dropboxusercontent")
    except dropbox.exceptions.ApiError as exception:
        if exception.error.is_shared_link_already_exists():
            shared_link_metadata = dbx.sharing_get_shared_links(f"/uploads/{filename}")
            shared_link = shared_link_metadata.links[0].url
            return shared_link.replace('?dl=0', '?dl=1').replace("www.dropbox","dl.dropboxusercontent")
        
def delete(filename):
    dbx.files_delete(f"/uploads/{filename}")

convertapi.api_secret = CONVERTAPI_SECRET
def convert(path,true_path):
    convertapi.convert('pdf', {'File': path}, from_format = 'docx').save_files(true_path)


views = Blueprint('views',__name__)

default_password = "lcb"

headings = ("ID","E-mail","Nom","Quota","Administrateur")

def toBoolean(option):
    if option == "on":
        return True
    else:
        return False

def toOuinNon(boo):
    if boo:
        return "Oui"
    else:
        return "Non"

@views.route('/users', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.admin:
        pass
    else:
        return redirect('/')
    if request.method == 'POST':
        email = request.form.get("email")
        name = request.form.get("name")
        admin = toBoolean(request.form.get("admin"))
        user = User.query.filter_by(email=email).first()
        if not email:
            flash('E-mail vide', category='error')
        elif not name:
            flash('Nom vide', category='error')
        elif user:
            flash('L\'e-mail existe déjà', category='error')
        else:
            new_user = User(email=email,name=name,password=generate_password_hash(default_password, method='sha256'),quota=1000,first_time=True,admin=admin)
            db.session.add(new_user)
            db.session.commit()
            flash("Compte utilisateur ajouté !",category="success")
            return redirect(url_for('views.create_user'))

    return render_template("users.html",headings=headings,user=current_user,userDB=User.query.all(), printDB=printDoc.query.all())


@views.route('/delete_user', methods=['POST'])
@login_required
def delete_user():
    user = json.loads(request.data)
    userId = user['userId']
    user = User.query.get(userId)
    if user and not user.admin:
        db.session.delete(user)
        db.session.commit()
    return jsonify({})




@views.route('/', methods=['GET', 'POST'])
@login_required
def main():
    if current_user.is_authenticated:
        return redirect(url_for('views.prints'))
    else:
        return redirect(url_for('auth.login'))


print_headings = ("ID","Statut","Nom de fichier","Fichier","Copies","Recto-verso","Date d'échéance","Quota","Commentaires supplémentaires")
        

def date_processing(date):
    datetime_obj = datetime.strptime(date,'%Y-%m-%dT%H:%M')
    return datetime_obj.strftime("%d/%m/%Y, %H:%M")
        


@views.route('/prints', methods=['GET', 'POST'])
@login_required
def prints():
    if request.method == "GET":
        try:
            notif = Notification.query.get(1)
            if notif.issue:    
                flash(f"Notification: {notif.message}", category='notify')
        except:
            pass
    if request.method == "POST":
        document = request.files['document']
        copies = request.form.get("copies")
        double_sided = toBoolean(request.form.get("double_sided"))
        comments = request.form.get("comments")
        due_date = request.form.get("due_date")
        if not document:
            flash("Aucun document n'a été téléchargé",category="error")
        elif not copies:
            flash("Indiquer le nombre de copies",category="error")
        elif not due_date:
            flash("Choisissez une date et une heure d'impression",category="error")
        else:
            document.filename = secure_filename(document.filename)
            if printDoc.query.filter_by(filename=document.filename).first():
                document.filename = str(random.randint(0,9999)) + document.filename
            path = os.path.join("website/", document.filename)
            document.save(path)
            name,ext = os.path.splitext(document.filename)
            if double_sided:
                quota = (num_of_pages(path)//2+num_of_pages(path)%2)*int(copies)
            else:
                quota = num_of_pages(path)*int(copies)
            if ext in ('.docx','.doc'):
                true_filename = name+"_pdf.pdf"
                true_path = os.path.join("website/", true_filename)
                convert(path, true_path)
                true_path = os.path.join("website/", true_filename)
                upload(true_path,true_filename)
                os.remove(true_path)
            else:
                true_filename = document.filename
                true_path = path
            upload(path,document.filename)
            os.remove(path)
            true_date = date_processing(due_date)
            if quota > current_user.quota:
                flash(f"Quota dépassé ({quota}), essayez d'imprimer recto-verso, imprimez moins de copies ou contactez un administrateur",category="error")
            else:
                dbx_path = dropbox_get_link(document.filename)
                dbx_true_path = dropbox_get_link(true_filename)
                new_print = printDoc(filename=document.filename,file_path=dbx_path,true_filename=true_filename,true_file_path=dbx_true_path,copies=copies,double_sided=double_sided,comments=comments,due_date=due_date,nice_date=true_date,completed=False,user_id=current_user.id,user_email=current_user.email,user_name=current_user.name,quota=quota)
                db.session.add(new_print)
                db.session.commit()
                flash("Nouvelle impression envoyée !", category="success")
            return redirect(url_for('views.prints'))

    return render_template("prints.html",headings=print_headings,user=current_user, printDB=printDoc.query.all())

        
@views.route('/delete_elem', methods=['POST'])
@login_required
def delete_elem():
    elem = json.loads(request.data)
    elemId = elem['elemId']
    elem = printDoc.query.get(elemId)
    if elem:
        try:
            delete(elem.filename)
        except:
            pass
        try:
            delete(elem.true_filename)
        except:
            pass
        db.session.delete(elem)
        db.session.commit()
    return jsonify({})
        


queue_headings = ("ID","Utilisateur","Nom de fichier","Fichier","Copies","Recto-verso","Date d'échéance","Quota","Commentaires supplémentaires","Terminée?")
queue_headings_out = ("ID","Utilisateur","Nom de fichier","Fichier","Copies","Recto-verso","Date d'échéance","Quota","Commentaires supplémentaires")

@views.route('/queue', methods=['GET', 'POST'])
@login_required
def queue():
    if current_user.admin:
        pass
    else:
        return redirect('/')
    try:
        if request.method == "GET":
            notif = Notification.query.get(1)
            if notif.issue:    
                flash(f"Notification: {notif.message}", category='notify')
    except:
        pass
    if request.method == "POST":
        elem_id = request.form.get("printing")
        elem = printDoc.query.get(int(elem_id))
        elem.completed = True
        if elem.file_path != elem.true_file_path:
            try:
                delete(elem.true_filename)
            except:
                pass
        user = User.query.get(int(elem.user_id))
        user.quota -= elem.quota
        flash('Impression du document confirmé', category='success')
        db.session.commit()
        send_mail(user,elem)
        
        return redirect(url_for('views.queue'))
    return render_template("queue.html",headings=queue_headings,user=current_user,printDB=printDoc.query.all(),headings2=queue_headings_out)

def num_of_pages(filepath):
    extension = os.path.splitext(filepath)[1]
    if extension in ('.docx','.doc'):
        document = zipfile.ZipFile(filepath)
        dxml = document.read('docProps/app.xml')
        uglyXml = xml.dom.minidom.parseString(dxml)
        page = uglyXml.getElementsByTagName('Pages')[0].childNodes[0].nodeValue
    else:
        document = open(filepath, 'rb')
        page = PyPDF4.PdfFileReader(document).numPages
        document.close()
    return int(page)

@views.route('/notify', methods=['GET', 'POST'])
@login_required
def notify():
    if current_user.admin:
        pass
    else:
        return redirect('/')
    if db.session.query(Notification.id).first() is None:
        notif = Notification(issue=False,message="")
        db.session.add(notif)
        db.session.commit()
    else:
        notif = Notification.query.get(1) 
    if request.method == 'POST':
        if not notif.issue:
            message = request.form.get("message")
            if not message:
                flash('Rédiger un message de notification',category="error")
                return redirect(url_for('views.notify')) 
            else:
                flash('Notification envoyée',category="success")
                notif.issue = True
                notif.message = message
                db.session.commit()
        else:
            flash('Notification supprimée',category="success")
            notif.issue = False
            db.session.commit()
        
        return redirect(url_for('views.notify'))       
    
    return render_template("notify.html", issue=notif.issue, message=notif.message, user=current_user, printDB=printDoc.query.all())


def send_mail(user,elem):
    email_address = user.email
    email_subject = f'Votre document a été imprimé [id:{elem.id}]'
    email_message = f'''Destinataire: {user.name}
Nom du document: {elem.filename}
Copies: {elem.copies}
Recto-verso: {toOuinNon(elem.double_sided)}
Quota de l'impression: {elem.quota}

Quota restant apres cette impression: {user.quota}

Merci, lcb-impression
'''

    sender_email = SENDER_EMAIL
    sender_password = SENDER_PASSWORD
    receiver_email = email_address

    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = receiver_email
    message['Subject'] = email_subject
    message.attach(MIMEText(email_message, 'plain'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender_email, sender_password)
    server.sendmail(sender_email, receiver_email, message.as_string())
    server.quit()
    

