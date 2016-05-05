from flask_wtf import Form
from wtforms import TextField,PasswordField,SubmitField
from wtforms.validators import InputRequired,Email,EqualTo,Length

class RegisterForm(Form):
    email=TextField('USTC Email',[InputRequired(),Email(),Length(max=63)])
    password=PasswordField('Password',[InputRequired(),EqualTo('confirm',message='Passwords must match')])
    confirm=PasswordField('Repeat Password',[InputRequired()])
    submit=SubmitField('Register')

class LoginForm(Form):
    email=TextField('Email',[InputRequired(),Email(),Length(max=63)])
    password=PasswordField('Password',[InputRequired()])
    submit=SubmitField('Login')

class ChangePasswordForm(Form):
    oldpassword=PasswordField('Current Password',[InputRequired()])
    password=PasswordField('New Password',[InputRequired(),EqualTo('confirm',message='Passwords must match')])
    confirm=PasswordField('Repeat Password',[InputRequired()])
    submit=SubmitField('Change Password')

class ResetPasswordForm(Form):
    email=TextField('Email',[InputRequired(),Email(),Length(max=63)])
    submit=SubmitField('Reset Password')



