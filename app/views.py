from app import *
from app.forms import *
from app.models import *
from app.mail import *
from flask import render_template, render_template_string, redirect, url_for, request, flash, abort, jsonify
from flask_login import current_user, login_required, login_user, logout_user
from itsdangerous import URLSafeTimedSerializer
from markupsafe import Markup
import datetime
from pathlib import Path
from app.utils import *
import json
import markdown

ts = URLSafeTimedSerializer(app.config['SECRET_KEY'])
DOC_ROOT_PATH = Path(app.root_path) / 'doc'


def render_markdown_file(markdown_file, **context):
    relative_path = Path(markdown_file)
    try:
        if relative_path.is_absolute():
            raise ValueError('absolute document path')
        markdown_path = (DOC_ROOT_PATH / relative_path).resolve()
        markdown_path.relative_to(DOC_ROOT_PATH.resolve())
    except ValueError:
        app.logger.warning('Rejected document path outside app/doc: %s', markdown_file)
        markdown_content = '*(missing)*'
    else:
        try:
            markdown_content = markdown_path.read_text(encoding='utf-8')
        except OSError as exc:
            app.logger.warning('Unable to read document %s: %s', markdown_path, exc)
            markdown_content = '*(missing)*'

    rendered_markdown = render_template_string(markdown_content, **context)
    return Markup(markdown.markdown(rendered_markdown, extensions=['extra', 'sane_lists']))


def render_document_set(config_key, **context):
    return [
        (title, render_markdown_file(filename, **context))
        for title, filename in app.config[config_key]
    ]


def library_api_response(studentno):
    try:
        result = fetch_from_lib_api(
            app.config['LIBRARY_API_URL'],
            studentno,
            timeout=app.config['LIBRARY_API_TIMEOUT'],
        )
    except LibraryAPIError as exc:
        app.logger.warning('Library API check failed for %s: %s', studentno, exc)
        return jsonify({'message': str(exc)}), 502
    return jsonify(result)


@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    records = current_user.get_records(10)
    renewal = (current_user.expiration - datetime.date.today()).days <= 180 if current_user.expiration else False
    escaped_email = current_user.email.replace('@', '%40')
    applying_count = User.get_applying_count()
    return render_template('index.html', user=current_user, records=records, sizeof_fmt=sizeof_fmt,
                           renewal=renewal, applying_count=applying_count,
                           constitution_documents=render_document_set('CONSTITUTION_DOCUMENTS'),
                           terms_documents=render_document_set('TERMS_DOCUMENTS'),
                           usage_documents=render_document_set(
                               'USAGE_DOCUMENTS', user=current_user,
                               escaped_email=escaped_email,
                           ))


@app.route('/constitution/')
def view_constitution():
    return render_template('view_constitution.html',
                           constitution_documents=render_document_set('CONSTITUTION_DOCUMENTS'))


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
                          'Follow this link to confirm your email:<br><a href="' + url + '">' + url + '</a>' +
                          '<br>If you are using USTC Email, please open a new tab and paste the URL manually!'
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
    except Exception:
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
    if current_user.status not in ['none', 'reject', 'applying', 'pass']:
        abort(403)
    form = ApplyForm(request.form, obj=current_user, id='applyForm')
    form.reasonClass.choices = [('', 'Select a qualification')] + [
        (reason, reason) for reason in app.config['APPLICATION_REASONS']
    ]
    if app.config['APPLICATION_REASONS']:
        form.reasonClass.validators = [InputRequired()]
    else:
        form._fields.pop('reasonClass', None)
    if request.method == 'POST':
        if form.validate_on_submit():
            name = form['name'].data
            studentno = form['studentno'].data
            phone = form['phone'].data
            selected_reason = form.reasonClass.data if 'reasonClass' in form._fields else ''
            freeform_reason = (form.reasonText.data or '').strip()
            reason = ' / '.join(filter(None, (selected_reason, freeform_reason)))
            agree = form['agree'].data
            if not agree:
                flash('You must agree to the constitution', 'error')
            # check_apply_info() is not imported
            # elif not app.config['DEBUG'] and not check_apply_info(current_user.email, name, studentno):
            #     flash('Incorrect information provided', 'error')
            else:
                if current_user.status == 'pass':
                    current_user.renewing = True
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
                if current_user.status == 'pass':
                    title = '{} Renewal: '.format(app.config['SITE_NAME'])
                else:
                    title = 'New {} Application: '.format(app.config['SITE_NAME'])
                send_mail(title + name, html, app.config['ADMIN_MAIL'])
                return redirect(url_for('index'))
    confirmation_enabled = bool(
        app.config['APPLICATION_CONFIRMATION_ENABLED'] and app.config['TERMS_DOCUMENTS']
    )
    if app.config['APPLICATION_CONFIRMATION_ENABLED'] and not app.config['TERMS_DOCUMENTS']:
        app.logger.warning('Application confirmation disabled because TERMS_DOCUMENTS is empty')
    return render_template('apply.html', form=form, renew=current_user.status == 'pass',
                           constitution_documents=render_document_set('CONSTITUTION_DOCUMENTS'),
                           terms_documents=render_document_set('TERMS_DOCUMENTS'),
                           confirmation_enabled=confirmation_enabled)


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


