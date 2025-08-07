from app import create_app
from app.models.models import db, User

def setup_database():
    """Initialize database tables and create default data"""
    app = create_app()
    
    with app.app_context():
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
    setup_database()
