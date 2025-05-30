import numpy as np
from sklearn.neighbors import NearestNeighbors
from scipy.sparse.linalg import svds
from scipy.sparse import csr_matrix
import pandas as pd

class RecommenderSystem:
    """Classe base para sistemas de recomendação"""
    
    def __init__(self, session):
        self.session = session
        self.user_item_matrix = None
        self.produtos_df = None
        self.usuarios_df = None
        self.avaliacoes_df = None
        self.produto_indices = None
        self.usuario_indices = None
        
    def preparar_dados(self):
        """Prepara os dados para o sistema de recomendação"""
        from models import Usuario, Produto, Avaliacao, Associacao
        
        # Obter todos os dados necessários do banco
        usuarios = self.session.query(Usuario).all()
        produtos = self.session.query(Produto).all()
        avaliacoes = self.session.query(Avaliacao).all()
        associacoes = self.session.query(Associacao).all()
        
        # Criar DataFrames
        self.usuarios_df = pd.DataFrame([u.to_dict() for u in usuarios])
        self.produtos_df = pd.DataFrame([p.to_dict() for p in produtos])
        self.avaliacoes_df = pd.DataFrame([a.to_dict() for a in avaliacoes])
        self.associacoes_df = pd.DataFrame([a.to_dict() for a in associacoes])
        
        # Criar mapeamentos de índices
        self.produto_indices = {produto.id: i for i, produto in enumerate(produtos)}
        self.usuario_indices = {usuario.id: i for i, usuario in enumerate(usuarios)}
        
        # Criar matriz usuário-item
        n_usuarios = len(usuarios)
        n_produtos = len(produtos)
        
        # Inicializar matriz com zeros
        self.user_item_matrix = np.zeros((n_usuarios, n_produtos))
        
        # Preencher matriz com avaliações
        for avaliacao in avaliacoes:
            usuario_idx = self.usuario_indices.get(avaliacao.usuario_id)
            produto_idx = self.produto_indices.get(avaliacao.produto_id)
            
            if usuario_idx is not None and produto_idx is not None:
                self.user_item_matrix[usuario_idx, produto_idx] = avaliacao.pontuacao
        
        print(f"Matriz usuário-item criada com dimensões: {self.user_item_matrix.shape}")
        
    def recomendar(self, usuario_id, lat, lon, mes_atual, limite=10):
        """Método base para recomendação, deve ser implementado pelas subclasses"""
        raise NotImplementedError("Método deve ser implementado pela subclasse")
    
    def filtrar_por_distancia_e_sazonalidade(self, recomendacoes, usuario_id, lat, lon, mes_atual):
        """Filtra recomendações por distância e sazonalidade"""
        from models import Produto, Associacao
        
        # Obter produtos e associações
        produtos = {p.id: p for p in self.session.query(Produto).all()}
        associacoes = {a.id: a for a in self.session.query(Associacao).all()}
        
        # Filtrar recomendações
        recomendacoes_filtradas = []
        
        for produto_id, pontuacao in recomendacoes:
            produto = produtos.get(produto_id)
            
            if not produto:
                continue
                
            # Verificar sazonalidade
            if not produto.esta_disponivel_no_mes(mes_atual):
                continue
                
            # Verificar distância
            associacao = associacoes.get(produto.associacao_id)
            if not associacao:
                continue
                
            distancia = associacao.calcular_distancia(lat, lon)
            
            # Ajustar pontuação com base na distância
            pontuacao_ajustada = pontuacao - (distancia * 0.05)
            
            # Adicionar bônus para produtos orgânicos
            if produto.organico:
                pontuacao_ajustada += 1
                
            recomendacoes_filtradas.append({
                'id': produto.id,
                'nome': produto.nome,
                'categoria': produto.categoria,
                'preco': produto.preco,
                'associacao_id': produto.associacao_id,
                'associacao_nome': associacao.nome,
                'distancia': round(distancia, 2),
                'organico': produto.organico,
                'media_avaliacoes': produto.media_avaliacoes(),
                'pontuacao_recomendacao': round(pontuacao_ajustada, 2)
            })
        
        # Ordenar por pontuação ajustada
        recomendacoes_filtradas.sort(key=lambda x: x['pontuacao_recomendacao'], reverse=True)
        
        return recomendacoes_filtradas

