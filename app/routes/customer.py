from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, Flight, Train, Hotel, Vehicle, Booking, User, HelpDeskMessage
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_
import json

bp = Blueprint('customer', __name__, url_prefix='/customer')


# ────────────────────────────────────────────
#  Availability helpers (overlap-based)
# ────────────────────────────────────────────

def _available_seats_for_date(flight, travel_date):
    """Get available seats for a flight on a specific date (overlap-based)."""
    booked = db.session.query(func.coalesce(func.sum(Booking.number_of_passengers), 0)).filter(
        Booking.flight_id == flight.id,
        Booking.start_date == travel_date,
        Booking.booking_status != 'cancelled'
    ).scalar()
    return flight.total_seats - int(booked)


def _available_seats_for_train_date(train, travel_date):
    """Get available seats for a train on a specific date."""
    booked = db.session.query(func.coalesce(func.sum(Booking.number_of_passengers), 0)).filter(
        Booking.train_id == train.id,
        Booking.start_date == travel_date,
        Booking.booking_status != 'cancelled'
    ).scalar()
    return train.total_seats - int(booked)


def _available_rooms_for_dates(hotel, check_in, check_out):
    """Get available rooms for a hotel during a date range (overlap-based).
    A room is occupied if existing booking overlaps with [check_in, check_out).
    """
    overlapping = db.session.query(func.coalesce(func.sum(Booking.number_of_rooms), 0)).filter(
        Booking.hotel_id == hotel.id,
        Booking.booking_status != 'cancelled',
        Booking.start_date < check_out,
        Booking.end_date > check_in,
    ).scalar()
    return hotel.total_rooms - int(overlapping)


def _available_vehicles_for_dates(vehicle, start_date, end_date):
    """Get available vehicles during a date range (overlap-based)."""
    overlapping = db.session.query(func.coalesce(func.sum(Booking.number_of_vehicles), 0)).filter(
        Booking.vehicle_id == vehicle.id,
        Booking.booking_status != 'cancelled',
        Booking.start_date < end_date,
        Booking.end_date > start_date,
    ).scalar()
    return vehicle.total_units - int(overlapping)


# ────────────────────────────────────────────
#  Recommendation scoring helpers
# ────────────────────────────────────────────

def _booking_counts():
    """Return dict of {booking_type: {item_id: count}}"""
    rows = (
        db.session.query(Booking.booking_type, Booking.flight_id,
                         Booking.train_id, Booking.hotel_id,
                         Booking.vehicle_id, func.count(Booking.id))
        .group_by(Booking.booking_type, Booking.flight_id,
                  Booking.train_id, Booking.hotel_id, Booking.vehicle_id)
        .all()
    )
    counts = {'flight': {}, 'train': {}, 'hotel': {}, 'vehicle': {}}
    for btype, fid, tid, hid, vid, cnt in rows:
        if btype == 'flight' and fid:
            counts['flight'][fid] = cnt
        elif btype == 'train' and tid:
            counts['train'][tid] = cnt
        elif btype == 'hotel' and hid:
            counts['hotel'][hid] = cnt
        elif btype == 'vehicle' and vid:
            counts['vehicle'][vid] = cnt
    return counts


