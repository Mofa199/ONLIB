#!/usr/bin/env python3
import os
import sys
from app import create_app

app = create_app()

def setup_database():
    """Initialize database tables and create default data"""
    with app.app_context():
        from app.models.models import db, User
        
        # Create all database tables
        db.create_all()
        
        # Create default admin user if not exists
        admin = User.query.filter_by(email='admin@medicore.com').first()
        if not admin:
            admin = User(
                name='Admin User',
                email='admin@medicore.com',
                is_admin=True,
                track='Medical'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin user created (admin@medicore.com / admin123)")
        else:
            print("✅ Admin user already exists")
        
        print("✅ Database setup completed successfully!")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        setup_database()
    else:
        # Set up database on first run
        try:
            with app.app_context():
                from app.models.models import db
                db.create_all()
                print("✅ Database initialized")
        except Exception as e:
            print(f"⚠️  Database initialization warning: {e}")
        
        # Run the Flask development server
        port = int(os.environ.get('PORT', 5000))
        print(f"🚀 Starting MediCore Library on http://localhost:{port}")
        print("📝 Access the login page to get started")
        app.run(debug=True, host='0.0.0.0', port=port)
