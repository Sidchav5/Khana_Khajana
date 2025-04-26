from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import base64
import pymysql
import requests
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)

# Flask config
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'

# MySQL config
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'Siddhesh@5'
DB_NAME = 'khana_khajana'

# DB connection function
def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.Cursor
    )

# Login manager
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
    conn.close()
    if user:
        return User(id=user[0], username=user[1], email=user[2], password=user[3])
    return None

@app.route('/')
def home():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, photo, likes, dislikes FROM recipes ORDER BY likes DESC LIMIT 6")
        top_liked_recipes = cur.fetchall()
    conn.close()
    top_liked_recipes_with_photos = []
    for recipe in top_liked_recipes:
        photo_data_url = f"data:image/jpeg;base64,{recipe[2]}"
        top_liked_recipes_with_photos.append({
            'id': recipe[0], 'name': recipe[1], 'photo_data_url': photo_data_url,
            'likes': recipe[3], 'dislikes': recipe[4]
        })
    return render_template('index.html', top_liked_recipes=top_liked_recipes_with_photos)

@app.route('/post_it')
@login_required
def post_it():
    return render_template('post_it.html')

@app.route('/submit', methods=['POST'])
@login_required
def submit():
    if request.method == 'POST':
        data = request.form
        photo = request.files['photo']
        if photo and allowed_file(photo.filename):
            photo_base64 = base64.b64encode(photo.read()).decode('utf-8')
        else:
            flash('Invalid image file!', 'danger')
            return redirect(url_for('post_it'))

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO recipes (type, name, description, ingredients, time, instructions, photo, user_id, writer, comments)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['type'], data['name'], data['description'], data['ingredients'], data['time'],
                data['instructions'], photo_base64, current_user.id, data['writer'], ""
            ))
            conn.commit()
        conn.close()

        flash('Recipe submitted successfully!', 'success')
        return redirect(url_for('post_it'))

@app.route('/blogs')
def blogs():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM recipes")
        recipes = cur.fetchall()
        cur.execute("SELECT name, photo, likes, dislikes FROM recipes ORDER BY likes DESC LIMIT 5")
        top_liked = cur.fetchall()
    conn.close()

    recipes_with_photos = []
    for r in recipes:
        recipes_with_photos.append({
            'id': r[0], 'type': r[1], 'name': r[2], 'description': r[3], 'ingredients': r[4],
            'time': r[5], 'instructions': r[6], 'photo_data_url': f"data:image/jpeg;base64,{r[7]}",
            'user_id': r[8], 'likes': r[9], 'dislikes': r[10], 'writer': r[11], 'comments': r[12]
        })

    top_liked_recipes_with_photos = [{
        'name': r[0], 'photo_data_url': f"data:image/jpeg;base64,{r[1]}", 'likes': r[2], 'dislikes': r[3]
    } for r in top_liked]

    return render_template('blog.html', recipes=recipes_with_photos, top_liked_recipes=top_liked_recipes_with_photos)
@app.route('/search')
def search():
    query = request.args.get('query', '').strip()
    connection = get_db_connection()
    with connection.cursor() as cursor:
        if query:
            sql = """
                SELECT * FROM recipes
                WHERE name LIKE %s OR writer LIKE %s
                ORDER BY id DESC
            """
            like_pattern = f"%{query}%"
            cursor.execute(sql, (like_pattern, like_pattern))
        else:
            sql = "SELECT * FROM recipes ORDER BY id DESC"
            cursor.execute(sql)
        recipes = cursor.fetchall()
    connection.close()

    # Convert each tuple into a dictionary for the template
    recipes_with_photos = []
    for r in recipes:
        recipes_with_photos.append({
            'id': r[0],
            'type': r[1],
            'name': r[2],
            'description': r[3],
            'ingredients': r[4],
            'time': r[5],
            'instructions': r[6],
            'photo_data_url': f"data:image/jpeg;base64,{r[7]}",
            'user_id': r[8],
            'likes': r[9],
            'dislikes': r[10],
            'writer': r[11],
            'comments': r[12]
        })

    return render_template('blog.html', recipes=recipes_with_photos)


