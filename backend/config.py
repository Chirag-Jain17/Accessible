import os
from dotenv import load_dotenv

# Explicitly load .env from backend directory
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Database Connection Settings
DB_HOST = os.getenv('MYSQL_HOST', 'localhost')
DB_USER = os.getenv('MYSQL_USER', 'root')
DB_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
DB_NAME = os.getenv('MYSQL_DB', 'mydatabase')

# Server Settings
SERVER_HOST = os.getenv('HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('PORT', 5000))
DEBUG_MODE = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')

# SQL Validation Whitelists
ALLOWED_AGGREGATES = {'COUNT', 'SUM', 'AVG', 'MIN', 'MAX'}
ALLOWED_JOIN_TYPES = {'INNER', 'LEFT', 'RIGHT'}
ALLOWED_OPERATORS = {'=', '!=', '>', '<', '>=', '<=', 'LIKE', 'NOT LIKE', 'IS NULL', 'IS NOT NULL'}
