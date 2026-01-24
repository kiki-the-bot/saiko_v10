import sqlite3
import os

# 1. Where is THIS file? (src/data/database.py)
CURRENT_FILE = os.path.abspath(__file__)
    
    # 2. What folder is it in? (src/data)
DATA_DIR = os.path.dirname(CURRENT_FILE)
    
    # 3. Go up to 'src'
SRC_DIR = os.path.dirname(DATA_DIR)
    
    # 4. Go up to 'saiko_v10' (ROOT)
ROOT_DIR = os.path.dirname(SRC_DIR)
    
    # 5. Build the final path
DB_PATH = os.path.join(ROOT_DIR, "omnicorp.db")

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
                cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
                
                row = cursor.fetchone() # Fetch one result
                
                # DELETE THIS LINE: print(session.context.order_id) <-- CRASH CAUSED HERE
                print(f"DEBUG CHECK: Looking up ID {order_id}") # <-- Use the argument instead
                
                if row:
                    # Convert to normal Python Dict
                    return dict(row) 
                else:
                    return None
                    
        except Exception as e:
            print(f"❌ SQL ERROR: {e}")
            return None
        
    @staticmethod
    def cancel_order(order_id: str) -> dict:
        """
        Simulates a POST /orders/{id}/cancel API call.
        Returns: {'success': bool, 'msg': str, 'new_status': str}
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # 1. GET CURRENT STATUS (The "Pre-Flight" Check)
            cursor.execute("SELECT status, item_name FROM orders WHERE order_id = ?", (order_id,))
            row = cursor.fetchone()
            
            if not row:
                return {
                    "success": False, 
                    "msg": "Order ID not found in system.", 
                    "new_status": "UNKNOWN"
                }
                
            current_status, item_name = row
            
            # 2. BUSINESS RULES (The "Guardrails")
            # You can't cancel something that is already on a truck.
            non_cancellable = ["SHIPPED", "DELIVERED", "CANCELLED", "IN_TRANSIT"]
            
            if current_status in non_cancellable:
                return {
                    "success": False, 
                    "msg": f"Cancellation rejected. Item '{item_name}' is currently {current_status}.", 
                    "new_status": current_status
                }
            
            # 3. EXECUTE UPDATE (The "Write")
            cursor.execute("UPDATE orders SET status = 'CANCELLED' WHERE order_id = ?", (order_id,))
            conn.commit()
            
            return {
                "success": True, 
                "msg": f"Success. Order for '{item_name}' has been cancelled.", 
                "new_status": "CANCELLED"
            }
            
        except Exception as e:
            return {"success": False, "msg": f"Database Error: {e}", "new_status": "ERROR"}
            
        finally:
            conn.close()
    
    @staticmethod
    def verify_pin(order_id: str, input_digits: str) -> bool:

        conn = sqlite3.connect (DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT phone_last4 FROM orders WHERE order_id = ?", (order_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row[0]:
            return False 
            
        return input_digits.strip() == row[0].strip()