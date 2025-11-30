"""
================================================================================
MESSAGING SYSTEM - Database Setup
================================================================================
Add this to your existing database initialization
Run this script ONCE to add the messages table
================================================================================
"""

import sqlite3
from datetime import datetime

def add_messaging_system():
    """Add messages table to existing database"""
    conn = sqlite3.connect('cellar_society.db')
    c = conn.cursor()
    
    try:
        # Create messages table
        c.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            sender_type TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )''')
        
        print("✅ Messages table created successfully!")
        
        # Add index for faster queries
        c.execute('''CREATE INDEX IF NOT EXISTS idx_messages_customer 
                     ON messages(customer_id, created_at DESC)''')
        
        print("✅ Added index for messages")
        
        conn.commit()
        print("\n✅ Messaging system setup complete!")
        print("\nTable structure:")
        print("- id: Message ID")
        print("- customer_id: Which customer this conversation belongs to")
        print("- sender_type: 'customer' or 'admin'")
        print("- message: Message text")
        print("- is_read: 0 (unread) or 1 (read)")
        print("- created_at: Timestamp")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    add_messaging_system()