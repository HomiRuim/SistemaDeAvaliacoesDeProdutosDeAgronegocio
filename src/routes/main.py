import pandas as pd
import folium
import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session as flask_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import init_db, Usuario, Produto, Associacao, Avaliacao, Compra
from recommenders import get_recommender

# Criar o blueprint para as rotas principais
main_bp = Blueprint('main', __name__)

# Inicializar banco de dados
db_session = init_db()

# Inicializar recomendadores
knn_recommender = None
svd_recommender = None

# Função para carregar dados iniciais
def carregar_dados_iniciais():
    global knn_recommender, svd_recommender
    
    try:
        # Inicializar recomendadores
        from recommenders import KNNRecommender, SVDRecommender
        
        print("Inicializando recomendadores...")
        knn_recommender = KNNRecommender(db_session)
        svd_recommender = SVDRecommender(db_session)
        
        # Preparar dados para os recomendadores
        print("Preparando dados para recomendadores...")
        knn_recommender.preparar_dados()
        svd_recommender.preparar_dados()
        
        # Treinar modelos
        print("Treinando modelos de recomendação...")
        knn_recommender.treinar()
        svd_recommender.treinar()
        
        print("Recomendadores inicializados com sucesso!")
        
    except Exception as e:
        print(f"Erro ao inicializar recomendadores: {e}")

# Rota principal
@main_bp.route('/')
def index():
    # Definir algoritmo padrão se não estiver na sessão
    if 'algoritmo' not in flask_session:
        flask_session['algoritmo'] = 'knn'
        
    return render_template('index.html', algoritmo=flask_session['algoritmo'])

# Rota para alternar algoritmo
@main_bp.route('/api/alternar_algoritmo', methods=['POST'])
def alternar_algoritmo():
    data = request.json
    algoritmo = data.get('algoritmo', 'knn')
    
    # Validar algoritmo
    if algoritmo not in ['knn', 'svd']:
        return jsonify({'error': 'Algoritmo inválido'}), 400
    
    # Salvar na sessão
    flask_session['algoritmo'] = algoritmo
    
    return jsonify({'success': True, 'algoritmo': algoritmo})

# Rota para obter dados do mapa
@main_bp.route('/api/mapa')
def get_mapa_data():
    # Obter localização do usuário (padrão: Brasília)
    user_lat = float(request.args.get('lat', -15.7939))
    user_lon = float(request.args.get('lon', -47.8828))
    
    # Obter associações do banco
    associacoes = db_session.query(Associacao).all()
    
    # Criar dados para o mapa
    mapa_data = []
    for assoc in associacoes:
        distancia = assoc.calcular_distancia(user_lat, user_lon)
        mapa_data.append({
            'id': assoc.id,
            'nome': assoc.nome,
            'regiao': assoc.regiao,
            'lat': assoc.lat,
            'lon': assoc.lon,
            'distancia': round(distancia, 2),
            'num_produtos': len(assoc.produtos)
        })
    
    return jsonify(mapa_data)

# Rota para obter produtos
@main_bp.route('/api/produtos')
def get_produtos():
    # Parâmetros de filtro
    associacao_id = request.args.get('associacao_id')
    apenas_organicos = request.args.get('organicos') == 'true'
    mes_atual = request.args.get('mes')
    if mes_atual:
        mes_atual = int(mes_atual)
    else:
        mes_atual = datetime.now().month
    
    # Consultar produtos do banco
    query = db_session.query(Produto)
    
    # Filtrar por associação se especificado
    if associacao_id:
        query = query.filter(Produto.associacao_id == int(associacao_id))
    
    # Filtrar por orgânicos se solicitado
    if apenas_organicos:
        query = query.filter(Produto.organico == True)
    
    produtos = query.all()
    
    # Filtrar por sazonalidade e formatar resposta
    produtos_filtrados = []
    for produto in produtos:
        # Filtrar por sazonalidade
        if not produto.esta_disponivel_no_mes(mes_atual):
            continue
            
        # Adicionar à lista de produtos filtrados
        produtos_filtrados.append({
            'id': produto.id,
            'nome': produto.nome,
            'categoria': produto.categoria,
            'preco': produto.preco,
            'associacao_id': produto.associacao_id,
            'disponivel': produto.disponivel,
            'organico': produto.organico,
            'meses_disponibilidade': produto.meses_disponibilidade,
            'media_avaliacoes': produto.media_avaliacoes()
        })
    
    return jsonify(produtos_filtrados)

