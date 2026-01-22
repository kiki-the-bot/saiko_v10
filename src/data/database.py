import sqlite3
import os
# We import the initializer to ensure DB exists before we query it
from src.data.db_init import init_db, DB_NAME

class OmniCorpDB:
    # 1. AUTO-INIT: Run the creator script once when this class loads
    init_db()

    @staticmethod
    def get_order(order_id):
        try:
            # Connect to the file
            # check_same_thread=False is needed because FastAPI is multi-threaded
            with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
                
                # 'row_factory' makes the results look like Dictionaries (easier for Python)
                conn.row_factory = sqlite3.Row 
                cursor = conn.cursor()
                
                # 2. THE QUERY
                # "SELECT all columns FROM orders table WHERE the ID matches..."
                # The '?' is a security feature (prevents SQL Injection)
                cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
                
                row = cursor.fetchone() # Fetch one result
                
                if row:
                    # Convert to normal Python Dict
                    return dict(row) 
                else:
                    return None
                    
        except Exception as e:
            print(f"❌ SQL ERROR: {e}")
            return None