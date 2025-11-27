"""
Script para popular o banco de dados com dados de teste
"""
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.categoria import Categoria
from app.models.produto import Produto
from app.models.fornecedor import Fornecedor
from datetime import datetime

# Conectar ao banco
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Tenant ID e User ID (Marmores ABC - verificado no banco)
TENANT_ID = 4
USER_ID = 2

print("[SEED] Iniciando seed do banco de dados...")

try:
    # CATEGORIAS
    print("\n[CATEGORIAS] Criando categorias...")

    # Categorias principais
    cat_marmores = Categoria(
        tenant_id=TENANT_ID,
        nome="Mármores",
        descricao="Mármores nacionais e importados",
        codigo="MAR",
        created_by=USER_ID
    )
    db.add(cat_marmores)
    db.flush()

    cat_granitos = Categoria(
        tenant_id=TENANT_ID,
        nome="Granitos",
        descricao="Granitos nacionais e importados",
        codigo="GRA",
        created_by=USER_ID
    )
    db.add(cat_granitos)
    db.flush()

    cat_ferramentas = Categoria(
        tenant_id=TENANT_ID,
        nome="Ferramentas",
        descricao="Ferramentas para corte e acabamento",
        codigo="FER",
        created_by=USER_ID
    )
    db.add(cat_ferramentas)
    db.flush()

    cat_insumos = Categoria(
        tenant_id=TENANT_ID,
        nome="Insumos",
        descricao="Produtos químicos e insumos",
        codigo="INS",
        created_by=USER_ID
    )
    db.add(cat_insumos)
    db.flush()

    # Subcategorias de Mármores
    cat_marmore_branco = Categoria(
        tenant_id=TENANT_ID,
        nome="Mármore Branco",
        descricao="Mármores de tonalidade branca",
        codigo="MAR-BRA",
        categoria_pai_id=cat_marmores.id,
        created_by=USER_ID
    )
    db.add(cat_marmore_branco)

    cat_marmore_bege = Categoria(
        tenant_id=TENANT_ID,
        nome="Mármore Bege",
        descricao="Mármores de tonalidade bege",
        codigo="MAR-BEG",
        categoria_pai_id=cat_marmores.id,
        created_by=USER_ID
    )
    db.add(cat_marmore_bege)

    # Subcategorias de Granitos
    cat_granito_preto = Categoria(
        tenant_id=TENANT_ID,
        nome="Granito Preto",
        descricao="Granitos de tonalidade preta",
        codigo="GRA-PRE",
        categoria_pai_id=cat_granitos.id,
        created_by=USER_ID
    )
    db.add(cat_granito_preto)

    cat_granito_cinza = Categoria(
        tenant_id=TENANT_ID,
        nome="Granito Cinza",
        descricao="Granitos de tonalidade cinza",
        codigo="GRA-CIN",
        categoria_pai_id=cat_granitos.id,
        created_by=USER_ID
    )
    db.add(cat_granito_cinza)

    db.commit()
    print(f"[OK] {db.query(Categoria).filter_by(tenant_id=TENANT_ID).count()} categorias criadas")

    # PRODUTOS
    print("\n[PRODUTOS] Criando produtos...")

    produtos = [
        # Mármores Brancos
        {
            "codigo": "MAR-CAR-001",
            "nome": "Mármore Carrara Extra",
            "descricao": "Mármore branco italiano com veios cinzas suaves",
            "categoria_id": cat_marmore_branco.id,
            "unidade_medida": "M2",
            "estoque_minimo": 50,
            "estoque_maximo": 200,
            "estoque_atual": 120,
            "preco_referencia": 450.00,
            "especificacoes": {
                "origem": "Itália",
                "espessura": "2cm",
                "acabamento": "Polido",
                "aplicacao": "Piso, Parede, Bancada"
            }
        },
        {
            "codigo": "MAR-PIG-001",
            "nome": "Mármore Piguês",
            "descricao": "Mármore branco nacional de alta qualidade",
            "categoria_id": cat_marmore_branco.id,
            "unidade_medida": "M2",
            "estoque_minimo": 30,
            "estoque_maximo": 150,
            "estoque_atual": 85,
            "preco_referencia": 320.00,
            "especificacoes": {
                "origem": "Brasil - ES",
                "espessura": "2cm",
                "acabamento": "Polido",
                "aplicacao": "Piso, Parede"
            }
        },
        # Mármores Bege
        {
            "codigo": "MAR-CRE-001",
            "nome": "Mármore Crema Marfil",
            "descricao": "Mármore bege espanhol clássico",
            "categoria_id": cat_marmore_bege.id,
            "unidade_medida": "M2",
            "estoque_minimo": 40,
            "estoque_maximo": 180,
            "estoque_atual": 95,
            "preco_referencia": 380.00,
            "especificacoes": {
                "origem": "Espanha",
                "espessura": "2cm",
                "acabamento": "Polido",
                "aplicacao": "Piso, Parede, Bancada"
            }
        },
        {
            "codigo": "MAR-BOT-001",
            "nome": "Mármore Botticino",
            "descricao": "Mármore bege italiano com fosseis",
            "categoria_id": cat_marmore_bege.id,
            "unidade_medida": "M2",
            "estoque_minimo": 25,
            "estoque_maximo": 100,
            "estoque_atual": 45,
            "preco_referencia": 420.00,
            "especificacoes": {
                "origem": "Itália",
                "espessura": "2cm",
                "acabamento": "Polido",
                "aplicacao": "Parede, Bancada"
            }
        },
        # Granitos Pretos
        {
            "codigo": "GRA-SAO-001",
            "nome": "Granito São Gabriel",
            "descricao": "Granito preto absoluto nacional",
            "categoria_id": cat_granito_preto.id,
            "unidade_medida": "M2",
            "estoque_minimo": 60,
            "estoque_maximo": 250,
            "estoque_atual": 180,
            "preco_referencia": 280.00,
            "especificacoes": {
                "origem": "Brasil - ES",
                "espessura": "2cm e 3cm",
                "acabamento": "Polido, Flameado",
                "aplicacao": "Piso, Bancada, Revestimento"
            }
        },
        {
            "codigo": "GRA-ZIM-001",
            "nome": "Granito Zimbabwe",
            "descricao": "Granito preto importado premium",
            "categoria_id": cat_granito_preto.id,
            "unidade_medida": "M2",
            "estoque_minimo": 30,
            "estoque_maximo": 120,
            "estoque_atual": 65,
            "preco_referencia": 550.00,
            "especificacoes": {
                "origem": "África do Sul",
                "espessura": "2cm e 3cm",
                "acabamento": "Polido",
                "aplicacao": "Bancada, Revestimento"
            }
        },
        # Granitos Cinza
        {
            "codigo": "GRA-CIN-001",
            "nome": "Granito Cinza Corumbá",
            "descricao": "Granito cinza com pontos pretos",
            "categoria_id": cat_granito_cinza.id,
            "unidade_medida": "M2",
            "estoque_minimo": 50,
            "estoque_maximo": 200,
            "estoque_atual": 135,
            "preco_referencia": 220.00,
            "especificacoes": {
                "origem": "Brasil - MG",
                "espessura": "2cm e 3cm",
                "acabamento": "Polido, Flameado",
                "aplicacao": "Piso, Bancada"
            }
        },
        {
            "codigo": "GRA-AND-001",
            "nome": "Granito Cinza Andorinha",
            "descricao": "Granito cinza claro com veios escuros",
            "categoria_id": cat_granito_cinza.id,
            "unidade_medida": "M2",
            "estoque_minimo": 40,
            "estoque_maximo": 160,
            "estoque_atual": 90,
            "preco_referencia": 240.00,
            "especificacoes": {
                "origem": "Brasil - ES",
                "espessura": "2cm",
                "acabamento": "Polido",
                "aplicacao": "Piso, Bancada, Parede"
            }
        },
        # Ferramentas
        {
            "codigo": "FER-DIS-001",
            "nome": "Disco Diamantado 110mm",
            "descricao": "Disco para corte de mármore e granito",
            "categoria_id": cat_ferramentas.id,
            "unidade_medida": "UN",
            "estoque_minimo": 20,
            "estoque_maximo": 100,
            "estoque_atual": 45,
            "preco_referencia": 85.00,
            "especificacoes": {
                "diametro": "110mm",
                "tipo": "Segmentado",
                "aplicacao": "Mármore e Granito"
            }
        },
        {
            "codigo": "FER-LIX-001",
            "nome": "Lixa d'água Grana 120",
            "descricao": "Lixa para polimento manual",
            "categoria_id": cat_ferramentas.id,
            "unidade_medida": "UN",
            "estoque_minimo": 50,
            "estoque_maximo": 200,
            "estoque_atual": 120,
            "preco_referencia": 12.00
        },
        {
            "codigo": "FER-LIX-002",
            "nome": "Lixa d'água Grana 220",
            "descricao": "Lixa para polimento fino",
            "categoria_id": cat_ferramentas.id,
            "unidade_medida": "UN",
            "estoque_minimo": 50,
            "estoque_maximo": 200,
            "estoque_atual": 95,
            "preco_referencia": 13.50
        },
        # Insumos
        {
            "codigo": "INS-RES-001",
            "nome": "Resina Cristal Líquida",
            "descricao": "Resina para acabamento e proteção",
            "categoria_id": cat_insumos.id,
            "unidade_medida": "LT",
            "estoque_minimo": 10,
            "estoque_maximo": 50,
            "estoque_atual": 28,
            "preco_referencia": 145.00,
            "especificacoes": {
                "tipo": "Poliéster",
                "aplicacao": "Proteção e brilho",
                "rendimento": "8-10 m²/litro"
            }
        },
        {
            "codigo": "INS-MAS-001",
            "nome": "Massa Plástica para Pedras",
            "descricao": "Massa para correção de trincas e furos",
            "categoria_id": cat_insumos.id,
            "unidade_medida": "KG",
            "estoque_minimo": 15,
            "estoque_maximo": 80,
            "estoque_atual": 42,
            "preco_referencia": 68.00,
            "especificacoes": {
                "cores": "Diversas",
                "tempo_secagem": "30 minutos",
                "aplicacao": "Correção de imperfeições"
            }
        },
        {
            "codigo": "INS-IMP-001",
            "nome": "Impermeabilizante para Pedras",
            "descricao": "Proteção contra manchas e umidade",
            "categoria_id": cat_insumos.id,
            "unidade_medida": "LT",
            "estoque_minimo": 12,
            "estoque_maximo": 60,
            "estoque_atual": 35,
            "preco_referencia": 95.00,
            "especificacoes": {
                "tipo": "Silicone",
                "aplicacao": "Mármores e Granitos",
                "rendimento": "15-20 m²/litro"
            }
        }
    ]

    for p_data in produtos:
        produto = Produto(
            tenant_id=TENANT_ID,
            created_by=USER_ID,
            **p_data
        )
        db.add(produto)

    db.commit()
    print(f"[OK] {len(produtos)} produtos criados")

    # FORNECEDORES
    print("\n[FORNECEDORES] Criando fornecedores...")

    fornecedores = [
        {
            "razao_social": "Pedras Naturais Ltda",
            "nome_fantasia": "Pedras Naturais",
            "cnpj": "12345678000101",
            "endereco": "Av. das Rochas, 1500",
            "cidade": "Cachoeiro de Itapemirim",
            "estado": "ES",
            "cep": "29300000",
            "contatos": {
                "telefone": "(28) 3522-1234",
                "email": "vendas@pedrasnaturais.com.br",
                "responsavel": "Carlos Silva"
            },
            "categorias_produtos": ["Mármores", "Granitos"],
            "condicoes_pagamento": "30/60 dias ou 5% desconto à vista",
            "rating": 4.5,
            "aprovado": True
        },
        {
            "razao_social": "Mármores Italianos Importadora S.A.",
            "nome_fantasia": "Itália Mármores",
            "cnpj": "98765432000188",
            "endereco": "Rua Importação, 890",
            "cidade": "São Paulo",
            "estado": "SP",
            "cep": "01310100",
            "contatos": {
                "telefone": "(11) 3456-7890",
                "email": "import@italiamarmores.com.br",
                "responsavel": "Giuseppe Rossi"
            },
            "categorias_produtos": ["Mármores Importados"],
            "condicoes_pagamento": "45/60/75 dias",
            "rating": 4.8,
            "aprovado": True
        },
        {
            "razao_social": "Ferramentas Diamantadas Brasil Ltda",
            "nome_fantasia": "Diamanta Tools",
            "cnpj": "45678912000134",
            "endereco": "Rua Industrial, 2500",
            "cidade": "Belo Horizonte",
            "estado": "MG",
            "cep": "30130000",
            "contatos": {
                "telefone": "(31) 3210-5678",
                "email": "vendas@diamantatools.com.br",
                "responsavel": "Ana Paula Costa"
            },
            "categorias_produtos": ["Ferramentas", "Discos de Corte"],
            "condicoes_pagamento": "28 dias",
            "rating": 4.2,
            "aprovado": True
        },
        {
            "razao_social": "Química para Pedras Comercial Ltda",
            "nome_fantasia": "QuimiPedra",
            "cnpj": "78912345000167",
            "endereco": "Av. Química, 750",
            "cidade": "São Paulo",
            "estado": "SP",
            "cep": "02345000",
            "contatos": {
                "telefone": "(11) 2987-4321",
                "email": "vendas@quimipedra.com.br",
                "responsavel": "Roberto Alves"
            },
            "categorias_produtos": ["Insumos Químicos", "Resinas"],
            "condicoes_pagamento": "21/42 dias",
            "rating": 4.3,
            "aprovado": True
        },
        {
            "razao_social": "Granitos do Sul Exportação S.A.",
            "nome_fantasia": "Sul Granitos",
            "cnpj": "32165498000199",
            "endereco": "Rod. BR-101, Km 45",
            "cidade": "Varginha",
            "estado": "MG",
            "cep": "37010000",
            "contatos": {
                "telefone": "(35) 3221-9876",
                "email": "comercial@sulgranitos.com.br",
                "responsavel": "Marcos Fernandes"
            },
            "categorias_produtos": ["Granitos Nacionais"],
            "condicoes_pagamento": "30/60 dias",
            "rating": 4.6,
            "aprovado": True
        },
        {
            "razao_social": "Distribuidora de Abrasivos Nacional Ltda",
            "nome_fantasia": "Abrasivos Nacional",
            "cnpj": "65432198000145",
            "endereco": "Rua dos Abrasivos, 1200",
            "cidade": "Rio de Janeiro",
            "estado": "RJ",
            "cep": "20040020",
            "contatos": {
                "telefone": "(21) 3456-1234",
                "email": "vendas@abrasivosnacional.com.br",
                "responsavel": "Juliana Santos"
            },
            "categorias_produtos": ["Lixas", "Abrasivos"],
            "condicoes_pagamento": "30 dias",
            "rating": 4.0,
            "aprovado": True
        },
        {
            "razao_social": "Pedras Exóticas Premium Ltda",
            "nome_fantasia": "Exótica Premium",
            "cnpj": "15935745000122",
            "endereco": "Av. das Pedras Raras, 3200",
            "cidade": "Vitória",
            "estado": "ES",
            "cep": "29050000",
            "contatos": {
                "telefone": "(27) 3334-5566",
                "email": "atendimento@exoticapremium.com.br",
                "responsavel": "Fernando Lima"
            },
            "categorias_produtos": ["Mármores Especiais", "Granitos Importados"],
            "condicoes_pagamento": "45/60 dias",
            "rating": 4.7,
            "aprovado": True
        },
        {
            "razao_social": "Resinas e Químicos Industriais S.A.",
            "nome_fantasia": "ResQuim",
            "cnpj": "75395145000189",
            "endereco": "Distrito Industrial, Quadra 15",
            "cidade": "Contagem",
            "estado": "MG",
            "cep": "32010000",
            "contatos": {
                "telefone": "(31) 3567-8901",
                "email": "vendas@resquim.com.br",
                "responsavel": "Patricia Mendes"
            },
            "categorias_produtos": ["Resinas", "Impermeabilizantes"],
            "condicoes_pagamento": "21 dias ou 3% desconto à vista",
            "rating": 4.1,
            "aprovado": False  # Em processo de aprovação
        }
    ]

    for f_data in fornecedores:
        fornecedor = Fornecedor(
            tenant_id=TENANT_ID,
            created_by=USER_ID,
            **f_data
        )
        db.add(fornecedor)

    db.commit()
    print(f"[OK] {len(fornecedores)} fornecedores criados")

    print("\n[SUCCESS] Seed concluido com sucesso!")
    print(f"\n[RESUMO]:")
    print(f"   - Categorias: {db.query(Categoria).filter_by(tenant_id=TENANT_ID).count()}")
    print(f"   - Produtos: {db.query(Produto).filter_by(tenant_id=TENANT_ID).count()}")
    print(f"   - Fornecedores: {db.query(Fornecedor).filter_by(tenant_id=TENANT_ID).count()}")

except Exception as e:
    print(f"\n[ERROR] Erro ao executar seed: {e}")
    db.rollback()
    raise
finally:
    db.close()
