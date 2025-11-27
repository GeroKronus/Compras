import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Button } from '../components/ui/button';
import { useAuth } from '../hooks/useAuth';
import {
  MagnifyingGlassIcon,
  EyeIcon,
  CheckIcon,
  XCircleIcon,
  PaperAirplaneIcon,
  TruckIcon,
  DocumentCheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ClockIcon,
  CalendarIcon,
  CurrencyDollarIcon,
  BuildingStorefrontIcon,
} from '@heroicons/react/24/outline';

interface ItemPedido {
  id: number;
  produto_id: number;
  quantidade: number;
  quantidade_recebida: number;
  preco_unitario: number;
  desconto_percentual: number;
  valor_total: number;
  marca?: string;
  produto_nome?: string;
  produto_codigo?: string;
}

interface Pedido {
  id: number;
  numero: string;
  fornecedor_id: number;
  fornecedor_nome?: string;
  fornecedor_cnpj?: string;
  solicitacao_cotacao_id?: number;
  solicitacao_numero?: string;
  proposta_id?: number;
  status: string;
  data_pedido: string;
  data_aprovacao?: string;
  data_envio?: string;
  data_entrega?: string;
  valor_produtos: number;
  valor_frete: number;
  valor_desconto: number;
  valor_total: number;
  condicoes_pagamento?: string;
  prazo_entrega?: number;
  observacoes?: string;
  motivo_cancelamento?: string;
  itens: ItemPedido[];
}

const statusColors: Record<string, string> = {
  RASCUNHO: 'bg-gray-100 text-gray-800',
  AGUARDANDO_APROVACAO: 'bg-yellow-100 text-yellow-800',
  APROVADO: 'bg-blue-100 text-blue-800',
  ENVIADO_FORNECEDOR: 'bg-indigo-100 text-indigo-800',
  CONFIRMADO: 'bg-purple-100 text-purple-800',
  EM_TRANSITO: 'bg-orange-100 text-orange-800',
  ENTREGUE_PARCIAL: 'bg-teal-100 text-teal-800',
  ENTREGUE: 'bg-green-100 text-green-800',
  CANCELADO: 'bg-red-100 text-red-800',
};

const statusLabels: Record<string, string> = {
  RASCUNHO: 'Rascunho',
  AGUARDANDO_APROVACAO: 'Aguardando Aprovacao',
  APROVADO: 'Aprovado',
  ENVIADO_FORNECEDOR: 'Enviado ao Fornecedor',
  CONFIRMADO: 'Confirmado',
  EM_TRANSITO: 'Em Transito',
  ENTREGUE_PARCIAL: 'Entregue Parcial',
  ENTREGUE: 'Entregue',
  CANCELADO: 'Cancelado',
};

