import MySQLdb
from werkzeug.security import generate_password_hash

# Database connection
db = MySQLdb.connect(host="localhost", user="root", passwd="", db="uos_cafeteria")

# Cursor initialization
cursor = db.cursor()

# Admin credentials
username = "uoscafeteria@gmail.com"
password = "miansajid123"
role = "admin"
name = "Mian Sajid"

# Hash the password
hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

# Insert the admin into the database
cursor.execute("INSERT INTO users (username, password, role, name) VALUES (%s, %s, %s, %s)", (username, hashed_password, role, name))

# Commit the transaction
db.commit()

# Close the connection
cursor.close()
db.close()

print("Admin registered successfully!")
