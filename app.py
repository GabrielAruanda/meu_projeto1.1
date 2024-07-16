from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL  # Importa a extensão MySQL para Flask
from config import Config  # Importa as configurações do arquivo Config.py
import random
import string
from werkzeug.security import generate_password_hash, check_password_hash  # Importa funções de hash de senha

# Cria uma instância do aplicativo Flask
app = Flask(__name__)
# Configura o aplicativo Flask com as configurações do arquivo Config.py
app.config.from_object(Config)
# Define a chave secreta do aplicativo para uso com sessões
app.secret_key = Config.SECRET_KEY

# Cria uma instância da conexão MySQL usando as configurações do Flask
mysql = MySQL(app)

# Função para gerar uma URL curta baseada na URL original
def generate_short_url(original_url):
    url_name = original_url.rstrip('/').rsplit('/', 1)[-1][:3]  # Extrai parte da URL para formar o nome
    random_part = ''.join(random.choices(string.digits, k=3))  # Gera parte aleatória da URL curta
    return f"web-encurt.{url_name}{random_part}"  # Retorna a URL curta gerada

# Rota para redirecionar para a URL original a partir da URL curta
@app.route('/<short_url>')
def redirect_to_url(short_url):
    cur = mysql.connection.cursor()  # Cria um cursor para a conexão MySQL
    cur.execute("SELECT original_url FROM urls WHERE short_url = %s", (short_url,))
    result = cur.fetchone()  # Obtém a URL original correspondente à URL curta
    if result:
        cur.execute("UPDATE urls SET click_count = click_count + 1 WHERE short_url = %s", (short_url,))
        local_ip = request.remote_addr  # Obtém o endereço IP do cliente
        user_id = session.get('user_id')  # Obtém o ID do usuário da sessão (se existir)
        if user_id:
            cur.execute("""
                INSERT INTO clicks (url_id, user_id, local_ip_address)
                VALUES ((SELECT id FROM urls WHERE short_url = %s), %s, %s)
            """, (short_url, user_id, local_ip))  # Insere registro de clique com ID do usuário
        else:
            cur.execute("""
                INSERT INTO clicks (url_id, local_ip_address)
                VALUES ((SELECT id FROM urls WHERE short_url = %s), %s)
            """, (short_url, local_ip))  # Insere registro de clique sem ID de usuário
        
        mysql.connection.commit()  # Confirma as alterações no banco de dados
        cur.close()  # Fecha o cursor
        return redirect(result[0])  # Redireciona para a URL original
    else:
        flash('URL encurtada não encontrada.', 'danger')  # Exibe mensagem de erro
        return redirect(url_for('index'))  # Redireciona para a página inicial

# Rota para a página inicial
@app.route('/')
def index():
    return render_template('index.html')  # Renderiza o template index.html

# Rota para a página principal após o login
@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'logged_in' in session:  # Verifica se o usuário está logado na sessão
        user_id = session['user_id']  # Obtém o ID do usuário da sessão
        username = session['username']  # Obtém o nome de usuário da sessão
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
        urls = cur.fetchall()  # Obtém todas as URLs encurtadas pelo usuário
        cur.close()

        urls = sorted(urls, key=lambda x: x[3], reverse=True)  # Ordena as URLs por contagem de cliques
        
        return render_template('home.html', username=username, logged_in=True, urls=urls)  # Renderiza o template home.html com dados do usuário
    else:
        flash('Você precisa estar logado para acessar esta página.', 'danger')
        return redirect(url_for('index'))  # Redireciona para a página inicial se não estiver logado

# Rota para a página de recursos do aplicativo
@app.route('/features')
def features():
    return render_template('features.html')  # Renderiza o template features.html

# Rota para a página de contato
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        flash('Mensagem enviada com sucesso!', 'success')
        return redirect(url_for('contact'))  # Redireciona para a página de contato após enviar a mensagem
    return render_template('contact.html')  # Renderiza o template contact.html

# Rota para a página de registro de novo usuário
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        hashed_password = generate_password_hash(password)  # Gera hash da senha
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        mysql.connection.commit()
        cur.close()
        flash('Cadastro realizado com sucesso! Faça login agora.', 'success')
        return redirect(url_for('login'))  # Redireciona para a página de login após o registro
    return render_template('register.html')  # Renderiza o template register.html

# Rota para a página de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        if user and check_password_hash(user[2], password):  # Verifica se o usuário existe e a senha está correta
            session['logged_in'] = True  # Define o login como True na sessão
            session['username'] = username  # Armazena o nome de usuário na sessão
            session['user_id'] = user[0]  # Armazena o ID do usuário na sessão
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('home'))  # Redireciona para a página principal após o login
        else:
            flash('Usuário ou senha incorretos.', 'danger')
    return render_template('login.html')  # Renderiza o template login.html

# Rota para efetuar logout do usuário
@app.route('/logout')
def logout():
    session.pop('logged_in', None)  # Remove o status de logado da sessão
    session.pop('username', None)  # Remove o nome de usuário da sessão
    session.pop('user_id', None)  # Remove o ID do usuário da sessão
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('index'))  # Redireciona para a página inicial após o logout

# Rota para a página de política de privacidade
@app.route('/privacy')
def privacy():
    return render_template('privacy.html')  # Renderiza o template privacy.html

# Rota para a página de termos de uso
@app.route('/terms')
def terms():
    return render_template('terms.html')  # Renderiza o template terms.html

# Rota para renderizar a página do gráfico
@app.route('/grafic')
def mostrar_grafico():
    return render_template('grafic.html')  # Renderiza o template grafic.html

# Rota para obter os dados de cliques em formato JSON
@app.route('/get_click_data')
def get_click_data():
    if 'logged_in' in session:  # Verifica se o usuário está logado na sessão
        user_id = session['user_id']  # Obtém o ID do usuário da sessão
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT urls.original_url, COUNT(clicks.id) as click_count
            FROM clicks
            JOIN urls ON clicks.url_id = urls.id
            WHERE urls.user_id = %s
            GROUP BY urls.original_url
        """, (user_id,))
        click_data = cur.fetchall()  # Obtém os dados de cliques para URLs do usuário
        cur.close()
        return jsonify({'click_data': click_data})  # Retorna os dados de cliques em formato JSON
    else:
        return jsonify({'click_data': []})  # Retorna uma lista vazia se o usuário não estiver logado

# Executa o aplicativo Flask
if __name__ == '__main__':
    app.run(debug=True)