class KNNRecommender(RecommenderSystem):
    """Sistema de recomendação baseado em KNN (k-Nearest Neighbors)"""
    
    def __init__(self, session, k=5):
        super().__init__(session)
        self.k = k
        self.model = None
        
    def treinar(self):
        """Treina o modelo KNN"""
        if self.user_item_matrix is None:
            self.preparar_dados()
            
        # Usar apenas linhas com pelo menos uma avaliação
        mask = np.sum(self.user_item_matrix, axis=1) > 0
        filtered_matrix = self.user_item_matrix[mask]
        
        # Treinar modelo KNN
        self.model = NearestNeighbors(metric='cosine', algorithm='brute', n_neighbors=self.k+1)
        self.model.fit(filtered_matrix)
        
        # Manter mapeamento de índices filtrados para índices originais
        self.filtered_indices = np.where(mask)[0]
        self.reverse_map = {i: self.filtered_indices[i] for i in range(len(self.filtered_indices))}
        
        print(f"Modelo KNN treinado com {len(self.filtered_indices)} usuários ativos")
        
    def recomendar(self, usuario_id, lat, lon, mes_atual, limite=10):
        """Recomenda produtos usando KNN"""
        if self.model is None:
            self.treinar()
            
        # Obter índice do usuário
        usuario_idx = self.usuario_indices.get(usuario_id)
        
        if usuario_idx is None:
            print(f"Usuário {usuario_id} não encontrado")
            return []
            
        # Verificar se o usuário está no conjunto filtrado
        if usuario_idx not in self.filtered_indices:
            print(f"Usuário {usuario_id} não tem avaliações suficientes para KNN")
            # Retornar recomendações baseadas em popularidade
            return self.recomendar_por_popularidade(usuario_id, lat, lon, mes_atual, limite)
            
        # Encontrar índice filtrado do usuário
        filtered_idx = np.where(self.filtered_indices == usuario_idx)[0][0]
        
        # Obter vizinhos mais próximos
        distances, indices = self.model.kneighbors(
            self.user_item_matrix[usuario_idx].reshape(1, -1), 
            n_neighbors=self.k+1
        )
        
        # Remover o próprio usuário (primeiro resultado)
        indices = indices.flatten()[1:]
        distances = distances.flatten()[1:]
        
        # Converter índices filtrados para índices originais
        neighbor_indices = [self.reverse_map[idx] for idx in indices]
        
        # Calcular pontuações de recomendação
        produto_scores = {}
        
        for neighbor_idx, distance in zip(neighbor_indices, distances):
            # Converter distância de similaridade para peso (mais próximo = maior peso)
            similarity = 1 - distance
            
            # Iterar sobre avaliações do vizinho
            for produto_idx, rating in enumerate(self.user_item_matrix[neighbor_idx]):
                if rating > 0:
                    # Verificar se o usuário já avaliou este produto
                    if self.user_item_matrix[usuario_idx, produto_idx] > 0:
                        continue
                        
                    # Obter ID real do produto
                    produto_id = None
                    for pid, idx in self.produto_indices.items():
                        if idx == produto_idx:
                            produto_id = pid
                            break
                            
                    if produto_id is None:
                        continue
                        
                    # Adicionar pontuação ponderada pela similaridade
                    if produto_id not in produto_scores:
                        produto_scores[produto_id] = 0
                        
                    produto_scores[produto_id] += rating * similarity
        
        # Ordenar produtos por pontuação
        recomendacoes = sorted(produto_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Filtrar por distância e sazonalidade
        return self.filtrar_por_distancia_e_sazonalidade(recomendacoes, usuario_id, lat, lon, mes_atual)[:limite]
    
    def recomendar_por_popularidade(self, usuario_id, lat, lon, mes_atual, limite=10):
        """Recomenda produtos baseado em popularidade (fallback)"""
        # Calcular média de avaliações por produto
        produto_ratings = {}
        
        for _, row in self.avaliacoes_df.iterrows():
            produto_id = row['produto_id']
            pontuacao = row['pontuacao']
            
            if produto_id not in produto_ratings:
                produto_ratings[produto_id] = []
                
            produto_ratings[produto_id].append(pontuacao)
        
        # Calcular média e número de avaliações
        produto_scores = {}
        for produto_id, ratings in produto_ratings.items():
            # Fórmula que considera tanto a média quanto a popularidade
            avg_rating = sum(ratings) / len(ratings)
            num_ratings = len(ratings)
            produto_scores[produto_id] = avg_rating * (1 + 0.1 * min(num_ratings, 10))  # Cap em 10 avaliações
        
        # Ordenar produtos por pontuação
        recomendacoes = sorted(produto_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Filtrar por distância e sazonalidade
        return self.filtrar_por_distancia_e_sazonalidade(recomendacoes, usuario_id, lat, lon, mes_atual)[:limite]

class SVDRecommender(RecommenderSystem):
    """Sistema de recomendação baseado em SVD (Singular Value Decomposition)"""
    
    def __init__(self, session, n_fatores=20):
        super().__init__(session)
        self.n_fatores = n_fatores
        self.user_features = None
        self.item_features = None
        self.item_bias = None
        self.user_bias = None
        self.global_bias = None
        
    def treinar(self):
        """Treina o modelo SVD"""
        if self.user_item_matrix is None:
            self.preparar_dados()
            
        # Calcular média global (ignorando zeros)
        ratings = self.user_item_matrix[self.user_item_matrix > 0]
        self.global_bias = np.mean(ratings) if len(ratings) > 0 else 0
        
        # Preencher valores ausentes com a média global
        normalized_matrix = np.copy(self.user_item_matrix)
        normalized_matrix[normalized_matrix == 0] = self.global_bias
        
        # Calcular SVD
        u, sigma, vt = svds(normalized_matrix, k=min(self.n_fatores, min(normalized_matrix.shape)-1))
        
        # Ordenar componentes por valores singulares
        idx = np.argsort(-sigma)
        sigma = sigma[idx]
        u = u[:, idx]
        vt = vt[idx, :]
        
        # Calcular matrizes de características
        self.user_features = u
        self.item_features = vt.T
        
        # Calcular bias de usuários e itens
        self.user_bias = np.mean(normalized_matrix, axis=1) - self.global_bias
        self.item_bias = np.mean(normalized_matrix, axis=0) - self.global_bias
        
        print(f"Modelo SVD treinado com {self.n_fatores} fatores")
        
    def recomendar(self, usuario_id, lat, lon, mes_atual, limite=10):
        """Recomenda produtos usando SVD"""
        if self.user_features is None:
            self.treinar()
            
        # Obter índice do usuário
        usuario_idx = self.usuario_indices.get(usuario_id)
        
        if usuario_idx is None:
            print(f"Usuário {usuario_id} não encontrado")
            return []
            
        # Calcular pontuações previstas para todos os produtos
        user_pred = self.global_bias + self.user_bias[usuario_idx]
        user_pred = user_pred + np.dot(self.user_features[usuario_idx], self.item_features.T)
        
        # Criar lista de (produto_id, pontuação)
        produto_scores = {}
        
        for produto_id, produto_idx in self.produto_indices.items():
            # Verificar se o usuário já avaliou este produto
            if self.user_item_matrix[usuario_idx, produto_idx] > 0:
                continue
                
            # Adicionar pontuação prevista
            produto_scores[produto_id] = user_pred[produto_idx]
        
        # Ordenar produtos por pontuação
        recomendacoes = sorted(produto_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Filtrar por distância e sazonalidade
        return self.filtrar_por_distancia_e_sazonalidade(recomendacoes, usuario_id, lat, lon, mes_atual)[:limite]

# Função para obter o recomendador apropriado
def get_recommender(session, algoritmo='knn'):
    """Retorna o recomendador apropriado com base no algoritmo escolhido"""
    if algoritmo.lower() == 'svd':
        return SVDRecommender(session)
    else:  # default para KNN
        return KNNRecommender(session)

# Teste dos recomendadores
if __name__ == "__main__":
    from models import init_db
    
    # Inicializar banco de dados
    session = init_db()
    
    # Testar KNN
    print("\nTestando recomendador KNN...")
    knn = KNNRecommender(session)
    knn.preparar_dados()
    knn.treinar()
    
    # Testar recomendação para um usuário
    usuario_id = 1
    lat = -15.7939
    lon = -47.8828
    mes_atual = 5  # Maio
    
    recomendacoes_knn = knn.recomendar(usuario_id, lat, lon, mes_atual)
    print(f"Top 5 recomendações KNN para usuário {usuario_id}:")
    for i, rec in enumerate(recomendacoes_knn[:5]):
        print(f"{i+1}. {rec['nome']} - Pontuação: {rec['pontuacao_recomendacao']}")
    
    # Testar SVD
    print("\nTestando recomendador SVD...")
    svd = SVDRecommender(session)
    svd.preparar_dados()
    svd.treinar()
    
    recomendacoes_svd = svd.recomendar(usuario_id, lat, lon, mes_atual)
    print(f"Top 5 recomendações SVD para usuário {usuario_id}:")
    for i, rec in enumerate(recomendacoes_svd[:5]):
        print(f"{i+1}. {rec['nome']} - Pontuação: {rec['pontuacao_recomendacao']}")
