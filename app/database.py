from datetime import datetime, timedelta, date
from app.models import db, User, Flight, Train, Hotel, Vehicle


def init_db(app):
    """Initialize database with default data"""
    with app.app_context():
        db.create_all()
        
        # Check if data already exists
        if User.query.first():
            print("Database already initialized")
            return
        
        # Create admin user
        admin = User(
            username='admin',
            email='admin@travelbooking.com',
            first_name='Admin',
            last_name='User',
            phone='9876543210',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create demo customer
        customer = User(
            username='customer1',
            email='customer@travelbooking.com',
            first_name='Edwin',
            last_name='Maju',
            phone='9123456789',
            role='customer'
        )
        customer.set_password('customer123')
        db.session.add(customer)
        
        db.session.commit()

        # Broad schedule window (Starts today, ends next year)
        today = date.today()
        sched_end = today + timedelta(days=365)
        # Reference date for time-of-day (Using today's date so it looks current)
        ref_date = datetime.combine(today, datetime.min.time())
        
        # ============================================================
        #  FLIGHTS (20) - Universal everyday flights
        # ============================================================
        flights_data = [
            {'flight_number': 'AI-101', 'airline': 'Air India', 'departure_city': 'Mumbai', 'arrival_city': 'Delhi', 'dep_h': 8, 'dep_m': 0, 'arr_h': 10, 'arr_m': 15, 'price': 5000},
            {'flight_number': 'IN-202', 'airline': 'IndiGo', 'departure_city': 'Mumbai', 'arrival_city': 'Delhi', 'dep_h': 10, 'dep_m': 30, 'arr_h': 12, 'arr_m': 45, 'price': 4200},
            {'flight_number': 'UK-303', 'airline': 'Vistara', 'departure_city': 'Mumbai', 'arrival_city': 'Delhi', 'dep_h': 14, 'dep_m': 0, 'arr_h': 16, 'arr_m': 15, 'price': 6500},
            {'flight_number': 'SG-404', 'airline': 'SpiceJet', 'departure_city': 'Mumbai', 'arrival_city': 'Delhi', 'dep_h': 19, 'dep_m': 0, 'arr_h': 21, 'arr_m': 15, 'price': 3800},
            
            {'flight_number': 'IN-505', 'airline': 'IndiGo', 'departure_city': 'Delhi', 'arrival_city': 'Bangalore', 'dep_h': 7, 'dep_m': 0, 'arr_h': 9, 'arr_m': 45, 'price': 5500},
            {'flight_number': 'AI-606', 'airline': 'Air India', 'departure_city': 'Delhi', 'arrival_city': 'Bangalore', 'dep_h': 13, 'dep_m': 0, 'arr_h': 15, 'arr_m': 45, 'price': 5800},
            {'flight_number': 'I5-707', 'airline': 'AirAsia', 'departure_city': 'Delhi', 'arrival_city': 'Bangalore', 'dep_h': 21, 'dep_m': 30, 'arr_h': 0, 'arr_m': 15, 'price': 4500},
            
            {'flight_number': 'SG-808', 'airline': 'SpiceJet', 'departure_city': 'Mumbai', 'arrival_city': 'Goa', 'dep_h': 9, 'dep_m': 0, 'arr_h': 10, 'arr_m': 15, 'price': 3200},
            {'flight_number': 'IN-909', 'airline': 'IndiGo', 'departure_city': 'Mumbai', 'arrival_city': 'Goa', 'dep_h': 16, 'dep_m': 0, 'arr_h': 17, 'arr_m': 15, 'price': 3500},
            {'flight_number': 'AI-110', 'airline': 'Air India', 'departure_city': 'Mumbai', 'arrival_city': 'Goa', 'dep_h': 12, 'dep_m': 0, 'arr_h': 13, 'arr_m': 15, 'price': 4800},
            
            {'flight_number': 'IN-211', 'airline': 'IndiGo', 'departure_city': 'Bangalore', 'arrival_city': 'Chennai', 'dep_h': 7, 'dep_m': 30, 'arr_h': 8, 'arr_m': 30, 'price': 2200},
            {'flight_number': 'UK-312', 'airline': 'Vistara', 'departure_city': 'Bangalore', 'arrival_city': 'Chennai', 'dep_h': 18, 'dep_m': 45, 'arr_h': 19, 'arr_m': 45, 'price': 3500},
            
            {'flight_number': 'IN-413', 'airline': 'IndiGo', 'departure_city': 'Delhi', 'arrival_city': 'Jaipur', 'dep_h': 6, 'dep_m': 0, 'arr_h': 7, 'arr_m': 0, 'price': 2000},
            {'flight_number': 'AI-514', 'airline': 'Air India', 'departure_city': 'Delhi', 'arrival_city': 'Jaipur', 'dep_h': 20, 'dep_m': 0, 'arr_h': 21, 'arr_m': 0, 'price': 2800},
            
            {'flight_number': 'I5-615', 'airline': 'AirAsia', 'departure_city': 'Kolkata', 'arrival_city': 'Delhi', 'dep_h': 11, 'dep_m': 0, 'arr_h': 13, 'arr_m': 30, 'price': 4600},
            {'flight_number': 'IN-716', 'airline': 'IndiGo', 'departure_city': 'Hyderabad', 'arrival_city': 'Mumbai', 'dep_h': 15, 'dep_m': 0, 'arr_h': 16, 'arr_m': 30, 'price': 3100},
            {'flight_number': 'UK-817', 'airline': 'Vistara', 'departure_city': 'Pune', 'arrival_city': 'Delhi', 'dep_h': 8, 'dep_m': 30, 'arr_h': 10, 'arr_m': 45, 'price': 5200},
            {'flight_number': 'IN-918', 'airline': 'IndiGo', 'departure_city': 'Delhi', 'arrival_city': 'Kochi', 'dep_h': 10, 'dep_m': 0, 'arr_h': 13, 'arr_m': 15, 'price': 6800},
            {'flight_number': 'IN-919', 'airline': 'IndiGo', 'departure_city': 'Delhi', 'arrival_city': 'Mumbai', 'dep_h': 18, 'dep_m': 0, 'arr_h': 20, 'arr_m': 15, 'price': 4300},
            {'flight_number': 'AI-920', 'airline': 'Air India', 'departure_city': 'Delhi', 'arrival_city': 'Mumbai', 'dep_h': 22, 'dep_m': 0, 'arr_h': 0, 'arr_m': 15, 'price': 4100},
        ]
        
        for f in flights_data:
            flight = Flight(
                flight_number=f['flight_number'], airline=f['airline'],
                departure_city=f['departure_city'], arrival_city=f['arrival_city'],
                departure_time=ref_date.replace(hour=f['dep_h'], minute=f['dep_m']),
                arrival_time=ref_date.replace(hour=f['arr_h'], minute=f['arr_m']),
                price=f['price'], total_seats=200, available_seats=200,
                operating_days='Mon,Tue,Wed,Thu,Fri,Sat,Sun',
                schedule_start=today, schedule_end=sched_end, created_by=admin.id
            )
            db.session.add(flight)
        
        # ============================================================
        #  TRAINS (20)
        # ============================================================
        trains_data = [
            {'train_number': 'T-101', 'train_name': 'Rajdhani Exp', 'departure_city': 'Mumbai', 'arrival_city': 'Delhi', 'dep_h': 16, 'dep_m': 0, 'arr_h': 8, 'arr_m': 30, 'price': 2800, 'coach_type': 'AC'},
            {'train_number': 'T-102', 'train_name': 'AK Rajdhani', 'departure_city': 'Mumbai', 'arrival_city': 'Delhi', 'dep_h': 17, 'dep_m': 40, 'arr_h': 10, 'arr_m': 55, 'price': 2500, 'coach_type': 'AC'},
            {'train_number': 'T-103', 'train_name': 'Garib Rath', 'departure_city': 'Mumbai', 'arrival_city': 'Delhi', 'dep_h': 12, 'dep_m': 0, 'arr_h': 6, 'arr_m': 0, 'price': 1200, 'coach_type': 'AC'},
            {'train_number': 'T-104', 'train_name': 'Golden Temple', 'departure_city': 'Mumbai', 'arrival_city': 'Delhi', 'dep_h': 21, 'dep_m': 30, 'arr_h': 18, 'arr_m': 0, 'price': 900, 'coach_type': 'Non-AC'},
            
            {'train_number': 'T-201', 'train_name': 'Shatabdi Exp', 'departure_city': 'Delhi', 'arrival_city': 'Jaipur', 'dep_h': 6, 'dep_m': 5, 'arr_h': 10, 'arr_m': 40, 'price': 800, 'coach_type': 'AC'},
            {'train_number': 'T-202', 'train_name': 'Double Decker', 'departure_city': 'Delhi', 'arrival_city': 'Jaipur', 'dep_h': 17, 'dep_m': 35, 'arr_h': 22, 'arr_m': 10, 'price': 600, 'coach_type': 'AC'},
            
            {'train_number': 'T-301', 'train_name': 'Shatabdi Exp', 'departure_city': 'Bangalore', 'arrival_city': 'Chennai', 'dep_h': 6, 'dep_m': 0, 'arr_h': 11, 'arr_m': 0, 'price': 950, 'coach_type': 'AC'},
            {'train_number': 'T-302', 'train_name': 'Brindavan Exp', 'departure_city': 'Bangalore', 'arrival_city': 'Chennai', 'dep_h': 14, 'dep_m': 30, 'arr_h': 20, 'arr_m': 30, 'price': 450, 'coach_type': 'Non-AC'},
            
            {'train_number': 'T-401', 'train_name': 'Deccan Queen', 'departure_city': 'Mumbai', 'arrival_city': 'Pune', 'dep_h': 17, 'dep_m': 10, 'arr_h': 20, 'arr_m': 25, 'price': 500, 'coach_type': 'AC'},
            {'train_number': 'T-402', 'train_name': 'Intercity', 'departure_city': 'Mumbai', 'arrival_city': 'Pune', 'dep_h': 6, 'dep_m': 40, 'arr_h': 10, 'arr_m': 0, 'price': 350, 'coach_type': 'Non-AC'},
            
            {'train_number': 'T-501', 'train_name': 'Duronto Exp', 'departure_city': 'Delhi', 'arrival_city': 'Kolkata', 'dep_h': 13, 'dep_m': 0, 'arr_h': 6, 'arr_m': 0, 'price': 3200, 'coach_type': 'AC'},
            {'train_number': 'T-601', 'train_name': 'Konkan Kanya', 'departure_city': 'Mumbai', 'arrival_city': 'Goa', 'dep_h': 23, 'dep_m': 0, 'arr_h': 10, 'arr_m': 30, 'price': 1500, 'coach_type': 'Sleeper'},
            {'train_number': 'T-701', 'train_name': 'Netravati', 'departure_city': 'Mumbai', 'arrival_city': 'Kochi', 'dep_h': 11, 'dep_m': 40, 'arr_h': 15, 'arr_m': 0, 'price': 1800, 'coach_type': 'Sleeper'},
            {'train_number': 'T-801', 'train_name': 'Hampi Exp', 'departure_city': 'Bangalore', 'arrival_city': 'Hubli', 'dep_h': 22, 'dep_m': 0, 'arr_h': 7, 'arr_m': 0, 'price': 1100, 'coach_type': 'Sleeper'},
            {'train_number': 'T-901', 'train_name': 'Taj Exp', 'departure_city': 'Delhi', 'arrival_city': 'Agra', 'dep_h': 6, 'dep_m': 45, 'arr_h': 9, 'arr_m': 30, 'price': 450, 'coach_type': 'AC'},
            {'train_number': 'T-910', 'train_name': 'Shatabdi', 'departure_city': 'Delhi', 'arrival_city': 'Mumbai', 'dep_h': 6, 'dep_m': 0, 'arr_h': 14, 'arr_m': 0, 'price': 2400, 'coach_type': 'AC'},
            {'train_number': 'T-911', 'train_name': 'Firozpur Exp', 'departure_city': 'Delhi', 'arrival_city': 'Mumbai', 'dep_h': 21, 'dep_m': 0, 'arr_h': 20, 'arr_m': 0, 'price': 950, 'coach_type': 'Sleeper'},
        ]
        
        for t in trains_data:
            train = Train(
                train_number=t['train_number'], train_name=t['train_name'],
                departure_city=t['departure_city'], arrival_city=t['arrival_city'],
                departure_time=ref_date.replace(hour=t['dep_h'], minute=t['dep_m']),
                arrival_time=ref_date.replace(hour=t['arr_h'], minute=t['arr_m']),
                price=t['price'], coach_type=t['coach_type'],
                total_seats=500, available_seats=500,
                operating_days='Mon,Tue,Wed,Thu,Fri,Sat,Sun',
                schedule_start=today, schedule_end=sched_end, created_by=admin.id
            )
            db.session.add(train)

        # ============================================================
        #  HOTELS (20)
        # ============================================================
        hotels_data = [
            {'name': 'Taj Mansingh', 'city': 'Delhi', 'price': 12000, 'rating': 4.9},
            {'name': 'ITC Maurya', 'city': 'Delhi', 'price': 9500, 'rating': 4.8},
            {'name': 'The Leela Palace', 'city': 'Delhi', 'price': 15000, 'rating': 4.9},
            {'name': 'Ginger Delhi', 'city': 'Delhi', 'price': 3500, 'rating': 4.0},
            
            {'name': 'Taj Mahal Palace', 'city': 'Mumbai', 'price': 18000, 'rating': 5.0},
            {'name': 'Trident Nariman', 'city': 'Mumbai', 'price': 11000, 'rating': 4.7},
            {'name': 'JW Marriott', 'city': 'Mumbai', 'price': 13000, 'rating': 4.8},
            {'name': 'Ibis Mumbai', 'city': 'Mumbai', 'price': 5500, 'rating': 4.2},
            
            {'name': 'Taj Exotica', 'city': 'Goa', 'price': 16000, 'rating': 4.9},
            {'name': 'Zuri White Sands', 'city': 'Goa', 'price': 8500, 'rating': 4.5},
            {'name': 'Lemon Tree Goa', 'city': 'Goa', 'price': 6000, 'rating': 4.3},
            {'name': 'Hostel Goa', 'city': 'Goa', 'price': 800, 'rating': 4.1},
            
            {'name': 'Ritz-Carlton', 'city': 'Bangalore', 'price': 14000, 'rating': 4.9},
            {'name': 'Marriott Whitefield', 'city': 'Bangalore', 'price': 9000, 'rating': 4.6},
            {'name': 'Park Inn', 'city': 'Bangalore', 'price': 5000, 'rating': 4.3},
            
            {'name': 'Rambagh Palace', 'city': 'Jaipur', 'price': 25000, 'rating': 5.0},
            {'name': 'Fairmont Jaipur', 'city': 'Jaipur', 'price': 14000, 'rating': 4.8},
            {'name': 'Royal Heritage', 'city': 'Jaipur', 'price': 4500, 'rating': 4.4},
        ]
        
        for h in hotels_data:
            hotel = Hotel(
                name=h['name'], city=h['city'], address=f"{h['city']} Center",
                description=f"Wonderful stay at {h['name']}",
                price_per_night=h['price'], rating=h['rating'],
                total_rooms=50, available_rooms=50,
                amenities='Wifi, AC, Pool, Restaurant',
                created_by=admin.id
            )
            db.session.add(hotel)

        # ============================================================
        #  VEHICLES (20)
        # ============================================================
        vehicles_data = [
            {'num': 'DL-01', 'type': 'Car', 'city': 'Delhi', 'price': 3500, 'desc': 'Fortuner SUV'},
            {'num': 'DL-02', 'type': 'Car', 'city': 'Delhi', 'price': 2200, 'desc': 'Honda City'},
            {'num': 'DL-03', 'type': 'Car', 'city': 'Delhi', 'price': 1500, 'desc': 'Swift'},
            
            {'num': 'MH-01', 'type': 'Car', 'city': 'Mumbai', 'price': 3000, 'desc': 'Innova'},
            {'num': 'MH-02', 'type': 'Car', 'city': 'Mumbai', 'price': 2500, 'desc': 'Creta'},
            {'num': 'MH-03', 'type': 'Auto', 'city': 'Mumbai', 'price': 800, 'desc': 'Rickshaw'},
            
            {'num': 'GA-01', 'type': 'Bike', 'city': 'Goa', 'price': 1000, 'desc': 'RE Classic'},
            {'num': 'GA-02', 'type': 'Bike', 'city': 'Goa', 'price': 500, 'desc': 'Activa'},
            {'num': 'GA-03', 'type': 'Car', 'city': 'Goa', 'price': 4000, 'desc': 'Thar 4x4'},
            
            {'num': 'KA-01', 'type': 'Car', 'city': 'Bangalore', 'price': 2800, 'desc': 'Seltos'},
            {'num': 'KA-02', 'type': 'Car', 'city': 'Bangalore', 'price': 2400, 'desc': 'Nexon EV'},
            
            {'num': 'RJ-01', 'type': 'Car', 'city': 'Jaipur', 'price': 5000, 'desc': 'Vintage Jeep'},
            {'num': 'RJ-02', 'type': 'Car', 'city': 'Jaipur', 'price': 1800, 'desc': 'Etios'},
        ]
        
        for v in vehicles_data:
            vehicle = Vehicle(
                vehicle_number=v['num'], vehicle_type=v['type'], city=v['city'],
                description=v['desc'], price_per_day=v['price'],
                capacity=5, total_units=10, available_units=10,
                created_by=admin.id
            )
            db.session.add(vehicle)
        
        db.session.commit()
        print("Database fully reset and seeded with Everyday Dynamic Schedules!")
