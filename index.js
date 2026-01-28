const express = require('express');
const axios = require('axios');
const app = express();
app.use(express.json());

// --- CONFIGURATION CHECKS ---
const FB_DB_URL = process.env.FB_DB_URL?.replace(/\/$/, ""); 
const META_TOKEN = process.env.META_TOKEN;
const PHONE_ID = process.env.PHONE_ID;
const VERIFY_TOKEN = "tiffin_demo_secret";

// Check if critical variables are missing
if (!FB_DB_URL || !META_TOKEN || !PHONE_ID) {
    console.warn("⚠️ WARNING: Missing one or more Environment Variables (FB_DB_URL, META_TOKEN, PHONE_ID). App may crash.");
}

// 1. Webhook Verification
app.get('/webhook', (req, res) => {
    if (req.query['hub.verify_token'] === VERIFY_TOKEN) {
        res.send(req.query['hub.challenge']);
    } else {
        res.sendStatus(403);
    }
});

// 2. Handle Incoming WhatsApp Messages
app.post('/webhook', async (req, res) => {
    // Always respond 200 OK immediately to prevent WhatsApp retries
    res.sendStatus(200);

    try {
        const entry = req.body.entry?.[0]?.changes?.[0]?.value;
        const message = entry?.messages?.[0];

        if (!message) return; // No message found

        const from = message.from;

        // --- PHASE 1: User types 'menu' ---
        if (message.type === 'text' && message.text.body.toLowerCase().trim() === 'menu') {
            console.log(`Fetching menus for user: ${from}`);
            
            // Fetch from Firebase
            const response = await axios.get(`${FB_DB_URL}/menus.json`);
            const kitchens = response.data;

            if (!kitchens) {
                await sendSimpleMsg(from, "Sorry, no kitchens are live right now.");
                return;
            }

            // Construct Rows (Safe Version)
            // WhatsApp LIMITS: Title max 24 chars, Desc max 72 chars
            const rows = Object.keys(kitchens).map(id => {
                const kName = kitchens[id].name || "Unknown Kitchen";
                return {
                    id: id, 
                    title: kName.substring(0, 23), // Safety cut-off
                    description: "Tap to see today's thali".substring(0, 72)
                };
            }).slice(0, 10);

            // Send Interactive List
            await axios.post(`https://graph.facebook.com/v21.0/${PHONE_ID}/messages`, {
                messaging_product: "whatsapp",
                to: from,
                type: "interactive",
                interactive: {
                    type: "list",
                    header: { type: "text", text: "🍱 TiffinFlow Menu" },
                    body: { text: "Select a kitchen to view today's meal:" },
                    footer: { text: "Pure Home Taste" },
                    action: {
                        button: "View Kitchens",
                        sections: [{
                            title: "Nearby Kitchens",
                            rows: rows
                        }]
                    }
                }
            }, { headers: { Authorization: `Bearer ${META_TOKEN}` } });
        }

        // --- PHASE 2: User clicks a Kitchen button ---
        if (message.type === 'interactive' && message.interactive.type === 'list_reply') {
            const selectionId = message.interactive.list_reply.id;
            console.log(`User selected kitchen ID: ${selectionId}`);
            
            const response = await axios.get(`${FB_DB_URL}/menus/${selectionId}.json`);
            const menu = response.data;

            if (menu) {
                const mealDetails = `*${menu.name} Today's Menu:*\n\n🍴 ${menu.items || 'Menu coming soon'}\n💰 Price: ₹${menu.price || '120'}\n\nReply 'ORDER' to book now!`;
                await sendSimpleMsg(from, mealDetails);
            } else {
                await sendSimpleMsg(from, "Sorry, details for this kitchen are not available.");
            }
        }

    } catch (err) {
        // Detailed Error Logging
        console.error("❌ ERROR OCCURRED:");
        if (err.response) {
            console.error("API Response Data:", JSON.stringify(err.response.data, null, 2));
        } else {
            console.error("Error Message:", err.message);
        }
    }
});

// Helper function
async function sendSimpleMsg(to, text) {
    try {
        await axios.post(`https://graph.facebook.com/v21.0/${PHONE_ID}/messages`, {
            messaging_product: "whatsapp",
            to: to,
            type: "text",
            text: { body: text }
        }, { headers: { Authorization: `Bearer ${META_TOKEN}` } });
    } catch (error) {
        console.error("Failed to send text message:", error.response ? error.response.data : error.message);
    }
}

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => console.log(`Server live on port ${PORT}`));