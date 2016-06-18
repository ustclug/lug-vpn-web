from flask_wtf import Form
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, BooleanField
from wtforms.validators import InputRequired, Email, EqualTo, Length


class RegisterForm(Form):
    email = StringField('USTC Email', [InputRequired(), Email(), Length(max=63)])
    password = PasswordField('Password', [InputRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password', [InputRequired()])
    submit = SubmitField('Register')


class LoginForm(Form):
    email = StringField('Email', [InputRequired(), Email(), Length(max=63)])
    password = PasswordField('Password', [InputRequired()])
    submit = SubmitField('Login')


class ApplyForm(Form):
    name = StringField('Name', [InputRequired()])
    studentno = StringField('Student No.', [InputRequired()])
    phone = StringField('Phone', [InputRequired()])
    reason = TextAreaField('Apply reason', [InputRequired()])
    agree = BooleanField('I agree to the following constitution')
    submit = SubmitField('Apply')


class ChangePasswordForm(Form):
    oldpassword = PasswordField('Current Password', [InputRequired()])
    password = PasswordField('New Password', [InputRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password', [InputRequired()])
    submit = SubmitField('Change Password')


class ResetPasswordForm(Form):
    email = StringField('Email', [InputRequired(), Email(), Length(max=63)])
    submit = SubmitField('Reset Password')
