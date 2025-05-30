from datetime import datetime

class Produto:
    def __init__(self, id, nome, categoria, preco, associacao_id, disponivel=True, organico=False):
        self.id = id
        self.nome = nome
        self.categoria = categoria
        self.preco = preco
        self.associacao_id = associacao_id
        self.disponivel = disponivel
        self.organico = organico
        self.avaliacoes = []
        self.meses_disponibilidade = []  # Lista de meses em que o produto está disponível (1-12)
        
    def adicionar_avaliacao(self, usuario_id, pontuacao, comentario=""):
        """Adiciona uma avaliação ao produto"""
        avaliacao = {
            "usuario_id": usuario_id,
            "pontuacao": pontuacao,
            "comentario": comentario,
            "data": datetime.now()
        }
        self.avaliacoes.append(avaliacao)
        
    def media_avaliacoes(self):
        """Retorna a média das avaliações do produto"""
        if not self.avaliacoes:
            return 0
        return sum(a["pontuacao"] for a in self.avaliacoes) / len(self.avaliacoes)
    
    def definir_sazonalidade(self, meses):
        """Define os meses em que o produto está disponível"""
        self.meses_disponibilidade = meses
        
    def esta_disponivel_no_mes(self, mes):
        """Verifica se o produto está disponível no mês especificado"""
        if not self.meses_disponibilidade:  # Se não tiver sazonalidade definida, está sempre disponível
            return True
        return mes in self.meses_disponibilidade
