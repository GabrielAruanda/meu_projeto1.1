from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from config import Config
import random
import string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

mysql = MySQL(app)

def generate_short_url(original_url):
    url_name = original_url.rstrip('/').rsplit('/', 1)[-1][:3]
    random_part = ''.join(random.choices(string.digits, k=3))
    return f"web-encurt.{url_name}{random_part}"

@app.route('/<short_url>')
def redirect_to_url(short_url):
    cur = mysql.connection.cursor()
    cur.execute("SELECT original_url FROM urls WHERE short_url = %s", (short_url,))
    result = cur.fetchone()
    if result:
        cur.execute("UPDATE urls SET click_count = click_count + 1 WHERE short_url = %s", (short_url,))
        local_ip = request.remote_addr
        user_id = session.get('user_id')
        if user_id:
            cur.execute("""
                INSERT INTO clicks (url_id, user_id, local_ip_address)
                VALUES ((SELECT id FROM urls WHERE short_url = %s), %s, %s)
            """, (short_url, user_id, local_ip))
        else:
            cur.execute("""
                INSERT INTO clicks (url_id, local_ip_address)
                VALUES ((SELECT id FROM urls WHERE short_url = %s), %s)
            """, (short_url, local_ip))
        
        mysql.connection.commit()
        cur.close()
        return redirect(result[0])
    else:
        flash('URL encurtada não encontrada.', 'danger')
        return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'logged_in' in session:
        user_id = session['user_id']
        username = session['username']
        if request.method == 'POST':
            original_url = request.form['original_url']
            cur = mysql.connection.cursor()
            try:
                cur.execute("SELECT short_url FROM urls WHERE original_url = %s AND user_id = %s", (original_url, user_id))
                existing_short_url = cur.fetchone()
                if existing_short_url:
                    short_url = existing_short_url[0]
                    flash(f'URL encurtada já existente: {request.url_root}{short_url}', 'info')
                else:
                    short_url = generate_short_url(original_url)
                    cur.execute("""
                        INSERT INTO urls (original_url, short_url, user_id)
                        VALUES (%s, %s, %s)
                    """, (original_url, short_url, user_id))
                    mysql.connection.commit()
                    flash(f'URL encurtada: {request.url_root}{short_url}', 'success')
            except Exception as e:
                flash(f'Erro ao encurtar a URL: {e}', 'danger')
            cur.close()
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, original_url, short_url, click_count FROM urls WHERE user_id = %s", (user_id,))
        urls = cur.fetchall()
        cur.close()

        urls = sorted(urls, key=lambda x: x[3], reverse=True)
        
        return render_template('home.html', username=username, logged_in=True, urls=urls)
    else:
        flash('Você precisa estar logado para acessar esta página.', 'danger')
        return redirect(url_for('index'))

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        flash('Mensagem enviada com sucesso!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        hashed_password = generate_password_hash(password)
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        mysql.connection.commit()
        cur.close()
        flash('Cadastro realizado com sucesso! Faça login agora.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        if user and check_password_hash(user[2], password):
            session['logged_in'] = True
            session['username'] = username
            session['user_id'] = user[0]
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Usuário ou senha incorretos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('user_id', None)
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('index'))

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')



# Rota para renderizar a página do gráfico
@app.route('/grafic')
def mostrar_grafico():
    return render_template('grafic.html')

# Rota para obter os dados de cliques
@app.route('/get_click_data')
def get_click_data():
    if 'logged_in' in session:
        user_id = session['user_id']
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT urls.original_url, COUNT(clicks.id) as click_count
            FROM clicks
            JOIN urls ON clicks.url_id = urls.id
            WHERE urls.user_id = %s
            GROUP BY urls.original_url
        """, (user_id,))
        click_data = cur.fetchall()
        cur.close()
        return jsonify({'click_data': click_data})
    else:
        return jsonify({'click_data': []})

if __name__ == '__main__':
    app.run(debug=True)
