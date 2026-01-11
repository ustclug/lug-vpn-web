from app import app, db
from app.models import User, WireGuardPeer

def init_db():
    with app.app_context():
        print("Creating all database tables...")
        db.create_all()
        print("Database initialized.")

        # Optional: Add admin user if not exists
        if not User.query.filter_by(email="ustcaf@yfgao.com").first():
            print("Creating default admin user...")
            u = User(email="ustcaf@yfgao.com", password="tNz-bTL-cgp-K4T")
            u.status = 'pass'
            u.admin = True
            u.active = True
            db.session.add(u)
            db.session.commit()
            print("Admin user created.")

if __name__ == "__main__":
    init_db()
