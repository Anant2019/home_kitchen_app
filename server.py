import http.server
import socketserver
import json
import google.generativeai as genai
import os
from urllib.parse import urlparse, parse_qs

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
DB_FILE = 'db.json'

def load_db():
    if not os.path.exists(DB_FILE):
        return {"menus": {}, "orders": []}
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"menus": {}, "orders": []}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        if parsed_path.path == '/api/menu':
            kitchen_id = query_params.get('kitchenId', [None])[0]
            if not kitchen_id:
                self.send_error(400, "Missing kitchenId")
                return
            
            db = load_db()
            menu = db["menus"].get(kitchen_id, [])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(menu).encode('utf-8'))
            return

        elif parsed_path.path == '/api/orders':
            kitchen_id = query_params.get('kitchenId', [None])[0]
            if not kitchen_id:
                self.send_error(400, "Missing kitchenId")
                return

            db = load_db()
            # Filter orders for this kitchen
            kitchen_orders = [o for o in db["orders"] if o.get('owner') == kitchen_id]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(kitchen_orders).encode('utf-8'))
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

            db = load_db()
            db["menus"][kitchen_id] = menu_items
            save_db(db)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            return

        elif self.path == '/api/orders':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            order_data = json.loads(post_data.decode('utf-8'))
            
            # Basic validation
            if not order_data.get('owner') or not order_data.get('items'):
                self.send_error(400, "Invalid order data")
                return

            db = load_db()
            db["orders"].append(order_data)
            save_db(db)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "orderId": order_data.get('id')}).encode('utf-8'))
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

            # NLP Logic
            db = load_db()
            menu = db["menus"].get(kitchen_id, [])
            # Simplify menu for prompt
            menu_simple = [{ 'id': m['id'], 'name': m['name'], 'price': m['price'] } for m in menu]
            
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
                # Clean response text in case of markdown code blocks
                text = response.text.replace('```json', '').replace('```', '').strip()
                nlp_result = json.loads(text)
                
                if nlp_result.get('clarification_needed'):
                     app_url = f"http://{self.headers.get('Host')}/customer.html?kitchenId={kitchen_id}"
                     response_text = f"Sorry, I didn't catch that. Please check our menu here: {app_url}"
                else:
                    # Create Order
                    from datetime import datetime
                    items_summary = ", ".join([f"{i['qty']}x {i['name']}" for i in nlp_result['items']])
                    new_order = {
                        "id": f"WA-{int(datetime.now().timestamp())}",
                        "owner": kitchen_id,
                        "items": items_summary,
                        "total": nlp_result['total'],
                        "status": "New",
                        "time": datetime.now().strftime("%I:%M %p"),
                        "customer": { "name": "WhatsApp User", "phone": sender, "source": "WhatsApp" }
                    }
                    
                    db["orders"].append(new_order)
                    save_db(db)
                    
                    response_text = f"✅ Order placed! {items_summary}. Total: ₹{nlp_result['total']}"

            except Exception as e:
                print(f"NLP Error: {e}")
                # Fallback: Simple Regex
                import re
                items_found = []
                total = 0
                
                # Try to find numbers followed by menu item names (simplified)
                for m in menu:
                    # Regex to find "2 burger" or "2 burgers" or just "burger" (assume 1)
                    # This is very basic
                    pattern = r"(\d+)?\s*" + re.escape(m['name'].lower())
                    matches = re.findall(pattern, message.lower())
                    for qty_str in matches:
                        qty = int(qty_str) if qty_str else 1
                        items_found.append({ "id": m['id'], "qty": qty, "name": m['name'], "price": m['price'] })
                        total += qty * int(m['price'])
                
                if items_found:
                    from datetime import datetime
                    items_summary = ", ".join([f"{i['qty']}x {i['name']}" for i in items_found])
                    new_order = {
                        "id": f"WA-{int(datetime.now().timestamp())}",
                        "owner": kitchen_id,
                        "items": items_summary,
                        "total": total,
                        "status": "New",
                        "time": datetime.now().strftime("%I:%M %p"),
                        "customer": { "name": "WhatsApp User", "phone": sender, "source": "WhatsApp" }
                    }
                    db["orders"].append(new_order)
                    save_db(db)
                    response_text = f"✅ Order placed (Fallback)! {items_summary}. Total: ₹{total}"
                else:
                    response_text = "Sorry, I'm having trouble understanding. Please use the menu link."

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
