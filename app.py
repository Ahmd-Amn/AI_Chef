import os
import re
import secrets
import ssl
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, g, jsonify, render_template, request, session
from google import genai
from google.genai.errors import ServerError
import pymysql
from pymysql.constants import CLIENT
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
app = Flask(__name__, static_folder='public/static')
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE') == '1',
    MAX_CONTENT_LENGTH=16 * 1024,
)


def db():
    if 'db' not in g:
        host = os.environ['MYSQL_HOST']
        g.db = pymysql.connect(
            host=host, port=int(os.environ.get('MYSQL_PORT', '4000')),
            user=os.environ['MYSQL_USER'], password=os.environ['MYSQL_PASSWORD'],
            database=os.environ['MYSQL_DATABASE'], charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor, connect_timeout=5,
            client_flag=CLIENT.FOUND_ROWS,
            ssl=ssl.create_default_context() if host not in ('localhost', '127.0.0.1') else None,
        )
    return g.db


def query(statement, params=()):
    cursor = db().cursor()
    cursor.execute(statement, params)
    return cursor


@app.teardown_appcontext
def close_db(_error):
    connection = g.pop('db', None)
    if connection:
        connection.close()


def init_db():
    with app.app_context():
        for statement in Path(__file__).with_name('schema.sql').read_text().split(';'):
            if statement.strip():
                query(statement)
        db().commit()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify(error='Please log in first.'), 401
        return view(*args, **kwargs)
    return wrapped


def csrf_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not secrets.compare_digest(request.headers.get('X-CSRF-Token', ''), session.get('csrf_token', '')):
            return jsonify(error='Invalid session token. Reload the page.'), 403
        return view(*args, **kwargs)
    return wrapped


def fields():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@app.route('/')
def home():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return render_template('index.html', csrf_token=session['csrf_token'], logged_in=bool(session.get('user_id')))


@app.post('/auth/register')
@csrf_required
def register():
    data = fields()
    email = str(data.get('email', '')).strip().lower()
    password = data.get('password', '')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or len(email) > 254 or not isinstance(password, str) or len(password) < 12 or len(password) > 128:
        return jsonify(error='Enter a valid email and a password of 12–128 characters.'), 400
    try:
        cursor = query('INSERT INTO users(email, password_hash) VALUES (%s, %s)',
                       (email, generate_password_hash(password)))
        db().commit()
    except pymysql.IntegrityError:
        db().rollback()
        return jsonify(error='This email is already registered.'), 409
    session.clear()
    session['user_id'] = cursor.lastrowid
    session['csrf_token'] = secrets.token_urlsafe(32)
    return jsonify(csrf_token=session['csrf_token']), 201


@app.post('/auth/login')
@csrf_required
def login():
    data = fields()
    email = str(data.get('email', '')).strip().lower()
    password = data.get('password', '')
    user = query('SELECT id, password_hash FROM users WHERE email = %s', (email,)).fetchone()
    if not user or not isinstance(password, str) or not check_password_hash(user['password_hash'], password):
        return jsonify(error='Invalid email or password.'), 401
    session.clear()
    session['user_id'] = user['id']
    session['csrf_token'] = secrets.token_urlsafe(32)
    return jsonify(csrf_token=session['csrf_token'])


@app.post('/auth/logout')
@login_required
@csrf_required
def logout():
    session.clear()
    return jsonify(ok=True)


@app.post('/api/recipe')
@csrf_required
def generate_recipe():
    ingredients = fields().get('ingredients', '')
    if not isinstance(ingredients, str) or not ingredients.strip() or len(ingredients) > 1000:
        return jsonify(error='Enter ingredients (up to 1000 characters).'), 400
    ingredients = ingredients.strip()
    try:
        prompt = f'''You are an expert, friendly chef. I have these ingredients: {ingredients}.
Suggest one recipe using these and a few basic pantry staples if needed.
Return Markdown with this format:
# Recipe Name
*Brief Description*
## Ingredients
- ingredient
## Instructions
1. Step
'''
        with genai.Client() as client:
            try:
                recipe = client.models.generate_content(model='gemini-3.8-flash', contents=prompt).text
            except ServerError as error:
                if error.code != 503:
                    raise
                recipe = client.models.generate_content(model='gemini-3.5-flash-lite', contents=prompt).text
        if not recipe or not recipe.strip():
            raise ValueError('Empty recipe')
    except Exception:
        app.logger.exception('Recipe generation failed')
        return jsonify(error='Could not make a recipe right now. Please try again.'), 502
    title = next((line.lstrip('# ').strip() for line in recipe.splitlines() if line.startswith('# ')), 'Untitled recipe')[:160]
    if 'user_id' not in session:
        return jsonify(recipe=recipe)
    cursor = query('INSERT INTO recipes(user_id, title, ingredients, recipe) VALUES (%s, %s, %s, %s)',
                   (session['user_id'], title, ingredients, recipe))
    db().commit()
    return jsonify(id=cursor.lastrowid, recipe=recipe)


@app.get('/api/recipes')
@login_required
def recipes():
    rows = query('SELECT id, title, ingredients, favorite, created_at FROM recipes WHERE user_id = %s ORDER BY id DESC',
                 (session['user_id'],)).fetchall()
    return jsonify(recipes=rows)


@app.get('/api/recipes/<int:recipe_id>')
@login_required
def recipe_detail(recipe_id):
    row = query('SELECT * FROM recipes WHERE id = %s AND user_id = %s',
                (recipe_id, session['user_id'])).fetchone()
    return jsonify(row) if row else (jsonify(error='Recipe not found.'), 404)


@app.route('/api/recipes/<int:recipe_id>/favorite', methods=['POST', 'DELETE'])
@login_required
@csrf_required
def favorite(recipe_id):
    cursor = query('UPDATE recipes SET favorite = %s WHERE id = %s AND user_id = %s',
                   (int(request.method == 'POST'), recipe_id, session['user_id']))
    db().commit()
    return jsonify(ok=True) if cursor.rowcount else (jsonify(error='Recipe not found.'), 404)


@app.get('/api/favorites')
@login_required
def favorites():
    rows = query('SELECT id, title, ingredients, favorite, created_at FROM recipes WHERE user_id = %s AND favorite = 1 ORDER BY id DESC',
                 (session['user_id'],)).fetchall()
    return jsonify(recipes=rows)


if __name__ == '__main__':
    app.run(debug=True)
