from app import *
from app.forms import *
from app.models import *
from app.mail import *
from flask import render_template, redirect, url_for, request, flash
from flask.ext.login import current_user, login_required, login_user, logout_user
from itsdangerous import URLSafeTimedSerializer
import datetime

ts = URLSafeTimedSerializer(app.config['SECRET_KEY'])

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Yi', suffix)

@app.route('/')
@login_required
def index():
    records = current_user.get_records(10)
    return render_template('index.html', user=current_user, records=records, sizeof_fmt=sizeof_fmt)


@app.route('/register/', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            email = form['email'].data
            password = form['password'].data
            if User.get_user_by_email(email):
                flash('Email already exists', 'error')
            else:
                token = ts.dumps(email, salt='email-confirm-key')
                url = url_for('confirm', token=token, _external=True)
                send_mail('Confirm your email',
                          'Follow this link to confirm your email:<br><a href="' + url + '">' + url + '</a>'
                          , email)
                user = User(email, password)
                user.save()
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
        email = ts.loads(token, salt="email-confirm-key", max_age=600)
    except:
        flash('Invalid token or token out of date', 'error')
        return render_template('confirm_error.html')
    user = User.get_user_by_email(email)
    if not user:
        flash('Invalid user', 'error')
        return render_template('confirm_error.html')
    user.active = True
    user.save()
    flash('User actived')
    return redirect(url_for('login'))


@app.route('/login/', methods=['POST', 'GET'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            email = form['email'].data
            password = form['password'].data
            user = User.get_user_by_email(email)
            if not user:
                flash('Email not found', 'error')
            elif user.password != password:
                flash('Password incorrect', 'error')
            elif not user.active:
                flash('Email not confirmed', 'error')
            else:
                login_user(user)
                return redirect(url_for('index'))
    return render_template('login.html', form=form)


@app.route('/apply/', methods=['POST', 'GET'])
@login_required
def apply():
    form = ApplyForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            name = form['name'].data
            studentno = form['studentno'].data
            phone = form['phone'].data
            reason = form['reason'].data
            agree = form['agree'].data
            if not agree:
                flash('You must agree to the terms of conditions', 'error')
            elif current_user.apply == 'none':
                current_user.apply = 'applying'
                current_user.name = name
                current_user.studentno = studentno
                current_user.phone = phone
                current_user.reason = reason
                current_user.applytime = datetime.datetime.now()
                current_user.save()
                return redirect(url_for('index'))
    return render_template('apply.html', form=form)


@app.route('/logout/')
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
    passed_users = list(map(lambda u: (u, User.get_user_by_email(u.username), u.get_record()), VPNAccount.get_all()))
    return render_template('manage.html', applying_users=applying_users, passed_users=passed_users)


@app.route('/pass/<int:id>', methods=['POST', 'GET'])
@login_required
def pass_(id):
    if current_user.admin:
        user = User.get_user_by_id(id)
        if user.apply == 'applying':
            user.pass_apply()
    return redirect(url_for('manage'))


@app.route('/reject/<int:id>', methods=['POST', 'GET'])
@login_required
def reject(id):
    if current_user.admin:
        user = User.get_user_by_id(id)
        if user.apply == 'applying':
            user.reject_apply()
    return redirect(url_for('manage'))
