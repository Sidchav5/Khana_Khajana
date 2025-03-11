from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import base64
from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import requests
import logging
app = Flask(__name__)

# Flask configuration
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  # Use your MySQL username
app.config['MYSQL_PASSWORD'] = 'Siddhesh@5'  # Use your MySQL password
app.config['MYSQL_DB'] = 'khana_khajana'  # Use your MySQL database name

# Initialize MySQL
mysql = MySQL(app)

# Initialize Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password

# Load user for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", [user_id])
    user = cur.fetchone()
    cur.close()
    if user:
        return User(id=user[0], username=user[1], email=user[2], password=user[3])
    return None

# Home Page
# Home Page
@app.route('/')
def home():
    cur = mysql.connection.cursor()

    # Fetch top 5 most liked recipes (name, photo, likes, dislikes)
    cur.execute("SELECT id, name, photo, likes, dislikes FROM recipes ORDER BY likes DESC LIMIT 6")
    top_liked_recipes = cur.fetchall()
    cur.close()

    # Convert photo data to base64 URL format
    top_liked_recipes_with_photos = []
    for recipe in top_liked_recipes:
        photo_base64 = recipe[2]  # 'photo' is the 3rd column in the query
        photo_data_url = f"data:image/jpeg;base64,{photo_base64}"
        recipe_dict = {
            'id': recipe[0],  # Recipe ID
            'name': recipe[1],  # Recipe name
            'photo_data_url': photo_data_url,  # Base64 photo
            'likes': recipe[3],  # Number of likes
            'dislikes': recipe[4]  # Number of dislikes
        }
        top_liked_recipes_with_photos.append(recipe_dict)

    return render_template('index.html', top_liked_recipes=top_liked_recipes_with_photos)

# Post It Form
@app.route('/post_it')
@login_required
def post_it():
    return render_template('post_it.html')

# Submit Recipe
@app.route('/submit', methods=['POST'])
@login_required
def submit():
    if request.method == 'POST':
        type = request.form['type']
        name = request.form['name']
        description = request.form['description']
        ingredients = request.form['ingredients']
        time = request.form['time']
        instructions = request.form['instructions']
        photo = request.files['photo']

        # Convert the image to base64
        if photo and allowed_file(photo.filename):
            photo_base64 = base64.b64encode(photo.read()).decode('utf-8')
        else:
            flash('Invalid image file!', 'danger')
            return redirect(url_for('post_it'))

        # Save to database with user_id
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO recipes (type, name, description, ingredients, time, instructions, photo, user_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (type, name, description, ingredients, time, instructions, photo_base64, current_user.id)
        )
        mysql.connection.commit()
        cur.close()

        flash('Recipe submitted successfully!', 'success')
        return redirect(url_for('post_it'))
# Blog Page
@app.route('/blogs')
def blogs():
    cur = mysql.connection.cursor()

    # Fetch all recipes
    cur.execute("SELECT * FROM recipes")
    recipes = cur.fetchall()

    # Fetch top 5 most liked recipes (only name, photo, likes, dislikes)
    cur.execute("SELECT name, photo, likes, dislikes FROM recipes ORDER BY likes DESC LIMIT 5")
    top_liked_recipes = cur.fetchall()

    cur.close()

    # Add photo_data_url to each recipe
    recipes_with_photos = []
    for recipe in recipes:
        photo_base64 = recipe[7]  # Assuming 'photo' is the 7th column
        photo_data_url = f"data:image/jpeg;base64,{photo_base64}"
        recipe_dict = {
            'id': recipe[0],
            'type': recipe[1],
            'name': recipe[2],
            'description': recipe[3],
            'ingredients': recipe[4],
            'time': recipe[5],
            'instructions': recipe[6],
            'photo_data_url': photo_data_url,
            'user_id': recipe[8],
            'likes': recipe[9],  # New likes column
            'dislikes': recipe[10]  # New dislikes column
        }
        recipes_with_photos.append(recipe_dict)

    # Add photo_data_url to top liked recipes
    top_liked_recipes_with_photos = []
    for recipe in top_liked_recipes:
        photo_base64 = recipe[1]  # 'photo' is the 2nd column in the query
        photo_data_url = f"data:image/jpeg;base64,{photo_base64}"
        recipe_dict = {
            'name': recipe[0],  # 'name' is the 1st column in the query
            'photo_data_url': photo_data_url,
            'likes': recipe[2],  # 'likes' is the 3rd column in the query
            'dislikes': recipe[3]  # 'dislikes' is the 4th column in the query
        }
        top_liked_recipes_with_photos.append(recipe_dict)

    return render_template('blog.html', recipes=recipes_with_photos, top_liked_recipes=top_liked_recipes_with_photos)
