from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import or_
from sqlalchemy import and_
import os
import pytz

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://scheduler_gp4w_user:4I2dxWzkZ6luTNRPB2MQxYCUPYoneIsq@dpg-cs8e34tsvqrc73bpaq2g-a/scheduler_gp4w'  # Database URI 'sqlite:///schedule.db'#
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'

db = SQLAlchemy(app)

class StatusReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report = db.Column(db.String(255), nullable=False)  # Adjust the length as needed

# Create the database and tables
with app.app_context():
    db.create_all()

@app.route('/status', methods=['GET', 'POST'])
def status():
    if request.method == 'POST':
        report_text = request.form['report_text']  # Get the report text from the form
        new_report = StatusReport(report=report_text)
        db.session.add(new_report)
        db.session.commit()
        
        flash('Status report added successfully!', 'success')
        return redirect(url_for('status'))

    status_reports = StatusReport.query.all()
    return render_template('status.html', reports=status_reports)

@app.route('/remove_status', methods=['POST'])
def remove_status():
    password = request.form['password']
    if password == "removeifpt":  # Use the same password for deletion
        try:
            report_id = int(request.form['report_id'])  # Get the report ID
            report_to_remove = StatusReport.query.get(report_id)
            if report_to_remove:
                db.session.delete(report_to_remove)
                db.session.commit()
                flash('Status report removed successfully!', 'success')
            else:
                flash('Status report not found.', 'error')
        except (ValueError, IndexError):
            flash('Invalid report ID.', 'error')
    else:
        flash('Incorrect password.', 'error')

    return redirect(url_for('status'))

# Database model for scheduled entries
class ScheduleEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    calendar_type = db.Column(db.String(50), nullable=False)  # New column for calendar type


# Create the database and tables
with app.app_context():
    db.create_all()

def get_entries_for_week(calendar_type):
    entries = []
    # Get the current date and time in UTC
    now_utc = datetime.now(pytz.utc)
    
    # Start of the week in UTC at midnight (00:00:00) on the most recent Monday
    start_of_week = now_utc - timedelta(days=now_utc.weekday())  # Get the latest Monday
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)  # Set to 00:00:00

    # Loop through the days of the week and get the events for each day, filtered by calendar_type
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        
        # Filter events based on calendar_type and the specific day
        events = ScheduleEntry.query.filter(
            ScheduleEntry.start_time >= day,
            ScheduleEntry.start_time < day + timedelta(days=1),
            ScheduleEntry.calendar_type == calendar_type  # Filter by calendar type
        ).all()
        
        entries.append({
            'date': day.date(),
            'events': events
        })
    
    return entries

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calendar/<calendar_type>')
def calendar(calendar_type):
    entries = get_entries_for_week(calendar_type)
    return render_template('calendar.html', entries=entries, calendar_type=calendar_type)

@app.route('/schedule/<calendar_type>', methods=['POST'])
def schedule(calendar_type):
    new_event_scheduled = False  # Flag to indicate if a new event was scheduled
    try:
        start_date = request.form['start_date']
        all_day = 'all_day' in request.form
        email = request.form['email']

        start_date_dt = datetime.fromisoformat(start_date).replace(tzinfo=pytz.utc)

        if all_day:
            start_time_dt = start_date_dt
            end_time_dt = start_time_dt.replace(hour=23, minute=59, second=59)
        else:
            start_time = request.form['start_time']
            end_time = request.form['end_time']

            start_time_dt = datetime.fromisoformat(f"{start_date}T{start_time}").replace(tzinfo=pytz.utc)
            end_time_dt = datetime.fromisoformat(f"{start_date}T{end_time}").replace(tzinfo=pytz.utc)

            if end_time_dt <= start_time_dt:
                flash('End time must be after start time.', 'error')
                return redirect(url_for('calendar', calendar_type=calendar_type))

        # Overlap check
        overlapping_events = ScheduleEntry.query.filter(
            and_(
                ScheduleEntry.start_time < end_time_dt,
                ScheduleEntry.end_time > start_time_dt,
                ScheduleEntry.calendar_type == calendar_type
            )
        ).all()

        if overlapping_events:
            flash('The scheduled time overlaps with an existing event.', 'error')
            return redirect(url_for('calendar', calendar_type=calendar_type))

        # Add the new schedule entry
        new_entry = ScheduleEntry(
            start_time=start_time_dt,
            end_time=end_time_dt,
            email=email,
            calendar_type=calendar_type
        )
        db.session.add(new_entry)
        db.session.commit()

        flash('Event successfully scheduled!', 'success')
        new_event_scheduled = True  # Set flag to True

    except KeyError as e:
        flash(f'Missing required field: {str(e)}', 'error')
        return redirect(url_for('calendar', calendar_type=calendar_type))

    return redirect(url_for('calendar', calendar_type=calendar_type, new_event=new_event_scheduled))

@app.route('/remove_entry', methods=['POST'])
def remove_entry():
    password = request.form['password']
    if password == "removeifpt":
        try:
            entry_id = int(request.form['entry_index'])  # This should be the actual ID
            entry_to_remove = ScheduleEntry.query.get(entry_id)
            if entry_to_remove:
                db.session.delete(entry_to_remove)
                db.session.commit()
                flash('Entry removed successfully!', 'success')
            else:
                flash('Entry not found.', 'error')
        except (ValueError, IndexError):
            flash('Invalid entry index.', 'error')
    else:
        flash('Incorrect password.', 'error')

    return redirect(url_for('calendar'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=False)
