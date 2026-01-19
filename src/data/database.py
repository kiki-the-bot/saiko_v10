# mock_data.py
import random
import datetime

class OmniCorpDB:
#fake database to prevent leaking real company PII during the demo.
    
    
    @staticmethod
    def get_order(order_id):
        # Deterministic "Randomness" based on the ID so it feels real
        # If ID e0nds in even number -> In Transit. Odd -> Delivered.
        
        digits = [int(s) for s in order_id if s.isdigit()]
        if not digits: return None
        
        last_digit = digits[-1]
        
        # FAKE INVENTORY ITEMS
        items = [
            "Industrial Titan-X Generator", 
            "Quantum-Core Processor Unit", 
            "Heavy-Duty Hydraulic Pump",
            "Neural-Link Interface Cable"
        ]
        
        item = items[last_digit % len(items)]
        
        if last_digit % 2 == 0:
            status = "IN_TRANSIT"
            loc = "Distribution Center: Mexico City North"
            eta = (datetime.datetime.now() + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
        else:
            status = "DELIVERED"
            loc = "Front Desk / Reception"
            eta = "N/A"
            
        return {
            "order_id": order_id,
            "item": item,
            "status": status,
            "location": loc,
            "estimated_delivery": eta,
            "customer_name": "J. Doe"
        }
