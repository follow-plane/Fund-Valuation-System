import sqlite3
import pandas as pd
import os
from datetime import datetime

DB_FILE = 'fund_data.db'

def init_db():
    """Initialize the database with necessary tables."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Holdings table: Stores user's fund holdings
    c.execute('''
        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_code TEXT NOT NULL,
            fund_name TEXT,
            share REAL NOT NULL,
            cost_price REAL NOT NULL,
            purchase_date TEXT
        )
    ''')
    
    # Investment Plans table: Stores auto-investment (定投) plans
    c.execute('''
        CREATE TABLE IF NOT EXISTS investment_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_code TEXT NOT NULL,
            fund_name TEXT,
            amount REAL NOT NULL,
            frequency TEXT NOT NULL,
            start_date TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')

    # Knowledge/Favorites table
    c.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT,
            category TEXT,
            added_date TEXT
        )
    ''')
    
    # Intraday Ticks table: Stores real-time ticks for charts
    # We store timestamp as TEXT (ISO format)
    c.execute('''
        CREATE TABLE IF NOT EXISTS intraday_ticks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_code TEXT NOT NULL,
            record_time TEXT NOT NULL,
            pct REAL NOT NULL,
            price REAL,
            UNIQUE(fund_code, record_time)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_FILE)

# --- Intraday Ticks Operations ---
def save_tick_batch(ticks_data):
    """
    Save a batch of tick data.
    ticks_data: list of tuples (fund_code, record_time, pct, price)
    """
    if not ticks_data:
        return
        
    conn = get_connection()
    c = conn.cursor()
    # Use INSERT OR IGNORE to avoid duplicates if we fetch same second twice
    c.executemany('''
        INSERT OR IGNORE INTO intraday_ticks (fund_code, record_time, pct, price)
        VALUES (?, ?, ?, ?)
    ''', ticks_data)
    conn.commit()
    conn.close()

def get_today_ticks(fund_code):
    """
    Get ticks for a specific fund for the current day.
    Returns DataFrame with columns ['record_time', 'pct', 'price']
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    # Filter by time starting with today's date
    query = f"SELECT record_time, pct, price FROM intraday_ticks WHERE fund_code = ? AND record_time LIKE '{today_str}%' ORDER BY record_time ASC"
    df = pd.read_sql(query, conn, params=(fund_code,))
    conn.close()
    return df

def cleanup_old_ticks(days_to_keep=2):
    """Delete ticks older than N days to save space."""
    conn = get_connection()
    c = conn.cursor()
    # Simple date string comparison works for ISO format
    # But calculating the cutoff date string is safer
    # For simplicity, we just delete anything not from today? 
    # User might want to see yesterday's data if today hasn't started.
    # Let's keep it simple: Delete everything that is NOT today.
    # Wait, if user opens app at night, they want to see today's data.
    # If they open tomorrow morning before market, they might want to see yesterday's.
    # Let's keep last 3 days.
    
    # actually, SQLite date modifier: date('now', '-2 days')
    c.execute("DELETE FROM intraday_ticks WHERE record_time < date('now', '-3 days')")
    conn.commit()
    conn.close()

# --- Holdings Operations ---
def add_holding(fund_code, fund_name, share, cost_price, purchase_date=None):
    if not purchase_date:
        purchase_date = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO holdings (fund_code, fund_name, share, cost_price, purchase_date) VALUES (?, ?, ?, ?, ?)',
              (fund_code, fund_name, share, cost_price, purchase_date))
    conn.commit()
    conn.close()

def get_holdings():
    conn = get_connection()
    df = pd.read_sql('SELECT * FROM holdings', conn)
    conn.close()
    return df

def delete_holding(holding_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM holdings WHERE id = ?', (holding_id,))
    conn.commit()
    conn.close()

def update_holding(holding_id, share, cost_price):
    """Update share and cost price for an existing holding."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE holdings SET share = ?, cost_price = ? WHERE id = ?',
              (share, cost_price, holding_id))
    conn.commit()
    conn.close()

# --- Investment Plan Operations ---
def add_plan(fund_code, fund_name, amount, frequency, start_date):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO investment_plans (fund_code, fund_name, amount, frequency, start_date) VALUES (?, ?, ?, ?, ?)',
              (fund_code, fund_name, amount, frequency, start_date))
    conn.commit()
    conn.close()

def get_plans():
    conn = get_connection()
    df = pd.read_sql('SELECT * FROM investment_plans', conn)
    conn.close()
    return df

def update_plan_status(plan_id, status):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE investment_plans SET status = ? WHERE id = ?', (status, plan_id))
    conn.commit()
    conn.close()

# Initialize DB on module load if not exists
if not os.path.exists(DB_FILE):
    init_db()
else:
    # Check if tables exist to avoid errors if file exists but empty
    init_db()