def _score_flights(flights, booking_counts):
    """Score each flight and return list of (flight, score, badge, reason)"""
    if not flights:
        return []
    prices = [f.price for f in flights]
    min_price = min(prices) if prices else 1
    max_price = max(prices) if prices else 1
    price_range = max_price - min_price if max_price != min_price else 1

    scored = []
    for f in flights:
        price_score = (1 - (f.price - min_price) / price_range) * 40  # 0-40
        avail_score = min(f.available_seats / max(f.total_seats, 1), 1) * 20  # 0-20
        pop = booking_counts.get('flight', {}).get(f.id, 0)
        pop_score = min(pop / 10, 1) * 40  # 0-40
        total = price_score + avail_score + pop_score
        scored.append((f, round(total, 1), pop))

    scored.sort(key=lambda x: x[1], reverse=True)

    result = []
    best_value_given = False
    most_popular_given = False
    for f, score, pop in scored:
        badge = None
        reason = ''
        if not best_value_given and f.price == min_price:
            badge = 'Best Value'
            reason = 'Lowest price in your search'
            best_value_given = True
        elif not most_popular_given and pop > 0:
            badge = 'Most Popular'
            reason = f'Booked {pop} times recently'
            most_popular_given = True
        elif score >= 60:
            badge = 'Recommended'
            reason = 'Great balance of price & availability'
        result.append({'item': f, 'score': score, 'badge': badge, 'reason': reason})
    return result


def _score_trains(trains, booking_counts):
    if not trains:
        return []
    prices = [t.price for t in trains]
    min_price = min(prices) if prices else 1
    max_price = max(prices) if prices else 1
    price_range = max_price - min_price if max_price != min_price else 1

    scored = []
    for t in trains:
        price_score = (1 - (t.price - min_price) / price_range) * 40
        avail_score = min(t.available_seats / max(t.total_seats, 1), 1) * 20
        pop = booking_counts.get('train', {}).get(t.id, 0)
        pop_score = min(pop / 10, 1) * 40
        total = price_score + avail_score + pop_score
        scored.append((t, round(total, 1), pop))

    scored.sort(key=lambda x: x[1], reverse=True)
    result = []
    best_value_given = False
    most_popular_given = False
    for t, score, pop in scored:
        badge = None
        reason = ''
        if not best_value_given and t.price == min_price:
            badge = 'Best Value'
            reason = 'Lowest price in your search'
            best_value_given = True
        elif not most_popular_given and pop > 0:
            badge = 'Most Popular'
            reason = f'Booked {pop} times recently'
            most_popular_given = True
        elif score >= 60:
            badge = 'Recommended'
            reason = 'Great balance of price & availability'
        result.append({'item': t, 'score': score, 'badge': badge, 'reason': reason})
    return result


def _score_hotels(hotels, booking_counts):
    if not hotels:
        return []
    prices = [h.price_per_night for h in hotels]
    min_price = min(prices) if prices else 1
    max_price = max(prices) if prices else 1
    price_range = max_price - min_price if max_price != min_price else 1

    scored = []
    for h in hotels:
        price_score = (1 - (h.price_per_night - min_price) / price_range) * 25
        avail_score = min(h.available_rooms / max(h.total_rooms, 1), 1) * 15
        rating_score = (h.rating or 3) / 5 * 30
        pop = booking_counts.get('hotel', {}).get(h.id, 0)
        pop_score = min(pop / 10, 1) * 30
        total = price_score + avail_score + rating_score + pop_score
        scored.append((h, round(total, 1), pop))

    scored.sort(key=lambda x: x[1], reverse=True)
    result = []
    best_value_given = False
    top_rated_given = False
    most_popular_given = False
    for h, score, pop in scored:
        badge = None
        reason = ''
        if not top_rated_given and (h.rating or 0) >= 4.5:
            badge = 'Top Rated'
            reason = f'Rated {h.rating}★ by guests'
            top_rated_given = True
        elif not best_value_given and h.price_per_night == min_price:
            badge = 'Best Value'
            reason = 'Lowest price per night'
            best_value_given = True
        elif not most_popular_given and pop > 0:
            badge = 'Most Popular'
            reason = f'Booked {pop} times recently'
            most_popular_given = True
        elif score >= 55:
            badge = 'Recommended'
            reason = 'Great balance of price, rating & availability'
        result.append({'item': h, 'score': score, 'badge': badge, 'reason': reason})
    return result


