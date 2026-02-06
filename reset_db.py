import os
from app import db, app

with app.app_context():
    # Delete database file
    if os.path.exists('shop.db'):
        os.remove('shop.db')
        print("✅ Database deleted")
    
    # Recreate database
    db.create_all()
    print("✅ New database created")