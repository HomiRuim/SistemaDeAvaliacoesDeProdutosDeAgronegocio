import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!
from flask import Flask, session
from src.routes.main import main_bp, carregar_dados_iniciais

# Criar aplicação Flask
app = Flask(__name__)
app.secret_key = 'sistema_recomendacao_2025'  # Necessário para sessões

# Registrar blueprints
app.register_blueprint(main_bp)

# Carregar dados iniciais
# Versão atualizada para Flask 2.0+
with app.app_context():
    carregar_dados_iniciais()

# Rota de teste
@app.route('/teste')
def teste():
    return 'API funcionando!'

# Iniciar aplicação
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
