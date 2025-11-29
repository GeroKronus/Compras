"""Script para popular banco de producao Railway com produtos de mineradora"""
import psycopg2
from datetime import datetime
from decimal import Decimal

conn_str = 'postgresql://postgres:ONWumyNBfhJEpgxfPeAMrFuJgReLgbDG@shinkansen.proxy.rlwy.net:49885/railway'
conn = psycopg2.connect(conn_str)
cur = conn.cursor()

tenant_id = 3  # PicStone

# IDs das categorias (criadas anteriormente)
CAT = {
    'discos': 3,      # Discos e Laminas
    'abrasivos': 4,   # Abrasivos
    'epis': 5,        # EPIs
    'quimicos': 6,    # Quimicos
    'pecas': 7,       # Pecas Reposicao
    'embalagens': 8,  # Embalagens
    'lubrificantes': 9,  # Lubrificantes
    'ferramentas': 1, # Ferramentas
    'insumos': 2      # Insumos
}

produtos = [
    # DISCOS E LAMINAS (cat 3)
    {'codigo': 'DIS-DIA-350', 'nome': 'Disco Diamantado 350mm para Marmore', 'cat': 'discos', 'un': 'UN', 'preco': 450.00, 'estoque': 12, 'min': 5, 'desc': 'Disco diamantado segmentado para corte de marmore, 350mm diametro'},
    {'codigo': 'DIS-DIA-400', 'nome': 'Disco Diamantado 400mm para Granito', 'cat': 'discos', 'un': 'UN', 'preco': 680.00, 'estoque': 8, 'min': 3, 'desc': 'Disco diamantado para corte de granito, 400mm diametro'},
    {'codigo': 'DIS-DIA-500', 'nome': 'Disco Diamantado 500mm Multiuso', 'cat': 'discos', 'un': 'UN', 'preco': 950.00, 'estoque': 5, 'min': 2, 'desc': 'Disco diamantado 500mm para corte pesado'},
    {'codigo': 'FIO-DIA-001', 'nome': 'Fio Diamantado para Teares', 'cat': 'discos', 'un': 'M', 'preco': 85.00, 'estoque': 200, 'min': 50, 'desc': 'Fio diamantado para corte em teares, preco por metro'},
    {'codigo': 'LAM-SER-001', 'nome': 'Lamina de Serra Circular 600mm', 'cat': 'discos', 'un': 'UN', 'preco': 1200.00, 'estoque': 4, 'min': 2, 'desc': 'Lamina de serra circular para bloco de granito'},
    {'codigo': 'SEG-DIA-001', 'nome': 'Segmento Diamantado para Fio', 'cat': 'discos', 'un': 'UN', 'preco': 45.00, 'estoque': 50, 'min': 20, 'desc': 'Segmento diamantado de reposicao para fio'},

    # ABRASIVOS (cat 4)
    {'codigo': 'LIX-AGU-080', 'nome': 'Lixa DAgua Grao 80', 'cat': 'abrasivos', 'un': 'FL', 'preco': 3.50, 'estoque': 200, 'min': 50, 'desc': 'Lixa dagua grao 80 para desbaste inicial'},
    {'codigo': 'LIX-AGU-120', 'nome': 'Lixa DAgua Grao 120', 'cat': 'abrasivos', 'un': 'FL', 'preco': 3.50, 'estoque': 200, 'min': 50, 'desc': 'Lixa dagua grao 120'},
    {'codigo': 'LIX-AGU-220', 'nome': 'Lixa DAgua Grao 220', 'cat': 'abrasivos', 'un': 'FL', 'preco': 3.80, 'estoque': 150, 'min': 50, 'desc': 'Lixa dagua grao 220 para acabamento'},
    {'codigo': 'LIX-AGU-400', 'nome': 'Lixa DAgua Grao 400', 'cat': 'abrasivos', 'un': 'FL', 'preco': 4.00, 'estoque': 150, 'min': 40, 'desc': 'Lixa dagua grao 400 para polimento'},
    {'codigo': 'LIX-AGU-600', 'nome': 'Lixa DAgua Grao 600', 'cat': 'abrasivos', 'un': 'FL', 'preco': 4.20, 'estoque': 100, 'min': 30, 'desc': 'Lixa dagua grao 600 para polimento fino'},
    {'codigo': 'LIX-AGU-1200', 'nome': 'Lixa DAgua Grao 1200', 'cat': 'abrasivos', 'un': 'FL', 'preco': 4.50, 'estoque': 80, 'min': 25, 'desc': 'Lixa dagua grao 1200 para polimento ultra fino'},
    {'codigo': 'FEL-POL-001', 'nome': 'Feltro para Polimento 4 polegadas', 'cat': 'abrasivos', 'un': 'UN', 'preco': 28.00, 'estoque': 25, 'min': 10, 'desc': 'Disco de feltro para polimento final'},
    {'codigo': 'MAS-POL-001', 'nome': 'Massa de Polir para Marmore 1kg', 'cat': 'abrasivos', 'un': 'KG', 'preco': 65.00, 'estoque': 15, 'min': 5, 'desc': 'Massa abrasiva para polimento de marmore'},
    {'codigo': 'ESP-ABR-001', 'nome': 'Esponja Abrasiva Diamantada', 'cat': 'abrasivos', 'un': 'UN', 'preco': 35.00, 'estoque': 40, 'min': 15, 'desc': 'Esponja diamantada para acabamento manual'},

    # EPIs (cat 5)
    {'codigo': 'EPI-LUV-001', 'nome': 'Luva de Raspa Cano Longo', 'cat': 'epis', 'un': 'PAR', 'preco': 25.00, 'estoque': 30, 'min': 10, 'desc': 'Luva de raspa de couro cano longo para protecao'},
    {'codigo': 'EPI-LUV-002', 'nome': 'Luva Nitrilo Azul', 'cat': 'epis', 'un': 'PAR', 'preco': 8.00, 'estoque': 100, 'min': 40, 'desc': 'Luva de nitrilo para manuseio de quimicos'},
    {'codigo': 'EPI-OCU-001', 'nome': 'Oculos de Protecao Ampla Visao', 'cat': 'epis', 'un': 'UN', 'preco': 18.00, 'estoque': 25, 'min': 10, 'desc': 'Oculos de protecao anti-estilhaco'},
    {'codigo': 'EPI-PRO-001', 'nome': 'Protetor Auricular Plug', 'cat': 'epis', 'un': 'PAR', 'preco': 2.50, 'estoque': 200, 'min': 80, 'desc': 'Protetor auricular de silicone'},
    {'codigo': 'EPI-PRO-002', 'nome': 'Protetor Auricular Abafador', 'cat': 'epis', 'un': 'UN', 'preco': 45.00, 'estoque': 15, 'min': 5, 'desc': 'Abafador tipo concha 23dB'},
    {'codigo': 'EPI-MAS-001', 'nome': 'Mascara PFF2 com Valvula', 'cat': 'epis', 'un': 'UN', 'preco': 12.00, 'estoque': 150, 'min': 50, 'desc': 'Mascara respiratoria PFF2 para poeira de pedra'},
    {'codigo': 'EPI-BOT-001', 'nome': 'Bota de Seguranca Bico de Aco', 'cat': 'epis', 'un': 'PAR', 'preco': 120.00, 'estoque': 12, 'min': 4, 'desc': 'Bota de seguranca com bico de aco e solado antiderrapante'},
    {'codigo': 'EPI-CAP-001', 'nome': 'Capacete de Seguranca Classe B', 'cat': 'epis', 'un': 'UN', 'preco': 35.00, 'estoque': 20, 'min': 8, 'desc': 'Capacete de seguranca com jugular'},
    {'codigo': 'EPI-AVE-001', 'nome': 'Avental de Raspa', 'cat': 'epis', 'un': 'UN', 'preco': 55.00, 'estoque': 10, 'min': 4, 'desc': 'Avental de raspa de couro para protecao frontal'},

    # QUIMICOS (cat 6)
    {'codigo': 'QUI-RES-001', 'nome': 'Resina Epoxi Transparente 1kg', 'cat': 'quimicos', 'un': 'KG', 'preco': 85.00, 'estoque': 20, 'min': 8, 'desc': 'Resina epoxi bicomponente para reparos e colagem'},
    {'codigo': 'QUI-RES-002', 'nome': 'Resina Poliester 5kg', 'cat': 'quimicos', 'un': 'GL', 'preco': 180.00, 'estoque': 10, 'min': 4, 'desc': 'Resina poliester para preenchimento de fissuras'},
    {'codigo': 'QUI-IMP-001', 'nome': 'Impermeabilizante para Pedras 5L', 'cat': 'quimicos', 'un': 'GL', 'preco': 220.00, 'estoque': 8, 'min': 3, 'desc': 'Impermeabilizante a base de silicone para marmores e granitos'},
    {'codigo': 'QUI-SEL-001', 'nome': 'Selante de Silicone Neutro 280ml', 'cat': 'quimicos', 'un': 'TB', 'preco': 22.00, 'estoque': 40, 'min': 15, 'desc': 'Selante de silicone para vedacao de juntas'},
    {'codigo': 'QUI-LIM-001', 'nome': 'Limpa Pedras Concentrado 5L', 'cat': 'quimicos', 'un': 'GL', 'preco': 95.00, 'estoque': 12, 'min': 5, 'desc': 'Detergente concentrado para limpeza de pedras naturais'},
    {'codigo': 'QUI-REM-001', 'nome': 'Removedor de Ferrugem 1L', 'cat': 'quimicos', 'un': 'LT', 'preco': 45.00, 'estoque': 15, 'min': 6, 'desc': 'Removedor de manchas de ferrugem em pedras'},
    {'codigo': 'QUI-MAS-001', 'nome': 'Massa Plastica Marmore 1kg', 'cat': 'quimicos', 'un': 'KG', 'preco': 38.00, 'estoque': 25, 'min': 10, 'desc': 'Massa plastica cor marmore para reparos'},
    {'codigo': 'QUI-COL-001', 'nome': 'Cola Marmore Granito 1kg', 'cat': 'quimicos', 'un': 'KG', 'preco': 42.00, 'estoque': 30, 'min': 12, 'desc': 'Adesivo especial para colagem de marmores e granitos'},

    # PECAS REPOSICAO (cat 7)
    {'codigo': 'PEC-COR-001', 'nome': 'Correia Transportadora 1000mm', 'cat': 'pecas', 'un': 'M', 'preco': 180.00, 'estoque': 30, 'min': 10, 'desc': 'Correia transportadora para esteiras, largura 1000mm'},
    {'codigo': 'PEC-ROL-001', 'nome': 'Rolamento 6205 2RS', 'cat': 'pecas', 'un': 'UN', 'preco': 28.00, 'estoque': 40, 'min': 15, 'desc': 'Rolamento blindado 6205 para polidoras'},
    {'codigo': 'PEC-ROL-002', 'nome': 'Rolamento 6308 2RS', 'cat': 'pecas', 'un': 'UN', 'preco': 65.00, 'estoque': 20, 'min': 8, 'desc': 'Rolamento blindado 6308 para serras'},
    {'codigo': 'PEC-MAN-001', 'nome': 'Mangueira Hidraulica 1/2 - Metro', 'cat': 'pecas', 'un': 'M', 'preco': 45.00, 'estoque': 50, 'min': 20, 'desc': 'Mangueira hidraulica alta pressao 1/2 polegada'},
    {'codigo': 'PEC-FIL-001', 'nome': 'Filtro de Ar Compressor', 'cat': 'pecas', 'un': 'UN', 'preco': 85.00, 'estoque': 8, 'min': 3, 'desc': 'Elemento filtrante para compressor de ar'},
    {'codigo': 'PEC-FIL-002', 'nome': 'Filtro Oleo Hidraulico', 'cat': 'pecas', 'un': 'UN', 'preco': 120.00, 'estoque': 6, 'min': 2, 'desc': 'Filtro de oleo para sistema hidraulico'},
    {'codigo': 'PEC-VED-001', 'nome': 'Kit Vedacao Cilindro Hidraulico', 'cat': 'pecas', 'un': 'KT', 'preco': 95.00, 'estoque': 10, 'min': 4, 'desc': 'Kit de vedacao para cilindros hidraulicos'},

    # EMBALAGENS (cat 8)
    {'codigo': 'EMB-PAL-001', 'nome': 'Pallet de Madeira 1200x1000mm', 'cat': 'embalagens', 'un': 'UN', 'preco': 45.00, 'estoque': 80, 'min': 30, 'desc': 'Pallet de madeira padrao para chapas de pedra'},
    {'codigo': 'EMB-CAN-001', 'nome': 'Cantoneira de Papelao 50mm', 'cat': 'embalagens', 'un': 'UN', 'preco': 2.80, 'estoque': 500, 'min': 200, 'desc': 'Cantoneira de protecao em papelao 50x50mm'},
    {'codigo': 'EMB-CAN-002', 'nome': 'Cantoneira Plastica 40mm', 'cat': 'embalagens', 'un': 'UN', 'preco': 4.50, 'estoque': 300, 'min': 100, 'desc': 'Cantoneira de protecao plastica reutilizavel'},
    {'codigo': 'EMB-FIT-001', 'nome': 'Fita de Arqueacao PP 16mm', 'cat': 'embalagens', 'un': 'RL', 'preco': 85.00, 'estoque': 20, 'min': 8, 'desc': 'Fita de polipropileno para arqueacao 16mm x 1000m'},
    {'codigo': 'EMB-FIL-001', 'nome': 'Filme Stretch 500mm', 'cat': 'embalagens', 'un': 'RL', 'preco': 55.00, 'estoque': 30, 'min': 12, 'desc': 'Filme stretch para embalagem 500mm x 300m'},
    {'codigo': 'EMB-ISO-001', 'nome': 'Isopor Protecao 20mm', 'cat': 'embalagens', 'un': 'M2', 'preco': 12.00, 'estoque': 100, 'min': 40, 'desc': 'Placa de isopor para protecao de pecas'},

    # LUBRIFICANTES (cat 9)
    {'codigo': 'LUB-OLE-001', 'nome': 'Oleo Hidraulico ISO 68 - 20L', 'cat': 'lubrificantes', 'un': 'BD', 'preco': 280.00, 'estoque': 8, 'min': 3, 'desc': 'Oleo hidraulico mineral ISO VG 68'},
    {'codigo': 'LUB-OLE-002', 'nome': 'Oleo Lubrificante SAE 40 - 1L', 'cat': 'lubrificantes', 'un': 'LT', 'preco': 32.00, 'estoque': 24, 'min': 10, 'desc': 'Oleo lubrificante para motores diesel'},
    {'codigo': 'LUB-GRA-001', 'nome': 'Graxa Industrial EP2 - 1kg', 'cat': 'lubrificantes', 'un': 'KG', 'preco': 45.00, 'estoque': 15, 'min': 6, 'desc': 'Graxa multiuso para rolamentos e mancais'},
    {'codigo': 'LUB-GRA-002', 'nome': 'Graxa Calcio Resistente Agua 500g', 'cat': 'lubrificantes', 'un': 'UN', 'preco': 28.00, 'estoque': 20, 'min': 8, 'desc': 'Graxa a base de calcio para ambientes umidos'},
    {'codigo': 'LUB-FLU-001', 'nome': 'Fluido de Corte Soluvel 20L', 'cat': 'lubrificantes', 'un': 'BD', 'preco': 320.00, 'estoque': 6, 'min': 2, 'desc': 'Fluido de corte soluvel para serras e polidoras'},
    {'codigo': 'LUB-DES-001', 'nome': 'Desengripante Spray 300ml', 'cat': 'lubrificantes', 'un': 'UN', 'preco': 22.00, 'estoque': 30, 'min': 12, 'desc': 'Spray desengripante e lubrificante multiuso'},

    # FERRAMENTAS (cat 1)
    {'codigo': 'FER-DIS-001', 'nome': 'Disco Diamantado 110mm', 'cat': 'ferramentas', 'un': 'UN', 'preco': 45.00, 'estoque': 20, 'min': 8, 'desc': 'Disco diamantado 110mm para esmerilhadeira'},
    {'codigo': 'FER-LIX-001', 'nome': 'Lixa d agua Grana 120', 'cat': 'ferramentas', 'un': 'FL', 'preco': 2.50, 'estoque': 100, 'min': 30, 'desc': 'Lixa d agua grana 120'},
    {'codigo': 'FER-LIX-002', 'nome': 'Lixa d agua Grana 220', 'cat': 'ferramentas', 'un': 'FL', 'preco': 2.50, 'estoque': 100, 'min': 30, 'desc': 'Lixa d agua grana 220'},
]

print('Inserindo produtos...')
count = 0
for p in produtos:
    cur.execute('''
        INSERT INTO produtos (codigo, nome, descricao, categoria_id, unidade_medida,
                             preco_referencia, estoque_atual, estoque_minimo, tenant_id,
                             ativo, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (p['codigo'], p['nome'], p['desc'], CAT[p['cat']], p['un'],
          Decimal(str(p['preco'])), p['estoque'], p['min'], tenant_id,
          True, datetime.now(), datetime.now()))
    count += 1

conn.commit()
print(f'{count} produtos inseridos com sucesso!')

# Verificar total
cur.execute('SELECT COUNT(*) FROM produtos WHERE tenant_id = %s', (tenant_id,))
total = cur.fetchone()[0]
print(f'Total de produtos no tenant {tenant_id}: {total}')

cur.close()
conn.close()
