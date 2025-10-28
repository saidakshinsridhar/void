import os
import re
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
load_dotenv()
app = Flask(__name__)
bcrypt = Bcrypt(app)
CORS(app)

# --- DATABASE CONNECTION ---
try:
    # Get the MongoDB connection string from environment variables
    MONGO_URI = os.getenv("MONGO_URI")
    
    # Check if the URI is just the placeholder
    if not MONGO_URI or MONGO_URI == "your_mongodb_connection_string_goes_here":
        print("WARNING: MONGO_URI is not set or is still the placeholder.")
        print("Database connection will fail until this is fixed in the .env file.")
        client = None
        db = None
    else:
        client = MongoClient(MONGO_URI)
        
        # 'client.admin.command('ping')' is used to test the connection
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas!")
        
        # Define your database. It will be created if it doesn't exist.
        db = client["rewearth"] 
        
        # You can define your collections here for later
        # users_collection = db["users"]
        # items_collection = db["items"]
        # eco_data_collection = db["eco_data"]

except Exception as e:
    print(f"ERROR: Could not connect to MongoDB Atlas: {e}")
    client = None
    db = None

# --- API ROUTES ---

@app.route("/")
def home():
    # A simple route to test if the server is running
    return jsonify({"message": "Hello from the ReWearth Flask Backend!"})

# --- Add your API routes here ---
# (We will build these next)
@app.route("/api/eco-data")
def get_eco_data():
    item_name = request.args.get('item')

    if not item_name:
        return jsonify({"error": "No item specified. Use ?item=... query."}), 400

    if db is None:
        return jsonify({"error": "Database not connected"}), 503

    try:
        # --- THIS IS THE FIX ---
        # We must escape the search query here as well
        escaped_item_name = re.escape(item_name)

        found_item = db.eco_data.find_one(
            {"ItemName": {"$regex": escaped_item_name, "$options": "i"}},
            {"_id": 0}
        )
        # --- END OF FIX ---
        
        if found_item:
            return jsonify(found_item)
        else:
            return jsonify({"error": f"Data not found for '{item_name}'"}), 404
            
    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500
@app.route("/api/register", methods=["POST"])
def register_user():
    # 1. Get the data
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify({"error": "Invalid JSON data"}), 400

    # 2. Validate the data
    if not data:
        return jsonify({"error": "No data provided"}), 400

    email = data.get('email')
    password = data.get('password')
    college_id = data.get('college_id')

    if not email or not password or not college_id:
        return jsonify({"error": "Missing email, password, or college_id"}), 400

    # 3. Hash the password
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    print(f"--- REGISTRATION ATTEMPT ---")
    print(f"Email: {email}")
    print(f"Original Pass: {password}")
    print(f"Hashed Pass: {hashed_password}")
    print(f"College ID: {college_id}")
    print(f"-----------------------------")

    # 4. Check if DB is connected
    

    # --- (This is the real code for when your DB works) ---
    
    # # 5. Check if user already exists
    try:
         if db.users.find_one({"email": email.lower()}):
             return jsonify({"error": "Email already registered"}), 409 # 409 means "Conflict"
    
         # 6. Save new user to database
         new_user = {
             "email": email.lower(),
             "password": hashed_password,
             "college_id": college_id,
             "verified": False, # Default to not verified
             "credits": 100
         }
         db.users.insert_one(new_user)
        
         return jsonify({
             "message": "User registered successfully! (But this is just a test)"
         }), 201

    except Exception as e:
         return jsonify({"error": f"An error occurred: {e}"}), 500
    
    # --- (End of real code) ---
    
    # This is a temporary line to stop the code from breaking
    # We'll remove this once the DB is fixed.
    
