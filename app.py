from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy.session import Session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import and_, func
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, ParkingZone, Booking, MarshalShift, ContactMessage
from forms import LoginForm, SignupForm
from datetime import datetime
import requests


app = Flask(__name__)
app.config['SECRET_KEY'] = 'FFAGSR3242455YHY9765'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)
session = Session(db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return session.get(User, int(user_id))

def create_tables():
    db.create_all()
    if not ParkingZone.query.all():
        zones = [ParkingZone(name=f'{x}') for x in ["Second Street", "Posselt Ave", "Pine Street"]]
        db.session.add_all(zones)
        db.session.commit()

@app.cli.command('init-db')
def init_db():
    db.drop_all()
    db.create_all()

    # Seed zones
    zones = [ParkingZone(name=f'{x}') for x in ["Second Street", "Posselt Ave", "Pine Street"]]
    db.session.add_all(zones)
    db.session.commit()

    print("Database initialized.")

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        profile_type = form.profile_type.data
        if profile_type == 'user':
            new_user = User(
                profile_type=profile_type,
                national_id=form.national_id.data,
                first_name=form.first_name.data,
                surname=form.surname.data,
                email=form.email.data,
                gender=form.gender.data,
                phone=form.phone.data,
                password=generate_password_hash(form.password.data)
            )
        elif profile_type in ['marshal', 'admin']:
            new_user = User(
                profile_type=profile_type,
                employee_id=form.employee_id.data,
                first_name=form.first_name.data,
                surname=form.surname.data,
                email=form.email.data,
                gender=form.gender.data,
                phone=form.phone.data,
                zone=form.zone.data if profile_type == 'marshal' else None,
                password=generate_password_hash(form.password.data)
            )
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully. Please login.')
        return redirect(url_for('login'))
    return render_template('signup.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        profile_type = form.profile_type.data
        identifier = form.identifier.data
        if profile_type == 'user':
            user = User.query.filter_by(profile_type='user', national_id=identifier).first()
        else:
            user = User.query.filter_by(profile_type=profile_type, employee_id=identifier).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for(f'dashboard_{profile_type}'))
        flash('Invalid credentials.')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard_user')
@login_required
def dashboard_user():
    if current_user.profile_type != 'user':
        return redirect(url_for('home'))
    zones = ParkingZone.query.all()
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard_user.html', zones=zones, bookings=bookings)


@app.route('/book/<int:zone_id>', methods=['GET', 'POST'])
@login_required
def book(zone_id):
    if current_user.profile_type != 'user':
        return redirect(url_for('home'))

    if request.method == 'POST':
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')

        booking = Booking(
            user_id=current_user.id,
            zone_id=zone_id,
            start_time=start_time,
            end_time=end_time
        )
        db.session.add(booking)
        db.session.commit()

        flash("Booking successful.")
        return redirect(url_for('dashboard_user'))

    zone = ParkingZone.query.get_or_404(zone_id)
    return render_template('book.html', zone=zone)


# Shift check-in route (simulate time & location)
@app.route('/update_location', methods=['POST'])
@login_required
def update_location():
    if current_user.profile_type != 'marshal':
        return jsonify({'status': 'unauthorized'}), 403

    lat = request.form.get('lat')
    lng = request.form.get('lng')

    if not lat and not lng:
        location = "Error"
    else:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json"
        headers = {'User-Agent': 'ParkingSystem/1.0'}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            address = data.get('address', {})
            city = address.get('city', address.get('town', ''))
            street = address.get('road', '')
            location = f"{street}, {city}"
        else:
            location = f"Lat:{lat}, Lon:{lng}"

    today = datetime.now().date()

    shift = MarshalShift.query.filter(
        MarshalShift.marshal_id == current_user.id,
        MarshalShift.shift_date == today
    ).first()

    if not shift:
        shift = MarshalShift(
            marshal_id=current_user.id,
            zone_id=ParkingZone.query.filter_by(id=current_user.zone).first().id,
            shift_date=today,
            check_in_time=datetime.now(),
            location=location,
            approved=None,
            declined_reason=None
        )
        db.session.add(shift)
        db.session.commit()
    else:
        if not shift.check_in_time:
            shift.check_in_time = datetime.now()
            shift.latitude = lat
            shift.longitude = lng
            db.session.commit()

    return jsonify({'status': 'success'})

@app.route('/dashboard_marshal', methods=['GET', 'POST'])
@login_required
def dashboard_marshal():
    if current_user.profile_type != 'marshal':
        return redirect(url_for('home'))

    # Pull zone bookings
    zone = current_user.zone
    zone_obj = session.query(ParkingZone).filter_by(id=zone).first()
    bookings = Booking.query.filter(and_(Booking.zone_id == zone_obj.id, Booking.status == 'booked')).all()

    return render_template('dashboard_marshal.html', bookings=bookings, zone=zone)

@app.route('/marshal/payment/<int:booking_id>', methods=['POST'])
@login_required
def process_payment(booking_id):
    if current_user.profile_type != 'marshal':
        return redirect(url_for('home'))

    booking = Booking.query.get_or_404(booking_id)
    currency = request.form.get('currency')
    amount = request.form.get('amount')
    booking.payment_currency = currency
    booking.payment_amount = float(amount)
    booking.payment_time = datetime.now()
    booking.status = 'paid'
    db.session.commit()

    return redirect(url_for('receipt', booking_id=booking.id))

@app.route('/marshal/cancel/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    if current_user.profile_type != 'marshal':
        return redirect(url_for('home'))

    booking = Booking.query.get_or_404(booking_id)
    booking.status = 'cancelled'
    db.session.commit()

    flash("Booking cancelled successfully")
    return redirect(url_for('dashboard_marshal'))

@app.route('/receipt/<int:booking_id>')
@login_required
def receipt(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    user = User.query.get(booking.user_id)
    return render_template('receipt.html', booking=booking, user=user)

@app.route('/dashboard_admin')
@login_required
def dashboard_admin():
    if current_user.profile_type != 'admin':
        return redirect(url_for('home'))

    # All marshal shifts
    shifts = MarshalShift.query.join(User, MarshalShift.marshal_id == User.id).add_columns(
        User.first_name, User.surname, User.zone, MarshalShift.id, MarshalShift.check_in_time,
        MarshalShift.location, MarshalShift.approved, MarshalShift.declined_reason)

    # Payments Summary
    payments_usd = db.session.query(func.sum(Booking.payment_amount)).filter(
        Booking.payment_currency == 'USD', Booking.status == 'paid').scalar() or 0

    payments_zig = db.session.query(func.sum(Booking.payment_amount)).filter(
        Booking.payment_currency == 'ZiG', Booking.status == 'paid').scalar() or 0

    # Marshal-wise payments
    marshals = User.query.filter_by(profile_type='marshal').all()
    marshal_summaries = []
    for marshal in marshals:
        total_usd = db.session.query(func.sum(Booking.payment_amount)).filter(
            Booking.payment_currency == 'USD',
            Booking.status == 'paid',
            Booking.zone_id == session.query(ParkingZone).filter_by(id=marshal.zone).first().id).scalar() or 0

        total_zig = db.session.query(func.sum(Booking.payment_amount)).filter(
            Booking.payment_currency == 'ZiG',
            Booking.status == 'paid',
            Booking.zone_id == session.query(ParkingZone).filter_by(id=marshal.zone).first().id
        ).scalar() or 0

        marshal_summaries.append({
            'marshal': marshal,
            'total_usd': total_usd,
            'total_zig': total_zig
        })

    messages = ContactMessage.query.order_by(ContactMessage.timestamp.desc()).all()

    return render_template('dashboard_admin.html',
                           messages=messages,
                           shifts=shifts,
                           payments_usd=payments_usd,
                           payments_zig=payments_zig,
                           marshal_summaries=marshal_summaries)

@app.route('/admin/approve/<int:shift_id>', methods=['POST'])
@login_required
def approve_shift(shift_id):
    if current_user.profile_type != 'admin':
        return redirect(url_for('home'))

    shift = MarshalShift.query.get_or_404(shift_id)
    shift.approved = True
    shift.decline_reason = None
    db.session.commit()

    flash("Shift approved")
    return redirect(url_for('dashboard_admin'))

@app.route('/admin/decline/<int:shift_id>', methods=['POST'])
@login_required
def decline_shift(shift_id):
    if current_user.profile_type != 'admin':
        return redirect(url_for('home'))

    reason = request.form.get('reason')
    shift = MarshalShift.query.get_or_404(shift_id)
    shift.approved = False
    shift.decline_reason = reason
    db.session.commit()

    flash("Shift declined")
    return redirect(url_for('dashboard_admin'))

@app.route('/marshal/summary')
@login_required
def summary():
    if current_user.profile_type != 'marshal':
        return redirect(url_for('home'))

    zone_obj = ParkingZone.query.filter_by(id=current_user.zone).first()

    paid_bookings = Booking.query.filter_by(zone_id=zone_obj.id, status='paid').all()
    cancelled_bookings = Booking.query.filter_by(zone_id=zone_obj.id, status='cancelled').all()

    total_usd = sum(b.payment_amount for b in paid_bookings if b.payment_currency == 'USD')
    total_zig = sum(b.payment_amount for b in paid_bookings if b.payment_currency == 'ZiG')

    return render_template('summary.html',
                           paid_bookings=paid_bookings,
                           cancelled_bookings=cancelled_bookings,
                           total_usd=total_usd,
                           total_zig=total_zig)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']

        # You can store this in DB or send via email
        msg = ContactMessage(name=name, email=email, subject=subject, message=message)
        db.session.add(msg)
        db.session.commit()

        flash('Your message has been sent. We will get back to you soon.')
        return redirect(url_for('contact'))

    return render_template('contact.html')

@app.route('/help')
def help():
    return render_template('help.html')


if __name__ == '__main__':
    with app.app_context():
        create_tables()
    app.run('0.0.0.0', debug=True)
