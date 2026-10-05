# Travel Booking System - Flask Web Application

A comprehensive Flask-based travel booking system that allows customers to plan and book complete trips including flights, trains, hotels, and vehicles. Includes admin panel for managing bookings and services.

## Features

### Customer Features
- ✈️ **Flight Booking** - Search and book flights to various destinations
- 🚂 **Train Booking** - Reserve train tickets with different coach types
- 🏨 **Hotel Booking** - Reserve accommodations with detailed amenities
- 🚗 **Vehicle Rental** - Rent vehicles for local transportation
- 💳 **Integrated Payment** - QR code-based payment system
- 📸 **Document Upload** - Upload payment proof and trip details
- 📋 **Booking History** - View and manage all bookings
- 📊 **Records & Invoice** - Download booking invoices

### Admin Features
- 📊 **Dashboard** - Real-time statistics and metrics
- ✅ **Booking Management** - Review and confirm customer bookings
- ✈️ **Flight Management** - Add, edit, and manage flights
- 🚂 **Train Management** - Add and manage train services
- 🏨 **Hotel Management** - Add and manage hotel accommodations
- 🚗 **Vehicle Management** - Add and manage rental vehicles
- 👥 **User Management** - Manage customer accounts
- 📁 **Records** - View comprehensive booking and payment records

## Technology Stack

- **Backend**: Flask 2.3.2
- **Database**: SQLite
- **ORM**: SQLAlchemy
- **Authentication**: Flask-Login
- **Forms**: WTForms
- **Payment QR**: qrcode library
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **Image Processing**: Pillow

## Installation

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Setup Steps

1. **Clone or extract the project**
```bash
cd Voya
```

2. **Create virtual environment (optional but recommended)**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
python run.py
```

The application will start on `http://localhost:5000`

## Default Credentials

### Admin Account
- **Username**: `admin`
- **Password**: `admin123`
- **Role**: Admin
- **Email**: admin@travelbooking.com

### Demo Customer Account
- **Username**: `customer1`
- **Password**: `customer123`
- **Role**: Customer
- **Email**: customer@travelbooking.com

## Database

The application uses **SQLite** with automatic initialization. Default sample data is included:

### Pre-populated Data
- 6 Flights (connecting major cities: Delhi, Mumbai, Bangalore, Goa)
- 4 Trains (with different coach types)
- 6 Hotels (across different cities with amenities)
- 6 Vehicles (cars, bikes, buses)

## Project Structure

```
Voya/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── models.py                # Database models
│   ├── database.py              # Database initialization
│   ├── routes/
│   │   ├── auth.py              # Authentication routes
│   │   ├── customer.py          # Customer dashboard & search
│   │   ├── booking.py           # Booking & payment routes
│   │   └── admin.py             # Admin panel routes
│   ├── static/
│   │   ├── css/                 # Stylesheets
│   │   ├── js/                  # JavaScript files
│   │   └── uploads/             # Document uploads & QR codes
│   └── templates/
│       ├── base.html            # Base template
│       ├── auth/                # Login/Register templates
│       ├── customer/            # Customer templates
│       ├── booking/             # Booking templates
│       └── admin/               # Admin templates
├── config.py                    # Configuration settings
├── run.py                       # Application entry point
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Key Features Explained

### 1. Integrated Itinerary Booking
Users can book flights to a destination, and the system automatically shows:
- Available hotels in that city
- Vehicle rental options for local transport
- All bookable from one place

### 2. Date Validation
- Users can only book from the current date onwards
- Past date bookings are blocked
- Automatic availability check

### 3. Payment System
- **QR Code Generation**: Unique QR code for each booking
- **Payment Upload**: Customers upload payment screenshots
- **Document Verification**: Admin reviews before confirmation
- **Transaction Tracking**: Transaction IDs for each payment

### 4. Dual Dashboard
- **Customer Dashboard**: Shows bookings, statistics, and quick actions
- **Admin Dashboard**: Shows system metrics, pending reviews, and management tools

### 5. Complete Booking Lifecycle
```
Search → Select → Provide Details → Proceed to Payment → 
Upload Proof → Admin Review → Confirmation → Download Invoice
```

## Usage Guide

### For Customers

1. **Register** - Create a new account
2. **Login** - Access your dashboard
3. **Search** - Find flights, trains, hotels, or vehicles
4. **Book** - Select services and book
5. **Pay** - Scan QR code and upload payment proof
6. **Confirm** - Wait for admin approval
7. **View** - Check booking history and download invoices

### For Admin

1. **Login** - Use admin credentials
2. **Dashboard** - View system statistics
3. **Manage Services** - Add/edit flights, trains, hotels, vehicles
4. **Review Bookings** - Confirm or reject pending bookings
5. **Manage Users** - View and manage customer accounts
6. **View Records** - Access complete booking and payment history

## API Endpoints

### Authentication
- `POST /auth/register` - Register new customer
- `POST /auth/login` - Customer login
- `GET /auth/logout` - Logout

### Customer
- `GET /customer/dashboard` - Customer dashboard
- `GET /customer/search-page` - Search page
- `GET /customer/search` - Search results
- `GET /customer/my-records` - All bookings
- `GET /customer/view-booking/<id>` - Booking details

### Booking
- `POST /booking/flight/<id>` - Book flight
- `POST /booking/train/<id>` - Book train
- `POST /booking/hotel/<id>` - Book hotel
- `POST /booking/vehicle/<id>` - Book vehicle
- `GET/POST /booking/payment/<id>` - Payment page

### Admin
- `GET /admin/dashboard` - Admin dashboard
- `GET /admin/bookings` - Manage bookings
- `POST /admin/booking/<id>/confirm` - Confirm booking
- `POST /admin/booking/<id>/reject` - Reject booking
- `GET /admin/flights` - Manage flights
- `POST /admin/flight/add` - Add flight

## Database Models

### User
- `username`, `email`, `password_hash`
- `first_name`, `last_name`, `phone`
- `role` (customer/admin), `is_active`

### Booking
- Links customer with flights, trains, hotels, vehicles
- `booking_status` (pending/confirmed/cancelled)
- `total_cost`, `booking_type`
- Stores dates, quantities, and admin notes

### Payment
- `amount`, `payment_status`
- `qr_code_path`, `qr_code_data`
- `payment_screenshot`, `transaction_id`

### Flight, Train, Hotel, Vehicle
- Availability tracking
- Pricing information
- Location/route details
- Capacity/resource management

## Security Features

- Password hashing with Werkzeug
- User authentication with Flask-Login
- Admin-only route protection
- CSRF protection on forms
- Input validation
- Secure file uploads

## Future Enhancements

- Email notifications for bookings
- SMS alerts
- Payment gateway integration (Razorpay, Stripe)
- Rating and reviews system
- Cancellation policy and refunds
- Multi-language support
- Mobile app
- Real-time seat availability
- Advanced analytics

## Troubleshooting

### Database Issues
- Delete `travel_booking.db` to reset database
- Database will be recreated with default data on next run

### Port Already in Use
- Change port in `run.py`: `app.run(port=5001)`

### Missing Dependencies
```bash
pip install -r requirements.txt --upgrade
```

### Upload Issues
- Ensure `app/static/uploads/` folder has write permissions
- Check file format (only PNG, JPG, PDF allowed)

## License

This project is provided for educational purposes.

## Support

For issues or questions, please review:
1. Database models in `app/models.py`
2. Routes in `app/routes/`
3. Configuration in `config.py`

## Version History

- **v1.0.0** - Initial release with full features

---

**Built with ❤️ using Flask | Travel Booking System 2024**
