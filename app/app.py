import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
import os
import google.generativeai as genai
import functools
from reporting_module import api
from psycopg2.errors import OperationalError
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func

load_dotenv()

app = Flask(__name__)

app.register_blueprint(api.report_module_api, url_prefix= '/api')

def get_db_connection():
    try:
        app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://username:password@host:port/database_name"
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db = SQLAlchemy(app)
        return db
    except OperationalError as e:
        return(f"Error establishing primary database connection: {e}")
    
postgres_db = get_db_connection()

cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-pro')
def gemini_request(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error using gemini api: {e}")
        return "There was an error while processing your request."   


# Add this cache to avoid repeated API calls
exchange_rate_cache = {}

@functools.lru_cache(maxsize=32)
def get_exchange_rate_cached(from_currency, to_currency='PLN'):
    """Cached version of get_exchange_rate to reduce API calls"""
    cache_key = f"{from_currency}_{to_currency}"
    
    # Check if we have a cached value less than 1 day old
    if cache_key in exchange_rate_cache:
        cached_time, rate = exchange_rate_cache[cache_key]
        if datetime.now() - cached_time < timedelta(days=1):
            return rate
    
    # If not in cache or too old, get a fresh rate
    try:
        if from_currency == to_currency:
            rate = 1.0
        else:
            response = requests.get(f'https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}', 
                                   timeout=5)  # Add timeout
            response.raise_for_status()
            data = response.json()
            rate = data['rates'][to_currency]
        
        # Cache the result
        exchange_rate_cache[cache_key] = (datetime.now(), rate)
        return rate
    except requests.exceptions.RequestException as e:
        print(f"Error fetching exchange rate: {e}")
        # Return last cached value if available
        if cache_key in exchange_rate_cache:
            print(f"Using cached exchange rate for {cache_key}")
            return exchange_rate_cache[cache_key][1]
        return 1.0  # Default fallback

def get_exchange_rate(from_currency, to_currency='PLN'):
    if from_currency == to_currency:
        return 1.0
    try:
         response = requests.get(f'https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}')
         response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
         data = response.json()
         return data['rates'][to_currency]
    except requests.exceptions.RequestException as e:
         print(f"Error fetching exchange rate: {e}")
         return 1.0 # Return a default rate of 1 if API fails

def convert_to_pln(amount, currency):
    return float(amount) * get_exchange_rate_cached(currency)


def check_and_update_schema():
    pass
"""    conn = get_db_connection()
    
    # Check if the role column exists in the users table
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'role' not in columns:
        print("Adding 'role' column to users table")
        try:
            # Add the role column to the users table
            conn.execute('ALTER TABLE users ADD COLUMN role TEXT DEFAULT "User"')
            conn.commit()
            print("Role column added successfully")
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"Error: {e}")
    
    conn.close()"""


if __name__ == '__main__':
    app.run(debug=True)