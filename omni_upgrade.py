import sqlite3
import os

# Locate DB
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "omnicorp.db") # Adjust path if needed

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # 1. Add column (ignore error if exists)
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN phone_last4 TEXT")
    except:
        pass # Already exists

    # 2. Update your Neural Link orders with a known PIN (e.g., "8888")
    # This acts as the "Secret Key" for the demo
    cursor.execute("UPDATE orders SET phone_last4 = '8888'")
    
    conn.commit()
    print("✅ Database Patched: All orders now require Phone ending in '8888'")
    
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    conn.close()