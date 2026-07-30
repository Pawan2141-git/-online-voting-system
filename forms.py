from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, DateTimeLocalField, RadioField, DateField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from datetime import datetime, timezone
from models import User

INDIAN_STATES = [
    ('Delhi (NCT)', 'Delhi (NCT)'),
    ('Maharashtra', 'Maharashtra'),
    ('Uttar Pradesh', 'Uttar Pradesh'),
    ('Tamil Nadu', 'Tamil Nadu'),
    ('West Bengal', 'West Bengal'),
    ('Karnataka', 'Karnataka'),
    ('Gujarat', 'Gujarat'),
    ('Telangana', 'Telangana'),
    ('Rajasthan', 'Rajasthan'),
    ('Punjab', 'Punjab'),
    ('Kerala', 'Kerala'),
    ('Bihar', 'Bihar'),
    ('Madhya Pradesh', 'Madhya Pradesh'),
    ('Odisha', 'Odisha'),
    ('Assam', 'Assam'),
    ('Haryana', 'Haryana'),
    ('Other State/UT', 'Other State/UT')
]

class LoginForm(FlaskForm):
    identity = StringField('Email or EPIC / Voter ID Card No.', validators=[DataRequired(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class RegisterForm(FlaskForm):
    full_name = StringField('Full Name (as per Voter ID Card)', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    voter_id = StringField('EPIC Number (Voter ID Card No.)', validators=[DataRequired(), Length(min=5, max=50)])
    date_of_birth = DateField('Date of Birth (Must be 18+ Years Old)', format='%Y-%m-%d', validators=[DataRequired(message="Please enter a valid date of birth (YYYY-MM-DD).")])
    state = SelectField('State / Union Territory of Residence', choices=INDIAN_STATES, validators=[DataRequired()])
    constituency = StringField('Parliamentary / Assembly Constituency', validators=[DataRequired(), Length(min=2, max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=100)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Register Voter Account')

    def validate_date_of_birth(self, field):
        if field.data:
            today = datetime.now(timezone.utc).date()
            age = today.year - field.data.year - ((today.month, today.day) < (field.data.month, field.data.day))
            if age < 18:
                raise ValidationError(f'Voter Ineligible: You are currently {age} years old. You must be at least 18 years old to register to vote in India.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError('An account with this email address already exists.')

    def validate_voter_id(self, field):
        v_id = field.data.upper().strip()
        if len(v_id) < 5:
            raise ValidationError('Invalid EPIC Number. Minimum 5 characters required.')
        if User.query.filter_by(voter_id=v_id).first():
            raise ValidationError('An account with this EPIC / Voter ID Card Number already exists.')


class ElectionForm(FlaskForm):
    title = StringField('Election Name / Constituency', validators=[DataRequired(), Length(max=150)])
    description = TextAreaField('Description / Notification Details', validators=[Length(max=1000)])
    start_time = DateTimeLocalField('Voting Start Date & Time (IST)', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_time = DateTimeLocalField('Voting End Date & Time (IST)', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    status = SelectField('Election Status', choices=[
        ('upcoming', 'Upcoming'),
        ('active', 'Active Voting Open'),
        ('closed', 'Closed')
    ], default='upcoming')
    submit = SubmitField('Save Election Notification')

    def validate_end_time(self, field):
        if self.start_time.data and field.data:
            if field.data <= self.start_time.data:
                raise ValidationError('End time must be after the start time.')


class CandidateForm(FlaskForm):
    name = StringField('Candidate Full Name', validators=[DataRequired(), Length(max=100)])
    party = StringField('Political Party & Election Symbol', validators=[DataRequired(), Length(max=100)])
    photo_file = FileField('Upload Candidate Photo File', validators=[
        FileAllowed(['jpg', 'png', 'jpeg', 'webp'], 'Image files only (.jpg, .png, .jpeg, .webp)')
    ])
    photo_url = StringField('Or External Photo URL (Optional)', validators=[Length(max=255)])
    bio = TextAreaField('Manifesto / Candidate Profile', validators=[Length(max=1000)])
    submit = SubmitField('Save Candidate Record')



class VoteForm(FlaskForm):
    candidate_id = RadioField('Select Candidate / Party Symbol', coerce=int, validators=[DataRequired(message="Please select a candidate before pressing Submit Vote.")])
    submit = SubmitField('Cast My Vote')


class BulkVoterImportForm(FlaskForm):
    csv_file = FileField('Upload Voters CSV File', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV files only (.csv)')
    ])
    submit = SubmitField('Import Voters List')


class ResetPasswordRequestForm(FlaskForm):
    identity = StringField('Registered Email or EPIC Number', validators=[DataRequired(), Length(max=120)])
    submit = SubmitField('Request Password Reset Token')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=6, max=100)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Reset Password')
