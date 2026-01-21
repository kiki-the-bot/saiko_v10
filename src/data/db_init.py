import sqlite3
import random
from datetime import datetime, timedelta

# This creates a file named 'omnicorp.db' in your project root
DB_NAME = "omnicorp.db"

def init_db():
    """
    Checks for the DB. If missing, creates tables and seeds 10k rows.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. SQL COMMAND: Create the structure
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_name TEXT,
            item_name TEXT,
            status TEXT,
            location TEXT,
            eta TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. SQL COMMAND: Count existing rows
    cursor.execute('SELECT count(*) FROM orders')
    row = cursor.fetchone()
    count = row[0] if row else 0
    
    if count == 0:
        print("⚡ [SQL] DATABASE EMPTY. SEEDING 10,000 RECORDS...")
        _seed_data(conn)
    else:
        print(f"✅ [SQL] DATABASE READY ({count} Records Loaded).")
    
    conn.commit()
    conn.close()

def _seed_data(conn):
    cursor = conn.cursor()
    items = [
        "Industrial Titan-X Generator", "Quantum-Core Processor", 
        "Hydraulic Pump MK-IV", "Neural-Link Interface",
        "Bio-Synthetic Filter", "Plasma Containment Unit"
    ]
    statuses = ["IN_TRANSIT", "DELIVERED", "PENDING", "LOST"]
    locations = ["Mexico City Hub", "Guadalajara North", "Monterrey Depot", "Front Desk"]
    
    data = []
    
    # Generate 10,000 simulations
    for i in range(10000):
        # Random ID
        oid = f"AB-{random.randint(10000000, 99999999)}"
        
        # FORCE A KNOWN ID FOR DEMOS (So you don't look stupid live)
        if i == 0: oid = "WH-12345678"
            
        item = random.choice(items)
        status = random.choice(statuses)
        loc = random.choice(locations)
        
        # Date Logic
        if status == "DELIVERED":
            eta = "N/A"
        else:
            future = datetime.now() + timedelta(days=random.randint(1, 5))
            eta = future.strftime("%Y-%m-%d")
            
        data.append((oid, f"Customer_{i}", item, status, loc, eta))
        
    # Bulk Insert (The Flex)
    cursor.executemany('INSERT OR IGNORE INTO orders VALUES (?, ?, ?, ?, ?, ?, NULL)', data)
    print("✅ SEEDING COMPLETE.")

if __name__ == "__main__":
    init_db()