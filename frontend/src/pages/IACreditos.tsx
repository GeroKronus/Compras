import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Button } from '../components/ui/button';
import { PageLayout, PageSection } from '../components/PageLayout';
import { Modal } from '../components/Modal';
import { useModal } from '../hooks/useModal';
import { formatDate } from '../utils/formatters';
import {
  SparklesIcon,
  ChartBarIcon,
  ClockIcon,
  Cog6ToothIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  DocumentTextIcon,
  EnvelopeIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

interface DashboardIA {
  mes_referencia: string;
  resumo: {
    chamadas: {
      usado: number;
      limite: number;
      disponivel: number;
      percentual: number;
    };
    tokens: {
      usado: number;
      limite: number;
      disponivel: number;
      percentual: number;
    };
    custo: {
      usado: number;
      limite: number;
      disponivel: number;
      percentual: number;
    };
  };
  por_tipo: Record<string, { chamadas: number; tokens: number; custo: number }>;
  status: {
    ia_disponivel: boolean;
    mensagem: string;
  };
  alertas: Array<{ tipo: string; mensagem: string }>;
}

interface HistoricoItem {
  id: number;
  tipo_operacao: string;
  modelo: string;
  tokens_entrada: number;
  tokens_saida: number;
  tokens_total: number;
  custo_estimado: number;
  referencia_id?: number;
  referencia_tipo?: string;
  descricao?: string;
  usuario_id?: number;
  created_at: string;
}

interface Limites {
  tokens_mensais_limite: number;
  chamadas_mensais_limite: number;
  custo_mensal_limite: number;
  usando_chave_propria: boolean;
  tem_chave_propria: boolean;
}

const tipoOperacaoIcons: Record<string, React.ReactNode> = {
  analise_proposta: <DocumentTextIcon className="h-5 w-5" />,
  extracao_email: <EnvelopeIcon className="h-5 w-5" />,
  classificacao_email: <SparklesIcon className="h-5 w-5" />,
};

const tipoOperacaoLabels: Record<string, string> = {
  analise_proposta: 'Analise de Proposta',
  extracao_email: 'Extracao de Email',
  classificacao_email: 'Classificacao de Email',
};

function ProgressBar({
  value,
  max,
  color = 'blue',
  showLabel = true
}: {
  value: number;
  max: number;
  color?: 'blue' | 'green' | 'yellow' | 'red';
  showLabel?: boolean;
}) {
  const percentage = max > 0 ? Math.min((value / max) * 100, 100) : 0;

  const colorClasses = {
    blue: 'bg-blue-600',
    green: 'bg-green-600',
    yellow: 'bg-yellow-500',
    red: 'bg-red-600',
  };

  const bgClasses = {
    blue: 'bg-blue-100',
    green: 'bg-green-100',
    yellow: 'bg-yellow-100',
    red: 'bg-red-100',
  };

  return (
    <div className="w-full">
      <div className={`h-3 rounded-full ${bgClasses[color]} overflow-hidden`}>
        <div
          className={`h-full ${colorClasses[color]} transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>{value.toLocaleString()}</span>
          <span>{percentage.toFixed(1)}%</span>
        </div>
      )}
    </div>
  );
}

function getProgressColor(percentage: number): 'blue' | 'green' | 'yellow' | 'red' {
  if (percentage >= 100) return 'red';
  if (percentage >= 80) return 'yellow';
  if (percentage >= 50) return 'blue';
  return 'green';
}

export default function IACreditos() {
  const queryClient = useQueryClient();
  const configModal = useModal();

  // Form de configuracao
  const [tokensLimite, setTokensLimite] = useState<string>('');
  const [chavePropria, setChavePropria] = useState<string>('');
  const [usarChavePropria, setUsarChavePropria] = useState<boolean>(false);

  // Paginacao historico
  const [page, setPage] = useState(1);
  const [tipoFiltro, setTipoFiltro] = useState<string>('');

  // Queries
  const { data: dashboardData, isLoading: loadingDashboard } = useQuery({
    queryKey: ['ia-dashboard'],
    queryFn: async () => (await api.get('/ia/dashboard')).data,
  });

  const { data: limitesData } = useQuery({
    queryKey: ['ia-limites'],
    queryFn: async () => (await api.get('/ia/limites')).data,
  });

  const { data: historicoData, isLoading: loadingHistorico } = useQuery({
    queryKey: ['ia-historico', page, tipoFiltro],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('page_size', '10');
      if (tipoFiltro) params.append('tipo', tipoFiltro);
      return (await api.get(`/ia/historico?${params}`)).data;
    },
  });

  const dashboard: DashboardIA | null = dashboardData;
  const limites: Limites | null = limitesData;
  const historico: HistoricoItem[] = historicoData?.items || [];

  // Mutations
  const atualizarLimitesMutation = useMutation({
    mutationFn: (data: any) => api.put('/ia/limites', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ia-dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['ia-limites'] });
      configModal.close();
    },
  });

  // Handlers
  const openConfigModal = () => {
    if (limites) {
      setTokensLimite(limites.tokens_mensais_limite.toString());
      setUsarChavePropria(limites.usando_chave_propria);
      setChavePropria('');
    }
    configModal.open();
  };

  const handleSalvarConfig = () => {
    const data: any = {};
    if (tokensLimite) data.tokens_limite = parseInt(tokensLimite);
    if (chavePropria) data.chave_propria = chavePropria;
    data.usar_chave_propria = usarChavePropria;

    atualizarLimitesMutation.mutate(data);
  };

  if (loadingDashboard) {
    return (
      <PageLayout title="Creditos de IA" subtitle="Carregando...">
        <div className="flex justify-center items-center h-64">
          <ArrowPathIcon className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title="Creditos de IA"
      subtitle="Controle de uso da inteligencia artificial"
      headerActions={
        <Button onClick={openConfigModal} variant="outline">
          <Cog6ToothIcon className="h-5 w-5 mr-2" />
          Configurar Limites
        </Button>
      }
    >
      {/* Status e Alertas */}
      {dashboard && (
        <>
          {/* Status da IA */}
          <div className={`rounded-lg p-4 mb-6 ${
            dashboard.status.ia_disponivel
              ? 'bg-green-50 border border-green-200'
              : 'bg-red-50 border border-red-200'
          }`}>
            <div className="flex items-center gap-3">
              {dashboard.status.ia_disponivel ? (
                <CheckCircleIcon className="h-6 w-6 text-green-600" />
              ) : (
                <XCircleIcon className="h-6 w-6 text-red-600" />
              )}
              <div>
                <p className={`font-medium ${
                  dashboard.status.ia_disponivel ? 'text-green-800' : 'text-red-800'
                }`}>
                  {dashboard.status.ia_disponivel ? 'IA Disponivel' : 'IA Indisponivel'}
                </p>
                <p className={`text-sm ${
                  dashboard.status.ia_disponivel ? 'text-green-600' : 'text-red-600'
                }`}>
                  {dashboard.status.mensagem}
                </p>
              </div>
            </div>
          </div>

          {/* Alertas */}
          {dashboard.alertas.length > 0 && (
            <div className="space-y-2 mb-6">
              {dashboard.alertas.map((alerta, index) => (
                <div
                  key={index}
                  className={`rounded-lg p-3 flex items-center gap-2 ${
                    alerta.tipo === 'error'
                      ? 'bg-red-50 border border-red-200 text-red-800'
                      : 'bg-yellow-50 border border-yellow-200 text-yellow-800'
                  }`}
                >
                  <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0" />
                  <span className="text-sm">{alerta.mensagem}</span>
                </div>
              ))}
            </div>
          )}

          {/* Cards de Resumo - Apenas Tokens */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            {/* Tokens Utilizados */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <ChartBarIcon className="h-6 w-6 text-purple-600" />
                  <h3 className="font-medium text-gray-900">Tokens Utilizados</h3>
                </div>
                <span className="text-3xl font-bold text-purple-600">
                  {dashboard.resumo.tokens.usado.toLocaleString()}
                </span>
              </div>
              <ProgressBar
                value={dashboard.resumo.tokens.usado}
                max={dashboard.resumo.tokens.limite}
                color={getProgressColor(dashboard.resumo.tokens.percentual)}
              />
              <p className="text-sm text-gray-500 mt-2">
                {dashboard.resumo.tokens.percentual.toFixed(1)}% do limite mensal
              </p>
            </div>

            {/* Saldo de Tokens */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <SparklesIcon className="h-6 w-6 text-green-600" />
                  <h3 className="font-medium text-gray-900">Saldo Disponivel</h3>
                </div>
                <span className="text-3xl font-bold text-green-600">
                  {dashboard.resumo.tokens.disponivel.toLocaleString()}
                </span>
              </div>
              <div className="text-sm text-gray-500">
                <p>Limite mensal: <span className="font-medium">{dashboard.resumo.tokens.limite.toLocaleString()}</span> tokens</p>
                <p className="mt-1">Chamadas realizadas: <span className="font-medium">{dashboard.resumo.chamadas.usado}</span></p>
              </div>
            </div>
          </div>

          {/* Uso por Tipo */}
          {Object.keys(dashboard.por_tipo).length > 0 && (
            <PageSection title="Uso por Tipo de Operacao" className="mb-8">
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Chamadas</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Tokens</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {Object.entries(dashboard.por_tipo).map(([tipo, dados]) => (
                      <tr key={tipo} className="hover:bg-gray-50">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            {tipoOperacaoIcons[tipo] || <SparklesIcon className="h-5 w-5" />}
                            <span className="font-medium">{tipoOperacaoLabels[tipo] || tipo}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-right text-gray-900">
                          {dados.chamadas}
                        </td>
                        <td className="px-6 py-4 text-right text-gray-900 font-medium">
                          {dados.tokens.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </PageSection>
          )}
        </>
      )}

      {/* Historico de Chamadas */}
      <PageSection title="Historico de Chamadas">
        <div className="mb-4">
          <select
            value={tipoFiltro}
            onChange={(e) => { setTipoFiltro(e.target.value); setPage(1); }}
            className="rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
          >
            <option value="">Todos os tipos</option>
            <option value="analise_proposta">Analise de Proposta</option>
            <option value="extracao_email">Extracao de Email</option>
            <option value="classificacao_email">Classificacao de Email</option>
          </select>
        </div>

        <div className="bg-white rounded-lg shadow overflow-hidden">
          {loadingHistorico ? (
            <div className="p-8 text-center text-gray-500">
              <ArrowPathIcon className="h-8 w-8 animate-spin mx-auto mb-2" />
              Carregando...
            </div>
          ) : historico.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <ClockIcon className="h-12 w-12 mx-auto mb-2 text-gray-300" />
              <p>Nenhuma chamada registrada</p>
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Data</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Operacao</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Tokens</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Referencia</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {historico.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(item.created_at)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {tipoOperacaoIcons[item.tipo_operacao] || <SparklesIcon className="h-5 w-5" />}
                        <span className="text-sm font-medium">{tipoOperacaoLabels[item.tipo_operacao] || item.tipo_operacao}</span>
                      </div>
                      {item.descricao && (
                        <p className="text-xs text-gray-500 mt-1">{item.descricao}</p>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                      <div>
                        <span className="font-bold text-purple-600">{item.tokens_total.toLocaleString()}</span>
                      </div>
                      <div className="text-xs text-gray-400">
                        {item.tokens_entrada.toLocaleString()} entrada / {item.tokens_saida.toLocaleString()} saida
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {item.referencia_tipo && item.referencia_id && (
                        <span className="text-primary-600">
                          {item.referencia_tipo} #{item.referencia_id}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* Paginacao */}
          {historicoData?.total > 10 && (
            <div className="px-6 py-4 border-t flex justify-between items-center">
              <span className="text-sm text-gray-500">
                Mostrando {(page - 1) * 10 + 1} - {Math.min(page * 10, historicoData.total)} de {historicoData.total}
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
                  disabled={page * 10 >= historicoData.total}
                >
                  Proximo
                </Button>
              </div>
            </div>
          )}
        </div>
      </PageSection>

      {/* Modal Configurar Limites */}
      <Modal
        isOpen={configModal.isOpen}
        title="Configurar Limites de IA"
        subtitle="Defina o limite mensal de tokens"
        onClose={configModal.close}
        onSubmit={handleSalvarConfig}
        submitLabel="Salvar"
        submitLoading={atualizarLimitesMutation.isPending}
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Limite de Tokens Mensais
            </label>
            <input
              type="number"
              value={tokensLimite}
              onChange={(e) => setTokensLimite(e.target.value)}
              placeholder="100000"
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Quantidade maxima de tokens que podem ser usados por mes
            </p>
          </div>

          <div className="border-t pt-4">
            <h4 className="font-medium text-gray-900 mb-3">Chave API Propria (Opcional)</h4>

            <div className="flex items-center mb-3">
              <input
                type="checkbox"
                id="usarChavePropria"
                checked={usarChavePropria}
                onChange={(e) => setUsarChavePropria(e.target.checked)}
                className="h-4 w-4 text-primary-600 border-gray-300 rounded"
              />
              <label htmlFor="usarChavePropria" className="ml-2 text-sm text-gray-700">
                Usar minha propria chave API Anthropic
              </label>
            </div>

            {usarChavePropria && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Chave API Anthropic
                </label>
                <input
                  type="password"
                  value={chavePropria}
                  onChange={(e) => setChavePropria(e.target.value)}
                  placeholder="sk-ant-..."
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  {limites?.tem_chave_propria
                    ? 'Voce ja tem uma chave configurada. Deixe em branco para manter a atual.'
                    : 'Insira sua chave API para usar tokens ilimitados.'}
                </p>
              </div>
            )}

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-3">
              <p className="text-sm text-blue-800">
                <strong>Nota:</strong> Ao usar sua propria chave API, o limite de tokens nao sera aplicado.
              </p>
            </div>
          </div>
        </div>
      </Modal>
    </PageLayout>
  );
}
