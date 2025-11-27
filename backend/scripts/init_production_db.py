"""
Script para inicializar o banco de dados em produção.
Cria todas as tabelas e o usuário MASTER inicial.

Uso:
    python scripts/init_production_db.py --email admin@empresa.com --senha SenhaForte123 --nome "Nome Admin"
"""
import sys
import os
import argparse

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal
from app.models.base import Base
from app.models.tenant import Tenant
from app.models.usuario import Usuario, TipoUsuario
import bcrypt


def create_tables():
    """Criar todas as tabelas no banco"""
    print("[*] Criando tabelas...")
    Base.metadata.create_all(bind=engine)
    print("[+] Tabelas criadas com sucesso!")


def create_master_tenant():
    """Criar o tenant MASTER (para o super admin)"""
    db = SessionLocal()
    try:
        # Verificar se já existe
        existing = db.query(Tenant).filter(Tenant.slug == "master").first()
        if existing:
            print("[!] Tenant MASTER já existe")
            return existing.id

        tenant = Tenant(
            nome_empresa="Sistema Master",
            razao_social="Administração do Sistema",
            cnpj="00000000000000",  # CNPJ fictício para master
            slug="master",
            ativo=True,
            plano="enterprise",
            max_usuarios=999,
            max_produtos=99999,
            max_fornecedores=99999,
            ia_habilitada=True
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        print(f"[+] Tenant MASTER criado com ID: {tenant.id}")
        return tenant.id
    finally:
        db.close()


def create_master_user(tenant_id: int, email: str, senha: str, nome: str):
    """Criar o usuário MASTER"""
    db = SessionLocal()
    try:
        # Verificar se já existe
        existing = db.query(Usuario).filter(
            Usuario.email == email,
            Usuario.tipo == TipoUsuario.MASTER
        ).first()

        if existing:
            print(f"[!] Usuário MASTER com email {email} já existe")
            return

        # Hash da senha
        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        usuario = Usuario(
            tenant_id=tenant_id,
            nome_completo=nome,
            email=email,
            senha_hash=senha_hash,
            tipo=TipoUsuario.MASTER,
            ativo=True,
            notificacoes_email=True,
            notificacoes_sistema=True
        )
        db.add(usuario)
        db.commit()
        print(f"[+] Usuário MASTER criado: {email}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Inicializar banco de dados em produção")
    parser.add_argument("--email", required=True, help="Email do usuário MASTER")
    parser.add_argument("--senha", required=True, help="Senha do usuário MASTER")
    parser.add_argument("--nome", required=True, help="Nome completo do usuário MASTER")
    parser.add_argument("--skip-tables", action="store_true", help="Pular criação de tabelas")

    args = parser.parse_args()

    print("=" * 50)
    print("INICIALIZAÇÃO DO BANCO DE DADOS - PRODUÇÃO")
    print("=" * 50)

    # Validações
    if len(args.senha) < 8:
        print("[ERRO] Senha deve ter pelo menos 8 caracteres")
        sys.exit(1)

    # Criar tabelas
    if not args.skip_tables:
        create_tables()

    # Criar tenant master
    tenant_id = create_master_tenant()

    # Criar usuário master
    create_master_user(tenant_id, args.email, args.senha, args.nome)

    print("=" * 50)
    print("[+] Inicialização concluída!")
    print(f"[*] Login: {args.email}")
    print(f"[*] CNPJ do tenant master: 00000000000000")
    print("=" * 50)


if __name__ == "__main__":
    main()