def _score_vehicles(vehicles, booking_counts):
    if not vehicles:
        return []
    prices = [v.price_per_day for v in vehicles]
    min_price = min(prices) if prices else 1
    max_price = max(prices) if prices else 1
    price_range = max_price - min_price if max_price != min_price else 1

    scored = []
    for v in vehicles:
        price_score = (1 - (v.price_per_day - min_price) / price_range) * 40
        avail_score = min(v.available_units / max(v.total_units, 1), 1) * 20
        pop = booking_counts.get('vehicle', {}).get(v.id, 0)
        pop_score = min(pop / 10, 1) * 40
        total = price_score + avail_score + pop_score
        scored.append((v, round(total, 1), pop))

    scored.sort(key=lambda x: x[1], reverse=True)
    result = []
    best_value_given = False
    most_popular_given = False
    for v, score, pop in scored:
        badge = None
        reason = ''
        if not best_value_given and v.price_per_day == min_price:
            badge = 'Best Value'
            reason = 'Lowest daily rate'
            best_value_given = True
        elif not most_popular_given and pop > 0:
            badge = 'Most Popular'
            reason = f'Booked {pop} times recently'
            most_popular_given = True
        elif score >= 60:
            badge = 'Recommended'
            reason = 'Great balance of price & availability'
        result.append({'item': v, 'score': score, 'badge': badge, 'reason': reason})
    return result


# ────────────────────────────────────────────
#  Routes
# ────────────────────────────────────────────

@bp.route('/dashboard')
@login_required
def dashboard():
    """Customer dashboard"""
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    
    # Get customer's bookings
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    
    # Summary statistics
    total_bookings = len(bookings)
    confirmed_bookings = len([b for b in bookings if b.booking_status == 'confirmed'])
    pending_bookings = len([b for b in bookings if b.booking_status == 'pending'])
    total_spent = sum([b.total_cost for b in bookings if b.booking_status == 'confirmed'])
    
    return render_template('customer/dashboard.html', 
                         bookings=bookings,
                         total_bookings=total_bookings,
                         confirmed_bookings=confirmed_bookings,
                         pending_bookings=pending_bookings,
                         total_spent=total_spent)

