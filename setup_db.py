import psycopg2
import json
import os
from datetime import datetime

# Database Configuration
DB_NAME = "postgres"
DB_USER = "kavitasingh" # Default user on mac usually matches system user or is 'postgres'
DB_PASS = ""
DB_HOST = "localhost"
DB_PORT = "5432"

# Try connecting to default 'postgres' user first, if fails try system user
def get_connection():
    try:
        return psycopg2.connect(dbname=DB_NAME, user="postgres", password=DB_PASS, host=DB_HOST, port=DB_PORT)
    except:
        try:
            return psycopg2.connect(dbname=DB_NAME, user=os.environ.get('USER'), password=DB_PASS, host=DB_HOST, port=DB_PORT)
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return None

def setup_database():
    conn = get_connection()
    if not conn:
        print("Could not connect to PostgreSQL. Please ensure it is running.")
        return

    cur = conn.cursor()

    print("Dropping existing tables...")
    cur.execute("DROP TABLE IF EXISTS orders;")
    cur.execute("DROP TABLE IF EXISTS menu_items;")
    cur.execute("DROP TABLE IF EXISTS kitchens;")

    print("Creating tables...")
    # Kitchens Table
    cur.execute("""
        CREATE TABLE kitchens (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(100) NOT NULL
        );
    """)

    # Menu Items Table
    cur.execute("""
        CREATE TABLE menu_items (
            id SERIAL PRIMARY KEY,
            kitchen_id VARCHAR(50) REFERENCES kitchens(id),
            name VARCHAR(255) NOT NULL,
            price INTEGER NOT NULL,
            description TEXT,
            img TEXT
        );
    """)

    # Orders Table
    cur.execute("""
        CREATE TABLE orders (
            id VARCHAR(50) PRIMARY KEY,
            kitchen_id VARCHAR(50) REFERENCES kitchens(id),
            items_summary TEXT NOT NULL,
            total INTEGER NOT NULL,
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            customer_json JSONB
        );
    """)

    conn.commit()
    print("Tables created successfully.")

    # Seed Data from db.json
    if os.path.exists('db.json'):
        print("Seeding data from db.json...")
        with open('db.json', 'r') as f:
            data = json.load(f)

        # Seed Kitchens (Infer from data or hardcode for now since db.json structure is simple)
        # We know we have 'kitchen1'
        cur.execute("INSERT INTO kitchens (id, name) VALUES (%s, %s)", ('kitchen1', 'Annapurna Kitchen'))

        # Seed Menu
        menus = data.get('menus', {}).get('kitchen1', [])
        for item in menus:
            cur.execute("""
                INSERT INTO menu_items (kitchen_id, name, price, description, img)
                VALUES (%s, %s, %s, %s, %s)
            """, ('kitchen1', item['name'], item['price'], item['description'], item['img']))

        # Seed Orders
        orders = data.get('orders', [])
        for order in orders:
            # Handle time format if needed, but for now we just store it in customer_json or ignore exact timestamp match for old orders
            # The schema has created_at, we can leave it as NOW() for migrated orders or try to parse
            
            customer_data = json.dumps(order.get('customer', {}))
            
            cur.execute("""
                INSERT INTO orders (id, kitchen_id, items_summary, total, status, customer_json)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (order['id'], order['owner'], order['items'], order['total'], order['status'], customer_data))

        conn.commit()
        print("Data seeded successfully.")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    setup_database()