@app.route('/manageusers/')
@login_required
def manage_users():
    if not current_user.admin:
        return redirect(url_for('index'))
    users = User.get_users()
    rejected_users = User.get_rejected()
    all_month_traffic = User.all_month_traffic()
    all_last_month_traffic = User.all_last_month_traffic()
    return render_template('manageusers.html', users=users, rejected_users=rejected_users,
                           all_month_traffic=all_month_traffic, all_last_month_traffic=all_last_month_traffic)


@app.route('/manageapplications/')
@login_required
def manage_applications():
    if not current_user.admin:
        return redirect(url_for('index'))
    applying_users = User.get_applying()
    return render_template(
        'manageapplications.html', applying_users=applying_users,
        library_api_enabled=bool(app.config['LIBRARY_API_URL']),
    )


@app.route('/create/', methods=['POST', 'GET'])
@login_required
def create():
    if not current_user.admin:
        abort(403)
    form = CreateForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            email = form['email'].data
            password = form['password'].data
            if User.get_user_by_email(email):
                flash('Email already exists', 'error')
            else:
                token = ts.dumps(email, salt=app.config['SECRET_KEY'] + 'email-confirm-key')
                url = url_for('confirm', token=token, _external=True)
                user = User(email, password)
                user.save()
                send_mail('Confirm your email',
                          'Follow this link to confirm your email:<br><a href="' + url + '">' + url + '</a>' +
                          '<br>If you are using USTC Email, please open a new tab and paste the URL manually!'
                          , email)
                return redirect(url_for('register_ok'))
    return render_template('register.html', form=form)


@app.route('/pass/<int:id>', methods=['POST'])
@login_required
def pass_(id):
    if not current_user.admin:
        abort(403)
    user = User.get_user_by_id(id)
    expiration_type = request.args.get('expiration_type', 'semester')
    if expiration_type not in EXPIRATION_TYPES:
        abort(400)
    if user.status in ['applying', 'reject']:
        user.pass_apply(expiration_type)
        html = 'Username: ' + user.email + \
               '<br>Password: ' + user.vpnpassword + \
               '<br>Please login to <a href="' + \
               url_for('index', _external=True) + \
               '">{} application website</a> for detail.'.format(app.config['SITE_NAME'])
        send_mail('Your {} application has passed'.format(app.config['SITE_NAME']), html, user.email)
    elif user.renewing:
        user.pass_renewal(expiration_type)
        html = 'Your {} renewal has passed<br>Please login for detail.'.format(app.config['SITE_NAME'])
        send_mail('Your {} renewal has passed'.format(app.config['SITE_NAME']), html, user.email)
    return redirect(url_for('manage_applications'))


@app.route('/reject/<int:id>', methods=['POST', 'GET'])
@login_required
def reject(id):
    if not current_user.admin:
        abort(403)
    user = User.get_user_by_id(id)
    form = RejectForm(
        rejectreason=user.rejectreason,
        expiration=user.expiration or datetime.date.today(),
        force=False,
    )
    if request.method == 'POST':
        if form.validate_on_submit():
            rejectreason = form['rejectreason'].data
            expiration = form['expiration'].data
            force = form['force'].data
            html = 'Reason:<br>' + rejectreason
            if not expiration:
                expiration = datetime.date.today()
            was_renewing = user.renewing
            user.reject(rejectreason, expiration, force=force)
            if was_renewing:
                subject = 'Your {} renewal has been rejected'.format(app.config['SITE_NAME'])
            else:
                subject = 'Your {} application has been rejected'.format(app.config['SITE_NAME'])
            send_mail(subject, html, user.email)
            return redirect(url_for('manage_applications'))
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
            send_mail('Your {} application has been banned'.format(app.config['SITE_NAME']), html, user.email)
            return redirect(url_for('manage_users'))
    return render_template('ban.html', form=form, email=user.email)