@app.route('/add_comment/<int:id>', methods=['POST'])
@login_required
def add_comment(id):
    comment = request.form['comment']
    if not comment:
        flash('Comment cannot be empty.', 'danger')
        return redirect(url_for('recipe_detail', id=id))

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT comments FROM recipes WHERE id = %s", (id,))
        result = cur.fetchone()  # ✅ Fetch once
        existing = result[0] if result and result[0] else ""  # ✅ Safe check
        updated_comments = existing + f"{current_user.username}: {comment}\n"

        cur.execute("UPDATE recipes SET comments = %s WHERE id = %s", (updated_comments, id))
        conn.commit()

    conn.close()
    flash('Comment added!', 'success')
    return redirect(url_for('recipe_detail', id=id))


@app.route('/recipe/<int:id>')
def recipe_detail(id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM recipes WHERE id = %s", (id,))
        recipe = cur.fetchone()
    conn.close()
    if recipe:
        photo_data_url = f"data:image/jpeg;base64,{recipe[7]}"
        return render_template('recipe_detail.html', recipe=recipe, photo_data_url=photo_data_url)
    else:
        flash('Recipe not found!', 'danger')
        return redirect(url_for('blogs'))

@app.route('/delete_recipe/<int:id>', methods=['POST'])
@login_required
def delete_recipe(id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM recipes WHERE id = %s", (id,))
        recipe = cur.fetchone()
        if not recipe:
            return jsonify({'success': False, 'message': 'Recipe not found'}), 404
        if recipe[0] != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        cur.execute("DELETE FROM recipes WHERE id = %s", (id,))
        conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Recipe deleted'}), 200

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.form
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s OR email = %s", (data['username'], data['email']))
            if cur.fetchone():
                flash('Username or email already exists!', 'danger')
                return redirect(url_for('signup'))
            cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (data['username'], data['email'], data['password']))
            conn.commit()
        conn.close()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (data['email'],))
            user = cur.fetchone()
        conn.close()
        if user and user[3] == data['password']:
            user_obj = User(id=user[0], username=user[1], email=user[2], password=user[3])
            login_user(user_obj)
            flash('Logged in!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'success')
    return redirect(url_for('home'))

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/like_recipe/<int:id>', methods=['POST'])
@login_required
def like_recipe(id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE recipes SET likes = likes + 1 WHERE id = %s", (id,))
        conn.commit()
    conn.close()
    return jsonify(success=True)

@app.route('/dislike_recipe/<int:id>', methods=['POST'])
@login_required
def dislike_recipe(id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE recipes SET dislikes = dislikes + 1 WHERE id = %s", (id,))
        conn.commit()
    conn.close()
    return jsonify(success=True)

# AI section
GEMINI_API_KEY = "AIzaSyA1CRQ7RqfGMspM7MXfnNuiUJXXm3zClZ8"
logging.basicConfig(level=logging.INFO)

def get_gemini_response(user_input):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": user_input}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response.")
    except requests.exceptions.Timeout:
        return "AI is taking too long to respond. Try again."
    except Exception as e:
        logging.error(e)
        return "AI service error."

def is_recipe_query(text):
    keywords = ["recipe", "ingredients", "cook", "dish", "prepare", "food", "How to make"]
    return any(k in text.lower() for k in keywords)

@app.route('/get_response', methods=['POST'])
def chatbot_response():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"response": "Please enter a message."})
    if not is_recipe_query(user_message):
        return jsonify({"response": "I can only answer recipe-related questions."})
    reply = get_gemini_response(user_message)
    return jsonify({"response": reply})

if __name__ == '__main__':
    app.run(debug=True)
