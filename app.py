from flask import Flask, request, jsonify, render_template
import sqlite3
import jwt
import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "mobibridge_secret_2026"

# -----------------------------
# DATABASE SETUP
# -----------------------------
def init_db():
    conn = sqlite3.connect("mobibridge.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wallets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        balance REAL DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        amount REAL,
        status TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# JWT MIDDLEWARE
# -----------------------------
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"error": "Token missing"}), 401

        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user_id = data["user_id"]

        except:
            return jsonify({"error": "Invalid or expired token"}), 401

        return f(current_user_id, *args, **kwargs)

    return decorated

# -----------------------------
# FRONTEND PAGE
# -----------------------------
@app.route("/app")
def app_ui():
    return render_template("index.html")

# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return "MobiBridge API running 🚀"

# -----------------------------
# REGISTER
# -----------------------------
@app.route("/register", methods=["POST"])
def register():

    data = request.get_json()

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    hashed_password = generate_password_hash(password)

    conn = sqlite3.connect("mobibridge.db")
    cursor = conn.cursor()

    try:
        cursor.execute("""
        INSERT INTO users (username, email, password)
        VALUES (?, ?, ?)
        """, (username, email, hashed_password))

        user_id = cursor.lastrowid

        cursor.execute("""
        INSERT INTO wallets (user_id, balance)
        VALUES (?, ?)
        """, (user_id, 0))

        conn.commit()

        return jsonify({
            "status": "success",
            "user_id": user_id
        })

    except:
        return jsonify({
            "status": "error",
            "message": "Registration failed"
        })

    finally:
        conn.close()

# -----------------------------
# LOGIN (JWT)
# -----------------------------
@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    conn = sqlite3.connect("mobibridge.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, password FROM users WHERE username = ?
    """, (username,))

    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({"status": "error", "message": "User not found"})

    user_id = user[0]
    stored_password = user[1]

    if check_password_hash(stored_password, password):

        token = jwt.encode({
            "user_id": user_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }, app.config["SECRET_KEY"], algorithm="HS256")

        return jsonify({
            "status": "success",
            "token": token
        })

    return jsonify({"status": "error", "message": "Invalid password"})

# -----------------------------
# BALANCE (PROTECTED)
# -----------------------------
@app.route("/balance")
@token_required
def balance(current_user_id):

    conn = sqlite3.connect("mobibridge.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT balance FROM wallets WHERE user_id = ?
    """, (current_user_id,))

    result = cursor.fetchone()
    conn.close()

    if result:
        return jsonify({
            "user_id": current_user_id,
            "balance": result[0]
        })

    return jsonify({"error": "Wallet not found"})

# -----------------------------
# TRANSFER (PROTECTED)
# -----------------------------
@app.route("/transfer", methods=["POST"])
@token_required
def transfer(current_user_id):

    data = request.get_json()

    receiver_id = data.get("receiver_id")
    amount = float(data.get("amount"))

    conn = sqlite3.connect("mobibridge.db")
    cursor = conn.cursor()

    sender_id = current_user_id

    cursor.execute("SELECT balance FROM wallets WHERE user_id = ?", (sender_id,))
    sender = cursor.fetchone()

    cursor.execute("SELECT balance FROM wallets WHERE user_id = ?", (receiver_id,))
    receiver = cursor.fetchone()

    if not sender or not receiver:
        return jsonify({"error": "Invalid users"})

    if sender[0] < amount:
        return jsonify({"error": "Insufficient balance"})

    cursor.execute("""
    UPDATE wallets SET balance = balance - ?
    WHERE user_id = ?
    """, (amount, sender_id))

    cursor.execute("""
    UPDATE wallets SET balance = balance + ?
    WHERE user_id = ?
    """, (amount, receiver_id))

    cursor.execute("""
    INSERT INTO transactions (sender_id, receiver_id, amount, status)
    VALUES (?, ?, ?, ?)
    """, (sender_id, receiver_id, amount, "SUCCESS"))

    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Transfer complete"})

# -----------------------------
# TRANSACTIONS
# -----------------------------
@app.route("/transactions")
@token_required
def transactions(current_user_id):

    conn = sqlite3.connect("mobibridge.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT sender_id, receiver_id, amount, status, timestamp
    FROM transactions
    WHERE sender_id = ? OR receiver_id = ?
    ORDER BY timestamp DESC
    """, (current_user_id, current_user_id))

    rows = cursor.fetchall()
    conn.close()

    data = []

    for r in rows:
        data.append({
            "sender_id": r[0],
            "receiver_id": r[1],
            "amount": r[2],
            "status": r[3],
            "timestamp": r[4]
        })

    return jsonify({"transactions": data})

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)