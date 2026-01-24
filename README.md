# TiffinFlow - Home Kitchen Management SaaS

TiffinFlow is a SaaS platform designed for home kitchens to manage menus, orders, and customer interactions. It features a modern dashboard for kitchen owners and a seamless ordering experience for customers, including WhatsApp automation.

## 🚀 Features

- **Kitchen Dashboard**: Manage menus, view orders pipeline, and simulate WhatsApp interactions.
- **Customer App**: Mobile-friendly ordering page with cart, checkout modal, and geolocation address capture.
- **WhatsApp Automation**:
    - **Simulator**: Test "real" automation logic without a live WhatsApp API.
    - **NLP Parsing**: Uses Google Gemini AI to parse natural language orders (e.g., "2 thalis and a burger").
    - **Fallback Logic**: Robust regex fallback if AI service is unavailable.
- **Menu Management**: Add items with AI-generated descriptions and images.

## 🛠️ Setup & Installation

1.  **Prerequisites**:
    - Python 3.x installed.
    - PostgreSQL installed and running (`brew install postgresql` on Mac).
2.  **Clone the Repository**:
    ```bash
    git clone https://github.com/Anant2019/home_kitchen_app.git
    cd home_kitchen_app
    ```
3.  **Install Dependencies**:
    ```bash
    pip install google-generativeai psycopg2-binary PyJWT bcrypt
    ```
4.  **Database Setup**:
    ```bash
    python3 setup_db.py
    ```
5.  **Run the Server**:
    ```bash
    python3 server.py
    ```
    *The server runs on port 8001 by default to avoid conflicts.*

## 📖 Usage Guide

### Kitchen Owner
1.  Open `http://localhost:8001` in your browser.
2.  Login with credentials:
    - **Username**: `kitchen1`
    - **Password**: `123`
3.  **Tabs**:
    - **Menu**: Add/Edit dishes. Use the "✨ AI" button to auto-generate descriptions and images.
    - **Pipeline**: View incoming orders in real-time.
    - **WhatsApp Sim**: Simulate customer messages to test the automation bot.

### Customer
1.  Open `http://localhost:8001/customer.html?kitchenId=kitchen1`.
2.  Browse the menu and add items to the cart.
3.  Click **Proceed to Checkout**.
4.  Enter Name, Phone, and use **"📍 Use Current Location"** for address.
5.  Place the order and see the success overlay.

### WhatsApp Simulator
1.  Go to the **WhatsApp Sim** tab in the Kitchen Dashboard.
2.  Type a message like: *"I want 2 Special Veg Thali and 1 Gulab Jamun"*.
3.  The bot will reply with an order confirmation and total amount.
4.  Check the **Pipeline** tab to see the automatically created order.

## 📝 Pending Tasks

- [ ] **Real WhatsApp Integration**: Connect to WhatsApp Business API (Twilio/Meta) instead of the simulator.
- [ ] **Database Migration**: Move from `db.json` to a real database (PostgreSQL/MongoDB) for scalability.
- [x] **Authentication**: Implement secure JWT-based authentication for kitchen owners.
- [ ] **Payment Gateway**: Integrate Razorpay/Stripe for online payments.

## 🤝 Contribution Guide

We welcome contributions! Here's how to work on the project:

1.  **Branching**: Create a new branch for your feature (e.g., `feature/payment-integration`).
2.  **Code Structure**:
    - `server.py`: Backend logic (API endpoints, NLP, persistence).
    - `index.html`: Kitchen Owner Dashboard (React + Tailwind).
    - `customer.html`: Customer Ordering App (React + Tailwind).
    - `db.json`: JSON-based database (do not commit sensitive data).
3.  **Testing**:
    - Always verify changes in both the **Kitchen Dashboard** and **Customer App**.
    - Use the **WhatsApp Simulator** to test any changes to the ordering logic.
4.  **Pull Requests**: Push your branch and create a PR with a detailed description of changes.

---
*Built with ❤️ for Home Chefs.*