@bp.route('/search', methods=['GET'])
@login_required
def search():
    """Search for flights, trains, hotels, vehicles — with recurring schedule logic"""
    departure = request.args.get('departure', '')
    arrival = request.args.get('arrival', '')
    travel_date = request.args.get('travel_date', '')
    return_date = request.args.get('return_date', '')
    transport_type = request.args.get('transport_type', 'flight')
    sort_by = request.args.get('sort_by', 'recommended')
    
    results = {'flights': [], 'trains': [], 'hotels': [], 'vehicles': []}
    scored = {'flights': [], 'trains': [], 'hotels': [], 'vehicles': []}
    
    try:
        if travel_date:
            travel_date_obj = datetime.strptime(travel_date, '%Y-%m-%d').date()
            
            # Check if date is not in the past
            if travel_date_obj < date.today():
                flash('Cannot book for past dates', 'warning')
                return redirect(url_for('customer.search_page'))
            
            return_date_obj = None
            if return_date:
                return_date_obj = datetime.strptime(return_date, '%Y-%m-%d').date()

            # ── Flights: recurring schedule match ──
            if transport_type in ['flight', 'all']:
                all_flights = Flight.query.filter(
                    Flight.departure_city.ilike(f'%{departure}%'),
                    Flight.arrival_city.ilike(f'%{arrival}%'),
                ).all()
                # Filter by operating_days and schedule window
                results['flights'] = [f for f in all_flights if f.runs_on(travel_date_obj)]
            
            # ── Trains: recurring schedule match ──
            if transport_type in ['train', 'all']:
                all_trains = Train.query.filter(
                    Train.departure_city.ilike(f'%{departure}%'),
                    Train.arrival_city.ilike(f'%{arrival}%'),
                ).all()
                results['trains'] = [t for t in all_trains if t.runs_on(travel_date_obj)]
            
            # ── Hotels: overlap-based availability ──
            if transport_type in ['hotel', 'all']:
                check_out = return_date_obj if return_date_obj else travel_date_obj + timedelta(days=1)
                all_hotels = Hotel.query.filter(
                    Hotel.city.ilike(f'%{arrival}%'),
                ).all()
                # Only include hotels with rooms available for the date range
                for h in all_hotels:
                    avail = _available_rooms_for_dates(h, travel_date_obj, check_out)
                    if avail > 0:
                        h.available_rooms = avail  # update for display
                        results['hotels'].append(h)
            
            # ── Vehicles: overlap-based availability ──
            if transport_type in ['vehicle', 'all']:
                v_end = return_date_obj if return_date_obj else travel_date_obj + timedelta(days=1)
                all_vehicles = Vehicle.query.filter(
                    Vehicle.city.ilike(f'%{arrival}%'),
                ).all()
                for v in all_vehicles:
                    avail = _available_vehicles_for_dates(v, travel_date_obj, v_end)
                    if avail > 0:
                        v.available_units = avail  # update for display
                        results['vehicles'].append(v)

            # Build recommendation scores
            bcounts = _booking_counts()
            scored['flights'] = _score_flights(results['flights'], bcounts)
            scored['trains'] = _score_trains(results['trains'], bcounts)
            scored['hotels'] = _score_hotels(results['hotels'], bcounts)
            scored['vehicles'] = _score_vehicles(results['vehicles'], bcounts)

            # Apply user-chosen sort
            if sort_by == 'price_low':
                scored['flights'].sort(key=lambda x: x['item'].price)
                scored['trains'].sort(key=lambda x: x['item'].price)
                scored['hotels'].sort(key=lambda x: x['item'].price_per_night)
                scored['vehicles'].sort(key=lambda x: x['item'].price_per_day)
            elif sort_by == 'price_high':
                scored['flights'].sort(key=lambda x: x['item'].price, reverse=True)
                scored['trains'].sort(key=lambda x: x['item'].price, reverse=True)
                scored['hotels'].sort(key=lambda x: x['item'].price_per_night, reverse=True)
                scored['vehicles'].sort(key=lambda x: x['item'].price_per_day, reverse=True)
            # 'recommended' is the default — already sorted by score
    
    except ValueError:
        flash('Invalid date format', 'danger')
    
    return render_template('customer/search.html', 
                         results=results,
                         scored=scored,
                         departure=departure,
                         arrival=arrival,
                         travel_date=travel_date,
                         return_date=return_date,
                         transport_type=transport_type,
                         sort_by=sort_by)

@bp.route('/search-page')
@login_required
def search_page():
    """Search page"""
    return render_template('customer/search_page.html')

