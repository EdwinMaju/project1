from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, User, Flight, Train, Hotel, Vehicle, Booking, Payment, HelpDeskMessage
from datetime import datetime, date
import uuid

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to check if user is admin"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required', 'danger')
            return redirect(url_for('customer.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard"""
    # Statistics
    total_bookings = Booking.query.count()
    confirmed_bookings = Booking.query.filter_by(booking_status='confirmed').count()
    pending_bookings = Booking.query.filter_by(booking_status='pending').count()
    cancelled_bookings = Booking.query.filter_by(booking_status='cancelled').count()
    
    total_users = User.query.filter_by(role='customer').count()
    
    confirmed_bookings_list = Booking.query.filter_by(booking_status='confirmed').all()
    total_revenue = sum([b.total_cost for b in confirmed_bookings_list])
    total_commission = sum([b.commission_amount or 0 for b in confirmed_bookings_list])
    
    # Recent bookings
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()
    
    # Pending payments
    pending_payments = Payment.query.filter_by(payment_status='pending').count()
    pending_amount = sum([b.total_cost for b in Booking.query.filter_by(booking_status='pending').all()])
    
    # Pending support messages
    unread_support_messages = HelpDeskMessage.query.filter_by(sender_type='customer', is_read=False).count()
    
    return render_template('admin/dashboard.html',
                         total_bookings=total_bookings,
                         confirmed_bookings=confirmed_bookings,
                         pending_bookings=pending_bookings,
                         cancelled_bookings=cancelled_bookings,
                         total_users=total_users,
                         total_revenue=total_revenue,
                         total_commission=total_commission,
                         pending_amount=pending_amount,
                         recent_bookings=recent_bookings,
                         pending_payments=pending_payments,
                         unread_support_messages=unread_support_messages)

# ========== BOOKING MANAGEMENT ==========

@bp.route('/bookings')
@login_required
@admin_required
def manage_bookings():
    """View all bookings"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = Booking.query
    if status:
        query = query.filter_by(booking_status=status)
    
    bookings = query.order_by(Booking.created_at.desc()).paginate(page=page, per_page=10)
    
    return render_template('admin/manage_bookings.html', bookings=bookings, status=status)

@bp.route('/booking/<int:booking_id>/confirm', methods=['POST'])
@login_required
@admin_required
def confirm_booking(booking_id):
    """Confirm a booking"""
    booking = Booking.query.get_or_404(booking_id)
    
    try:
        admin_notes = request.form.get('admin_notes', '')
        
        booking.booking_status = 'confirmed'
        booking.admin_notes = admin_notes
        booking.confirmed_by = current_user.id
        booking.confirmed_at = datetime.utcnow()
        
        # Update payment status
        if booking.payment:
            booking.payment.payment_status = 'completed'
        
        db.session.commit()
        
        flash('Booking confirmed successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error confirming booking: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_bookings'))

@bp.route('/booking/<int:booking_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_booking(booking_id):
    """Reject a booking"""
    booking = Booking.query.get_or_404(booking_id)
    
    try:
        admin_notes = request.form.get('admin_notes', '')
        
        # Restore availability
        if booking.flight_id:
            booking.flight.available_seats += booking.number_of_passengers
        elif booking.train_id:
            booking.train.available_seats += booking.number_of_passengers
        elif booking.hotel_id:
            booking.hotel.available_rooms += booking.number_of_rooms
        elif booking.vehicle_id:
            booking.vehicle.available_units += booking.number_of_vehicles
        
        booking.booking_status = 'cancelled'
        booking.admin_notes = admin_notes
        
        if booking.payment:
            booking.payment.payment_status = 'failed'
        
        db.session.commit()
        
        flash('Booking rejected and cancelled', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error rejecting booking: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_bookings'))

@bp.route('/booking/<int:booking_id>')
@login_required
@admin_required
def view_booking(booking_id):
    """View booking details"""
    booking = Booking.query.get_or_404(booking_id)
    payment = booking.payment
    user = booking.user
    
    return render_template('admin/view_booking.html', booking=booking, payment=payment, user=user)

# ========== FLIGHTS MANAGEMENT ==========

@bp.route('/flights')
@login_required
@admin_required
def manage_flights():
    """Manage flights"""
    page = request.args.get('page', 1, type=int)
    flights = Flight.query.order_by(Flight.departure_time.desc()).paginate(page=page, per_page=10)
    
    return render_template('admin/manage_flights.html', flights=flights)

@bp.route('/flight/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_flight():
    """Add new flight"""
    if request.method == 'POST':
        try:
            flight = Flight(
                flight_number=request.form.get('flight_number'),
                airline=request.form.get('airline'),
                departure_city=request.form.get('departure_city'),
                arrival_city=request.form.get('arrival_city'),
                departure_time=datetime.strptime(request.form.get('departure_time'), '%Y-%m-%dT%H:%M'),
                arrival_time=datetime.strptime(request.form.get('arrival_time'), '%Y-%m-%dT%H:%M'),
                price=float(request.form.get('price')),
                available_seats=int(request.form.get('seats', 200)),
                total_seats=int(request.form.get('seats', 200)),
                created_by=current_user.id
            )
            
            db.session.add(flight)
            db.session.commit()
            
            flash('Flight added successfully', 'success')
            return redirect(url_for('admin.manage_flights'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding flight: {str(e)}', 'danger')
    
    return render_template('admin/add_flight.html')

@bp.route('/flight/<int:flight_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_flight(flight_id):
    """Edit flight"""
    flight = Flight.query.get_or_404(flight_id)
    
    if request.method == 'POST':
        try:
            flight.flight_number = request.form.get('flight_number')
            flight.airline = request.form.get('airline')
            flight.departure_city = request.form.get('departure_city')
            flight.arrival_city = request.form.get('arrival_city')
            flight.departure_time = datetime.strptime(request.form.get('departure_time'), '%Y-%m-%dT%H:%M')
            flight.arrival_time = datetime.strptime(request.form.get('arrival_time'), '%Y-%m-%dT%H:%M')
            flight.price = float(request.form.get('price'))
            
            db.session.commit()
            
            flash('Flight updated successfully', 'success')
            return redirect(url_for('admin.manage_flights'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating flight: {str(e)}', 'danger')
    
    return render_template('admin/edit_flight.html', flight=flight)

@bp.route('/flight/<int:flight_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_flight(flight_id):
    """Delete flight"""
    flight = Flight.query.get_or_404(flight_id)
    
    try:
        db.session.delete(flight)
        db.session.commit()
        flash('Flight deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting flight: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_flights'))

# ========== TRAINS MANAGEMENT ==========

@bp.route('/trains')
@login_required
@admin_required
def manage_trains():
    """Manage trains"""
    page = request.args.get('page', 1, type=int)
    trains = Train.query.order_by(Train.departure_time.desc()).paginate(page=page, per_page=10)
    
    return render_template('admin/manage_trains.html', trains=trains)

@bp.route('/train/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_train():
    """Add new train"""
    if request.method == 'POST':
        try:
            train = Train(
                train_number=request.form.get('train_number'),
                train_name=request.form.get('train_name'),
                departure_city=request.form.get('departure_city'),
                arrival_city=request.form.get('arrival_city'),
                departure_time=datetime.strptime(request.form.get('departure_time'), '%Y-%m-%dT%H:%M'),
                arrival_time=datetime.strptime(request.form.get('arrival_time'), '%Y-%m-%dT%H:%M'),
                price=float(request.form.get('price')),
                coach_type=request.form.get('coach_type'),
                available_seats=int(request.form.get('seats', 500)),
                total_seats=int(request.form.get('seats', 500)),
                created_by=current_user.id
            )
            
            db.session.add(train)
            db.session.commit()
            
            flash('Train added successfully', 'success')
            return redirect(url_for('admin.manage_trains'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding train: {str(e)}', 'danger')
    
    return render_template('admin/add_train.html')

# ========== HOTELS MANAGEMENT ==========

@bp.route('/hotels')
@login_required
@admin_required
def manage_hotels():
    """Manage hotels"""
    page = request.args.get('page', 1, type=int)
    hotels = Hotel.query.order_by(Hotel.created_at.desc()).paginate(page=page, per_page=10)
    
    return render_template('admin/manage_hotels.html', hotels=hotels)

@bp.route('/hotel/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_hotel():
    """Add new hotel"""
    if request.method == 'POST':
        try:
            hotel = Hotel(
                name=request.form.get('name'),
                city=request.form.get('city'),
                address=request.form.get('address'),
                description=request.form.get('description'),
                price_per_night=float(request.form.get('price_per_night')),
                available_rooms=int(request.form.get('rooms', 50)),
                total_rooms=int(request.form.get('rooms', 50)),
                rating=float(request.form.get('rating', 4.0)),
                amenities=request.form.get('amenities'),
                created_by=current_user.id
            )
            
            db.session.add(hotel)
            db.session.commit()
            
            flash('Hotel added successfully', 'success')
            return redirect(url_for('admin.manage_hotels'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding hotel: {str(e)}', 'danger')
    
    return render_template('admin/add_hotel.html')

# ========== VEHICLES MANAGEMENT ==========

@bp.route('/vehicles')
@login_required
@admin_required
def manage_vehicles():
    """Manage vehicles"""
    page = request.args.get('page', 1, type=int)
    vehicles = Vehicle.query.order_by(Vehicle.created_at.desc()).paginate(page=page, per_page=10)
    
    return render_template('admin/manage_vehicles.html', vehicles=vehicles)

@bp.route('/vehicle/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_vehicle():
    """Add new vehicle"""
    if request.method == 'POST':
        try:
            vehicle = Vehicle(
                vehicle_number=request.form.get('vehicle_number'),
                vehicle_type=request.form.get('vehicle_type'),
                city=request.form.get('city'),
                description=request.form.get('description'),
                price_per_day=float(request.form.get('price_per_day')),
                available_units=int(request.form.get('units', 20)),
                total_units=int(request.form.get('units', 20)),
                capacity=int(request.form.get('capacity')),
                created_by=current_user.id
            )
            
            db.session.add(vehicle)
            db.session.commit()
            
            flash('Vehicle added successfully', 'success')
            return redirect(url_for('admin.manage_vehicles'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding vehicle: {str(e)}', 'danger')
    
    return render_template('admin/add_vehicle.html')

# ========== USERS MANAGEMENT ==========

@bp.route('/users')
@login_required
@admin_required
def manage_users():
    """Manage customers"""
    page = request.args.get('page', 1, type=int)
    users = User.query.filter_by(role='customer').paginate(page=page, per_page=10)
    
    return render_template('admin/manage_users.html', users=users)

@bp.route('/user/<int:user_id>/deactivate', methods=['POST'])
@login_required
@admin_required
def deactivate_user(user_id):
    """Deactivate user"""
    user = User.query.get_or_404(user_id)
    
    try:
        user.is_active = False
        db.session.commit()
        flash(f'User {user.username} deactivated', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deactivating user: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_users'))

@bp.route('/records')
@login_required
@admin_required
def records():
    """View all records"""
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    payments = Payment.query.order_by(Payment.created_at.desc()).all()
    
    return render_template('admin/records.html', bookings=bookings, payments=payments)

@bp.route('/income')
@login_required
@admin_required
def income():
    """View system income/commission from bookings"""
    # Only confirmed bookings generate actual realized income
    bookings = Booking.query.filter_by(booking_status='confirmed').order_by(Booking.created_at.desc()).all()
    
    total_commission = sum([b.commission_amount or 0 for b in bookings])
    
    return render_template('admin/income.html', bookings=bookings, total_commission=total_commission)

@bp.route('/help-desk')
@login_required
@admin_required
def help_desk():
    """Admin help desk overview - lists all customers who have sent messages"""
    # Get all unique users who have messaged
    # We want to show the latest message from each user
    from sqlalchemy import func
    
    subquery = db.session.query(
        HelpDeskMessage.user_id,
        func.max(HelpDeskMessage.created_at).label('max_created')
    ).group_by(HelpDeskMessage.user_id).subquery()
    
    chats = db.session.query(HelpDeskMessage).join(
        subquery,
        (HelpDeskMessage.user_id == subquery.c.user_id) & 
        (HelpDeskMessage.created_at == subquery.c.max_created)
    ).order_by(HelpDeskMessage.created_at.desc()).all()
    
    # Add unread count for each chat
    for chat in chats:
        chat.unread_count = HelpDeskMessage.query.filter_by(
            user_id=chat.user_id,
            sender_type='customer',
            is_read=False
        ).count()
        
    return render_template('admin/help_desk.html', chats=chats)

@bp.route('/help-desk/chat/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def view_chat(user_id):
    """Admin view of a specific customer chat"""
    customer = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        message_text = request.form.get('message')
        if message_text:
            new_message = HelpDeskMessage(
                user_id=user_id,
                message=message_text,
                sender_type='admin'
            )
            db.session.add(new_message)
            db.session.commit()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'status': 'success',
                    'message': message_text,
                    'created_at': new_message.created_at.strftime('%Y-%m-%d %H:%M')
                })
            
            return redirect(url_for('admin.view_chat', user_id=user_id))
    
    messages = HelpDeskMessage.query.filter_by(user_id=user_id).order_by(HelpDeskMessage.created_at.asc()).all()
    
    # Mark customer messages as read
    unread_customer_messages = HelpDeskMessage.query.filter_by(
        user_id=user_id,
        sender_type='customer',
        is_read=False
    ).all()
    for m in unread_customer_messages:
        m.is_read = True
    db.session.commit()
    
    return render_template('admin/chat_view.html', customer=customer, messages=messages)

@bp.route('/help-desk/api/messages/<int:user_id>')
@login_required
@admin_required
def get_messages(user_id):
    """API for polling new messages for a specific chat"""
    messages = HelpDeskMessage.query.filter_by(user_id=user_id).order_by(HelpDeskMessage.created_at.asc()).all()
    
    # Mark as read
    unread_customer_messages = HelpDeskMessage.query.filter_by(
        user_id=user_id,
        sender_type='customer',
        is_read=False
    ).all()
    for m in unread_customer_messages:
        m.is_read = True
    db.session.commit()

    return jsonify([{
        'message': m.message,
        'sender_type': m.sender_type,
        'created_at': m.created_at.strftime('%Y-%m-%d %H:%M'),
        'id': m.id
    } for m in messages])
