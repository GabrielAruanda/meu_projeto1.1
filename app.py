from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from config import Config
import random
import string
import hashlib  # Importa a biblioteca hashlib para codificar a senha
from werkzeug.security import generate_password_hash, check_password_hash  # Importa funções de hash do Werkzeug
import requests  # Importa a biblioteca requests para obter o IP público do usuário

# Configuração inicial do Flask
app = Flask(__name__)
app.config.from_object(Config)  # Carrega as configurações do arquivo Config
app.secret_key = Config.SECRET_KEY  # Define a chave secreta para sessões

# Configuração do MySQL
mysql = MySQL(app)

# Função para gerar URL curta aleatória
def generate_short_url(original_url):
    # Extrai os primeiros 3 caracteres do final da URL original
    url_name = original_url.rstrip('/').rsplit('/', 1)[-1][:3]
    # Gera uma parte aleatória com 3 números
    random_part = ''.join(random.choices(string.digits, k=3))
    # Retorna a URL curta formada pela combinação dos elementos
    return f"{url_name}{random_part}"

# Função para obter o endereço IP público do usuário
def get_public_ip():
    try:
        response = requests.get('https://api64.ipify.org?format=json')
        data = response.json()
        return data['ip']
    except Exception as e:
        print(f"Erro ao obter IP público: {e}")
        return None

# Rota para redirecionar URL encurtada
@app.route('/<short_url>')
def redirect_to_url(short_url):
    cur = mysql.connection.cursor()
    # Busca a URL original correspondente à URL curta fornecida
    cur.execute("SELECT original_url FROM urls WHERE short_url = %s", (short_url,))
    result = cur.fetchone()
    if result:
        # Incrementa o contador de cliques da URL
        cur.execute("UPDATE urls SET click_count = click_count + 1 WHERE short_url = %s", (short_url,))
        
        # Obtém o endereço IP local do usuário
        local_ip = request.remote_addr
        
        # Obtém e salva o endereço IP público do usuário
        public_ip = get_public_ip()
        
        # Registra o clique na tabela de clicks associando ao usuário logado, se houver
        user_id = session.get('user_id')
        if user_id:
            cur.execute("""
                INSERT INTO clicks (url_id, user_id, local_ip_address, public_ip_address)
                VALUES ((SELECT id FROM urls WHERE short_url = %s), %s, %s, %s)
            """, (short_url, user_id, local_ip, public_ip))
        else:
            cur.execute("""
                INSERT INTO clicks (url_id, local_ip_address, public_ip_address)
                VALUES ((SELECT id FROM urls WHERE short_url = %s), %s, %s)
            """, (short_url, local_ip, public_ip))
        
        mysql.connection.commit()
        cur.close()
        # Redireciona para a URL original
        return redirect(result[0])
    else:
        # Exibe mensagem de erro se a URL curta não for encontrada
        flash('URL encurtada não encontrada.', 'danger')
        return redirect(url_for('index'))

# Rota para a página inicial
@app.route('/')
def index():
    return render_template('index.html')

# Rota para a página home
@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'logged_in' in session:  # Verifica se o usuário está logado na sessão
        user_id = session['user_id']  # Obtém o ID do usuário da sessão
        username = session['username']  # Obtém o nome de usuário da sessão
        if request.method == 'POST':
            original_url = request.form['original_url']
            cur = mysql.connection.cursor()
            try:
                # Verifica se a URL original já foi encurtada pelo usuário
                cur.execute("SELECT short_url FROM urls WHERE original_url = %s AND user_id = %s", (original_url, user_id))
                existing_short_url = cur.fetchone()
                if existing_short_url:
                    # Se já existe, retorna a URL curta correspondente
                    short_url = existing_short_url[0]
                    flash(f'URL encurtada já existente: {request.url_root}{short_url}', 'info')
                else:
                    # Senão, gera uma nova URL curta e a insere no banco de dados
                    short_url = generate_short_url(original_url)
                    cur.execute("""
                        INSERT INTO urls (original_url, short_url, user_id)
                        VALUES (%s, %s, %s)
                    """, (original_url, short_url, user_id))
                    mysql.connection.commit()
                    flash(f'URL encurtada: {request.url_root}{short_url}', 'success')
            except Exception as e:
                # Exibe mensagem de erro se ocorrer algum problema na inserção
                flash(f'Erro ao encurtar a URL: {e}', 'danger')
            cur.close()
        
        # Obtém todas as URLs encurtadas do usuário logado
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, original_url, short_url, click_count FROM urls WHERE user_id = %s", (user_id,))
        urls = cur.fetchall()
        cur.close()

        # Ordena as URLs pelo número de cliques em ordem decrescente
        urls = sorted(urls, key=lambda x: x[3], reverse=True)
        
        # Renderiza a página home com as URLs do usuário
        return render_template('home.html', username=username, logged_in=True, urls=urls)
    else:
        # Se o usuário não está logado, redireciona para a página inicial com mensagem de aviso
        flash('Você precisa estar logado para acessar esta página.', 'danger')
        return redirect(url_for('index'))

# Rotas para outras páginas estáticas
@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        flash('Mensagem enviada com sucesso!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

# Rota para registro de usuário
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Codifica a senha antes de salvar no banco de dados
        hashed_password = generate_password_hash(password)
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        mysql.connection.commit()
        cur.close()
        flash('Cadastro realizado com sucesso! Faça login agora.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# Rota para login de usuário
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        if user and check_password_hash(user[2], password):  # Verifica a senha hashada
            # Se o login for bem-sucedido, define as variáveis de sessão
            session['logged_in'] = True
            session['username'] = username
            session['user_id'] = user[0]  # ID do usuário na posição 0 da tupla
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('home'))  # Redireciona para a página home
        else:
            # Exibe mensagem de erro se o login falhar
            flash('Usuário ou senha incorretos.', 'danger')
    return render_template('login.html')

# Rota para logout
@app.route('/logout')
def logout():
    # Remove as variáveis de sessão ao fazer logout
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

# Rotas para as páginas de contratação dos planos, passando o nome do plano na URL
@app.route('/contratar_form/<plano>', methods=['GET', 'POST'])
def contratar_form(plano):
    if request.method == 'POST':
        # Processa os dados do formulário de contratação
        flash(f'Contratação do {plano} realizada com sucesso!', 'success')
        return redirect(url_for('pagina_preco', plano=plano))
    return render_template('contratar_form.html', plano=plano)



# Roda o aplicativo Flask
if __name__ == '__main__':
    app.run(debug=True)