# Rota para adicionar avaliação
@main_bp.route('/api/avaliar', methods=['POST'])
def avaliar_produto():
    data = request.json
    produto_id = data.get('produto_id')
    pontuacao = data.get('pontuacao')
    comentario = data.get('comentario', '')
    
    # Validar dados
    if not produto_id or not pontuacao:
        return jsonify({'error': 'Produto ID e pontuação são obrigatórios'}), 400
    
    try:
        # Converter para inteiros
        produto_id = int(produto_id)
        pontuacao = int(pontuacao)
        
        # Encontrar o produto
        produto = db_session.query(Produto).filter(Produto.id == produto_id).first()
        if not produto:
            return jsonify({'error': 'Produto não encontrado'}), 404
        
        # Adicionar avaliação (usando ID do primeiro usuário para simplificar)
        usuario_id = 1
        usuario = db_session.query(Usuario).filter(Usuario.id == usuario_id).first()
        
        if not usuario:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Verificar se já existe uma avaliação deste usuário para este produto
        avaliacao_existente = db_session.query(Avaliacao).filter(
            Avaliacao.usuario_id == usuario_id,
            Avaliacao.produto_id == produto_id
        ).first()
        
        if avaliacao_existente:
            # Atualizar avaliação existente
            avaliacao_existente.pontuacao = pontuacao
            avaliacao_existente.comentario = comentario
            avaliacao_existente.data = datetime.now()
        else:
            # Criar nova avaliação
            avaliacao = Avaliacao(
                usuario_id=usuario_id,
                produto_id=produto_id,
                pontuacao=pontuacao,
                comentario=comentario,
                data=datetime.now()
            )
            db_session.add(avaliacao)
        
        # Commit das alterações
        db_session.commit()
        
        # Forçar recarga dos dados e retreinamento dos modelos
        if knn_recommender:
            knn_recommender.preparar_dados()
            knn_recommender.treinar()
        
        if svd_recommender:
            svd_recommender.preparar_dados()
            svd_recommender.treinar()
        
        # Obter média atualizada
        db_session.refresh(produto)
        media_atualizada = produto.media_avaliacoes()
        
        return jsonify({
            'success': True, 
            'media': media_atualizada,
            'message': 'Avaliação salva com sucesso!'
        })
        
    except Exception as e:
        print(f"Erro ao salvar avaliação: {e}")
        db_session.rollback()
        return jsonify({'error': f'Erro ao salvar avaliação: {str(e)}'}), 500

# Rota para obter recomendações personalizadas
@main_bp.route('/api/recomendacoes')
def get_recomendacoes():
    # Obter localização do usuário
    user_lat = float(request.args.get('lat', -15.7939))
    user_lon = float(request.args.get('lon', -47.8828))
    
    # Obter mês atual para filtro de sazonalidade
    mes_atual = int(request.args.get('mes', datetime.now().month))
    
    # Obter algoritmo da sessão (padrão: KNN)
    algoritmo = flask_session.get('algoritmo', 'knn')
    
    # Obter recomendador apropriado
    if algoritmo == 'svd' and svd_recommender:
        recommender = svd_recommender
    else:
        recommender = knn_recommender
    
    # Verificar se o recomendador está inicializado
    if not recommender:
        return jsonify([])
    
    # Obter recomendações (usando ID do primeiro usuário para simplificar)
    usuario_id = 1
    recomendacoes = recommender.recomendar(usuario_id, user_lat, user_lon, mes_atual, limite=10)
    
    # Adicionar informação sobre o algoritmo usado
    for rec in recomendacoes:
        rec['algoritmo'] = algoritmo.upper()
    
    return jsonify(recomendacoes)

# Rota para obter informações sobre o algoritmo atual
@main_bp.route('/api/algoritmo')
def get_algoritmo():
    algoritmo = flask_session.get('algoritmo', 'knn')
    return jsonify({'algoritmo': algoritmo})

# Rota para depuração - listar todas as avaliações
@main_bp.route('/api/debug/avaliacoes')
def debug_avaliacoes():
    avaliacoes = db_session.query(Avaliacao).all()
    return jsonify([{
        'id': a.id,
        'usuario_id': a.usuario_id,
        'produto_id': a.produto_id,
        'pontuacao': a.pontuacao,
        'comentario': a.comentario,
        'data': a.data.strftime('%Y-%m-%d %H:%M:%S')
    } for a in avaliacoes])

# Rota para depuração - obter avaliações de um produto específico
@main_bp.route('/api/debug/produto/<int:produto_id>/avaliacoes')
def debug_produto_avaliacoes(produto_id):
    produto = db_session.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        return jsonify({'error': 'Produto não encontrado'}), 404
        
    return jsonify({
        'produto': {
            'id': produto.id,
            'nome': produto.nome,
            'media_avaliacoes': produto.media_avaliacoes()
        },
        'avaliacoes': [{
            'id': a.id,
            'usuario_id': a.usuario_id,
            'pontuacao': a.pontuacao,
            'comentario': a.comentario,
            'data': a.data.strftime('%Y-%m-%d %H:%M:%S')
        } for a in produto.avaliacoes]
    })
