from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FileField, TextAreaField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

class TopicForm(FlaskForm):
    title = StringField('Topic Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    summary = TextAreaField('Summary')
    youtube_link = StringField('YouTube Video Link')
    pdf_file = FileField('Upload PDF File')
    submit = SubmitField('Save Topic')
