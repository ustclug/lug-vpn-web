from flask_wtf import Form
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, BooleanField, HiddenField
from wtforms.validators import InputRequired, Email, EqualTo, Length, Regexp


class RegisterForm(Form):
    email = StringField('Email', [InputRequired(), Email(), Length(max=63)])
    password = PasswordField('Password', [InputRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password', [InputRequired()])
    submit = SubmitField('Register')


class LoginForm(Form):
    email = StringField('Email', [InputRequired(), Email(), Length(max=63)])
    password = PasswordField('Password', [InputRequired()])
    submit = SubmitField('Login')


class ApplyForm(Form):
    name = StringField('Name', [InputRequired()])
    studentno = StringField('Student/Staff/Class No.', [InputRequired()])
    phone = StringField('Phone', [InputRequired()])
    location = StringField('Current living country/region', [InputRequired()])
    caseid = StringField('Case ID Number (Required for users in China, contact alumni(at)ustc.global for a case ID)')
    reason = TextAreaField('Apply reason (Please specify your current working/studying institution)', [InputRequired()])
    question1 = StringField('Security question 1: What is the website address of USTC Alumni Foundation (USTCAF)?', [InputRequired(), Regexp('^.*ustcaf\.org$|^.*ustc\.global$', message="Question 1 incorrect.")])
    question2 = StringField('Security question 2: In which year was USTCAF founded?', [InputRequired(), Regexp('^199[56]$', message="Question 2 incorrect")])
    agree = BooleanField('I agree to the following terms of conditions')
    submit_btn = SubmitField('Apply')



class ChangePasswordForm(Form):
    oldpassword = PasswordField('Current Password', [InputRequired()])
    password = PasswordField('New Password', [InputRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password', [InputRequired()])
    submit = SubmitField('Change Password')


class RecoverPasswordForm(Form):
    email = StringField('Email', [InputRequired(), Email(), Length(max=63)])
    submit = SubmitField('Recover Password')


class ResetPasswordForm(Form):
    password = PasswordField('New Password', [InputRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password', [InputRequired()])
    token = HiddenField("token")
    submit = SubmitField('Submit')


class RejectForm(Form):
    rejectreason = TextAreaField('Reject reason', [InputRequired()])
    submit = SubmitField('Reject')


class BanForm(Form):
    banreason = TextAreaField('Ban reason', [InputRequired()])
    submit = SubmitField('Ban')


class MailForm(Form):
    subject = StringField('Subject', [InputRequired()])
    content = TextAreaField('Content', [InputRequired()])
    submit = SubmitField('Send')


class EditForm(Form):
    name = StringField('Name')
    studentno = StringField('Student/Staff No.')
    phone = StringField('Phone')
    submit = SubmitField('Save')
