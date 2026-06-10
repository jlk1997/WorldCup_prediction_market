import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(user="postgres", password=os.getenv("DB_PASSWORD", "postgres"), host="127.0.0.1", port=5432, database="postgres")
    print("Success")
except Exception as e:
    # Try to encode back to latin1 and decode to gbk to see the real error message if it's messed up
    error_msg = str(e)
    try:
        print("GBK decoded:", error_msg.encode('latin1').decode('gbk'))
    except:
        print("Raw error:", error_msg)

try:
    conn = psycopg2.connect(user="postgres", password=os.getenv("DB_PASSWORD", "postgres"), host="127.0.0.1", port=5432, database="postgres")
    print("Success with old password")
except Exception as e:
    pass
