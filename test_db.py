from config import Config
import mysql.connector, traceback

print('Using DB config:', Config.DB_CONFIG)
try:
    conn = mysql.connector.connect(**Config.DB_CONFIG)
    print('DB connection OK')
    conn.close()
except Exception:
    traceback.print_exc()