@app.route("/api/login", methods=["POST"])
def login_user():
    # 1. Get the data
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify({"error": "Invalid JSON data"}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    # 2. Find the user in the database
    try:
        user = db.users.find_one({"email": email.lower()})

        # 3. Check if user exists and if password matches
        # 'user' is the doc from the DB, 'password' is the plain text from Postman
        if user and bcrypt.check_password_hash(user["password"], password):
            # Password is correct!
            # We'll create a session token here later (e.g., JWT)
            return jsonify({
                "message": "Login successful!",
                "user": {
                    "email": user["email"],
                    "college_id": user["college_id"],
                    "verified": user["verified"]
                }
            }), 200
        else:
            # Invalid email or password
            return jsonify({"error": "Invalid email or password"}), 401 # 401 means "Unauthorized"

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500
@app.route("/api/item/upload", methods=["POST"])
def upload_item():
    # 1. Get the data
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify({"error": "Invalid JSON data"}), 400

    # 2. Validate the data
    item_name = data.get('item_name')
    condition = data.get('condition')
    image_url = data.get('image_url')
    user_email = data.get('user_email')
    item_type = data.get('item_type')
    credit_cost = data.get('credit_cost')

    if not item_name or not condition or not image_url or not user_email or not item_type or credit_cost is None:
        return jsonify({"error": "Missing item_name, condition, image_url, user_email, item_type, or credit_cost"}), 400

    if db is None:
        return jsonify({"error": "Database not connected"}), 503

    try:
        # 3. Find the user
        user = db.users.find_one({"email": user_email.strip().lower()})
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        # 4. --- THIS IS THE FIX ---
        # We must escape the string in case it has special regex chars like ( or )
        escaped_item_type = re.escape(item_type)
        
        eco_data = db.eco_data.find_one(
            {"ItemName": {"$regex": f"^{escaped_item_type}$", "$options": "i"}},
            {"_id": 0} 
        )
        # --- END OF FIX ---

        if not eco_data:
            return jsonify({"error": f"Eco-data not found for item_type: '{item_type}'"}), 404

        # 5. Save new item
        new_item = {
            "owner_id": user["_id"],
            "owner_email": user["email"],
            "item_name": item_name,
            "condition": condition,
            "image_url": image_url,
            "available_for_swap": True,
            "sustainability_data": eco_data,
            "credit_cost": credit_cost
        }
        
        db.items.insert_one(new_item) 
        
        return jsonify({
            "message": "Item added to wardrobe successfully (with eco-data)!"
        }), 201

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500


@app.route("/api/wardrobe/my-items")
def get_my_items():
    # 1. Get the user's email from the query string (e.g., ?email=test@example.com)
    user_email = request.args.get('email')

    if not user_email:
        return jsonify({"error": "No email specified"}), 400

    if db is None:
        return jsonify({"error": "Database not connected"}), 503

    # 2. Find all items in the 'items' collection matching that email
    try:
        my_items = []
        
        # We use .find() to get ALL matching items
        for item in db.items.find({"owner_email": user_email.strip().lower()}):
            # We must convert the ObjectId to a string to send it as JSON
            item["_id"] = str(item["_id"])
            item["owner_id"] = str(item["owner_id"])
            my_items.append(item)
            
        return jsonify(my_items) # Return the list of items

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500
@app.route("/api/wardrobe/swap-feed")
def get_swap_feed():
    # 1. Get the user's email from the query string (so we can exclude them)
    user_email = request.args.get('email')

    if not user_email:
        return jsonify({"error": "No email specified to filter by"}), 400

    if db is None:
        return jsonify({"error": "Database not connected"}), 503

    # 2. Find all items where owner_email is NOT the user's email
    try:
        swap_items = []
        
        # $ne means "not equal". We're finding items where the
        # owner_email is "not equal" to the current user's email.
        query = {"owner_email": {"$ne": user_email.strip().lower()}}
        
        for item in db.items.find(query):
            item["_id"] = str(item["_id"])
            item["owner_id"] = str(item["owner_id"])
            swap_items.append(item)
            
        return jsonify(swap_items)

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500
@app.route("/api/swap/request", methods=["POST"])
@app.route("/api/swap/request", methods=["POST"])
def request_swap():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify({"error": "Invalid JSON data"}), 400

    # 1. Get the data
    requester_email = data.get('requester_email')
    item_requested_id = data.get('item_requested_id') # The item they WANT
    item_offered_id = data.get('item_offered_id')     # The item they are OFFERING

    if not requester_email or not item_requested_id or not item_offered_id:
        return jsonify({"error": "Missing requester_email, item_requested_id, or item_offered_id"}), 400

    if db is None:
        return jsonify({"error": "Database not connected"}), 503

    try:
        # 2. Define the transaction fee
        SWAP_FEE = 20

        # 3. Find the items and users
        item_requested = db.items.find_one({"_id": ObjectId(item_requested_id)})
        item_offered = db.items.find_one({"_id": ObjectId(item_offered_id)})
        requester = db.users.find_one({"email": requester_email.strip().lower()})
        
        if not item_requested or not item_offered:
            return jsonify({"error": "One or both items not found"}), 404
        if not requester:
            return jsonify({"error": "Requester user not found"}), 404

        receiver_email = item_requested.get('owner_email')
        receiver = db.users.find_one({"email": receiver_email})

        # 4. Check that both users can afford the 20-credit fee
        if requester.get('credits', 0) < SWAP_FEE:
            return jsonify({"error": "You have insufficient credits for the swap fee"}), 402
        if receiver.get('credits', 0) < SWAP_FEE:
            # We check the receiver now so they don't get a request they can't accept
            return jsonify({"error": "The other user cannot afford the swap fee right now"}), 400

        # 5. Check other logic
        if item_requested.get('owner_email') != receiver_email or item_offered.get('owner_email') != requester_email:
            return jsonify({"error": "Item ownership mismatch"}), 400
        if item_requested.get('available_for_swap') == False or item_offered.get('available_for_swap') == False:
            return jsonify({"error": "One or both items are no longer available"}), 400

        # 6. Create the pending swap request
        new_swap = {
            "requester_email": requester_email,
            "requester_id": requester.get('_id'),
            "requester_item_id": item_offered.get('_id'),
            "requester_item_name": item_offered.get('item_name'),
            
            "receiver_email": receiver_email,
            "receiver_id": receiver.get('_id'),
            "receiver_item_id": item_requested.get('_id'),
            "receiver_item_name": item_requested.get('item_name'),

            "status": "pending",
            "platform_fee": SWAP_FEE
        }
        
        db.swaps.insert_one(new_swap)
        
        return jsonify({
            "message": "Swap request sent successfully!"
        }), 201

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500
@app.route("/api/swap/inbox")
def get_swap_inbox():
    # 1. Get the user's email from the query string
    user_email = request.args.get('email')

    if not user_email:
        return jsonify({"error": "No email specified"}), 400

    if db is None:
        return jsonify({"error": "Database not connected"}), 503

    try:
        # 2. Find all pending swaps where the user is the RECEIVER
        pending_swaps = []
        
        query = {
            "receiver_email": user_email.strip().lower(),
            "status": "pending"
        }
        
        for swap in db.swaps.find(query):
            # Convert all ObjectIds to strings for JSON
            swap["_id"] = str(swap["_id"])
            swap["requester_id"] = str(swap["requester_id"])
            swap["receiver_id"] = str(swap["receiver_id"])
            swap["item_id"] = str(swap["item_id"])
            pending_swaps.append(swap)
            
        return jsonify(pending_swaps) # Return the list of pending requests

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500
@app.route("/api/swap/respond", methods=["POST"])
@app.route("/api/swap/respond", methods=["POST"])
def respond_to_swap():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify({"error": "Invalid JSON data"}), 400

    # 1. Get the data
    swap_id = data.get('swap_id')
    response = data.get('response') # "accepted" or "rejected"

    if not swap_id or not response or response not in ["accepted", "rejected"]:
        return jsonify({"error": "Missing or invalid swap_id or response"}), 400

    if db is None:
        return jsonify({"error": "Database not connected"}), 503

    try:
        # 2. Find the swap request
        swap = db.swaps.find_one({"_id": ObjectId(swap_id)})
        if not swap:
            return jsonify({"error": "Swap request not found"}), 404
        
        if swap.get('status') != "pending":
            return jsonify({"error": "This swap has already been responded to"}), 400

        # --- IF REJECTED ---
        if response == "rejected":
            db.swaps.update_one(
                {"_id": ObjectId(swap_id)},
                {"$set": {"status": "rejected"}}
            )
            return jsonify({"message": "Swap successfully rejected"}), 200

        # --- IF ACCEPTED ---
        if response == "accepted":
            # 3. Get all the data needed for the transaction
            requester_email = swap.get('requester_email')
            receiver_email = swap.get('receiver_email')
            requester_item_id = swap.get('requester_item_id')
            receiver_item_id = swap.get('receiver_item_id')
            fee = swap.get('platform_fee', 20) # Get the fee from the swap doc

            # 4. Perform the transaction
            
            # Step 1: Deduct 20 credits from requester
            db.users.update_one(
                {"email": requester_email},
                {"$inc": {"credits": -fee}}
            )
            
            # Step 2: Deduct 20 credits from receiver
            db.users.update_one(
                {"email": receiver_email},
                {"$inc": {"credits": -fee}}
            )
            
            # Step 3: Mark BOTH items as "sold"
            db.items.update_one(
                {"_id": requester_item_id},
                {"$set": {"available_for_swap": False}}
            )
            db.items.update_one(
                {"_id": receiver_item_id},
                {"$set": {"available_for_swap": False}}
            )
            
            # Step 4: Mark the swap as "completed"
            db.swaps.update_one(
                {"_id": ObjectId(swap_id)},
                {"$set": {"status": "completed"}}
            )
            
            return jsonify({"message": "Swap successfully completed! 20 credits deducted from both users."}), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500
@app.route("/api/credits/buy", methods=["POST"])
def buy_credits():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify({"error": "Invalid JSON data"}), 400

    # 1. Get the data
    email = data.get('email')
    amount_to_buy = data.get('amount_to_buy')

    if not email or not amount_to_buy:
        return jsonify({"error": "Missing email or amount_to_buy"}), 400

    if db is None:
        return jsonify({"error": "Database not connected"}), 503

    try:
        # 2. Find the user
        user = db.users.find_one({"email": email.strip().lower()})
        if not user:
            return jsonify({"error": "User not found"}), 404

        # 3. Add the credits to their account
        db.users.update_one(
            {"email": email.strip().lower()},
            {"$inc": {"credits": amount_to_buy}}
        )

        # 4. Get the new total credits to send back
        updated_user = db.users.find_one({"email": email.strip().lower()})
        new_credit_balance = updated_user.get('credits', 0)

        return jsonify({
            "message": "Credits purchased successfully!",
            "new_credit_balance": new_credit_balance
        }), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500

# --- RUN THE APP ---
if __name__ == "__main__":
    # Runs the server on port 5000 (default)
    # 'debug=True' auto-reloads the server when you save changes
    app.run(debug=True, port=5001)