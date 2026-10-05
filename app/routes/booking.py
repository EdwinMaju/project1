from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from app.models import db, Booking, Flight, Train, Hotel, Vehicle, Payment, User
from app.routes.customer import (
    _available_seats_for_date, _available_seats_for_train_date,
    _available_rooms_for_dates, _available_vehicles_for_dates
)
from datetime import datetime, date, timedelta
from sqlalchemy import func
from werkzeug.utils import secure_filename
import os
import qrcode
from io import BytesIO
import uuid

bp = Blueprint('booking', __name__, url_prefix='/booking')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_qr_code(booking_id, amount, customer_email):
    """Generate QR code for payment"""
    qr_data = f"BOOKING_ID:{booking_id}|AMOUNT:{amount}|EMAIL:{customer_email}|TIMESTAMP:{datetime.utcnow().isoformat()}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code
    filename = f"qr_{booking_id}_{datetime.utcnow().timestamp()}.png"
    filepath = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads', filename)
    img.save(filepath)
    
    return filename, qr_data

@bp.route('/flight/<int:flight_id>', methods=['GET', 'POST'])
@login_required
def book_flight(flight_id):
    """Book a flight"""
    flight = Flight.query.get_or_404(flight_id)
    
    if request.method == 'POST':
        try:
            num_passengers = int(request.form.get('num_passengers', 1))
            travel_date = request.form.get('travel_date')
            
            if not travel_date:
                flash('Travel date is required', 'danger')
                return redirect(url_for('booking.book_flight', flight_id=flight_id))
            
            travel_date_obj = datetime.strptime(travel_date, '%Y-%m-%d').date()
            
            # Validate date
            if travel_date_obj < date.today():
                flash('Cannot book for past dates', 'warning')
                return redirect(url_for('booking.book_flight', flight_id=flight_id))
            
            # Check if flight operates on this day
            if not flight.runs_on(travel_date_obj):
                flash('This flight does not operate on the selected date', 'warning')
                return redirect(url_for('booking.book_flight', flight_id=flight_id))
            
            # Overlap-based availability: seats available for THIS date
            avail_seats = _available_seats_for_date(flight, travel_date_obj)
            if num_passengers > avail_seats:
                flash(f'Only {avail_seats} seats available on {travel_date}', 'warning')
                return redirect(url_for('booking.book_flight', flight_id=flight_id))
            
            # Calculate cost
            base_cost = flight.price * num_passengers
            commission = base_cost * 0.10
            total_cost = base_cost + commission
            
            # Create booking (no permanent seat decrement — availability is computed)
            booking = Booking(
                user_id=current_user.id,
                flight_id=flight_id,
                booking_type='flight',
                start_date=travel_date_obj,
                number_of_passengers=num_passengers,
                total_cost=total_cost,
                commission_amount=commission,
                booking_status='pending'
            )
            
            db.session.add(booking)
            db.session.flush()
            
            db.session.commit()
            
            flash('Flight booked successfully! Proceed to payment', 'success')
            return redirect(url_for('booking.payment', booking_id=booking.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error booking flight: {str(e)}', 'danger')
            return redirect(url_for('booking.book_flight', flight_id=flight_id))
    
    travel_date = request.args.get('travel_date', '')
    return render_template('booking/book_flight.html', flight=flight, travel_date=travel_date)

@bp.route('/train/<int:train_id>', methods=['GET', 'POST'])
@login_required
def book_train(train_id):
    """Book a train"""
    train = Train.query.get_or_404(train_id)
    
    if request.method == 'POST':
        try:
            num_passengers = int(request.form.get('num_passengers', 1))
            travel_date = request.form.get('travel_date')
            
            if not travel_date:
                flash('Travel date is required', 'danger')
                return redirect(url_for('booking.book_train', train_id=train_id))
            
            travel_date_obj = datetime.strptime(travel_date, '%Y-%m-%d').date()
            
            if travel_date_obj < date.today():
                flash('Cannot book for past dates', 'warning')
                return redirect(url_for('booking.book_train', train_id=train_id))
            
            if not train.runs_on(travel_date_obj):
                flash('This train does not operate on the selected date', 'warning')
                return redirect(url_for('booking.book_train', train_id=train_id))
            
            avail_seats = _available_seats_for_train_date(train, travel_date_obj)
            if num_passengers > avail_seats:
                flash(f'Only {avail_seats} seats available on {travel_date}', 'warning')
                return redirect(url_for('booking.book_train', train_id=train_id))
            
            base_cost = train.price * num_passengers
            commission = base_cost * 0.10
            total_cost = base_cost + commission
            
            booking = Booking(
                user_id=current_user.id,
                train_id=train_id,
                booking_type='train',
                start_date=travel_date_obj,
                number_of_passengers=num_passengers,
                total_cost=total_cost,
                commission_amount=commission,
                booking_status='pending'
            )
            
            db.session.add(booking)
            db.session.flush()
            
            db.session.commit()
            
            flash('Train booked successfully! Proceed to payment', 'success')
            return redirect(url_for('booking.payment', booking_id=booking.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error booking train: {str(e)}', 'danger')
            return redirect(url_for('booking.book_train', train_id=train_id))
    
    travel_date = request.args.get('travel_date', '')
    return render_template('booking/book_train.html', train=train, travel_date=travel_date)

@bp.route('/hotel/<int:hotel_id>', methods=['GET', 'POST'])
@login_required
def book_hotel(hotel_id):
    """Book a hotel"""
    hotel = Hotel.query.get_or_404(hotel_id)
    
    if request.method == 'POST':
        try:
            check_in = request.form.get('check_in')
            check_out = request.form.get('check_out')
            num_rooms = int(request.form.get('num_rooms', 1))
            
            if not check_in or not check_out:
                flash('Check-in and check-out dates are required', 'danger')
                return redirect(url_for('booking.book_hotel', hotel_id=hotel_id))
            
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            
            if check_in_date < date.today():
                flash('Cannot book for past dates', 'warning')
                return redirect(url_for('booking.book_hotel', hotel_id=hotel_id))
            
            if check_out_date <= check_in_date:
                flash('Check-out date must be after check-in date', 'warning')
                return redirect(url_for('booking.book_hotel', hotel_id=hotel_id))
            
            # Overlap-based availability
            avail_rooms = _available_rooms_for_dates(hotel, check_in_date, check_out_date)
            if num_rooms > avail_rooms:
                flash(f'Only {avail_rooms} rooms available for those dates', 'warning')
                return redirect(url_for('booking.book_hotel', hotel_id=hotel_id))
            
            nights = (check_out_date - check_in_date).days
            base_cost = hotel.price_per_night * nights * num_rooms
            commission = base_cost * 0.10
            total_cost = base_cost + commission
            
            booking = Booking(
                user_id=current_user.id,
                hotel_id=hotel_id,
                booking_type='hotel',
                start_date=check_in_date,
                end_date=check_out_date,
                number_of_rooms=num_rooms,
                number_of_days=nights,
                total_cost=total_cost,
                commission_amount=commission,
                booking_status='pending'
            )
            
            db.session.add(booking)
            db.session.flush()
            
            db.session.commit()
            
            flash('Hotel booked successfully! Proceed to payment', 'success')
            return redirect(url_for('booking.payment', booking_id=booking.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error booking hotel: {str(e)}', 'danger')
            return redirect(url_for('booking.book_hotel', hotel_id=hotel_id))
    
    return render_template('booking/book_hotel.html', hotel=hotel)

@bp.route('/vehicle/<int:vehicle_id>', methods=['GET', 'POST'])
@login_required
def book_vehicle(vehicle_id):
    """Book a vehicle"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    if request.method == 'POST':
        try:
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            num_vehicles = int(request.form.get('num_vehicles', 1))
            
            if not start_date or not end_date:
                flash('Start and end dates are required', 'danger')
                return redirect(url_for('booking.book_vehicle', vehicle_id=vehicle_id))
            
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if start_date_obj < date.today():
                flash('Cannot book for past dates', 'warning')
                return redirect(url_for('booking.book_vehicle', vehicle_id=vehicle_id))
            
            if end_date_obj <= start_date_obj:
                flash('End date must be after start date', 'warning')
                return redirect(url_for('booking.book_vehicle', vehicle_id=vehicle_id))
            
            # Overlap-based availability
            avail_units = _available_vehicles_for_dates(vehicle, start_date_obj, end_date_obj)
            if num_vehicles > avail_units:
                flash(f'Only {avail_units} units available for those dates', 'warning')
                return redirect(url_for('booking.book_vehicle', vehicle_id=vehicle_id))
            
            days = (end_date_obj - start_date_obj).days
            base_cost = vehicle.price_per_day * days * num_vehicles
            commission = base_cost * 0.10
            total_cost = base_cost + commission
            
            booking = Booking(
                user_id=current_user.id,
                vehicle_id=vehicle_id,
                booking_type='vehicle',
                start_date=start_date_obj,
                end_date=end_date_obj,
                number_of_vehicles=num_vehicles,
                number_of_days=days,
                total_cost=total_cost,
                commission_amount=commission,
                booking_status='pending'
            )
            
            db.session.add(booking)
            db.session.flush()
            
            db.session.commit()
            
            flash('Vehicle booked successfully! Proceed to payment', 'success')
            return redirect(url_for('booking.payment', booking_id=booking.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error booking vehicle: {str(e)}', 'danger')
            return redirect(url_for('booking.book_vehicle', vehicle_id=vehicle_id))
    
    return render_template('booking/book_vehicle.html', vehicle=vehicle)

@bp.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def payment(booking_id):
    """Payment page with QR code and file upload"""
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('customer.dashboard'))
    
    if booking.booking_status == 'confirmed':
        flash('This booking is already confirmed', 'info')
        return redirect(url_for('customer.view_booking', booking_id=booking_id))
    
    # Check if payment already exists
    payment = Payment.query.filter_by(booking_id=booking_id).first()
    
    if not payment:
        # Generate QR code
        qr_filename, qr_data = generate_qr_code(booking_id, booking.total_cost, current_user.email)
        
        # Create payment record
        payment = Payment(
            user_id=current_user.id,
            booking_id=booking_id,
            amount=booking.total_cost,
            qr_code_path=qr_filename,
            qr_code_data=qr_data,
            payment_status='pending'
        )
        
        db.session.add(payment)
        db.session.commit()
    
    if request.method == 'POST':
        try:
            # Handle file uploads
            screenshot_file = request.files.get('payment_screenshot')
            document_file = request.files.get('trip_document')
            
            uploaded_files = {}
            
            if screenshot_file and allowed_file(screenshot_file.filename):
                filename = secure_filename(f"{uuid.uuid4()}_{screenshot_file.filename}")
                screenshot_file.save(os.path.join(
                    os.path.dirname(__file__), '..', 'static', 'uploads', filename
                ))
                payment.payment_screenshot = filename
                uploaded_files['screenshot'] = filename
            
            if document_file and allowed_file(document_file.filename):
                filename = secure_filename(f"{uuid.uuid4()}_{document_file.filename}")
                document_file.save(os.path.join(
                    os.path.dirname(__file__), '..', 'static', 'uploads', filename
                ))
                booking.screenshot = filename
                uploaded_files['document'] = filename
            
            if not screenshot_file:
                flash('Payment screenshot is required', 'warning')
                return redirect(url_for('booking.payment', booking_id=booking_id))
            
            # Mark payment as pending review
            payment.payment_status = 'pending'
            booking.booking_status = 'pending'
            payment.transaction_id = str(uuid.uuid4())
            payment.paid_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('Payment details submitted! Awaiting admin confirmation.', 'success')
            return redirect(url_for('customer.view_booking', booking_id=booking_id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing payment: {str(e)}', 'danger')
            return redirect(url_for('booking.payment', booking_id=booking_id))
    
    return render_template('booking/payment.html', booking=booking, payment=payment)

@bp.route('/qrcode/<int:payment_id>')
@login_required
def get_qrcode(payment_id):
    """Get QR code image"""
    payment = Payment.query.get_or_404(payment_id)
    
    if payment.user_id != current_user.id and not current_user.is_admin():
        flash('Unauthorized access', 'danger')
        return redirect(url_for('customer.dashboard'))
    
    qr_path = os.path.join(
        os.path.dirname(__file__), '..', 'static', 'uploads', payment.qr_code_path
    )
    
    if os.path.exists(qr_path):
        return send_file(qr_path, mimetype='image/png')
    
    flash('QR code not found', 'danger')
    return redirect(url_for('customer.dashboard'))
