import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Button } from '../components/ui/button';
import { PageLayout, PageSection } from '../components/PageLayout';
import { Modal } from '../components/Modal';
import { useModal } from '../hooks/useModal';
import { formatDate } from '../utils/formatters';
import {
  EnvelopeIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  EyeIcon,
  DocumentPlusIcon,
  FunnelIcon,
  InboxIcon,
  ClockIcon,
  SparklesIcon,
  UserIcon,
  BuildingOfficeIcon,
} from '@heroicons/react/24/outline';

interface EmailProcessado {
  id: number;
  email_uid: string;
  remetente: string;
  assunto: string;
  corpo_preview?: string;
  status: 'pendente' | 'classificado' | 'ignorado' | 'erro';
  metodo_classificacao?: 'assunto' | 'remetente' | 'ia' | 'manual';
  solicitacao_id?: number;
  solicitacao_numero?: string;
  fornecedor_id?: number;
  fornecedor_nome?: string;
  confianca_ia?: number;
  erro_mensagem?: string;
  created_at: string;
}

interface Solicitacao {
  id: number;
  numero: string;
  titulo: string;
  status: string;
}

interface Fornecedor {
  id: number;
  razao_social: string;
  cnpj: string;
}

interface Estatisticas {
  total: number;
  classificados: number;
  pendentes: number;
  ignorados: number;
  erros: number;
  por_metodo: {
    assunto: number;
    remetente: number;
    ia: number;
    manual: number;
  };
}

const statusColors: Record<string, string> = {
  pendente: 'bg-yellow-100 text-yellow-800',
  classificado: 'bg-green-100 text-green-800',
  ignorado: 'bg-gray-100 text-gray-800',
  erro: 'bg-red-100 text-red-800',
};

const statusLabels: Record<string, string> = {
  pendente: 'Pendente',
  classificado: 'Classificado',
  ignorado: 'Ignorado',
  erro: 'Erro',
};

const metodoIcons: Record<string, React.ReactNode> = {
  assunto: <DocumentPlusIcon className="h-4 w-4" />,
  remetente: <BuildingOfficeIcon className="h-4 w-4" />,
  ia: <SparklesIcon className="h-4 w-4" />,
  manual: <UserIcon className="h-4 w-4" />,
};

const metodoLabels: Record<string, string> = {
  assunto: 'Assunto',
  remetente: 'Remetente',
  ia: 'IA',
  manual: 'Manual',
};