@app.route('/unban/<int:id>', methods=['POST'])
@login_required
def unban(id):
    if current_user.admin:
        user = User.get_user_by_id(id)
        if user.status == 'banned':
            user.unban()
    return redirect(url_for('manage_users'))


@app.route('/renew/<expiration_type>/<int:id>', methods=['POST'])
@login_required
def renew(expiration_type, id):
    if not current_user.admin:
        abort(403)
    if expiration_type not in EXPIRATION_TYPES:
        abort(400)
    user = User.get_user_by_id(id)
    user.renew(expiration_type)
    return redirect(url_for('manage_users'))


@app.route('/setadmin/<int:id>', methods=['POST'])
@login_required
def setadmin(id):
    if current_user.admin:
        user = User.get_user_by_id(id)
        user.admin = 1
        user.save()
    return redirect(url_for('manage_users'))


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
    return redirect(url_for('manage_users'))


@app.route('/edit/<int:id>', methods=['POST', 'GET'])
@login_required
def edit(id):
    if not current_user.admin:
        abort(403)
    user = User.get_user_by_id(id)
    form = EditForm(request.form, obj=user)
    if request.method == 'POST':
        if form.validate_on_submit():
            user.name = form['name'].data
            user.studentno = form['studentno'].data
            user.phone = form['phone'].data
            user.set_quota(form['quota'].data)
            user.save()
            return redirect(url_for('manage_users'))
    else:
        form['quota'].data = user.get_quota()
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
            return redirect(url_for('manage_users'))
    return render_template('mail.html', form=form, email=user.email)


@app.route('/check/<int:id>', methods=['GET'])
@login_required
def check_with_lib(id):
    if not current_user.admin:
        abort(403)
    if not app.config['LIBRARY_API_URL']:
        abort(404)
    user = User.get_user_by_id(id)
    if not user:
        abort(404)
    return library_api_response(user.studentno)


@app.route('/manualcheck/<studentno>', methods=['GET'])
@login_required
def manual_check_with_lib(studentno):
    if not current_user.admin:
        abort(403)
    if not app.config['LIBRARY_API_URL']:
        abort(404)
    return library_api_response(studentno)


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
                          'Follow this link to confirm your email:<br><a href="' + url + '">' + url + '</a>' +
                          '<br>If you are using USTC Email, please open a new tab and paste the URL manually!'
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
    except Exception:
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
    if request.args.get('id'):
        if current_user.admin:
            user = User.get_user_by_id(request.args.get('id'))
        else:
            abort(403)
    else:
        user = current_user
    last_month_traffic = user.last_month_traffic_by_day()
    month_traffic = user.month_traffic_by_day()
    last_month_upload = [{'x': day, 'y': float(upload) / 1048576} for day, upload, _ in last_month_traffic]
    last_month_download = [{'x': day, 'y': float(download) / 1048576} for day, _, download in last_month_traffic]
    month_upload = [{'x': day, 'y': float(upload) / 1048576} for day, upload, _ in month_traffic]
    month_download = [{'x': day, 'y': float(download) / 1048576} for day, _, download in month_traffic]
    return json.dumps({'last_month_upload': last_month_upload, 'last_month_download': last_month_download,
                       'month_upload': month_upload, 'month_download': month_download})


@app.route('/profile/<int:id>')
@login_required
def profile(id):
    if not current_user.admin:
        abort(403)
    user = User.get_user_by_id(id)
    records = user.get_records(10)
    return render_template('profile.html', user=user, records=records, sizeof_fmt=sizeof_fmt)


@app.route('/su/<int:id>', methods=['POST'])
@login_required
def su(id):
    if not current_user.admin:
        abort(403)
    user = User.get_user_by_id(id)
    login_user(user)
    return redirect(url_for('index'))
