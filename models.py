from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Table, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import json
from datetime import datetime

Base = declarative_base()

# Tabela de associação para produtos favoritos
usuario_produto_favorito = Table(
    'usuario_produto_favorito', 
    Base.metadata,
    Column('usuario_id', Integer, ForeignKey('usuarios.id')),
    Column('produto_id', Integer, ForeignKey('produtos.id'))
)

# Tabela de associação para associações favoritas
usuario_associacao_favorita = Table(
    'usuario_associacao_favorita', 
    Base.metadata,
    Column('usuario_id', Integer, ForeignKey('usuarios.id')),
    Column('associacao_id', Integer, ForeignKey('associacoes.id'))
)

# Tabela de associação para produtos em compras
compra_produto = Table(
    'compra_produto', 
    Base.metadata,
    Column('compra_id', Integer, ForeignKey('compras.id')),
    Column('produto_id', Integer, ForeignKey('produtos.id'))
)

class Usuario(Base):
    __tablename__ = 'usuarios'
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    lat = Column(Float)
    lon = Column(Float)
    distancia_maxima = Column(Integer, default=20)
    apenas_organicos = Column(Boolean, default=False)
    
    # Relacionamentos
    avaliacoes = relationship("Avaliacao", back_populates="usuario")
    compras = relationship("Compra", back_populates="usuario")
    produtos_favoritos = relationship("Produto", secondary=usuario_produto_favorito)
    associacoes_favoritas = relationship("Associacao", secondary=usuario_associacao_favorita)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'lat': self.lat,
            'lon': self.lon,
            'distancia_maxima': self.distancia_maxima,
            'apenas_organicos': self.apenas_organicos,
            'produtos_favoritos': [p.id for p in self.produtos_favoritos],
            'associacoes_favoritas': [a.id for a in self.associacoes_favoritas]
        }

class Associacao(Base):
    __tablename__ = 'associacoes'
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    regiao = Column(String(100), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    
    # Relacionamentos
    produtos = relationship("Produto", back_populates="associacao")
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'regiao': self.regiao,
            'lat': self.lat,
            'lon': self.lon,
            'num_produtos': len(self.produtos)
        }
    
    def calcular_distancia(self, user_lat, user_lon):
        """Calcula a distância entre a associação e o usuário"""
        from geopy.distance import geodesic
        return geodesic((self.lat, self.lon), (user_lat, user_lon)).km

class Produto(Base):
    __tablename__ = 'produtos'
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    categoria = Column(String(50), nullable=False)
    preco = Column(Float, nullable=False)
    associacao_id = Column(Integer, ForeignKey('associacoes.id'), nullable=False)
    disponivel = Column(Boolean, default=True)
    organico = Column(Boolean, default=False)
    meses_disponibilidade = Column(JSON)  # Armazena lista de meses como JSON
    
    # Relacionamentos
    associacao = relationship("Associacao", back_populates="produtos")
    avaliacoes = relationship("Avaliacao", back_populates="produto")
    compras = relationship("Compra", secondary=compra_produto, back_populates="produtos")
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'categoria': self.categoria,
            'preco': self.preco,
            'associacao_id': self.associacao_id,
            'disponivel': self.disponivel,
            'organico': self.organico,
            'meses_disponibilidade': self.meses_disponibilidade,
            'media_avaliacoes': self.media_avaliacoes()
        }
    
    def esta_disponivel_no_mes(self, mes):
        """Verifica se o produto está disponível no mês especificado"""
        if not self.meses_disponibilidade:  # Se não tiver sazonalidade definida, está sempre disponível
            return True
        return mes in self.meses_disponibilidade
    
    def media_avaliacoes(self):
        """Retorna a média das avaliações do produto"""
        if not self.avaliacoes:
            return 0
        return sum(a.pontuacao for a in self.avaliacoes) / len(self.avaliacoes)

class Avaliacao(Base):
    __tablename__ = 'avaliacoes'
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    produto_id = Column(Integer, ForeignKey('produtos.id'), nullable=False)
    compra_id = Column(Integer, ForeignKey('compras.id'), nullable=True)
    pontuacao = Column(Integer, nullable=False)
    comentario = Column(Text)
    data = Column(DateTime, default=datetime.now)
    
    # Relacionamentos
    usuario = relationship("Usuario", back_populates="avaliacoes")
    produto = relationship("Produto", back_populates="avaliacoes")
    compra = relationship("Compra", back_populates="avaliacoes")
    
    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'produto_id': self.produto_id,
            'compra_id': self.compra_id,
            'pontuacao': self.pontuacao,
            'comentario': self.comentario,
            'data': self.data.strftime('%Y-%m-%d')
        }

class Compra(Base):
    __tablename__ = 'compras'
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    data = Column(DateTime, nullable=False)
    valor_total = Column(Float, nullable=False)
    
    # Relacionamentos
    usuario = relationship("Usuario", back_populates="compras")
    produtos = relationship("Produto", secondary=compra_produto, back_populates="compras")
    avaliacoes = relationship("Avaliacao", back_populates="compra")
    
    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'data': self.data.strftime('%Y-%m-%d'),
            'valor_total': self.valor_total,
            'produtos': [p.id for p in self.produtos]
        }

# Função para inicializar o banco de dados
def init_db(db_path='sqlite:///data/recomendacao.db'):
    engine = create_engine(db_path)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