@bp.route('/view-booking/<int:booking_id>')
@login_required
def view_booking(booking_id):
    """View booking details"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Verify user owns this booking
    if booking.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('customer.dashboard'))
    
    payment = booking.payment
    
    return render_template('customer/view_booking.html', booking=booking, payment=payment)

@bp.route('/my-records')
@login_required
def my_records():
    """View all booking records"""
    page = request.args.get('page', 1, type=int)
    
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(
        Booking.created_at.desc()
    ).paginate(page=page, per_page=10)
    
    return render_template('customer/my_records.html', bookings=bookings)

@bp.route('/download-invoice/<int:booking_id>')
@login_required
def download_invoice(booking_id):
    """Download booking invoice"""
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('customer.dashboard'))
    
    # Generate invoice (simplified - in production use library like ReportLab)
    from flask import make_response
    
    invoice_content = f"""
    TRAVEL BOOKING INVOICE
    ======================
    
    Booking ID: {booking.id}
    Customer: {current_user.first_name} {current_user.last_name}
    Email: {current_user.email}
    Phone: {current_user.phone}
    
    Booking Details:
    Type: {booking.booking_type}
    Status: {booking.booking_status}
    Start Date: {booking.start_date}
    End Date: {booking.end_date}
    
    Cost: Rs. {booking.total_cost}
    
    Booking Created: {booking.created_at.strftime('%Y-%m-%d %H:%M')}
    """
    
    response = make_response(invoice_content)
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{booking.id}.txt'
    return response

@bp.route('/compare')
@login_required
def compare():
    """Chart-based comparison page with recommendation"""
    compare_type = request.args.get('type', '')
    ids_str = request.args.get('ids', '')

    if not compare_type or not ids_str:
        flash('Select at least 2 items of the same type to compare.', 'warning')
        return redirect(url_for('customer.search_page'))

    try:
        ids = [int(i) for i in ids_str.split(',') if i.strip()]
    except ValueError:
        flash('Invalid comparison selection.', 'danger')
        return redirect(url_for('customer.search_page'))

    if len(ids) < 2:
        flash('Select at least 2 items to compare.', 'warning')
        return redirect(url_for('customer.search_page'))
    if len(ids) > 4:
        ids = ids[:4]

    items = []
    model_map = {
        'flight': Flight,
        'train': Train,
        'hotel': Hotel,
        'vehicle': Vehicle,
    }
    model = model_map.get(compare_type)
    if not model:
        flash('Invalid comparison type.', 'danger')
        return redirect(url_for('customer.search_page'))

    for item_id in ids:
        item = model.query.get(item_id)
        if item:
            items.append(item)

    if len(items) < 2:
        flash('Could not find enough items to compare.', 'warning')
        return redirect(url_for('customer.search_page'))

    # ── Build chart data ──
    bcounts = _booking_counts()
    chart_labels = []  # Item names
    chart_prices = []
    chart_availability = []
    chart_popularity = []
    chart_scores = []   # Overall recommendation scores
    chart_ratings = []  # For hotels
    chart_duration = [] # For flights/trains (minutes)

    # Determine max values for normalization
    if compare_type == 'flight':
        prices = [i.price for i in items]
        max_price = max(prices) if prices else 1
        for f in items:
            chart_labels.append(f'{f.airline} ({f.flight_number})')
            chart_prices.append(f.price)
            chart_availability.append(round(f.available_seats / max(f.total_seats, 1) * 100))
            pop = bcounts.get('flight', {}).get(f.id, 0)
            chart_popularity.append(min(pop * 10, 100))
            # Duration in minutes
            dur = int((f.arrival_time - f.departure_time).total_seconds() / 60)
            chart_duration.append(dur)
            # Overall score
            price_s = (1 - (f.price / max_price)) * 100 if max_price else 50
            chart_scores.append(round((price_s + chart_availability[-1] + chart_popularity[-1]) / 3))

    elif compare_type == 'train':
        prices = [i.price for i in items]
        max_price = max(prices) if prices else 1
        for t in items:
            chart_labels.append(f'{t.train_name}')
            chart_prices.append(t.price)
            chart_availability.append(round(t.available_seats / max(t.total_seats, 1) * 100))
            pop = bcounts.get('train', {}).get(t.id, 0)
            chart_popularity.append(min(pop * 10, 100))
            dur = int((t.arrival_time - t.departure_time).total_seconds() / 60)
            chart_duration.append(abs(dur))
            price_s = (1 - (t.price / max_price)) * 100 if max_price else 50
            chart_scores.append(round((price_s + chart_availability[-1] + chart_popularity[-1]) / 3))

    elif compare_type == 'hotel':
        prices = [i.price_per_night for i in items]
        max_price = max(prices) if prices else 1
        for h in items:
            chart_labels.append(h.name)
            chart_prices.append(h.price_per_night)
            chart_availability.append(round(h.available_rooms / max(h.total_rooms, 1) * 100))
            pop = bcounts.get('hotel', {}).get(h.id, 0)
            chart_popularity.append(min(pop * 10, 100))
            chart_ratings.append((h.rating or 3) * 20)  # scale to 0-100
            price_s = (1 - (h.price_per_night / max_price)) * 100 if max_price else 50
            chart_scores.append(round((price_s + chart_availability[-1] + chart_ratings[-1] + chart_popularity[-1]) / 4))

    elif compare_type == 'vehicle':
        prices = [i.price_per_day for i in items]
        max_price = max(prices) if prices else 1
        for v in items:
            chart_labels.append(f'{v.vehicle_type} ({v.vehicle_number})')
            chart_prices.append(v.price_per_day)
            chart_availability.append(round(v.available_units / max(v.total_units, 1) * 100))
            pop = bcounts.get('vehicle', {}).get(v.id, 0)
            chart_popularity.append(min(pop * 10, 100))
            price_s = (1 - (v.price_per_day / max_price)) * 100 if max_price else 50
            chart_scores.append(round((price_s + chart_availability[-1] + chart_popularity[-1]) / 3))

    # Find best pick
    best_idx = chart_scores.index(max(chart_scores)) if chart_scores else 0

    # Build radar chart data (normalized 0-100)
    radar_datasets = []
    colors = ['rgba(30,64,175,0.7)', 'rgba(16,185,129,0.7)', 'rgba(245,158,11,0.7)', 'rgba(139,92,246,0.7)']
    bg_colors = ['rgba(30,64,175,0.15)', 'rgba(16,185,129,0.15)', 'rgba(245,158,11,0.15)', 'rgba(139,92,246,0.15)']
    max_price_val = max(chart_prices) if chart_prices else 1

    for i, label in enumerate(chart_labels):
        # Price inverted (lower = better = higher score)
        price_norm = round((1 - chart_prices[i] / max_price_val) * 100) if max_price_val else 50
        data_points = [price_norm, chart_availability[i], chart_popularity[i]]
        radar_labels = ['Price Value', 'Availability', 'Popularity']
        if chart_ratings:
            data_points.append(chart_ratings[i])
            radar_labels.append('Rating')
        if chart_duration:
            max_dur = max(chart_duration) if chart_duration else 1
            dur_norm = round((1 - chart_duration[i] / max_dur) * 100) if max_dur else 50
            data_points.append(dur_norm)
            radar_labels.append('Speed')

        radar_datasets.append({
            'label': label,
            'data': data_points,
            'borderColor': colors[i % len(colors)],
            'backgroundColor': bg_colors[i % len(bg_colors)],
            'pointBackgroundColor': colors[i % len(colors)],
        })

    chart_data = {
        'labels': chart_labels,
        'prices': chart_prices,
        'scores': chart_scores,
        'radar_labels': radar_labels if chart_labels else [],
        'radar_datasets': radar_datasets,
        'best_idx': best_idx,
    }

    return render_template('customer/compare.html',
                         compare_type=compare_type,
                         items=items,
                         chart_data=json.dumps(chart_data),
                         best_idx=best_idx)

@bp.route('/planner', methods=['GET', 'POST'])
@login_required
def planner():
    """Smart Trip Planner - Bundles services based on budget"""
    if request.method == 'GET':
        return render_template('customer/planner.html', packages=None)

    # Get inputs
    departure = request.form.get('departure', '').strip()
    arrival = request.form.get('arrival', '').strip()
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    budget_str = request.form.get('budget', '0')
    
    # Clean budget string just in case
    budget_str = budget_str.replace('₹', '').replace(',', '').strip()
    try:
        budget = float(budget_str) if budget_str else 0
    except ValueError:
        budget = 0
    
    # Selected facilities
    facilities = request.form.getlist('facilities')
    need_flight = 'flight' in facilities
    need_train = 'train' in facilities
    need_hotel = 'hotel' in facilities
    need_vehicle = 'vehicle' in facilities

    if not start_date or not end_date:
        flash('Please select dates', 'warning')
        return redirect(url_for('customer.planner'))

    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        nights = (end_dt - start_dt).days
        if nights < 0:
            flash('End date must be after start date', 'warning')
            return redirect(url_for('customer.planner'))
        if nights == 0: nights = 1
    except ValueError:
        flash('Invalid date format', 'danger')
        return redirect(url_for('customer.planner'))

    # 1. Fetch available options (check requested date + surrounding days)
    # Expanded search to +/- 2 days for better flexibility in planner
    check_dates = [start_dt + timedelta(days=i) for i in range(-2, 3)]
    
    flights = []
    if need_flight:
        all_f = Flight.query.filter(Flight.departure_city.ilike(f'%{departure}%'), Flight.arrival_city.ilike(f'%{arrival}%')).all()
        for f in all_f:
            for cd in check_dates:
                if f.runs_on(cd):
                    flights.append(f)
                    break

    trains = []
    if need_train:
        all_t = Train.query.filter(Train.departure_city.ilike(f'%{departure}%'), Train.arrival_city.ilike(f'%{arrival}%')).all()
        for t in all_t:
            for cd in check_dates:
                if t.runs_on(cd):
                    trains.append(t)
                    break

    hotels = []
    if need_hotel:
        all_h = Hotel.query.filter(Hotel.city.ilike(f'%{arrival}%')).all()
        for h in all_h:
            if _available_rooms_for_dates(h, start_dt, end_dt) > 0:
                hotels.append(h)

    vehicles = []
    if need_vehicle:
        all_v = Vehicle.query.filter(Vehicle.city.ilike(f'%{arrival}%')).all()
        for v in all_v:
            if _available_vehicles_for_dates(v, start_dt, end_dt) > 0:
                vehicles.append(v)

    # 2. Build Packages Helper
    def create_package(trans_item, trans_type, h_list, v_list, mode='balanced'):
        pkg = {'flight': None, 'train': None, 'hotel': None, 'vehicle': None, 'total': 0, 'name': ''}
        
        # Transport
        if trans_item:
            pkg[trans_type] = trans_item
            pkg['total'] += trans_item.price
        
        # Hotel
        if need_hotel and h_list:
            h_list.sort(key=lambda x: x.price_per_night)
            if mode == 'budget': idx = 0
            elif mode == 'luxury': idx = -1
            else: idx = len(h_list) // 2
            
            # Ensure index is within bounds
            idx = max(0, min(idx, len(h_list) - 1))
            pkg['hotel'] = h_list[idx]
            pkg['total'] += h_list[idx].price_per_night * nights
            
        # Vehicle
        if need_vehicle and v_list:
            v_list.sort(key=lambda x: x.price_per_day)
            if mode == 'budget': idx = 0
            elif mode == 'luxury': idx = -1
            else: idx = len(v_list) // 2
            
            idx = max(0, min(idx, len(v_list) - 1))
            pkg['vehicle'] = v_list[idx]
            pkg['total'] += v_list[idx].price_per_day * nights
            
        mode_names = {'budget': 'Economy', 'balanced': 'Standard', 'luxury': 'Premium'}
        trans_label = 'Flight' if trans_type == 'flight' else 'Train' if trans_type == 'train' else 'Stay'
        pkg['name'] = f"{trans_label} {mode_names[mode]}"
        
        # Add 10% commission to total
        pkg['total'] = pkg['total'] * 1.10
        
        return pkg

    final_packages = []
    seen_packages = set()

    def get_pkg_key(p):
        """Generate a unique key for a package to detect duplicates"""
        return (
            p['flight'].id if p['flight'] else None,
            p['train'].id if p['train'] else None,
            p['hotel'].id if p['hotel'] else None,
            p['vehicle'].id if p['vehicle'] else None
        )
    
    # Generate Flight-based packages
    if need_flight and flights:
        flights.sort(key=lambda x: x.price)
        for mode in ['budget', 'balanced', 'luxury']:
            if mode == 'budget': idx = 0
            elif mode == 'luxury': idx = -1
            else: idx = len(flights) // 2
            
            idx = max(0, min(idx, len(flights) - 1))
            p = create_package(flights[idx], 'flight', hotels, vehicles, mode)
            
            key = get_pkg_key(p)
            if p['total'] <= budget and key not in seen_packages:
                final_packages.append(p)
                seen_packages.add(key)
                
    # Generate Train-based packages
    if need_train and trains:
        trains.sort(key=lambda x: x.price)
        for mode in ['budget', 'balanced', 'luxury']:
            if mode == 'budget': idx = 0
            elif mode == 'luxury': idx = -1
            else: idx = len(trains) // 2
            
            idx = max(0, min(idx, len(trains) - 1))
            p = create_package(trains[idx], 'train', hotels, vehicles, mode)
            
            key = get_pkg_key(p)
            if p['total'] <= budget and key not in seen_packages:
                final_packages.append(p)
                seen_packages.add(key)

    # If only non-transport services were requested
    if not need_flight and not need_train:
        for mode in ['budget', 'balanced', 'luxury']:
            p = create_package(None, None, hotels, vehicles, mode)
            
            key = get_pkg_key(p)
            if p['total'] <= budget and key not in seen_packages:
                final_packages.append(p)
                seen_packages.add(key)

    # Sort packages by price
    final_packages.sort(key=lambda x: x['total'])

    return render_template('customer/planner.html', 
                         packages=final_packages, 
                         budget=budget,
                         departure=departure,
                         arrival=arrival,
                         start_date=start_date,
                         end_date=end_date)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.email = request.form.get('email')
        current_user.phone = request.form.get('phone')
        
        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('customer.profile'))
        
    return render_template('customer/profile.html')

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(old_password):
            flash('Current password is incorrect', 'danger')
        elif new_password != confirm_password:
            flash('New passwords do not match', 'danger')
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash('Password updated successfully', 'success')
            return redirect(url_for('customer.settings'))
            
    return render_template('customer/settings.html')

@bp.route('/help-desk', methods=['GET', 'POST'])
@login_required
def help_desk():
    """Customer help desk chat"""
    if request.method == 'POST':
        message_text = request.form.get('message')
        if message_text:
            new_message = HelpDeskMessage(
                user_id=current_user.id,
                message=message_text,
                sender_type='customer'
            )
            db.session.add(new_message)
            db.session.commit()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'status': 'success',
                    'message': message_text,
                    'created_at': new_message.created_at.strftime('%Y-%m-%d %H:%M')
                })
            
            return redirect(url_for('customer.help_desk'))
    
    messages = HelpDeskMessage.query.filter_by(user_id=current_user.id).order_by(HelpDeskMessage.created_at.asc()).all()
    
    # Mark admin messages as read when user views the chat
    unread_admin_messages = HelpDeskMessage.query.filter_by(
        user_id=current_user.id, 
        sender_type='admin', 
        is_read=False
    ).all()
    for m in unread_admin_messages:
        m.is_read = True
    db.session.commit()
    
    return render_template('customer/help_desk.html', messages=messages)

@bp.route('/help-desk/api/messages')
@login_required
def get_messages():
    """API for polling new messages"""
    messages = HelpDeskMessage.query.filter_by(user_id=current_user.id).order_by(HelpDeskMessage.created_at.asc()).all()
    
    # Mark as read
    unread_admin_messages = HelpDeskMessage.query.filter_by(
        user_id=current_user.id, 
        sender_type='admin', 
        is_read=False
    ).all()
    for m in unread_admin_messages:
        m.is_read = True
    db.session.commit()

    return jsonify([{
        'message': m.message,
        'sender_type': m.sender_type,
        'created_at': m.created_at.strftime('%Y-%m-%d %H:%M'),
        'id': m.id
    } for m in messages])


