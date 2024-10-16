from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import or_
from sqlalchemy import and_
import os
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedule.db'  # Database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'

db = SQLAlchemy(app)
class StatusReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report = db.Column(db.String(255), nullable=False)  # Adjust the length as needed
# Create the database and tables
with app.app_context():
    db.create_all()  # This will create all models, including the new StatusReport model

@app.route('/status', methods=['GET', 'POST'])
def status():
    if request.method == 'POST':
        report_text = request.form['report_text']  # Get the report text from the form

        # Create a new StatusReport entry
        new_report = StatusReport(report=report_text)
        db.session.add(new_report)
        db.session.commit()
        
        flash('Status report added successfully!', 'success')
        return redirect(url_for('status'))

    # If GET request, fetch all status reports to display
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

# Create the database and tables
with app.app_context():
    db.create_all()

# Function to get entries for the current week
def get_entries_for_week():
    entries = []
    start_of_week = datetime.now() - timedelta(days=datetime.now().weekday())
    
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        entries.append({
            'date': day.date(),
            'events': ScheduleEntry.query.filter(ScheduleEntry.start_time >= day, ScheduleEntry.start_time < day + timedelta(days=1)).all()
        })
    
    return entries

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calendar')
def calendar():
    entries = get_entries_for_week()
    return render_template('calendar.html', entries=entries)


@app.route('/schedule', methods=['POST'])
def schedule():
    try:
        start_date = request.form['start_date']  # Get the start date
        all_day = 'all_day' in request.form  # Check if the all-day option is selected
        email = request.form['email']  # Get the email

        if all_day:
            # All Day Event: Set start and end times to cover the entire day
            start_time_dt = datetime.combine(datetime.fromisoformat(start_date)+ timedelta(days=1), datetime.min.time())  # Start of the day
            end_time_dt = datetime.combine(datetime.fromisoformat(start_date)+ timedelta(days=1), datetime.max.time())    # End of the day
        else:
            # Regular Event: Get start and end time from the form
            start_time = request.form['start_time']
            end_time = request.form['end_time']

            # Combine the start date and start time
            start_time_dt = datetime.fromisoformat(f"{start_date}T{start_time}")
            end_time_dt = datetime.fromisoformat(f"{start_date}T{end_time}")

            # Ensure the end time is after the start time
            if end_time_dt <= start_time_dt:
                flash('End time must be after start time.', 'error')
                return redirect(url_for('calendar'))

        # **Improved Overlap Check Logic**
        overlapping_events = ScheduleEntry.query.filter(
            and_(
                ScheduleEntry.start_time < end_time_dt,  # Existing event starts before the new one ends
                ScheduleEntry.end_time > start_time_dt   # Existing event ends after the new one starts
            )
        ).all()

        if overlapping_events:
            flash('The scheduled time overlaps with an existing event.', 'error')
            return redirect(url_for('calendar'))

        # **Add the event if no overlap**
        new_entry = ScheduleEntry(start_time=start_time_dt, end_time=end_time_dt, email=email)
        db.session.add(new_entry)
        db.session.commit()

    except KeyError as e:
        return f'Missing required field: {str(e)}', 400

    return redirect(url_for('calendar'))


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
    #app.run(debug=True)
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=False)
