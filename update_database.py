"""
Test script to manually set delivery dates on existing orders
Run this to test if the display is working
"""

import sqlite3
from datetime import datetime, timedelta

def test_delivery_dates():
    print("=" * 60)
    print("Testing Delivery Date Feature")
    print("=" * 60)
    
    conn = sqlite3.connect('cellar_society.db')
    c = conn.cursor()
    
    # Get all orders
    c.execute("SELECT id, status FROM orders")
    orders = c.fetchall()
    
    if not orders:
        print("❌ No orders found. Please create an order first.")
        conn.close()
        return
    
    print(f"\nFound {len(orders)} order(s)")
    print("\nUpdating orders with status 'Processing' or 'Delivered'...\n")
    
    shipped_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    delivery_date = (datetime.now() + timedelta(days=4)).strftime('%Y-%m-%d')
    
    updated_count = 0
    
    for order_id, status in orders:
        if status in ['Processing', 'Delivered']:
            c.execute('''
                UPDATE orders 
                SET shipped_date = ?, estimated_delivery_date = ?
                WHERE id = ?
            ''', (shipped_date, delivery_date, order_id))
            print(f"✅ Updated Order #{order_id} (Status: {status})")
            print(f"   Shipped: {shipped_date}")
            print(f"   Delivery: {delivery_date}")
            updated_count += 1
    
    if updated_count == 0:
        print("No orders with 'Processing' or 'Delivered' status found.")
        print("Updating first order as test...")
        if orders:
            order_id = orders[0][0]
            c.execute('''
                UPDATE orders 
                SET status = 'Processing',
                    shipped_date = ?, 
                    estimated_delivery_date = ?
                WHERE id = ?
            ''', (shipped_date, delivery_date, order_id))
            print(f"✅ Updated Order #{order_id} to Processing with delivery date")
            updated_count = 1
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Updated {updated_count} order(s)")
    print("=" * 60)
    print("Now check 'My Orders' page in the customer portal!")
    print("=" * 60)

if __name__ == '__main__':
    test_delivery_dates()