export default function Pedidos() {
  const { tenant } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [isAprovarModalOpen, setIsAprovarModalOpen] = useState(false);
  const [isCancelarModalOpen, setIsCancelarModalOpen] = useState(false);
  const [selectedPedido, setSelectedPedido] = useState<Pedido | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [justificativa, setJustificativa] = useState('');
  const [motivoCancelamento, setMotivoCancelamento] = useState('');
  const [expandedPedido, setExpandedPedido] = useState<number | null>(null);

  // Query
  const { data: pedidosData, isLoading } = useQuery({
    queryKey: ['pedidos', searchTerm, statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (searchTerm) params.append('busca', searchTerm);
      if (statusFilter) params.append('status', statusFilter);
      const response = await api.get(`/pedidos/?${params}`);
      return response.data;
    },
  });

  const pedidos: Pedido[] = pedidosData?.items || [];

  // Mutations
  const enviarAprovacaoMutation = useMutation({
    mutationFn: (id: number) => api.post(`/pedidos/${id}/enviar-aprovacao`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
    },
  });

  const aprovarMutation = useMutation({
    mutationFn: (data: { id: number; justificativa: string }) =>
      api.post(`/pedidos/${data.id}/aprovar`, { justificativa: data.justificativa }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
      setIsAprovarModalOpen(false);
      setJustificativa('');
    },
  });

  const enviarFornecedorMutation = useMutation({
    mutationFn: (id: number) => api.post(`/pedidos/${id}/enviar-fornecedor`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
    },
  });

  const confirmarMutation = useMutation({
    mutationFn: (id: number) => api.post(`/pedidos/${id}/confirmar`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
    },
  });

  const entregarMutation = useMutation({
    mutationFn: (id: number) => api.post(`/pedidos/${id}/registrar-entrega`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
    },
  });

  const cancelarMutation = useMutation({
    mutationFn: (data: { id: number; motivo: string }) =>
      api.post(`/pedidos/${data.id}/cancelar`, { motivo: data.motivo }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
      setIsCancelarModalOpen(false);
      setMotivoCancelamento('');
    },
  });

  const openViewModal = (pedido: Pedido) => {
    setSelectedPedido(pedido);
    setIsViewModalOpen(true);
  };

  const openAprovarModal = (pedido: Pedido) => {
    setSelectedPedido(pedido);
    setJustificativa('');
    setIsAprovarModalOpen(true);
  };

  const openCancelarModal = (pedido: Pedido) => {
    setSelectedPedido(pedido);
    setMotivoCancelamento('');
    setIsCancelarModalOpen(true);
  };

  const handleAprovar = () => {
    if (!selectedPedido || justificativa.length < 5) return;
    aprovarMutation.mutate({ id: selectedPedido.id, justificativa });
  };

  const handleCancelar = () => {
    if (!selectedPedido || motivoCancelamento.length < 10) return;
    cancelarMutation.mutate({ id: selectedPedido.id, motivo: motivoCancelamento });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-primary">Pedidos de Compra</h1>
            <p className="text-sm text-muted-foreground">{tenant?.nome_empresa}</p>
          </div>
          <Button onClick={() => navigate('/dashboard')} variant="outline">
            Voltar ao Dashboard
          </Button>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto px-4 py-8 space-y-6">
        {/* Filtros */}
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="h-5 w-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por numero..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
          >
            <option value="">Todos os status</option>
            {Object.entries(statusLabels).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>

        {/* Lista de Pedidos em Cards */}
        <div className="space-y-4">
          {isLoading ? (
            <div className="bg-white shadow rounded-lg p-8 text-center text-gray-500">
              Carregando...
            </div>
          ) : pedidos.length === 0 ? (
            <div className="bg-white shadow rounded-lg p-8 text-center text-gray-500">
              Nenhum pedido encontrado
            </div>
          ) : (
            pedidos.map((pedido) => (
              <div key={pedido.id} className="bg-white shadow rounded-lg overflow-hidden">
                {/* Cabecalho do Card */}
                <div
                  className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => setExpandedPedido(expandedPedido === pedido.id ? null : pedido.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="flex-shrink-0">
                        <div className="h-12 w-12 rounded-full bg-primary-100 flex items-center justify-center">
                          <BuildingStorefrontIcon className="h-6 w-6 text-primary-600" />
                        </div>
                      </div>
                      <div>
                        <div className="flex items-center space-x-3">
                          <h3 className="text-lg font-semibold text-gray-900">{pedido.numero}</h3>
                          <span className={`px-3 py-1 text-xs font-medium rounded-full ${statusColors[pedido.status]}`}>
                            {statusLabels[pedido.status]}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600">{pedido.fornecedor_nome}</p>
                        {pedido.solicitacao_numero && (
                          <p className="text-xs text-gray-400">Cotacao: {pedido.solicitacao_numero}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className="text-right">
                        <p className="text-xl font-bold text-primary-600">
                          {pedido.valor_total?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                        </p>
                        <p className="text-xs text-gray-500 flex items-center justify-end">
                          <CalendarIcon className="h-3 w-3 mr-1" />
                          {new Date(pedido.data_pedido).toLocaleDateString('pt-BR')}
                        </p>
                      </div>
                      {expandedPedido === pedido.id ? (
                        <ChevronUpIcon className="h-5 w-5 text-gray-400" />
                      ) : (
                        <ChevronDownIcon className="h-5 w-5 text-gray-400" />
                      )}
                    </div>
                  </div>

                  {/* Info resumida quando fechado */}
                  {expandedPedido !== pedido.id && (
                    <div className="mt-3 flex items-center space-x-6 text-sm text-gray-500">
                      <span className="flex items-center">
                        <CurrencyDollarIcon className="h-4 w-4 mr-1" />
                        {pedido.itens?.length || 0} item(ns)
                      </span>
                      {pedido.prazo_entrega && (
                        <span className="flex items-center">
                          <ClockIcon className="h-4 w-4 mr-1" />
                          Prazo: {pedido.prazo_entrega} dias
                        </span>
                      )}
                      {pedido.condicoes_pagamento && (
                        <span>Pgto: {pedido.condicoes_pagamento}</span>
                      )}
                    </div>
                  )}
                </div>

                {/* Conteudo Expandido */}
                {expandedPedido === pedido.id && (
                  <div className="border-t border-gray-100">
                    {/* Timeline de Status */}
                    <div className="px-4 py-3 bg-gray-50">
                      <h4 className="text-xs font-semibold text-gray-500 uppercase mb-3">Progresso do Pedido</h4>
                      <div className="flex items-center space-x-2 overflow-x-auto pb-2">
                        {['RASCUNHO', 'AGUARDANDO_APROVACAO', 'APROVADO', 'ENVIADO_FORNECEDOR', 'CONFIRMADO', 'EM_TRANSITO', 'ENTREGUE'].map((step, index) => {
                          const isActive = step === pedido.status;
                          const isPast = ['RASCUNHO', 'AGUARDANDO_APROVACAO', 'APROVADO', 'ENVIADO_FORNECEDOR', 'CONFIRMADO', 'EM_TRANSITO', 'ENTREGUE'].indexOf(pedido.status) > index;
                          const isCanceled = pedido.status === 'CANCELADO';
                          return (
                            <div key={step} className="flex items-center">
                              <div className={`
                                flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium
                                ${isCanceled ? 'bg-red-200 text-red-700' :
                                  isActive ? 'bg-primary-600 text-white' :
                                  isPast ? 'bg-green-500 text-white' :
                                  'bg-gray-200 text-gray-500'}
                              `}>
                                {isPast && !isActive ? <CheckIcon className="h-3 w-3" /> : index + 1}
                              </div>
                              {index < 6 && (
                                <div className={`w-8 h-0.5 ${isPast ? 'bg-green-500' : 'bg-gray-200'}`} />
                              )}
                            </div>
                          );
                        })}
                      </div>
                      <div className="flex justify-between text-xs text-gray-400 mt-1">
                        <span>Rascunho</span>
                        <span>Aprovacao</span>
                        <span>Enviado</span>
                        <span>Confirmado</span>
                        <span>Transito</span>
                        <span>Entregue</span>
                      </div>
                    </div>

                    {/* Detalhes do Pedido */}
                    <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <p className="text-xs font-medium text-gray-500">Fornecedor</p>
                        <p className="text-sm font-semibold">{pedido.fornecedor_nome}</p>
                        <p className="text-xs text-gray-400">{pedido.fornecedor_cnpj}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-gray-500">Condicoes Pagamento</p>
                        <p className="text-sm font-semibold">{pedido.condicoes_pagamento || 'N/A'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-gray-500">Prazo Entrega</p>
                        <p className="text-sm font-semibold">{pedido.prazo_entrega ? `${pedido.prazo_entrega} dias` : 'N/A'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-gray-500">Frete</p>
                        <p className="text-sm font-semibold">
                          {pedido.valor_frete?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) || 'R$ 0,00'}
                        </p>
                      </div>
                    </div>

                    {/* Itens do Pedido */}
                    {pedido.itens && pedido.itens.length > 0 && (
                      <div className="px-4 pb-4">
                        <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Itens do Pedido</h4>
                        <div className="bg-gray-50 rounded-lg overflow-hidden">
                          <table className="min-w-full text-sm">
                            <thead className="bg-gray-100">
                              <tr>
                                <th className="px-3 py-2 text-left font-medium text-gray-600">Produto</th>
                                <th className="px-3 py-2 text-right font-medium text-gray-600">Qtd</th>
                                <th className="px-3 py-2 text-right font-medium text-gray-600">Preco Unit.</th>
                                <th className="px-3 py-2 text-right font-medium text-gray-600">Total</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200">
                              {pedido.itens.map((item) => (
                                <tr key={item.id}>
                                  <td className="px-3 py-2">
                                    <span className="font-medium">{item.produto_codigo}</span> - {item.produto_nome}
                                    {item.marca && <span className="text-xs text-gray-400 ml-1">({item.marca})</span>}
                                  </td>
                                  <td className="px-3 py-2 text-right">{item.quantidade}</td>
                                  <td className="px-3 py-2 text-right">
                                    {item.preco_unitario?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                                  </td>
                                  <td className="px-3 py-2 text-right font-medium">
                                    {item.valor_total?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Observacoes */}
                    {pedido.observacoes && (
                      <div className="px-4 pb-4">
                        <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Observacoes</h4>
                        <p className="text-sm text-gray-600 bg-yellow-50 p-2 rounded">{pedido.observacoes}</p>
                      </div>
                    )}

                    {/* Motivo Cancelamento */}
                    {pedido.motivo_cancelamento && (
                      <div className="px-4 pb-4">
                        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                          <h4 className="text-xs font-semibold text-red-700 uppercase mb-1">Motivo do Cancelamento</h4>
                          <p className="text-sm text-red-800">{pedido.motivo_cancelamento}</p>
                        </div>
                      </div>
                    )}

                    {/* Acoes */}
                    <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex flex-wrap gap-2 justify-end">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openViewModal(pedido)}
                      >
                        <EyeIcon className="h-4 w-4 mr-1" />
                        Ver Detalhes
                      </Button>

                      {pedido.status === 'RASCUNHO' && (
                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => enviarAprovacaoMutation.mutate(pedido.id)}
                          disabled={enviarAprovacaoMutation.isPending}
                        >
                          <PaperAirplaneIcon className="h-4 w-4 mr-1" />
                          Enviar para Aprovacao
                        </Button>
                      )}

                      {pedido.status === 'AGUARDANDO_APROVACAO' && (
                        <Button
                          variant="default"
                          size="sm"
                          className="bg-green-600 hover:bg-green-700"
                          onClick={() => openAprovarModal(pedido)}
                        >
                          <CheckIcon className="h-4 w-4 mr-1" />
                          Aprovar Pedido
                        </Button>
                      )}

                      {pedido.status === 'APROVADO' && (
                        <Button
                          variant="default"
                          size="sm"
                          className="bg-indigo-600 hover:bg-indigo-700"
                          onClick={() => enviarFornecedorMutation.mutate(pedido.id)}
                          disabled={enviarFornecedorMutation.isPending}
                        >
                          <PaperAirplaneIcon className="h-4 w-4 mr-1" />
                          Enviar ao Fornecedor
                        </Button>
                      )}

                      {pedido.status === 'ENVIADO_FORNECEDOR' && (
                        <Button
                          variant="default"
                          size="sm"
                          className="bg-purple-600 hover:bg-purple-700"
                          onClick={() => confirmarMutation.mutate(pedido.id)}
                          disabled={confirmarMutation.isPending}
                        >
                          <DocumentCheckIcon className="h-4 w-4 mr-1" />
                          Confirmar Recebimento
                        </Button>
                      )}

                      {['CONFIRMADO', 'EM_TRANSITO', 'ENTREGUE_PARCIAL'].includes(pedido.status) && (
                        <Button
                          variant="default"
                          size="sm"
                          className="bg-green-600 hover:bg-green-700"
                          onClick={() => entregarMutation.mutate(pedido.id)}
                          disabled={entregarMutation.isPending}
                        >
                          <TruckIcon className="h-4 w-4 mr-1" />
                          Registrar Entrega
                        </Button>
                      )}

                      {!['ENTREGUE', 'CANCELADO'].includes(pedido.status) && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-red-600 border-red-300 hover:bg-red-50"
                          onClick={() => openCancelarModal(pedido)}
                        >
                          <XCircleIcon className="h-4 w-4 mr-1" />
                          Cancelar Pedido
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </main>

      {/* Modal Visualizar */}
      {isViewModalOpen && selectedPedido && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-medium text-gray-900">{selectedPedido.numero}</h3>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColors[selectedPedido.status]}`}>
                  {statusLabels[selectedPedido.status]}
                </span>
              </div>
              <button
                onClick={() => setIsViewModalOpen(false)}
                className="text-gray-400 hover:text-gray-500"
              >
                <XCircleIcon className="h-6 w-6" />
              </button>
            </div>

            <div className="px-6 py-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-500">Fornecedor</h4>
                  <p className="text-gray-900">{selectedPedido.fornecedor_nome}</p>
                  <p className="text-sm text-gray-500">{selectedPedido.fornecedor_cnpj}</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-500">Data do Pedido</h4>
                  <p className="text-gray-900">
                    {new Date(selectedPedido.data_pedido).toLocaleDateString('pt-BR')}
                  </p>
                </div>
                {selectedPedido.condicoes_pagamento && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-500">Condicoes Pagamento</h4>
                    <p className="text-gray-900">{selectedPedido.condicoes_pagamento}</p>
                  </div>
                )}
                {selectedPedido.prazo_entrega && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-500">Prazo Entrega</h4>
                    <p className="text-gray-900">{selectedPedido.prazo_entrega} dias</p>
                  </div>
                )}
              </div>

              <div className="border-t pt-4">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Itens do Pedido</h4>
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Produto</th>
                      <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">Qtd</th>
                      <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">Preco</th>
                      <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {selectedPedido.itens?.map((item) => (
                      <tr key={item.id}>
                        <td className="px-3 py-2 text-sm">
                          <span className="font-medium">{item.produto_codigo}</span> - {item.produto_nome}
                        </td>
                        <td className="px-3 py-2 text-sm text-right">{item.quantidade}</td>
                        <td className="px-3 py-2 text-sm text-right">
                          {item.preco_unitario?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                        </td>
                        <td className="px-3 py-2 text-sm text-right font-medium">
                          {item.valor_total?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg grid grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Produtos</p>
                  <p className="font-medium">
                    {selectedPedido.valor_produtos?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Frete</p>
                  <p className="font-medium">
                    {selectedPedido.valor_frete?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Total</p>
                  <p className="text-xl font-bold text-primary-600">
                    {selectedPedido.valor_total?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </p>
                </div>
              </div>

              {selectedPedido.observacoes && (
                <div>
                  <h4 className="text-sm font-medium text-gray-500">Observacoes</h4>
                  <p className="text-gray-900">{selectedPedido.observacoes}</p>
                </div>
              )}

              {selectedPedido.motivo_cancelamento && (
                <div className="bg-red-50 p-4 rounded-lg">
                  <h4 className="text-sm font-medium text-red-700">Motivo do Cancelamento</h4>
                  <p className="text-red-900">{selectedPedido.motivo_cancelamento}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal Aprovar */}
      {isAprovarModalOpen && selectedPedido && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">
                Aprovar Pedido {selectedPedido.numero}
              </h3>
            </div>

            <div className="px-6 py-4 space-y-4">
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">
                  <strong>Fornecedor:</strong> {selectedPedido.fornecedor_nome}
                </p>
                <p className="text-sm text-gray-600">
                  <strong>Valor:</strong> {selectedPedido.valor_total?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Justificativa da Aprovacao *
                </label>
                <textarea
                  value={justificativa}
                  onChange={(e) => setJustificativa(e.target.value)}
                  rows={3}
                  placeholder="Informe a justificativa (minimo 5 caracteres)"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                />
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
              <button
                onClick={() => setIsAprovarModalOpen(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleAprovar}
                disabled={aprovarMutation.isPending || justificativa.length < 5}
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
              >
                {aprovarMutation.isPending ? 'Aprovando...' : 'Aprovar Pedido'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Cancelar */}
      {isCancelarModalOpen && selectedPedido && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-red-900">
                Cancelar Pedido {selectedPedido.numero}
              </h3>
            </div>

            <div className="px-6 py-4 space-y-4">
              <div className="bg-red-50 p-4 rounded-lg">
                <p className="text-sm text-red-800">
                  Esta acao nao pode ser desfeita. O pedido sera marcado como cancelado.
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Motivo do Cancelamento *
                </label>
                <textarea
                  value={motivoCancelamento}
                  onChange={(e) => setMotivoCancelamento(e.target.value)}
                  rows={3}
                  placeholder="Informe o motivo do cancelamento (minimo 10 caracteres)"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                />
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
              <button
                onClick={() => setIsCancelarModalOpen(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Voltar
              </button>
              <button
                onClick={handleCancelar}
                disabled={cancelarMutation.isPending || motivoCancelamento.length < 10}
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
              >
                {cancelarMutation.isPending ? 'Cancelando...' : 'Confirmar Cancelamento'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
