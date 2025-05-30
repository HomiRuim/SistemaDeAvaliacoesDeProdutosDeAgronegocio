class Associacao:
    def __init__(self, id, nome, regiao, lat, lon):
        self.id = id
        self.nome = nome
        self.regiao = regiao
        self.lat = lat
        self.lon = lon
        self.produtos = []
        
    def adicionar_produto(self, produto):
        """Adiciona um produto à associação"""
        self.produtos.append(produto)
        
    def calcular_distancia(self, user_lat, user_lon):
        """Calcula a distância entre a associação e o usuário"""
        from geopy.distance import geodesic
        return geodesic((self.lat, self.lon), (user_lat, user_lon)).km