# Recipe Detail Page
@app.route('/recipe/<int:id>')
def recipe_detail(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM recipes WHERE id = %s", [id])
    recipe = cur.fetchone()
    cur.close()

    if recipe:
      photo_base64 = recipe[7]  # Assuming 'photo' is the 7th column
      photo_data_url = f"data:image/jpeg;base64,{photo_base64}"
      return render_template('recipe_detail.html', recipe=recipe, photo_data_url=photo_data_url)

    else:
        flash('Recipe not found!', 'danger')
        return redirect(url_for('blogs'))
# Delete Recipe
from flask import jsonify

@app.route('/delete_recipe/<int:id>', methods=['POST'])
@login_required
def delete_recipe(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT user_id FROM recipes WHERE id = %s", [id])
    recipe = cur.fetchone()

    if not recipe:
        return jsonify({'success': False, 'message': 'Recipe not found'}), 404

    if recipe[0] != current_user.id:
        return jsonify({'success': False, 'message': 'You are not authorized to delete this recipe'}), 403

    # Delete the recipe
    cur.execute("DELETE FROM recipes WHERE id = %s", [id])
    mysql.connection.commit()
    cur.close()
    
    return jsonify({'success': True, 'message': 'Recipe deleted successfully'}), 200


# Signup Page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if the username or email already exists
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        user = cur.fetchone()
        if user:
            flash('Username or email already exists!', 'danger')
            return redirect(url_for('signup'))

        # Create a new user
        cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, password))
        mysql.connection.commit()
        cur.close()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if the user exists
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", [email])
        user = cur.fetchone()
        cur.close()
        if user and user[3] == password:  # user[3] is the password field
            user_obj = User(id=user[0], username=user[1], email=user[2], password=user[3])
            login_user(user_obj)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

import os

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Like a recipe
@app.route('/like_recipe/<int:id>', methods=['POST'])
@login_required
def like_recipe(id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE recipes SET likes = likes + 1 WHERE id = %s", [id])
    mysql.connection.commit()
    cur.close()
    return jsonify(success=True)

# Dislike a recipe
@app.route('/dislike_recipe/<int:id>', methods=['POST'])
@login_required
def dislike_recipe(id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE recipes SET dislikes = dislikes + 1 WHERE id = %s", [id])
    mysql.connection.commit()
    cur.close()
    return jsonify(success=True)
# API Key (Consider moving this to a config file instead of hardcoding)
GEMINI_API_KEY = "AIzaSyA1CRQ7RqfGMspM7MXfnNuiUJXXm3zClZ8"

# Configure logging
logging.basicConfig(level=logging.INFO)

def get_gemini_response(user_input):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"parts": [{"text": user_input}]}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()  # Raise an error for HTTP status codes like 400/500

        response_json = response.json()
        return response_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response generated.")
    
    except requests.exceptions.Timeout:
        logging.error("Request timed out.")
        return "The AI service is taking too long to respond. Please try again."
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        return "Error communicating with the AI service."

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_response", methods=["POST"])
def chatbot_response():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"response": "Please enter a message."})

    bot_reply = get_gemini_response(user_message)
    return jsonify({"response": bot_reply})


if __name__ == '__main__':
    app.run(debug=True)