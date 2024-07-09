# config.py

class Config:
    # Configurações para acesso ao MySQL
    MYSQL_HOST = 'localhost'  # Endereço do servidor MySQL
    MYSQL_USER = 'root'       # Usuário do MySQL
    MYSQL_PASSWORD = ''       # Senha do MySQL (substitua pela senha adequada)
    MYSQL_DB = 'meu_projeto'  # Nome do banco de dados no MySQL

    # Chave secreta para sessões do Flask (substitua por uma chave segura)
    SECRET_KEY = 'supersecretkey'
