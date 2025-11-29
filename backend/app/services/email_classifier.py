"""
Servico de Classificacao de Emails para Sistema de Compras
Implementa classificacao multi-camada: ASSUNTO -> REMETENTE -> IA -> MANUAL
"""
import re
import json
from typing import Optional, List, Tuple
from datetime import datetime
from email.header import decode_header
from sqlalchemy.orm import Session
from app.models.email_processado import EmailProcessado, StatusEmailProcessado, MetodoClassificacao
from app.models.cotacao import SolicitacaoCotacao, PropostaFornecedor, StatusProposta
from app.models.fornecedor import Fornecedor
from app.services.email_service import email_service
from app.services.ai_service import ai_service


class EmailClassifier:
    """
    Servico de classificacao automatica de emails de cotacao

    Estrategia de classificacao em camadas:
    1. ASSUNTO - Busca padrao "COTACAO #XXX" no assunto
    2. REMETENTE - Associa pelo email do fornecedor cadastrado
    3. IA - Analise de conteudo pela Claude para emails orfaos
    4. MANUAL - Emails que nao puderam ser classificados automaticamente
    """

    # Padroes para extrair ID da solicitacao do assunto
    # Suporta tanto formato com ID numerico quanto com numero formatado (SOL-2024-XXXX ou SC-2025-XXXX)
    PADROES_ASSUNTO = [
        r'COTACAO\s*#\s*(\d+)',
        r'COTACAO-(\d+)',
        r'COTACAO\s+(\d+)',
        r'Re:\s*\[COTACAO\s*#\s*(\d+)\]',
        r'\[COTACAO\s+SOL-\d{4}-(\d+)\]',  # [COTAÇÃO SOL-2024-0001] -> extrai 0001
        r'\[COTACAO\s+SC-\d{4}-(\d+)\]',  # [COTAÇÃO SC-2025-00001] -> extrai 00001
        r'SOL-\d{4}-(\d+)',  # SOL-2024-0001 -> extrai 0001
        r'SC-\d{4}-(\d+)',  # SC-2025-00001 -> extrai 00001
        r'Referencia:\s*COTACAO-(\d+)',  # Referência: COTACAO-123
    ]

    def processar_emails_novos(
        self,
        db: Session,
        tenant_id: int,
        dias_atras: int = 7
    ) -> dict:
        """
        Processa emails novos da caixa de entrada

        Args:
            db: Sessao do banco de dados
            tenant_id: ID do tenant
            dias_atras: Quantos dias atras buscar

        Returns:
            Dict com estatisticas do processamento
        """
        if not email_service.is_configured:
            return {"error": "Servico de email nao configurado"}

        stats = {
            "total_lidos": 0,
            "novos": 0,
            "classificados_assunto": 0,
            "classificados_remetente": 0,
            "classificados_ia": 0,
            "pendentes_manual": 0,
            "erros": 0
        }

        try:
            # Ler emails da caixa de entrada
            emails = self._ler_emails_inbox(dias_atras)
            stats["total_lidos"] = len(emails)

            for email_data in emails:
                try:
                    # Verificar se ja foi processado
                    email_existente = db.query(EmailProcessado).filter(
                        EmailProcessado.tenant_id == tenant_id,
                        EmailProcessado.email_uid == email_data['uid']
                    ).first()

                    if email_existente:
                        continue

                    stats["novos"] += 1

                    # Criar registro do email
                    email_processado = self._criar_registro_email(
                        db, tenant_id, email_data
                    )

                    # Tentar classificar em camadas
                    metodo, solicitacao_id, fornecedor_id, confianca = self._classificar_email(
                        db, tenant_id, email_data
                    )

                    if metodo:
                        email_processado.metodo_classificacao = metodo
                        email_processado.solicitacao_id = solicitacao_id
                        email_processado.fornecedor_id = fornecedor_id
                        email_processado.confianca_ia = confianca
                        email_processado.status = StatusEmailProcessado.CLASSIFICADO

                        # Atualizar estatisticas
                        if metodo == MetodoClassificacao.ASSUNTO:
                            stats["classificados_assunto"] += 1
                        elif metodo == MetodoClassificacao.REMETENTE:
                            stats["classificados_remetente"] += 1
                        elif metodo == MetodoClassificacao.IA:
                            stats["classificados_ia"] += 1

                        # Se tem solicitacao e fornecedor, marcar proposta como RECEBIDA
                        if solicitacao_id and fornecedor_id:
                            # Primeiro, marcar proposta como RECEBIDA (mesmo sem dados extraidos)
                            proposta_id = self._marcar_proposta_recebida(
                                db, tenant_id, solicitacao_id, fornecedor_id
                            )
                            if proposta_id:
                                email_processado.proposta_id = proposta_id

                            # Tentar extrair dados da proposta via IA
                            dados_extraidos = self._extrair_dados_proposta(
                                email_data['corpo'],
                                email_data.get('conteudo_pdf')
                            )
                            if dados_extraidos:
                                email_processado.dados_extraidos = json.dumps(dados_extraidos)
                                # Atualizar proposta com os dados extraidos
                                self._atualizar_proposta_com_dados(
                                    db, tenant_id, solicitacao_id, fornecedor_id, dados_extraidos
                                )

                    else:
                        email_processado.status = StatusEmailProcessado.PENDENTE
                        stats["pendentes_manual"] += 1

                    email_processado.processado_em = datetime.utcnow()
                    db.commit()

                except Exception as e:
                    print(f"[CLASSIFICADOR] Erro ao processar email: {e}")
                    stats["erros"] += 1
                    db.rollback()

        except Exception as e:
            return {"error": f"Erro ao ler emails: {str(e)}"}

        return stats

    def _ler_emails_inbox(self, dias_atras: int) -> List[dict]:
        """
        Le emails da caixa de entrada usando IMAP
        """
        import imaplib
        import email as email_lib
        from datetime import timedelta

        emails = []
        mail = None

        try:
            mail = imaplib.IMAP4_SSL(
                email_service.imap_host,
                email_service.imap_port
            )
            mail.login(email_service.smtp_user, email_service.smtp_password)
            mail.select('INBOX')

            # Buscar emails dos ultimos N dias
            data_inicio = (datetime.now() - timedelta(days=dias_atras)).strftime('%d-%b-%Y')
            status, messages = mail.search(None, f'(SINCE "{data_inicio}")')

            if status != 'OK':
                print(f"[CLASSIFICADOR] Erro na busca IMAP: status={status}")
                return []

            email_ids = messages[0].split()
            print(f"[CLASSIFICADOR] Encontrados {len(email_ids)} emails nos ultimos {dias_atras} dias")

            for email_id in email_ids:
                try:
                    status, msg_data = mail.fetch(email_id, '(RFC822 UID)')
                    if status != 'OK':
                        continue

                    # Extrair UID
                    uid_match = re.search(rb'UID (\d+)', msg_data[0][0])
                    uid = uid_match.group(1).decode() if uid_match else email_id.decode()

                    raw_email = msg_data[0][1]
                    msg = email_lib.message_from_bytes(raw_email)

                    # Extrair dados
                    remetente = self._decode_header(msg['From'])
                    assunto = self._decode_header(msg['Subject'])
                    data_str = msg['Date']
                    message_id = msg.get('Message-ID', '')

                    # Extrair email do remetente
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+', remetente)
                    email_remetente = email_match.group(0) if email_match else remetente

                    # Extrair nome do remetente
                    nome_match = re.match(r'^([^<]+)', remetente)
                    nome_remetente = nome_match.group(1).strip() if nome_match else None

                    # Extrair corpo
                    corpo = self._extrair_corpo(msg)

                    # Extrair conteudo de anexos PDF
                    conteudo_pdf = self._extrair_anexos_pdf(msg)

                    # Parsear data
                    try:
                        from email.utils import parsedate_to_datetime
                        data_recebimento = parsedate_to_datetime(data_str)
                    except:
                        data_recebimento = datetime.utcnow()

                    emails.append({
                        'uid': uid,
                        'message_id': message_id,
                        'remetente': email_remetente,
                        'remetente_nome': nome_remetente,
                        'assunto': assunto or '',
                        'data_recebimento': data_recebimento,
                        'corpo': corpo,
                        'conteudo_pdf': conteudo_pdf
                    })

                except Exception as e:
                    print(f"[CLASSIFICADOR] Erro ao processar email ID {email_id}: {e}")
                    continue

        except Exception as e:
            print(f"[CLASSIFICADOR] Erro ao conectar IMAP: {e}")

        finally:
            # Garantir logout mesmo em caso de erro
            if mail:
                try:
                    mail.logout()
                except:
                    pass

        return emails

    def _decode_header(self, header: str) -> str:
        """Decodifica header de email"""
        if not header:
            return ""

        decoded_parts = decode_header(header)
        result = []

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(encoding or 'utf-8', errors='ignore'))
            else:
                result.append(part)

        return ' '.join(result)

    def _extrair_corpo(self, msg) -> str:
        """Extrai corpo do email"""
        corpo = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()

                if content_type == 'text/plain':
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        corpo = payload.decode(charset, errors='ignore')
                        break
                elif content_type == 'text/html' and not corpo:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        html_content = payload.decode(charset, errors='ignore')
                        corpo = re.sub(r'<[^>]+>', ' ', html_content)
                        corpo = re.sub(r'\s+', ' ', corpo).strip()
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                corpo = payload.decode(charset, errors='ignore')

        return corpo

    def _extrair_anexos_pdf(self, msg) -> str:
        """
        Extrai texto de anexos PDF do email.

        Args:
            msg: Mensagem de email

        Returns:
            Texto concatenado de todos os PDFs anexados
        """
        textos_pdf = []

        if not msg.is_multipart():
            return ""

        for part in msg.walk():
            content_type = part.get_content_type()
            filename = part.get_filename()

            # Verificar se e um PDF
            if content_type == 'application/pdf' or (filename and filename.lower().endswith('.pdf')):
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        texto = self._extrair_texto_pdf(payload)
                        if texto:
                            textos_pdf.append(f"[Anexo: {filename or 'documento.pdf'}]\n{texto}")
                except Exception as e:
                    print(f"[CLASSIFICADOR] Erro ao extrair PDF {filename}: {e}")
                    continue

        return "\n\n".join(textos_pdf)

    def _extrair_texto_pdf(self, pdf_bytes: bytes) -> str:
        """
        Extrai texto E campos de formulario (AcroForm) de um arquivo PDF.

        IMPORTANTE: PDFs preenchíveis armazenam valores em campos de formulário,
        não como texto visível. Esta função extrai AMBOS e formata de maneira
        estruturada para facilitar a análise pela IA.

        Args:
            pdf_bytes: Conteudo do PDF em bytes

        Returns:
            Texto extraido do PDF incluindo valores de campos de formulário
        """
        try:
            import io
            import re

            # Tentar usar PyPDF2/pypdf (preferido por suportar AcroForm)
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(pdf_bytes))

                # CRITICO: Extrair campos de formulario AcroForm PRIMEIRO
                campos_formulario = ""
                try:
                    fields = reader.get_fields()
                    if fields:
                        # Separar campos por tipo para formatação estruturada
                        itens_proposta = {}  # {indice: {preco_unit, total}}
                        dados_gerais = {}  # prazo, condicoes, frete, etc.

                        for nome_campo, info_campo in fields.items():
                            # Extrair valor do campo (/V = Value)
                            valor = None
                            if isinstance(info_campo, dict):
                                valor = info_campo.get('/V') or info_campo.get('value')
                            elif hasattr(info_campo, 'value'):
                                valor = info_campo.value

                            if valor:
                                valor_str = str(valor).strip()
                                print(f"[PDF] Campo encontrado: {nome_campo} = {valor_str}")

                                # Identificar campos de itens (preco_unit_0, total_0, etc.)
                                match_preco = re.match(r'preco_unit_(\d+)', nome_campo)
                                match_total = re.match(r'total_(\d+)', nome_campo)

                                if match_preco:
                                    idx = int(match_preco.group(1))
                                    if idx not in itens_proposta:
                                        itens_proposta[idx] = {}
                                    itens_proposta[idx]['preco_unitario'] = valor_str
                                elif match_total:
                                    idx = int(match_total.group(1))
                                    if idx not in itens_proposta:
                                        itens_proposta[idx] = {}
                                    itens_proposta[idx]['total'] = valor_str
                                else:
                                    # Campo geral (prazo, condicoes, etc.)
                                    dados_gerais[nome_campo] = valor_str

                        # Formatar saída de maneira estruturada para a IA
                        campos_formulario = "=== DADOS DA PROPOSTA EXTRAÍDOS DO PDF ===\n\n"

                        if itens_proposta:
                            campos_formulario += "PREÇOS POR ITEM:\n"
                            for idx in sorted(itens_proposta.keys()):
                                item_data = itens_proposta[idx]
                                campos_formulario += f"  Item {idx + 1}:\n"
                                if 'preco_unitario' in item_data:
                                    campos_formulario += f"    - Preço Unitário: R$ {item_data['preco_unitario']}\n"
                                if 'total' in item_data:
                                    campos_formulario += f"    - Total: R$ {item_data['total']}\n"
                            campos_formulario += "\n"

                        if dados_gerais:
                            campos_formulario += "DADOS GERAIS:\n"
                            mapeamento_campos = {
                                'prazo_entrega': 'Prazo de Entrega (dias)',
                                'condicoes_pagamento': 'Condições de Pagamento',
                                'frete': 'Frete',
                                'validade': 'Validade da Proposta (dias)',
                                'observacoes': 'Observações'
                            }
                            for campo, valor in dados_gerais.items():
                                nome_amigavel = mapeamento_campos.get(campo, campo)
                                campos_formulario += f"  - {nome_amigavel}: {valor}\n"

                        campos_formulario += "\n=== FIM DOS DADOS DO PDF ===\n\n"
                        print(f"[PDF] Total de campos extraidos: {len(fields)}")
                        print(f"[PDF] Itens com preço: {len(itens_proposta)}")
                except Exception as e:
                    print(f"[PDF] Erro ao extrair campos AcroForm: {e}")

                # Extrair texto visivel das paginas
                texto_paginas = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        texto_paginas += page_text + "\n"

                # Combinar: campos do formulario TEM PRIORIDADE
                resultado = campos_formulario + texto_paginas
                return resultado.strip()

            except ImportError:
                print("[PDF] pypdf nao disponivel, tentando alternativas...")

            # Tentar usar PyMuPDF (fitz) - tambem suporta widgets/formularios
            try:
                import fitz
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")

                campos_formulario = ""
                texto_paginas = ""

                for page in doc:
                    # Extrair widgets (campos de formulario) da pagina
                    try:
                        for widget in page.widgets():
                            if widget.field_value:
                                nome = widget.field_name or "campo"
                                valor = widget.field_value
                                campos_formulario += f"{nome}: {valor}\n"
                                print(f"[PDF/fitz] Campo: {nome} = {valor}")
                    except Exception as e:
                        print(f"[PDF/fitz] Erro ao extrair widgets: {e}")

                    texto_paginas += page.get_text() + "\n"

                doc.close()

                if campos_formulario:
                    campos_formulario = "=== VALORES PREENCHIDOS NO FORMULARIO ===\n" + campos_formulario + "=== FIM DOS CAMPOS DO FORMULARIO ===\n\n"

                return (campos_formulario + texto_paginas).strip()

            except ImportError:
                pass

            # Tentar usar pdfplumber (fallback - nao extrai formularios bem)
            try:
                import pdfplumber
                print("[PDF] Usando pdfplumber (campos de formulario podem nao ser extraidos)")
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    texto = ""
                    for page in pdf.pages:
                        texto += (page.extract_text() or "") + "\n"
                return texto.strip()
            except ImportError:
                pass

            print("[CLASSIFICADOR] Nenhuma biblioteca de PDF disponivel (pypdf, PyMuPDF ou pdfplumber)")
            return ""

        except Exception as e:
            print(f"[CLASSIFICADOR] Erro ao extrair texto do PDF: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def _criar_registro_email(
        self,
        db: Session,
        tenant_id: int,
        email_data: dict
    ) -> EmailProcessado:
        """Cria registro de email processado no banco"""
        email_processado = EmailProcessado(
            tenant_id=tenant_id,
            email_uid=email_data['uid'],
            message_id=email_data.get('message_id'),
            remetente=email_data['remetente'],
            remetente_nome=email_data.get('remetente_nome'),
            assunto=email_data['assunto'][:500] if email_data['assunto'] else '',
            data_recebimento=email_data['data_recebimento'],
            corpo_resumo=email_data['corpo'][:1000] if email_data['corpo'] else None,
            corpo_completo=email_data['corpo'],
            status='pendente'  # Usando string diretamente para compatibilidade com PostgreSQL
        )

        db.add(email_processado)
        db.flush()

        return email_processado

    def _classificar_email(
        self,
        db: Session,
        tenant_id: int,
        email_data: dict
    ) -> Tuple[Optional[MetodoClassificacao], Optional[int], Optional[int], Optional[int]]:
        """
        Classifica email usando estrategia em camadas

        Returns:
            Tupla (metodo, solicitacao_id, fornecedor_id, confianca)
        """
        # CAMADA 1: Classificacao por ASSUNTO
        solicitacao_id = self._classificar_por_assunto(db, tenant_id, email_data['assunto'])
        if solicitacao_id:
            # Tentar encontrar fornecedor pelo remetente
            fornecedor_id = self._buscar_fornecedor_por_email(db, tenant_id, email_data['remetente'])
            return (MetodoClassificacao.ASSUNTO, solicitacao_id, fornecedor_id, 100)

        # CAMADA 2: Classificacao por REMETENTE
        fornecedor_id = self._buscar_fornecedor_por_email(db, tenant_id, email_data['remetente'])
        if fornecedor_id:
            # Buscar solicitacoes em aberto para este fornecedor
            solicitacao_id = self._buscar_solicitacao_aberta_fornecedor(db, tenant_id, fornecedor_id)
            if solicitacao_id:
                return (MetodoClassificacao.REMETENTE, solicitacao_id, fornecedor_id, 80)

        # CAMADA 3: Classificacao por IA
        if ai_service.is_available:
            resultado_ia = self._classificar_por_ia(
                db, tenant_id, email_data['assunto'], email_data['corpo']
            )
            if resultado_ia:
                return resultado_ia

        # Nenhuma classificacao automatica possivel
        return (None, None, fornecedor_id, None)

    def _classificar_por_assunto(
        self,
        db: Session,
        tenant_id: int,
        assunto: str
    ) -> Optional[int]:
        """
        Tenta extrair ID da solicitacao do assunto do email
        """
        if not assunto:
            return None

        # Normalizar assunto: remover acentos e converter para maiusculas
        import unicodedata
        assunto_normalizado = unicodedata.normalize('NFD', assunto)
        assunto_normalizado = ''.join(c for c in assunto_normalizado if unicodedata.category(c) != 'Mn')
        assunto_normalizado = assunto_normalizado.upper()

        # Primeiro tentar extrair numero formatado completo (SC-2025-00001 ou SOL-2024-0001)
        match_numero = re.search(r'(SC|SOL)-(\d{4})-(\d+)', assunto_normalizado)
        if match_numero:
            numero_formatado = f"{match_numero.group(1)}-{match_numero.group(2)}-{match_numero.group(3)}"
            solicitacao = db.query(SolicitacaoCotacao).filter(
                SolicitacaoCotacao.tenant_id == tenant_id,
                SolicitacaoCotacao.numero == numero_formatado
            ).first()
            if solicitacao:
                return solicitacao.id

        # Fallback: tentar extrair ID numerico
        for padrao in self.PADROES_ASSUNTO:
            match = re.search(padrao, assunto_normalizado)
            if match:
                solicitacao_id = int(match.group(1))
                # Verificar se solicitacao existe por ID
                solicitacao = db.query(SolicitacaoCotacao).filter(
                    SolicitacaoCotacao.tenant_id == tenant_id,
                    SolicitacaoCotacao.id == solicitacao_id
                ).first()

                if solicitacao:
                    return solicitacao_id

        return None

    def _buscar_fornecedor_por_email(
        self,
        db: Session,
        tenant_id: int,
        email_remetente: str
    ) -> Optional[int]:
        """
        Busca fornecedor cadastrado pelo email
        """
        if not email_remetente:
            return None

        fornecedor = db.query(Fornecedor).filter(
            Fornecedor.tenant_id == tenant_id,
            Fornecedor.email_principal == email_remetente,
            Fornecedor.ativo == True
        ).first()

        return fornecedor.id if fornecedor else None

    def _buscar_solicitacao_aberta_fornecedor(
        self,
        db: Session,
        tenant_id: int,
        fornecedor_id: int
    ) -> Optional[int]:
        """
        Busca solicitacoes em aberto que foram enviadas para este fornecedor
        """
        from app.models.cotacao import StatusSolicitacao

        # Buscar solicitacoes EM_COTACAO ou ENVIADA que tem proposta pendente do fornecedor
        proposta = db.query(PropostaFornecedor).join(
            SolicitacaoCotacao,
            PropostaFornecedor.solicitacao_id == SolicitacaoCotacao.id
        ).filter(
            SolicitacaoCotacao.tenant_id == tenant_id,
            PropostaFornecedor.fornecedor_id == fornecedor_id,
            SolicitacaoCotacao.status.in_([StatusSolicitacao.EM_COTACAO, StatusSolicitacao.ENVIADA])
        ).order_by(
            PropostaFornecedor.created_at.desc()
        ).first()

        if proposta:
            return proposta.solicitacao_id

        return None

    def _classificar_por_ia(
        self,
        db: Session,
        tenant_id: int,
        assunto: str,
        corpo: str
    ) -> Optional[Tuple[MetodoClassificacao, Optional[int], Optional[int], int]]:
        """
        Usa IA para classificar email orfao
        """
        from app.models.cotacao import StatusSolicitacao

        # Buscar solicitacoes em aberto do tenant (ENVIADA ou EM_COTACAO)
        solicitacoes_abertas = db.query(SolicitacaoCotacao).filter(
            SolicitacaoCotacao.tenant_id == tenant_id,
            SolicitacaoCotacao.status.in_([StatusSolicitacao.ENVIADA, StatusSolicitacao.EM_COTACAO])
        ).all()

        if not solicitacoes_abertas:
            return None

        # Montar contexto para a IA
        contexto_solicitacoes = []
        for sol in solicitacoes_abertas:
            itens_desc = []
            for item in sol.itens:
                if item.produto:
                    itens_desc.append(f"- {item.produto.nome} ({item.quantidade} {item.produto.unidade_medida})")

            contexto_solicitacoes.append({
                "id": sol.id,
                "numero": sol.numero,
                "titulo": sol.titulo,
                "itens": itens_desc
            })

        prompt = f"""
Analise este email e identifique se e uma resposta a alguma das solicitacoes de cotacao listadas abaixo.

## EMAIL
Assunto: {assunto}
Corpo: {corpo[:2000]}

## SOLICITACOES EM ABERTO
{json.dumps(contexto_solicitacoes, indent=2, ensure_ascii=False)}

## INSTRUCOES
Responda APENAS com JSON no formato:
{{
    "e_proposta_cotacao": true/false,
    "solicitacao_id": <ID da solicitacao relacionada ou null>,
    "confianca": <0 a 100>,
    "motivo": "<explicacao>"
}}
"""

        try:
            response = ai_service.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
                system="Voce e um assistente que classifica emails de resposta a cotacoes. Responda apenas em JSON."
            )

            content = response.content[0].text

            # Parsear JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            resultado = json.loads(content.strip())

            if resultado.get('e_proposta_cotacao') and resultado.get('solicitacao_id'):
                # Verificar se solicitacao existe
                sol_id = resultado['solicitacao_id']
                if any(s.id == sol_id for s in solicitacoes_abertas):
                    return (
                        MetodoClassificacao.IA,
                        sol_id,
                        None,
                        resultado.get('confianca', 50)
                    )

        except Exception as e:
            print(f"[CLASSIFICADOR] Erro na classificacao por IA: {e}")

        return None

    def _extrair_dados_proposta(self, corpo: str, conteudo_pdf: str = None) -> Optional[dict]:
        """
        Extrai dados da proposta do corpo do email usando IA

        Args:
            corpo: Corpo do email
            conteudo_pdf: Conteudo extraido de anexos PDF (opcional)

        Returns:
            Dict com dados extraidos ou None
        """
        if not ai_service.is_available:
            return None

        # Se nao tiver corpo nem PDF, nao ha o que extrair
        if not corpo and not conteudo_pdf:
            return None

        return ai_service.extrair_dados_proposta_email(corpo or "", conteudo_pdf)

    def _marcar_proposta_recebida(
        self,
        db: Session,
        tenant_id: int,
        solicitacao_id: int,
        fornecedor_id: int
    ) -> Optional[int]:
        """
        Marca uma proposta como RECEBIDA quando um email de resposta e identificado.
        Se a proposta nao existir, CRIA uma nova proposta.
        Isso acontece ANTES da extracao de dados, garantindo que a proposta
        seja marcada mesmo que a IA nao consiga extrair os dados.

        Args:
            db: Sessao do banco
            tenant_id: ID do tenant
            solicitacao_id: ID da solicitacao
            fornecedor_id: ID do fornecedor

        Returns:
            ID da proposta ou None se erro
        """
        # Buscar proposta existente
        proposta = db.query(PropostaFornecedor).filter(
            PropostaFornecedor.solicitacao_id == solicitacao_id,
            PropostaFornecedor.fornecedor_id == fornecedor_id,
            PropostaFornecedor.tenant_id == tenant_id
        ).first()

        try:
            if not proposta:
                # CRIAR nova proposta se nao existir
                print(f"[CLASSIFICADOR] Criando proposta para solicitacao={solicitacao_id}, fornecedor={fornecedor_id}")
                proposta = PropostaFornecedor(
                    solicitacao_id=solicitacao_id,
                    fornecedor_id=fornecedor_id,
                    tenant_id=tenant_id,
                    status=StatusProposta.RECEBIDA,
                    data_recebimento=datetime.utcnow()
                )
                db.add(proposta)
                db.flush()
                print(f"[CLASSIFICADOR] Proposta {proposta.id} CRIADA como RECEBIDA")
            elif proposta.status == StatusProposta.PENDENTE:
                # Marcar como RECEBIDA (se ainda nao estiver)
                proposta.status = StatusProposta.RECEBIDA
                proposta.data_recebimento = datetime.utcnow()
                db.flush()
                print(f"[CLASSIFICADOR] Proposta {proposta.id} marcada como RECEBIDA")

            return proposta.id

        except Exception as e:
            print(f"[CLASSIFICADOR] Erro ao criar/marcar proposta como recebida: {e}")
            return None

    def _atualizar_proposta_com_dados(
        self,
        db: Session,
        tenant_id: int,
        solicitacao_id: int,
        fornecedor_id: int,
        dados_extraidos: dict
    ) -> Optional[int]:
        """
        Atualiza uma proposta existente com os dados extraidos do email

        Args:
            db: Sessao do banco
            tenant_id: ID do tenant
            solicitacao_id: ID da solicitacao
            fornecedor_id: ID do fornecedor
            dados_extraidos: Dados extraidos pela IA

        Returns:
            ID da proposta atualizada ou None
        """
        from app.models.cotacao import ItemSolicitacao, ItemProposta

        # Buscar proposta existente
        proposta = db.query(PropostaFornecedor).filter(
            PropostaFornecedor.solicitacao_id == solicitacao_id,
            PropostaFornecedor.fornecedor_id == fornecedor_id,
            PropostaFornecedor.tenant_id == tenant_id
        ).first()

        if not proposta:
            print(f"[CLASSIFICADOR] Proposta nao encontrada para solicitacao={solicitacao_id}, fornecedor={fornecedor_id}")
            return None

        try:
            # Atualizar dados gerais da proposta
            if dados_extraidos.get('prazo_entrega_dias') is not None:
                proposta.prazo_entrega = dados_extraidos['prazo_entrega_dias']

            if dados_extraidos.get('condicoes_pagamento'):
                proposta.condicoes_pagamento = dados_extraidos['condicoes_pagamento']

            if dados_extraidos.get('observacoes'):
                proposta.observacoes = dados_extraidos['observacoes']

            if dados_extraidos.get('frete_incluso') is not None:
                proposta.frete_tipo = 'CIF' if dados_extraidos['frete_incluso'] else 'FOB'

            if dados_extraidos.get('frete_valor') is not None:
                proposta.frete_valor = dados_extraidos['frete_valor']

            if dados_extraidos.get('validade_proposta_dias') is not None:
                from datetime import datetime, timedelta
                try:
                    dias = int(dados_extraidos['validade_proposta_dias'])
                    proposta.validade_proposta = datetime.utcnow() + timedelta(days=dias)
                except:
                    pass

            # Atualizar valor total
            if dados_extraidos.get('preco_total_proposta'):
                proposta.valor_total = dados_extraidos['preco_total_proposta']

            # Buscar TODOS os itens da solicitacao (na ordem)
            itens_solicitacao = db.query(ItemSolicitacao).filter(
                ItemSolicitacao.solicitacao_id == solicitacao_id
            ).order_by(ItemSolicitacao.id).all()

            # Extrair precos por item do novo formato
            itens_extraidos = dados_extraidos.get('itens', [])

            # Compatibilidade com formato antigo (preco_unitario unico)
            preco_unitario_geral = dados_extraidos.get('preco_unitario')
            marca_geral = dados_extraidos.get('marca_produto')

            print(f"[CLASSIFICADOR] Itens da solicitacao: {len(itens_solicitacao)}, Itens extraidos: {len(itens_extraidos)}")

            # Processar cada item da solicitacao
            for idx, item_solicitacao in enumerate(itens_solicitacao):
                # Buscar preco especifico para este item
                preco_item = None
                marca_item = None

                # Tentar encontrar item extraido pelo indice (aceitar base-0 ou base-1)
                for item_ext in itens_extraidos:
                    item_idx = item_ext.get('indice')
                    # Aceitar indice 0 ou 1 para o primeiro item, 1 ou 2 para o segundo, etc.
                    if item_idx == idx or item_idx == idx + 1:
                        preco_item = item_ext.get('preco_unitario')
                        marca_item = item_ext.get('marca')
                        print(f"[CLASSIFICADOR] Item {idx}: encontrado por indice {item_idx}, preco={preco_item}")
                        break

                # Se nao encontrou por indice, tentar pela posicao na lista
                if preco_item is None and idx < len(itens_extraidos):
                    item_ext = itens_extraidos[idx]
                    preco_item = item_ext.get('preco_unitario')
                    marca_item = item_ext.get('marca')
                    print(f"[CLASSIFICADOR] Item {idx}: usando posicao direta, preco={preco_item}")

                # Se ainda nao encontrou, usar preco geral (formato antigo)
                if preco_item is None and preco_unitario_geral:
                    preco_item = preco_unitario_geral
                    marca_item = marca_geral
                    print(f"[CLASSIFICADOR] Item {idx}: usando preco geral={preco_item}")

                # Se ainda nao tem preco, pular
                if preco_item is None:
                    print(f"[CLASSIFICADOR] Item {idx}: sem preco encontrado, pulando")
                    continue

                # Verificar se ja existe ItemProposta
                item_proposta = db.query(ItemProposta).filter(
                    ItemProposta.proposta_id == proposta.id,
                    ItemProposta.item_solicitacao_id == item_solicitacao.id
                ).first()

                if item_proposta:
                    # Atualizar existente
                    item_proposta.preco_unitario = preco_item
                    item_proposta.preco_final = preco_item
                    if marca_item:
                        item_proposta.marca_oferecida = marca_item
                else:
                    # Criar novo
                    item_proposta = ItemProposta(
                        proposta_id=proposta.id,
                        item_solicitacao_id=item_solicitacao.id,
                        preco_unitario=preco_item,
                        preco_final=preco_item,
                        quantidade_disponivel=item_solicitacao.quantidade,
                        marca_oferecida=marca_item,
                        tenant_id=tenant_id
                    )
                    db.add(item_proposta)

            # Calcular valor total se nao foi fornecido
            if not proposta.valor_total:
                total = sum(
                    (item.get('preco_unitario', 0) or 0) * (itens_solicitacao[item.get('indice', 0)].quantidade if item.get('indice', 0) < len(itens_solicitacao) else 1)
                    for item in itens_extraidos
                    if item.get('preco_unitario')
                )
                if total > 0:
                    proposta.valor_total = total

            db.flush()

            print(f"[CLASSIFICADOR] Proposta {proposta.id} atualizada: "
                  f"valor={proposta.valor_total}, prazo={proposta.prazo_entrega}, "
                  f"pagamento={proposta.condicoes_pagamento}, itens_criados={len(itens_solicitacao)}")

            return proposta.id

        except Exception as e:
            print(f"[CLASSIFICADOR] Erro ao atualizar proposta: {e}")
            return None

    def classificar_manualmente(
        self,
        db: Session,
        email_id: int,
        solicitacao_id: Optional[int],
        fornecedor_id: Optional[int],
        ignorar: bool = False
    ) -> bool:
        """
        Classifica email manualmente pelo usuario

        Args:
            db: Sessao do banco
            email_id: ID do email processado
            solicitacao_id: ID da solicitacao relacionada
            fornecedor_id: ID do fornecedor
            ignorar: Se True, marca email para ignorar

        Returns:
            True se classificado com sucesso
        """
        email = db.query(EmailProcessado).filter(
            EmailProcessado.id == email_id
        ).first()

        if not email:
            return False

        if ignorar:
            email.status = StatusEmailProcessado.IGNORADO
            email.metodo_classificacao = MetodoClassificacao.MANUAL
        else:
            email.solicitacao_id = solicitacao_id
            email.fornecedor_id = fornecedor_id
            email.status = StatusEmailProcessado.CLASSIFICADO
            email.metodo_classificacao = MetodoClassificacao.MANUAL

            # Extrair dados se tiver corpo
            if email.corpo_completo:
                dados = self._extrair_dados_proposta(email.corpo_completo)
                if dados:
                    email.dados_extraidos = json.dumps(dados)

        email.processado_em = datetime.utcnow()
        db.commit()

        return True

    def criar_proposta_de_email(
        self,
        db: Session,
        email_id: int
    ) -> Optional[int]:
        """
        Cria uma proposta de fornecedor a partir de um email classificado

        Args:
            db: Sessao do banco
            email_id: ID do email processado

        Returns:
            ID da proposta criada ou None
        """
        email = db.query(EmailProcessado).filter(
            EmailProcessado.id == email_id,
            EmailProcessado.status == StatusEmailProcessado.CLASSIFICADO
        ).first()

        if not email or not email.solicitacao_id or not email.fornecedor_id:
            return None

        # Verificar se ja existe proposta
        proposta_existente = db.query(PropostaFornecedor).filter(
            PropostaFornecedor.solicitacao_id == email.solicitacao_id,
            PropostaFornecedor.fornecedor_id == email.fornecedor_id
        ).first()

        if proposta_existente:
            # Atualizar proposta existente com dados do email
            email.proposta_id = proposta_existente.id
            db.commit()
            return proposta_existente.id

        # Criar nova proposta
        dados_extraidos = {}
        if email.dados_extraidos:
            try:
                dados_extraidos = json.loads(email.dados_extraidos)
            except:
                pass

        proposta = PropostaFornecedor(
            solicitacao_id=email.solicitacao_id,
            fornecedor_id=email.fornecedor_id,
            tenant_id=email.tenant_id,  # IMPORTANTE: definir tenant_id
            prazo_entrega=dados_extraidos.get('prazo_entrega_dias'),
            condicoes_pagamento=dados_extraidos.get('condicoes_pagamento'),
            frete_incluso=dados_extraidos.get('frete_incluso', False),
            frete_valor=dados_extraidos.get('frete_valor'),
            observacoes=dados_extraidos.get('observacoes'),
            status=StatusProposta.PENDENTE
        )

        db.add(proposta)
        db.flush()

        email.proposta_id = proposta.id
        db.commit()

        return proposta.id


# Instancia global
email_classifier = EmailClassifier()
