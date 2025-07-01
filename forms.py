from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Optional, Regexp


class LoginForm(FlaskForm):
    profile_type = SelectField('Profile Type', choices=[('user', 'User'), ('marshal', 'Marshal'), ('admin', 'Admin')])
    identifier = StringField('ID', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class SignupForm(FlaskForm):
    profile_type = SelectField('Profile Type', choices=[('user', 'User'), ('marshal', 'Marshal'), ('admin', 'Admin')])
    national_id = StringField('National ID', validators=[Optional()])
    employee_id = StringField('Employee ID', validators=[Optional()])
    first_name = StringField('First Name', validators=[DataRequired()])
    surname = StringField('Surname', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    gender = SelectField('Gender', validators=[DataRequired()], choices=[('Male', 'Male'), ('Female', 'Female')])
    phone = StringField('Phone', validators=[DataRequired()])
    zone = SelectField('Zone', validators=[Optional()], choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4')])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign Up')
