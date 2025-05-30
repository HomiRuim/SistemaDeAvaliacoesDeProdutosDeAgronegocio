from datetime import datetime

class Usuario:
    def __init__(self, id, nome, email, lat=None, lon=None):
        self.id = id
        self.nome = nome
        self.email = email
        self.lat = lat
        self.lon = lon
        self.preferencias = {
            "distancia_maxima": 20,  # km
            "apenas_organicos": False,
            "produtos_favoritos": [],
            "associacoes_favoritas": []
        }
        self.avaliacoes = []  # Lista de avaliações feitas pelo usuário
        
    def definir_localizacao(self, lat, lon):
        """Define a localização do usuário"""
        self.lat = lat
        self.lon = lon
        
    def adicionar_avaliacao(self, produto_id, pontuacao, comentario=""):
        """Adiciona uma avaliação feita pelo usuário"""
        from datetime import datetime
        avaliacao = {
            "produto_id": produto_id,
            "pontuacao": pontuacao,
            "comentario": comentario,
            "data": datetime.now()
        }
        self.avaliacoes.append(avaliacao)
        
    def atualizar_preferencias(self, distancia_maxima=None, apenas_organicos=None, 
                              produtos_favoritos=None, associacoes_favoritas=None):
        """Atualiza as preferências do usuário"""
        if distancia_maxima is not None:
            self.preferencias["distancia_maxima"] = distancia_maxima
        if apenas_organicos is not None:
            self.preferencias["apenas_organicos"] = apenas_organicos
        if produtos_favoritos is not None:
            self.preferencias["produtos_favoritos"] = produtos_favoritos
        if associacoes_favoritas is not None:
            self.preferencias["associacoes_favoritas"] = associacoes_favoritas