export default function EmailsRevisao() {
  const queryClient = useQueryClient();

  // Modais
  const viewModal = useModal<EmailProcessado>();
  const classificarModal = useModal<EmailProcessado>();

  // Filtros
  const [statusFilter, setStatusFilter] = useState<string>('pendente');
  const [page, setPage] = useState(1);

  // Form de classificacao manual
  const [solicitacaoId, setSolicitacaoId] = useState<number | null>(null);
  const [fornecedorId, setFornecedorId] = useState<number | null>(null);
  const [ignorar, setIgnorar] = useState(false);

  // Queries
  const { data: emailsData, isLoading } = useQuery({
    queryKey: ['emails-processados', statusFilter, page],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('page_size', '20');
      if (statusFilter) params.append('status', statusFilter);
      return (await api.get(`/emails/?${params}`)).data;
    },
  });

  const { data: estatisticasData } = useQuery({
    queryKey: ['emails-estatisticas'],
    queryFn: async () => {
      const data = (await api.get('/emails/estatisticas/resumo')).data;
      // Transformar a resposta do backend para o formato esperado pelo frontend
      return {
        total: data.total || 0,
        classificados: data.por_status?.classificado || 0,
        pendentes: data.por_status?.pendente || 0,
        ignorados: data.por_status?.ignorado || 0,
        erros: data.por_status?.erro || 0,
        por_metodo: data.por_metodo || {},
      };
    },
  });

  const { data: solicitacoesData } = useQuery({
    queryKey: ['solicitacoes-abertas'],
    queryFn: async () => (await api.get('/cotacoes/solicitacoes?status=ENVIADA&status=EM_COTACAO')).data,
  });

  const { data: fornecedoresData } = useQuery({
    queryKey: ['fornecedores-list'],
    queryFn: async () => (await api.get('/fornecedores/')).data,
  });

  const emails: EmailProcessado[] = emailsData?.items || [];
  const estatisticas: Estatisticas = estatisticasData || { total: 0, classificados: 0, pendentes: 0, ignorados: 0, erros: 0, por_metodo: {} };
  const solicitacoes: Solicitacao[] = solicitacoesData?.items || [];
  const fornecedores: Fornecedor[] = fornecedoresData?.items || [];

  // Mutations
  const processarMutation = useMutation({
    mutationFn: () => api.post('/emails/processar'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails-processados'] });
      queryClient.invalidateQueries({ queryKey: ['emails-estatisticas'] });
    },
  });

  const classificarMutation = useMutation({
    mutationFn: (data: { email_id: number; solicitacao_id?: number; fornecedor_id?: number; ignorar?: boolean }) =>
      api.post(`/emails/${data.email_id}/classificar`, {
        solicitacao_id: data.solicitacao_id,
        fornecedor_id: data.fornecedor_id,
        ignorar: data.ignorar,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails-processados'] });
      queryClient.invalidateQueries({ queryKey: ['emails-estatisticas'] });
      closeClassificarModal();
    },
  });

  const criarPropostaMutation = useMutation({
    mutationFn: (email_id: number) => api.post(`/emails/${email_id}/criar-proposta`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails-processados'] });
      queryClient.invalidateQueries({ queryKey: ['emails-estatisticas'] });
    },
  });

  // Handlers
  const closeClassificarModal = () => {
    classificarModal.close();
    setSolicitacaoId(null);
    setFornecedorId(null);
    setIgnorar(false);
  };

  const openClassificarModal = (email: EmailProcessado) => {
    setSolicitacaoId(email.solicitacao_id || null);
    setFornecedorId(email.fornecedor_id || null);
    setIgnorar(false);
    classificarModal.open(email);
  };

  const handleClassificar = () => {
    if (!classificarModal.data) return;

    if (!ignorar && !solicitacaoId) {
      alert('Selecione uma solicitacao ou marque para ignorar');
      return;
    }

    classificarMutation.mutate({
      email_id: classificarModal.data.id,
      solicitacao_id: ignorar ? undefined : solicitacaoId || undefined,
      fornecedor_id: ignorar ? undefined : fornecedorId || undefined,
      ignorar,
    });
  };

  return (
    <PageLayout
      title="Revisao de Emails"
      subtitle="Classifique emails de resposta de cotacao"
      headerActions={
        <Button
          onClick={() => processarMutation.mutate()}
          disabled={processarMutation.isPending}
        >
          <ArrowPathIcon className={`h-5 w-5 mr-2 ${processarMutation.isPending ? 'animate-spin' : ''}`} />
          {processarMutation.isPending ? 'Processando...' : 'Processar Emails'}
        </Button>
      }
    >
      {/* Estatisticas */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div
          className={`bg-white rounded-lg p-4 shadow cursor-pointer transition-all ${
            statusFilter === '' ? 'ring-2 ring-primary-500' : 'hover:shadow-md'
          }`}
          onClick={() => setStatusFilter('')}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total</p>
              <p className="text-2xl font-bold">{estatisticas.total}</p>
            </div>
            <InboxIcon className="h-8 w-8 text-gray-400" />
          </div>
        </div>

        <div
          className={`bg-white rounded-lg p-4 shadow cursor-pointer transition-all ${
            statusFilter === 'pendente' ? 'ring-2 ring-yellow-500' : 'hover:shadow-md'
          }`}
          onClick={() => setStatusFilter('pendente')}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Pendentes</p>
              <p className="text-2xl font-bold text-yellow-600">{estatisticas.pendentes}</p>
            </div>
            <ClockIcon className="h-8 w-8 text-yellow-400" />
          </div>
        </div>

        <div
          className={`bg-white rounded-lg p-4 shadow cursor-pointer transition-all ${
            statusFilter === 'classificado' ? 'ring-2 ring-green-500' : 'hover:shadow-md'
          }`}
          onClick={() => setStatusFilter('classificado')}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Classificados</p>
              <p className="text-2xl font-bold text-green-600">{estatisticas.classificados}</p>
            </div>
            <CheckCircleIcon className="h-8 w-8 text-green-400" />
          </div>
        </div>

        <div
          className={`bg-white rounded-lg p-4 shadow cursor-pointer transition-all ${
            statusFilter === 'ignorado' ? 'ring-2 ring-gray-500' : 'hover:shadow-md'
          }`}
          onClick={() => setStatusFilter('ignorado')}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Ignorados</p>
              <p className="text-2xl font-bold text-gray-600">{estatisticas.ignorados}</p>
            </div>
            <XCircleIcon className="h-8 w-8 text-gray-400" />
          </div>
        </div>

        <div
          className={`bg-white rounded-lg p-4 shadow cursor-pointer transition-all ${
            statusFilter === 'erro' ? 'ring-2 ring-red-500' : 'hover:shadow-md'
          }`}
          onClick={() => setStatusFilter('erro')}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Erros</p>
              <p className="text-2xl font-bold text-red-600">{estatisticas.erros}</p>
            </div>
            <ExclamationTriangleIcon className="h-8 w-8 text-red-400" />
          </div>
        </div>
      </div>

      {/* Classificacao por Metodo */}
      {estatisticas.classificados > 0 && (
        <div className="bg-white rounded-lg p-4 shadow mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Classificados por Metodo</h3>
          <div className="flex gap-4">
            {Object.entries(estatisticas.por_metodo || {}).map(([metodo, count]) => (
              <div key={metodo} className="flex items-center gap-2 text-sm">
                {metodoIcons[metodo]}
                <span className="text-gray-600">{metodoLabels[metodo]}:</span>
                <span className="font-medium">{count as number}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Lista de Emails */}
      <PageSection title={`Emails ${statusFilter ? `(${statusLabels[statusFilter] || statusFilter})` : ''}`}>
        <div className="bg-white shadow rounded-lg overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">
              <ArrowPathIcon className="h-8 w-8 animate-spin mx-auto mb-2" />
              Carregando...
            </div>
          ) : emails.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <EnvelopeIcon className="h-12 w-12 mx-auto mb-2 text-gray-300" />
              <p>Nenhum email encontrado</p>
              {statusFilter === 'pendente' && (
                <p className="text-sm mt-1">Clique em "Processar Emails" para verificar novos emails</p>
              )}
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Remetente</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assunto</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Classificacao</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Data</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acoes</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {emails.map((email) => (
                  <tr key={email.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">{email.remetente}</div>
                      {email.fornecedor_nome && (
                        <div className="text-xs text-gray-500">{email.fornecedor_nome}</div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 max-w-xs truncate">{email.assunto}</div>
                      {email.corpo_preview && (
                        <div className="text-xs text-gray-500 max-w-xs truncate">{email.corpo_preview}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs rounded-full ${statusColors[email.status]}`}>
                        {statusLabels[email.status]}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {email.metodo_classificacao ? (
                        <div className="flex items-center gap-2">
                          {metodoIcons[email.metodo_classificacao]}
                          <span className="text-sm text-gray-600">{metodoLabels[email.metodo_classificacao]}</span>
                          {email.confianca_ia && (
                            <span className="text-xs text-gray-400">({email.confianca_ia}%)</span>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-400 text-sm">-</span>
                      )}
                      {email.solicitacao_numero && (
                        <div className="text-xs text-primary-600 mt-1">{email.solicitacao_numero}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(email.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => viewModal.open(email)}
                          className="text-gray-600 hover:text-gray-900"
                          title="Visualizar"
                        >
                          <EyeIcon className="h-5 w-5" />
                        </button>
                        {email.status === 'pendente' && (
                          <button
                            onClick={() => openClassificarModal(email)}
                            className="text-blue-600 hover:text-blue-900"
                            title="Classificar"
                          >
                            <FunnelIcon className="h-5 w-5" />
                          </button>
                        )}
                        {email.status === 'classificado' && email.solicitacao_id && !email.fornecedor_id && (
                          <button
                            onClick={() => {
                              if (confirm('Criar proposta a partir deste email?')) {
                                criarPropostaMutation.mutate(email.id);
                              }
                            }}
                            className="text-green-600 hover:text-green-900"
                            title="Criar Proposta"
                            disabled={criarPropostaMutation.isPending}
                          >
                            <DocumentPlusIcon className="h-5 w-5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* Paginacao */}
          {emailsData?.total > 20 && (
            <div className="px-6 py-4 border-t flex justify-between items-center">
              <span className="text-sm text-gray-500">
                Mostrando {(page - 1) * 20 + 1} - {Math.min(page * 20, emailsData.total)} de {emailsData.total}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1}
                >
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page + 1)}
                  disabled={page * 20 >= emailsData.total}
                >
                  Proximo
                </Button>
              </div>
            </div>
          )}
        </div>
      </PageSection>

      {/* Modal Visualizar Email */}
      <Modal
        isOpen={viewModal.isOpen}
        title="Detalhes do Email"
        onClose={viewModal.close}
        size="lg"
      >
        {viewModal.data && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-gray-500">Remetente</h4>
              <p className="text-gray-900">{viewModal.data.remetente}</p>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-500">Assunto</h4>
              <p className="text-gray-900">{viewModal.data.assunto}</p>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-500">Status</h4>
              <span className={`px-2 py-1 text-xs rounded-full ${statusColors[viewModal.data.status]}`}>
                {statusLabels[viewModal.data.status]}
              </span>
            </div>
            {viewModal.data.metodo_classificacao && (
              <div>
                <h4 className="text-sm font-medium text-gray-500">Metodo de Classificacao</h4>
                <div className="flex items-center gap-2">
                  {metodoIcons[viewModal.data.metodo_classificacao]}
                  <span>{metodoLabels[viewModal.data.metodo_classificacao]}</span>
                </div>
              </div>
            )}
            {viewModal.data.solicitacao_numero && (
              <div>
                <h4 className="text-sm font-medium text-gray-500">Solicitacao Vinculada</h4>
                <p className="text-primary-600">{viewModal.data.solicitacao_numero}</p>
              </div>
            )}
            {viewModal.data.fornecedor_nome && (
              <div>
                <h4 className="text-sm font-medium text-gray-500">Fornecedor</h4>
                <p className="text-gray-900">{viewModal.data.fornecedor_nome}</p>
              </div>
            )}
            {viewModal.data.corpo_preview && (
              <div>
                <h4 className="text-sm font-medium text-gray-500">Preview do Conteudo</h4>
                <p className="text-gray-700 text-sm bg-gray-50 p-3 rounded whitespace-pre-wrap">
                  {viewModal.data.corpo_preview}
                </p>
              </div>
            )}
            {viewModal.data.erro_mensagem && (
              <div>
                <h4 className="text-sm font-medium text-red-500">Erro</h4>
                <p className="text-red-700 text-sm bg-red-50 p-3 rounded">
                  {viewModal.data.erro_mensagem}
                </p>
              </div>
            )}
            <div>
              <h4 className="text-sm font-medium text-gray-500">Recebido em</h4>
              <p className="text-gray-900">{formatDate(viewModal.data.created_at)}</p>
            </div>
          </div>
        )}
      </Modal>

      {/* Modal Classificar Email */}
      <Modal
        isOpen={classificarModal.isOpen}
        title="Classificar Email"
        subtitle="Vincule este email a uma solicitacao de cotacao"
        onClose={closeClassificarModal}
        onSubmit={handleClassificar}
        submitLabel={ignorar ? 'Ignorar Email' : 'Classificar'}
        submitLoading={classificarMutation.isPending}
        submitColor={ignorar ? 'primary' : 'blue'}
        size="lg"
      >
        {classificarModal.data && (
          <div className="space-y-4">
            {/* Info do Email */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">
                <strong>De:</strong> {classificarModal.data.remetente}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                <strong>Assunto:</strong> {classificarModal.data.assunto}
              </p>
            </div>

            {/* Opcao Ignorar */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="ignorar"
                checked={ignorar}
                onChange={(e) => setIgnorar(e.target.checked)}
                className="h-4 w-4 text-gray-600 border-gray-300 rounded"
              />
              <label htmlFor="ignorar" className="ml-2 text-sm text-gray-700">
                Ignorar este email (nao e uma resposta de cotacao)
              </label>
            </div>

            {/* Selecao de Solicitacao */}
            {!ignorar && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Solicitacao de Cotacao *
                  </label>
                  <select
                    value={solicitacaoId || ''}
                    onChange={(e) => setSolicitacaoId(e.target.value ? parseInt(e.target.value) : null)}
                    className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                    required
                  >
                    <option value="">Selecione uma solicitacao...</option>
                    {solicitacoes.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.numero} - {s.titulo}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Fornecedor (opcional)
                  </label>
                  <select
                    value={fornecedorId || ''}
                    onChange={(e) => setFornecedorId(e.target.value ? parseInt(e.target.value) : null)}
                    className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                  >
                    <option value="">Selecione o fornecedor...</option>
                    {fornecedores.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.razao_social}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    Se nao selecionado, o sistema tentara identificar pelo email do remetente
                  </p>
                </div>
              </>
            )}
          </div>
        )}
      </Modal>
    </PageLayout>
  );
}
