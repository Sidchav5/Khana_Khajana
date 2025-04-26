from flask import Flask
from flask_mysqldb import MySQL
import logging

app = Flask(__name__)

# Logging config
logging.basicConfig(level=logging.DEBUG)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = "Siddhesh@5"
app.config['MYSQL_DB'] = 'khana_khajana'

mysql = MySQL(app)

@app.route('/')
def index():
    try:
        logging.debug(f"mysql.connection: {mysql.connection}")
        cur = mysql.connection.cursor()
        cur.execute("SELECT DATABASE();")
        db = cur.fetchone()
        cur.close()
        return f"✅ Connected to database: {db[0]}"
    except Exception as e:
        logging.exception("Database connection failed:")
        return f"❌ Connection failed: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)
