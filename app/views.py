from app import *
from app.forms import *
from app.models import *
from app.mail import *
from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import current_user, login_required, login_user, logout_user
from itsdangerous import URLSafeTimedSerializer
import datetime
from app.utils import *
import json

ts = URLSafeTimedSerializer(app.config['SECRET_KEY'])


@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    records = current_user.get_records(10)
    return render_template('index.html', user=current_user, records=records, sizeof_fmt=sizeof_fmt)


@app.route('/register/', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            email = form['email'].data
            password = form['password'].data
            if not email.split('@')[-1] in ['ustc.edu.cn', 'mail.ustc.edu.cn', 'ustclug.org']:
                flash('Email must end with @[mail.]ustc.edu.cn', 'error')
            elif User.get_user_by_email(email):
                flash('Email already exists', 'error')
            else:
                token = ts.dumps(email, salt=app.config['SECRET_KEY'] + 'email-confirm-key')
                url = url_for('confirm', token=token, _external=True)
                user = User(email, password)
                user.save()
                send_mail('Confirm your email',
                          'Follow this link to confirm your email:<br><a href="' + url + '">' + url + '</a>'
                          , email)
                return redirect(url_for('register_ok'))
    return render_template('register.html', form=form)


@app.route('/register_ok/')
def register_ok():
    return render_template('register_ok.html')


@app.route('/confirm/')
def confirm():
    token = request.args.get('token')
    if not token:
        flash('No token provided', 'error')
        return render_template('confirm_error.html')
    try:
        email = ts.loads(token, salt=app.config['SECRET_KEY'] + "email-confirm-key", max_age=86400)
    except:
        flash('Invalid token or token out of date', 'error')
        return render_template('confirm_error.html')
    user = User.get_user_by_email(email)
    if not user:
        flash('Invalid user', 'error')
        return render_template('confirm_error.html')
    user.set_active()
    flash('User actived')
    return redirect(url_for('login'))


@app.route('/login/', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            email = form['email'].data
            password = form['password'].data
            user = User.get_user_by_email(email)
            if not user:
                flash('Email not found', 'error')
            elif not user.check_password(password):
                flash('Email or password incorrect', 'error')
            elif not user.active:
                flash('Email not confirmed. Please recover your account at the bottom of this page.', 'error')
            else:
                login_user(user)
                return redirect(url_for('index'))
    return render_template('login.html', form=form)


@app.route('/apply/', methods=['POST', 'GET'])
@login_required
def apply():
    if not current_user.status in ['none', 'reject', 'applying']:
        abort(403)
    form = ApplyForm(request.form, current_user)
    if request.method == 'POST':
        if form.validate_on_submit():
            name = form['name'].data
            studentno = form['studentno'].data
            phone = form['phone'].data
            reason = form['reason'].data
            agree = form['agree'].data
            if not agree:
                flash('You must agree to the constitution', 'error')
            else:
                current_user.status = 'applying'
                current_user.name = name
                current_user.studentno = studentno.upper()
                current_user.phone = phone
                current_user.reason = reason
                current_user.applytime = datetime.datetime.now()
                current_user.save()
                html = 'Name: ' + name + \
                       '<br>Email: ' + current_user.email + \
                       '<br>Student/Staff No: ' + studentno + \
                       '<br>Phone: ' + phone + \
                       '<br>Reason: ' + reason
                send_mail('New VPN Application: ' + name, html, app.config['ADMIN_MAIL'])
                return redirect(url_for('index'))
    return render_template('apply.html', form=form)


@app.route('/cancel/', methods=['POST'])
@login_required
def cancel():
    if current_user.status == 'applying':
        current_user.status = 'none'
        current_user.save()
    return redirect(url_for('index'))


@app.route('/logout/', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/manage/')
@login_required
def manage():
    if not current_user.admin:
        return redirect(url_for('index'))
    applying_users = User.get_applying()
    users = [(VPNAccount.get_account_by_email(u.email), u, u.get_record()) for u in User.get_users()]
    rejected_users = User.get_rejected()
    return render_template('manage.html', applying_users=applying_users, users=users, rejected_users=rejected_users)


@app.route('/pass/<int:id>', methods=['POST'])
@login_required
def pass_(id):
    if current_user.admin:
        user = User.get_user_by_id(id)
        if user.status in ['applying', 'reject']:
            user.pass_apply()
            html = 'Username: ' + user.email + \
                   '<br>Password: ' + user.vpnpassword + \
                   '<br> Please login to VPN apply website for detail.'
            send_mail('Your VPN application has passed', html, user.email)
    return redirect(url_for('manage'))


@app.route('/reject/<int:id>', methods=['POST', 'GET'])
@login_required
def reject(id):
    if not current_user.admin:
        abort(403)
    user = User.get_user_by_id(id)
    form = RejectForm(rejectreason=user.rejectreason)
    if request.method == 'POST':
        if form.validate_on_submit():
            rejectreason = form['rejectreason'].data
            user.reject_apply(rejectreason)
            html = 'Reason:<br>' + rejectreason
            send_mail('Your VPN application has been rejected', html, user.email)
            return redirect(url_for('manage'))
    return render_template('reject.html', form=form, email=user.email)


@app.route('/ban/<int:id>', methods=['POST', 'GET'])
@login_required
def ban(id):
    if not current_user.admin:
        abort(403)
    user = User.get_user_by_id(id)
    form = BanForm(banreason=user.banreason)
    if request.method == 'POST':
        if form.validate_on_submit():
            banreason = form['banreason'].data
            user.ban(banreason)
            html = 'Reason:<br>' + banreason
            send_mail('Your VPN application has been banned', html, user.email)
            return redirect(url_for('manage'))
    return render_template('ban.html', form=form, email=user.email)


@app.route('/unban/<int:id>', methods=['POST'])
@login_required
def unban(id):
    if current_user.admin:
        user = User.get_user_by_id(id)
        if user.status == 'banned':
            user.unban()
    return redirect(url_for('manage'))


@app.route('/setadmin/<int:id>', methods=['POST'])
@login_required
def setadmin(id):
    if current_user.admin:
        user = User.get_user_by_id(id)
        user.admin = 1
        user.save()
    return redirect(url_for('manage'))


@app.route('/unsetadmin/<int:id>', methods=['POST'])
@login_required
def unsetadmin(id):
    if current_user.admin:
        if current_user.id != id:
            user = User.get_user_by_id(id)
            user.admin = 0
            user.save()
        else:
            flash('You cannot unset yourself', 'error')
    return redirect(url_for('manage'))


@app.route('/edit/<int:id>', methods=['POST', 'GET'])
@login_required
def edit(id):
    if not current_user.admin:
        abort(403)
    user = User.get_user_by_id(id)
    form = EditForm(request.form, user)
    if request.method == 'POST':
        if form.validate_on_submit():
            user.name = form['name'].data
            user.studentno = form['studentno'].data
            user.phone = form['phone'].data
            user.save()
            return redirect(url_for('manage'))
    return render_template('edit.html', form=form, email=user.email)


@app.route('/mail/<int:id>', methods=['POST', 'GET'])
@login_required
def mail(id):
    if not current_user.admin:
        abort(403)
    user = User.get_user_by_id(id)
    form = MailForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            send_mail(form['subject'].data, form['content'].data, user.email)
            flash('Mail has been sent')
            return redirect(url_for('manage'))
    return render_template('mail.html', form=form, email=user.email)


@app.route('/changevpnpassword/', methods=['POST'])
@login_required
def changevpnpassword():
    if current_user.status == 'pass':
        current_user.change_vpn_password()
    return redirect(url_for('index'))


@app.route('/changepassword/', methods=['POST', 'GET'])
@login_required
def changepassword():
    form = ChangePasswordForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            oldpassword = form['oldpassword'].data
            password = form['password'].data
            if not current_user.check_password(oldpassword):
                flash('Current password incorrect', 'error')
            else:
                current_user.set_password(password)
                current_user.save()
                flash('Password successfully changed')
                return redirect(url_for('index'))
    return render_template('changepassword.html', form=form)


@app.route('/recoverpassword/', methods=['POST', 'GET'])
def recoverpassword():
    form = RecoverPasswordForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            email = form['email'].data
            if not User.get_user_by_email(email):
                flash('Email not found', 'error')
            else:
                token = ts.dumps(email, salt=app.config['SECRET_KEY'] + 'recover-password-key')
                url = url_for('resetpassword', token=token, _external=True)
                send_mail('Confirm your email',
                          'Follow this link to confirm your email:<br><a href="' + url + '">' + url + '</a>'
                          , email)
                return redirect(url_for('recover_password_ok'))
    return render_template('recoverpassword.html', form=form)


@app.route('/recover_password_ok/')
def recover_password_ok():
    return render_template('register_ok.html')


@app.route('/resetpassword/', methods=['POST', 'GET'])
def resetpassword():
    token = request.args.get('token')
    if not token:
        flash('No token provided', 'error')
        return render_template('confirm_error.html')
    try:
        email = ts.loads(token, salt=app.config['SECRET_KEY'] + "recover-password-key", max_age=86400)
    except:
        flash('Invalid token or token out of date', 'error')
        return render_template('confirm_error.html')
    user = User.get_user_by_email(email)
    if not user:
        flash('Invalid user', 'error')
        return render_template('confirm_error.html')
    elif not user.active:
        user.set_active()
        flash('User actived')
        return redirect(url_for('login'))
    form = ResetPasswordForm(token=token)
    if request.method == 'POST':
        if form.validate_on_submit():
            password = form['password'].data
            user.set_password(password)
            user.save()
            flash('Reset password succeeded')
            return redirect(url_for('login'))
    return render_template('resetpassword.html', form=form)


@app.route('/traffic/')
@login_required
def traffic():
    last_month_traffic = current_user.last_month_traffic_by_day()
    month_traffic = current_user.month_traffic_by_day()
    last_month_upload = [{'x': day, 'y': float(upload) / 1048576} for day, upload, _ in last_month_traffic]
    last_month_download = [{'x': day, 'y': float(download) / 1048576} for day, _, download in last_month_traffic]
    month_upload = [{'x': day, 'y': float(upload) / 1048576} for day, upload, _ in month_traffic]
    month_download = [{'x': day, 'y': float(download) / 1048576} for day, _, download in month_traffic]
    return json.dumps({'last_month_upload': last_month_upload, 'last_month_download': last_month_download,
                       'month_upload': month_upload, 'month_download': month_download})