# Função para migrar dados dos CSVs para o banco SQLite
def migrar_dados_csv_para_sqlite(session):
    import pandas as pd
    import ast
    from datetime import datetime
    
    # Carregar CSVs
    try:
        df_usuarios = pd.read_csv("data/usuarios_teste.csv")
        df_associacoes = pd.read_csv("data/associacoes_teste.csv")
        df_produtos = pd.read_csv("data/produtos_teste.csv")
        df_compras = pd.read_csv("data/compras_teste.csv")
        df_avaliacoes = pd.read_csv("data/avaliacoes_teste.csv")
        
        # Migrar associações
        for _, row in df_associacoes.iterrows():
            associacao = Associacao(
                id=row['id'],
                nome=row['nome'],
                regiao=row['regiao'],
                lat=row['lat'],
                lon=row['lon']
            )
            session.add(associacao)
        
        # Commit para ter IDs de associações disponíveis
        session.commit()
        print(f"Migradas {df_associacoes.shape[0]} associações")
        
        # Migrar produtos
        for _, row in df_produtos.iterrows():
            # Converter string de lista para lista Python
            if isinstance(row['meses_disponibilidade'], str):
                try:
                    meses = ast.literal_eval(row['meses_disponibilidade'])
                except:
                    meses = []
            else:
                meses = []
                
            produto = Produto(
                id=row['id'],
                nome=row['nome'],
                categoria=row['categoria'],
                preco=row['preco'],
                associacao_id=row['associacao_id'],
                disponivel=row['disponivel'],
                organico=row['organico'],
                meses_disponibilidade=meses
            )
            session.add(produto)
        
        # Commit para ter IDs de produtos disponíveis
        session.commit()
        print(f"Migrados {df_produtos.shape[0]} produtos")
        
        # Migrar usuários
        for _, row in df_usuarios.iterrows():
            # Converter string de dicionário para dicionário Python
            if isinstance(row['preferencias'], str):
                try:
                    prefs = ast.literal_eval(row['preferencias'])
                except:
                    prefs = {'distancia_maxima': 20, 'apenas_organicos': False, 'produtos_favoritos': [], 'associacoes_favoritas': []}
            else:
                prefs = {'distancia_maxima': 20, 'apenas_organicos': False, 'produtos_favoritos': [], 'associacoes_favoritas': []}
                
            usuario = Usuario(
                id=row['id'],
                nome=row['nome'],
                email=row['email'],
                lat=row['lat'],
                lon=row['lon'],
                distancia_maxima=prefs.get('distancia_maxima', 20),
                apenas_organicos=prefs.get('apenas_organicos', False)
            )
            session.add(usuario)
            
            # Adicionar produtos favoritos
            for produto_nome in prefs.get('produtos_favoritos', []):
                produto = session.query(Produto).filter(Produto.nome == produto_nome).first()
                if produto:
                    usuario.produtos_favoritos.append(produto)
            
            # Adicionar associações favoritas
            for assoc_nome in prefs.get('associacoes_favoritas', []):
                assoc = session.query(Associacao).filter(Associacao.nome == assoc_nome).first()
                if assoc:
                    usuario.associacoes_favoritas.append(assoc)
        
        # Commit para ter IDs de usuários disponíveis
        session.commit()
        print(f"Migrados {df_usuarios.shape[0]} usuários")
        
        # Migrar compras
        for _, row in df_compras.iterrows():
            # Converter string de lista para lista Python
            if isinstance(row['produtos'], str):
                try:
                    produtos_ids = ast.literal_eval(row['produtos'])
                except:
                    produtos_ids = []
            else:
                produtos_ids = []
                
            # Converter string de data para objeto datetime
            try:
                data_compra = datetime.strptime(row['data'], '%Y-%m-%d')
            except:
                data_compra = datetime.now()
                
            compra = Compra(
                id=row['id'],
                usuario_id=row['usuario_id'],
                data=data_compra,
                valor_total=row['valor_total']
            )
            session.add(compra)
            
            # Adicionar produtos à compra
            for produto_id in produtos_ids:
                produto = session.query(Produto).get(produto_id)
                if produto:
                    compra.produtos.append(produto)
        
        # Commit para ter IDs de compras disponíveis
        session.commit()
        print(f"Migradas {df_compras.shape[0]} compras")
        
        # Migrar avaliações
        for _, row in df_avaliacoes.iterrows():
            # Converter string de data para objeto datetime
            try:
                data_avaliacao = datetime.strptime(row['data'], '%Y-%m-%d')
            except:
                data_avaliacao = datetime.now()
                
            avaliacao = Avaliacao(
                id=row['id'],
                usuario_id=row['usuario_id'],
                produto_id=row['produto_id'],
                compra_id=row['compra_id'] if 'compra_id' in row and not pd.isna(row['compra_id']) else None,
                pontuacao=row['pontuacao'],
                comentario=row['comentario'],
                data=data_avaliacao
            )
            session.add(avaliacao)
        
        # Commit final
        session.commit()
        print(f"Migradas {df_avaliacoes.shape[0]} avaliações")
        
        return True
    
    except Exception as e:
        print(f"Erro ao migrar dados: {e}")
        session.rollback()
        return False

if __name__ == "__main__":
    # Inicializar banco de dados
    session = init_db()
    
    # Migrar dados
    sucesso = migrar_dados_csv_para_sqlite(session)
    
    if sucesso:
        print("Migração de dados concluída com sucesso!")
    else:
        print("Erro na migração de dados.")
