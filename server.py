import http.server
import socketserver
import json
import google.generativeai as genai
import os
import psycopg2
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# Configure Gemini
# Using the first key from user memory
API_KEY = "AIzaSyCxbLW9-ZqIHa6DpZKGx3aNA3IcoW78Znw"
genai.configure(api_key=API_KEY)

generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "application/json",
}

model = genai.GenerativeModel(
  model_name="gemini-2.0-flash",
  generation_config=generation_config,
)

PORT = 8001

# Database Configuration
DB_NAME = "postgres"
DB_PASS = ""
DB_HOST = "localhost"
DB_PORT = "5432"

def get_db_connection():
    try:
        return psycopg2.connect(dbname=DB_NAME, user="postgres", password=DB_PASS, host=DB_HOST, port=DB_PORT)
    except:
        try:
            return psycopg2.connect(dbname=DB_NAME, user=os.environ.get('USER'), password=DB_PASS, host=DB_HOST, port=DB_PORT)
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return None

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        if parsed_path.path == '/api/menu':
            kitchen_id = query_params.get('kitchenId', [None])[0]
            if not kitchen_id:
                self.send_error(400, "Missing kitchenId")
                return
            
            conn = get_db_connection()
            if not conn:
                self.send_error(500, "Database connection failed")
                return
            
            try:
                cur = conn.cursor()
                cur.execute("SELECT id, name, price, description, img FROM menu_items WHERE kitchen_id = %s", (kitchen_id,))
                rows = cur.fetchall()
                menu = []
                for row in rows:
                    menu.append({
                        "id": row[0],
                        "owner": kitchen_id,
                        "name": row[1],
                        "price": row[2],
                        "description": row[3],
                        "img": row[4]
                    })
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(menu).encode('utf-8'))
            except Exception as e:
                print(f"DB Error: {e}")
                self.send_error(500, str(e))
            finally:
                cur.close()
                conn.close()
            return

        elif parsed_path.path == '/api/orders':
            kitchen_id = query_params.get('kitchenId', [None])[0]
            if not kitchen_id:
                self.send_error(400, "Missing kitchenId")
                return

            conn = get_db_connection()
            if not conn:
                self.send_error(500, "Database connection failed")
                return

            try:
                cur = conn.cursor()
                cur.execute("SELECT id, items_summary, total, status, created_at, customer_json FROM orders WHERE kitchen_id = %s ORDER BY created_at DESC", (kitchen_id,))
                rows = cur.fetchall()
                orders = []
                for row in rows:
                    customer = row[5] if row[5] else {}
                    # Ensure customer is dict
                    if isinstance(customer, str):
                        try:
                            customer = json.loads(customer)
                        except:
                            pass

                    orders.append({
                        "id": row[0],
                        "owner": kitchen_id,
                        "items": row[1],
                        "total": row[2],
                        "status": row[3],
                        "time": row[4].strftime("%I:%M %p") if row[4] else "",
                        "customer": customer
                    })
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(orders).encode('utf-8'))
            except Exception as e:
                print(f"DB Error: {e}")
                self.send_error(500, str(e))
            finally:
                cur.close()
                conn.close()
            return

        # Serve static files (default behavior)
        super().do_GET()

    def do_POST(self):
        if self.path == '/api/generate':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            dish_name = data.get('dish_name')

            if not dish_name:
                self.send_response(400)
                self.end_headers()
                return

            try:
                prompt = f"""
                Generate a short, appetizing description (max 20 words) and a single, specific keyword for an image search for the food item: "{dish_name}".
                The image keyword should be specific enough to get a good result from a general image search (e.g. "paneer butter masala", "chocolate cake slice").
                Return JSON with keys: "description" and "image_keyword".
                """
                
                response = model.generate_content(prompt)
                result = json.loads(response.text)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode('utf-8'))
            except Exception as e:
                print(f"Error: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

        elif self.path == '/api/menu':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            kitchen_id = data.get('kitchenId')
            menu_items = data.get('menu')

            if not kitchen_id or menu_items is None:
                self.send_error(400, "Missing kitchenId or menu")
                return

            conn = get_db_connection()
            if not conn:
                self.send_error(500, "Database connection failed")
                return

            try:
                cur = conn.cursor()
                # Full replace strategy for simplicity as per original logic
                cur.execute("DELETE FROM menu_items WHERE kitchen_id = %s", (kitchen_id,))
                
                for item in menu_items:
                    cur.execute("""
                        INSERT INTO menu_items (kitchen_id, name, price, description, img)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (kitchen_id, item['name'], item['price'], item['description'], item['img']))
                
                conn.commit()

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
                print(f"DB Error: {e}")
                conn.rollback()
                self.send_error(500, str(e))
            finally:
                cur.close()
                conn.close()
            return

        elif self.path == '/api/orders':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            order_data = json.loads(post_data.decode('utf-8'))
            
            # Basic validation
            if not order_data.get('owner') or not order_data.get('items'):
                self.send_error(400, "Invalid order data")
                return

            conn = get_db_connection()
            if not conn:
                self.send_error(500, "Database connection failed")
                return

            try:
                cur = conn.cursor()
                customer_json = json.dumps(order_data.get('customer', {}))
                
                cur.execute("""
                    INSERT INTO orders (id, kitchen_id, items_summary, total, status, customer_json)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (order_data['id'], order_data['owner'], order_data['items'], order_data['total'], order_data['status'], customer_json))
                
                conn.commit()

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "orderId": order_data.get('id')}).encode('utf-8'))
            except Exception as e:
                print(f"DB Error: {e}")
                conn.rollback()
                self.send_error(500, str(e))
            finally:
                cur.close()
                conn.close()
            return

        elif self.path == '/api/whatsapp-webhook':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))
            
            message = payload.get('message')
            is_group = payload.get('isGroup')
            sender = payload.get('sender')
            kitchen_id = payload.get('kitchenId', 'kitchen1')

            if is_group:
                response_text = "We messaged you personally! Check your DM."
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"response": response_text}).encode('utf-8'))
                return

            conn = get_db_connection()
            if not conn:
                self.send_error(500, "Database connection failed")
                return

            try:
                cur = conn.cursor()
                # Fetch menu for NLP
                cur.execute("SELECT id, name, price FROM menu_items WHERE kitchen_id = %s", (kitchen_id,))
                menu_rows = cur.fetchall()
                menu_simple = [{ 'id': row[0], 'name': row[1], 'price': row[2] } for row in menu_rows]
                
                # NLP Logic
                prompt = f"""
                You are an order parser for a kitchen.
                Menu: {json.dumps(menu_simple)}
                User Message: "{message}"
                
                Extract items and quantities. Return a valid JSON object (no markdown) with:
                - "items": list of {{ "id": item_id, "qty": quantity, "name": item_name, "price": item_price }}
                - "total": total cost (number)
                - "clarification_needed": boolean (true if message is unclear or items not in menu)
                
                If unclear, set "items": [] and "clarification_needed": true.
                """

                try:
                    response = model.generate_content(prompt)
                    text = response.text.replace('```json', '').replace('```', '').strip()
                    nlp_result = json.loads(text)
                    
                    if nlp_result.get('clarification_needed'):
                         app_url = f"http://{self.headers.get('Host')}/customer.html?kitchenId={kitchen_id}"
                         response_text = f"Sorry, I didn't catch that. Please check our menu here: {app_url}"
                    else:
                        # Create Order
                        items_summary = ", ".join([f"{i['qty']}x {i['name']}" for i in nlp_result['items']])
                        order_id = f"WA-{int(datetime.now().timestamp())}"
                        total = nlp_result['total']
                        customer_json = json.dumps({ "name": "WhatsApp User", "phone": sender, "source": "WhatsApp" })
                        
                        cur.execute("""
                            INSERT INTO orders (id, kitchen_id, items_summary, total, status, customer_json)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (order_id, kitchen_id, items_summary, total, "New", customer_json))
                        
                        conn.commit()
                        response_text = f"✅ Order placed! {items_summary}. Total: ₹{total}"

                except Exception as e:
                    print(f"NLP Error: {e}")
                    # Fallback: Simple Regex
                    import re
                    items_found = []
                    total = 0
                    
                    for m in menu_simple:
                        pattern = r"(\d+)?\s*" + re.escape(m['name'].lower())
                        matches = re.findall(pattern, message.lower())
                        for qty_str in matches:
                            qty = int(qty_str) if qty_str else 1
                            items_found.append({ "id": m['id'], "qty": qty, "name": m['name'], "price": m['price'] })
                            total += qty * int(m['price'])
                    
                    if items_found:
                        items_summary = ", ".join([f"{i['qty']}x {i['name']}" for i in items_found])
                        order_id = f"WA-{int(datetime.now().timestamp())}"
                        customer_json = json.dumps({ "name": "WhatsApp User", "phone": sender, "source": "WhatsApp" })

                        cur.execute("""
                            INSERT INTO orders (id, kitchen_id, items_summary, total, status, customer_json)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (order_id, kitchen_id, items_summary, total, "New", customer_json))
                        
                        conn.commit()
                        response_text = f"✅ Order placed (Fallback)! {items_summary}. Total: ₹{total}"
                    else:
                        response_text = "Sorry, I'm having trouble understanding. Please use the menu link."

            except Exception as e:
                print(f"Webhook DB Error: {e}")
                conn.rollback()
                response_text = "System Error"
            finally:
                cur.close()
                conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"response": response_text}).encode('utf-8'))
            return

        else:
            self.send_error(404)

print(f"Serving on port {PORT}")
with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
    httpd.serve_forever()
