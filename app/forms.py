from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, BooleanField, HiddenField
from wtforms.validators import InputRequired, Email, EqualTo, Length


class RegisterForm(FlaskForm):
    email = StringField('USTC Email', [InputRequired(), Email(), Length(max=63)])
    password = PasswordField('Password', [InputRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password', [InputRequired()])
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    email = StringField('Email', [InputRequired(), Email(), Length(max=63)])
    password = PasswordField('Password', [InputRequired()])
    submit = SubmitField('Login')


class ApplyForm(FlaskForm):
    name = StringField('Name in Chinese', [InputRequired()])
    studentno = StringField('Student/Staff No.', [InputRequired()])
    phone = StringField('Phone', [InputRequired()])
    reason = TextAreaField('Apply reason (please specify the criteria which you meet)', [InputRequired()])
    agree = BooleanField('I agree to the following constitution')
    submit_btn = SubmitField('Apply')


class ChangePasswordForm(FlaskForm):
    oldpassword = PasswordField('Current Password', [InputRequired()])
    password = PasswordField('New Password', [InputRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password', [InputRequired()])
    submit = SubmitField('Change Password')


class RecoverPasswordForm(FlaskForm):
    email = StringField('Email', [InputRequired(), Email(), Length(max=63)])
    submit = SubmitField('Recover Password')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', [InputRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password', [InputRequired()])
    token = HiddenField("token")
    submit = SubmitField('Submit')


class RejectForm(FlaskForm):
    rejectreason = TextAreaField('Reject reason', [InputRequired()])
    submit = SubmitField('Reject')


class BanForm(FlaskForm):
    banreason = TextAreaField('Ban reason', [InputRequired()])
    submit = SubmitField('Ban')


class MailForm(FlaskForm):
    subject = StringField('Subject', [InputRequired()])
    content = TextAreaField('Content', [InputRequired()])
    submit = SubmitField('Send')


class EditForm(FlaskForm):
    name = StringField('Name')
    studentno = StringField('Student/Staff No.')
    phone = StringField('Phone')
    submit = SubmitField('Save')
