"""
Script para popular fornecedores no banco de dados
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.fornecedor import Fornecedor

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

TENANT_ID = 4
USER_ID = 2

print("[SEED] Inserindo fornecedores...")

try:
    fornecedores = [
        {
            "razao_social": "Pedras Naturais Ltda",
            "nome_fantasia": "Pedras Naturais",
            "cnpj": "12345678000101",
            "endereco_logradouro": "Av. das Rochas, 1500",
            "endereco_cidade": "Cachoeiro de Itapemirim",
            "endereco_estado": "ES",
            "endereco_cep": "29300000",
            "telefone_principal": "(28) 3522-1234",
            "email_principal": "vendas@pedrasnaturais.com.br",
            "contatos": [{"nome": "Carlos Silva", "cargo": "Vendedor", "telefone": "(28) 3522-1234", "email": "carlos@pedrasnaturais.com.br"}],
            "categorias_produtos": ["Marmores", "Granitos"],
            "condicoes_pagamento": "30/60 dias ou 5% desconto a vista",
            "rating": 4.5,
            "aprovado": True
        },
        {
            "razao_social": "Marmores Italianos Importadora S.A.",
            "nome_fantasia": "Italia Marmores",
            "cnpj": "98765432000188",
            "endereco_logradouro": "Rua Importacao, 890",
            "endereco_cidade": "Sao Paulo",
            "endereco_estado": "SP",
            "endereco_cep": "01310100",
            "telefone_principal": "(11) 3456-7890",
            "email_principal": "import@italiamarmores.com.br",
            "contatos": [{"nome": "Giuseppe Rossi", "cargo": "Gerente Comercial", "telefone": "(11) 3456-7890", "email": "giuseppe@italiamarmores.com.br"}],
            "categorias_produtos": ["Marmores Importados"],
            "condicoes_pagamento": "45/60/75 dias",
            "rating": 4.8,
            "aprovado": True
        },
        {
            "razao_social": "Ferramentas Diamantadas Brasil Ltda",
            "nome_fantasia": "Diamanta Tools",
            "cnpj": "45678912000134",
            "endereco_logradouro": "Rua Industrial, 2500",
            "endereco_cidade": "Belo Horizonte",
            "endereco_estado": "MG",
            "endereco_cep": "30130000",
            "telefone_principal": "(31) 3210-5678",
            "email_principal": "vendas@diamantatools.com.br",
            "contatos": [{"nome": "Ana Paula Costa", "cargo": "Vendedora", "telefone": "(31) 3210-5678", "email": "ana@diamantatools.com.br"}],
            "categorias_produtos": ["Ferramentas", "Discos de Corte"],
            "condicoes_pagamento": "28 dias",
            "rating": 4.2,
            "aprovado": True
        },
        {
            "razao_social": "Quimica para Pedras Comercial Ltda",
            "nome_fantasia": "QuimiPedra",
            "cnpj": "78912345000167",
            "endereco_logradouro": "Av. Quimica, 750",
            "endereco_cidade": "Sao Paulo",
            "endereco_estado": "SP",
            "endereco_cep": "02345000",
            "telefone_principal": "(11) 2987-4321",
            "email_principal": "vendas@quimipedra.com.br",
            "contatos": [{"nome": "Roberto Alves", "cargo": "Vendedor", "telefone": "(11) 2987-4321", "email": "roberto@quimipedra.com.br"}],
            "categorias_produtos": ["Insumos Quimicos", "Resinas"],
            "condicoes_pagamento": "21/42 dias",
            "rating": 4.3,
            "aprovado": True
        },
        {
            "razao_social": "Granitos do Sul Exportacao S.A.",
            "nome_fantasia": "Sul Granitos",
            "cnpj": "32165498000199",
            "endereco_logradouro": "Rod. BR-101, Km 45",
            "endereco_cidade": "Varginha",
            "endereco_estado": "MG",
            "endereco_cep": "37010000",
            "telefone_principal": "(35) 3221-9876",
            "email_principal": "comercial@sulgranitos.com.br",
            "contatos": [{"nome": "Marcos Fernandes", "cargo": "Gerente Comercial", "telefone": "(35) 3221-9876", "email": "marcos@sulgranitos.com.br"}],
            "categorias_produtos": ["Granitos Nacionais"],
            "condicoes_pagamento": "30/60 dias",
            "rating": 4.6,
            "aprovado": True
        },
        {
            "razao_social": "Distribuidora de Abrasivos Nacional Ltda",
            "nome_fantasia": "Abrasivos Nacional",
            "cnpj": "65432198000145",
            "endereco_logradouro": "Rua dos Abrasivos, 1200",
            "endereco_cidade": "Rio de Janeiro",
            "endereco_estado": "RJ",
            "endereco_cep": "20040020",
            "telefone_principal": "(21) 3456-1234",
            "email_principal": "vendas@abrasivosnacional.com.br",
            "contatos": [{"nome": "Juliana Santos", "cargo": "Vendedora", "telefone": "(21) 3456-1234", "email": "juliana@abrasivosnacional.com.br"}],
            "categorias_produtos": ["Lixas", "Abrasivos"],
            "condicoes_pagamento": "30 dias",
            "rating": 4.0,
            "aprovado": True
        },
        {
            "razao_social": "Pedras Exoticas Premium Ltda",
            "nome_fantasia": "Exotica Premium",
            "cnpj": "15935745000122",
            "endereco_logradouro": "Av. das Pedras Raras, 3200",
            "endereco_cidade": "Vitoria",
            "endereco_estado": "ES",
            "endereco_cep": "29050000",
            "telefone_principal": "(27) 3334-5566",
            "email_principal": "atendimento@exoticapremium.com.br",
            "contatos": [{"nome": "Fernando Lima", "cargo": "Diretor Comercial", "telefone": "(27) 3334-5566", "email": "fernando@exoticapremium.com.br"}],
            "categorias_produtos": ["Marmores Especiais", "Granitos Importados"],
            "condicoes_pagamento": "45/60 dias",
            "rating": 4.7,
            "aprovado": True
        },
        {
            "razao_social": "Resinas e Quimicos Industriais S.A.",
            "nome_fantasia": "ResQuim",
            "cnpj": "75395145000189",
            "endereco_logradouro": "Distrito Industrial, Quadra 15",
            "endereco_cidade": "Contagem",
            "endereco_estado": "MG",
            "endereco_cep": "32010000",
            "telefone_principal": "(31) 3567-8901",
            "email_principal": "vendas@resquim.com.br",
            "contatos": [{"nome": "Patricia Mendes", "cargo": "Gerente de Vendas", "telefone": "(31) 3567-8901", "email": "patricia@resquim.com.br"}],
            "categorias_produtos": ["Resinas", "Impermeabilizantes"],
            "condicoes_pagamento": "21 dias ou 3% desconto a vista",
            "rating": 4.1,
            "aprovado": False
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

    print("\n[SUCCESS] Seed de fornecedores concluido!")
    print(f"   - Fornecedores: {db.query(Fornecedor).filter_by(tenant_id=TENANT_ID).count()}")

except Exception as e:
    print(f"\n[ERROR] Erro: {e}")
    db.rollback()
    raise
finally:
    db.close()
