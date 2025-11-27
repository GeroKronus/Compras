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
    PADROES_ASSUNTO = [
        r'COTACAO\s*#\s*(\d+)',
        r'COTACAO-(\d+)',
        r'COTACAO\s+(\d+)',
        r'Re:\s*\[COTACAO\s*#\s*(\d+)\]',
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

                        # Se tem solicitacao e fornecedor, extrair dados da proposta
                        if solicitacao_id and fornecedor_id:
                            dados_extraidos = self._extrair_dados_proposta(
                                email_data['corpo'],
                                email_data.get('conteudo_pdf')
                            )
                            if dados_extraidos:
                                email_processado.dados_extraidos = json.dumps(dados_extraidos)

                                # Atualizar proposta existente com os dados extraidos
                                proposta_id = self._atualizar_proposta_com_dados(
                                    db, tenant_id, solicitacao_id, fornecedor_id, dados_extraidos
                                )
                                if proposta_id:
                                    email_processado.proposta_id = proposta_id

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
                return []

            email_ids = messages[0].split()

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

            mail.logout()

        except Exception as e:
            print(f"[CLASSIFICADOR] Erro ao conectar IMAP: {e}")

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
        Extrai texto de um arquivo PDF em bytes.

        Args:
            pdf_bytes: Conteudo do PDF em bytes

        Returns:
            Texto extraido do PDF
        """
        try:
            import io

            # Tentar usar PyPDF2/pypdf
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(pdf_bytes))
                texto = ""
                for page in reader.pages:
                    texto += page.extract_text() + "\n"
                return texto.strip()
            except ImportError:
                pass

            # Tentar usar PyMuPDF (fitz)
            try:
                import fitz
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                texto = ""
                for page in doc:
                    texto += page.get_text() + "\n"
                doc.close()
                return texto.strip()
            except ImportError:
                pass

            # Tentar usar pdfplumber
            try:
                import pdfplumber
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

        for padrao in self.PADROES_ASSUNTO:
            match = re.search(padrao, assunto.upper())
            if match:
                solicitacao_id = int(match.group(1))
                # Verificar se solicitacao existe
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

        # Buscar solicitacoes em aberto do tenant
        solicitacoes_abertas = db.query(SolicitacaoCotacao).filter(
            SolicitacaoCotacao.tenant_id == tenant_id,
            SolicitacaoCotacao.status == StatusSolicitacao.EM_COTACAO
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
            # Atualizar dados da proposta
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

            if dados_extraidos.get('validade_proposta'):
                from datetime import datetime
                try:
                    proposta.validade_proposta = datetime.strptime(
                        dados_extraidos['validade_proposta'], '%Y-%m-%d'
                    )
                except:
                    pass

            # Se tiver preco, atualizar valor total e criar/atualizar ItemProposta
            preco_total = dados_extraidos.get('preco_total')
            preco_unitario = dados_extraidos.get('preco_unitario')

            if preco_total:
                proposta.valor_total = preco_total
            elif preco_unitario and dados_extraidos.get('quantidade'):
                proposta.valor_total = preco_unitario * dados_extraidos['quantidade']

            # Criar ItemProposta se tiver preco unitario
            if preco_unitario:
                # Buscar primeiro item da solicitacao
                item_solicitacao = db.query(ItemSolicitacao).filter(
                    ItemSolicitacao.solicitacao_id == solicitacao_id
                ).first()

                if item_solicitacao:
                    # Verificar se ja existe ItemProposta
                    item_proposta = db.query(ItemProposta).filter(
                        ItemProposta.proposta_id == proposta.id,
                        ItemProposta.item_solicitacao_id == item_solicitacao.id
                    ).first()

                    if item_proposta:
                        # Atualizar existente
                        item_proposta.preco_unitario = preco_unitario
                        item_proposta.preco_final = preco_unitario
                        if dados_extraidos.get('marca_produto'):
                            item_proposta.marca_oferecida = dados_extraidos['marca_produto']
                    else:
                        # Criar novo
                        item_proposta = ItemProposta(
                            proposta_id=proposta.id,
                            item_solicitacao_id=item_solicitacao.id,
                            preco_unitario=preco_unitario,
                            preco_final=preco_unitario,
                            quantidade_disponivel=dados_extraidos.get('quantidade'),
                            marca_oferecida=dados_extraidos.get('marca_produto'),
                            tenant_id=tenant_id
                        )
                        db.add(item_proposta)

            # Atualizar status da proposta para RECEBIDA
            proposta.status = StatusProposta.RECEBIDA
            proposta.data_recebimento = datetime.utcnow()

            db.flush()

            print(f"[CLASSIFICADOR] Proposta {proposta.id} atualizada com dados do email: "
                  f"valor={proposta.valor_total}, prazo={proposta.prazo_entrega}, "
                  f"pagamento={proposta.condicoes_pagamento}")

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
