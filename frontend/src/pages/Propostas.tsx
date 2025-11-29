import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { Button } from '../components/ui/button';
import { useAuth } from '../hooks/useAuth';
import {
  PlusIcon,
  XCircleIcon,
  EyeIcon,
  CurrencyDollarIcon,
} from '@heroicons/react/24/outline';

interface ItemSolicitacao {
  id: number;
  produto_id: number;
  quantidade: number;
  unidade_medida: string;
  especificacoes?: string;
  produto_nome?: string;
  produto_codigo?: string;
}

interface Solicitacao {
  id: number;
  numero: string;
  titulo: string;
  descricao?: string;
  status: string;
  data_abertura: string;
  data_limite_proposta?: string;
  urgente: boolean;
  itens: ItemSolicitacao[];
}

interface ItemProposta {
  id?: number;
  item_solicitacao_id: number;
  preco_unitario: number;
  quantidade_disponivel?: number;
  desconto_percentual: number;
  prazo_entrega_item?: number;
  observacoes?: string;
  marca_oferecida?: string;
  produto_nome?: string;
  quantidade_solicitada?: number;
}

interface Proposta {
  id: number;
  solicitacao_id: number;
  fornecedor_id: number;
  status: 'PENDENTE' | 'RECEBIDA' | 'APROVADA' | 'REJEITADA' | 'VENCEDORA';
  data_envio_solicitacao?: string;
  data_recebimento?: string;
  condicoes_pagamento?: string;
  prazo_entrega?: number;
  validade_proposta?: string;
  frete_tipo?: string;
  frete_valor?: number;
  valor_total?: number;
  desconto_total: number;
  observacoes?: string;
  itens: ItemProposta[];
  fornecedor_nome?: string;
  fornecedor_cnpj?: string;
}

interface Fornecedor {
  id: number;
  razao_social: string;
  cnpj: string;
}

const statusColors: Record<string, string> = {
  PENDENTE: 'bg-yellow-100 text-yellow-800',
  RECEBIDA: 'bg-blue-100 text-blue-800',
  APROVADA: 'bg-green-100 text-green-800',
  REJEITADA: 'bg-red-100 text-red-800',
  VENCEDORA: 'bg-purple-100 text-purple-800',
};

const statusLabels: Record<string, string> = {
  PENDENTE: 'Pendente',
  RECEBIDA: 'Recebida',
  APROVADA: 'Aprovada',
  REJEITADA: 'Rejeitada',
  VENCEDORA: 'Vencedora',
};

export default function Propostas() {
  const { tenant } = useAuth();
  const navigate = useNavigate();
  const { solicitacaoId } = useParams();
  const queryClient = useQueryClient();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [editingProposta, setEditingProposta] = useState<Proposta | null>(null);
  const [viewingProposta, setViewingProposta] = useState<Proposta | null>(null);
  const [selectedFornecedor, setSelectedFornecedor] = useState<number>(0);

  const [formData, setFormData] = useState({
    condicoes_pagamento: '',
    prazo_entrega: '',
    validade_proposta: '',
    frete_tipo: 'CIF',
    frete_valor: '',
    observacoes: '',
  });

  const [itensProposta, setItensProposta] = useState<ItemProposta[]>([]);

  // Queries
  const { data: solicitacaoData } = useQuery({
    queryKey: ['solicitacao', solicitacaoId],
    queryFn: async () => {
      const response = await api.get(`/cotacoes/solicitacoes/${solicitacaoId}`);
      return response.data;
    },
    enabled: !!solicitacaoId,
  });

  const { data: propostasData, isLoading } = useQuery({
    queryKey: ['propostas', solicitacaoId],
    queryFn: async () => {
      const response = await api.get(`/cotacoes/solicitacoes/${solicitacaoId}/propostas`);
      return response.data;
    },
    enabled: !!solicitacaoId,
  });

  const { data: fornecedoresData } = useQuery({
    queryKey: ['fornecedores-list'],
    queryFn: async () => {
      const response = await api.get('/fornecedores/');
      return response.data;
    },
  });

  const solicitacao: Solicitacao | null = solicitacaoData || null;
  const propostas: Proposta[] = propostasData?.items || [];
  const fornecedores: Fornecedor[] = fornecedoresData?.items || [];

  // Inicializar itens quando solicitacao carregar
  useEffect(() => {
    if (solicitacao && solicitacao.itens && itensProposta.length === 0) {
      setItensProposta(
        solicitacao.itens.map((item) => ({
          item_solicitacao_id: item.id,
          preco_unitario: 0,
          quantidade_disponivel: item.quantidade,
          desconto_percentual: 0,
          prazo_entrega_item: undefined,
          observacoes: '',
          marca_oferecida: '',
          produto_nome: item.produto_nome,
          quantidade_solicitada: item.quantidade,
        }))
      );
    }
  }, [solicitacao, itensProposta.length]);

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: any) =>
      api.post(`/cotacoes/propostas/${solicitacaoId}/fornecedor/${selectedFornecedor}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['propostas', solicitacaoId] });
      closeModal();
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) => api.put(`/cotacoes/propostas/${editingProposta?.id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['propostas', solicitacaoId] });
      closeModal();
    },
  });

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingProposta(null);
    setSelectedFornecedor(0);
    setFormData({
      condicoes_pagamento: '',
      prazo_entrega: '',
      validade_proposta: '',
      frete_tipo: 'CIF',
      frete_valor: '',
      observacoes: '',
    });
    if (solicitacao) {
      setItensProposta(
        solicitacao.itens.map((item) => ({
          item_solicitacao_id: item.id,
          preco_unitario: 0,
          quantidade_disponivel: item.quantidade,
          desconto_percentual: 0,
          prazo_entrega_item: undefined,
          observacoes: '',
          marca_oferecida: '',
          produto_nome: item.produto_nome,
          quantidade_solicitada: item.quantidade,
        }))
      );
    }
  };

  const openCreateModal = () => {
    closeModal();
    setIsModalOpen(true);
  };

  const openEditModal = (proposta: Proposta) => {
    setEditingProposta(proposta);
    setSelectedFornecedor(proposta.fornecedor_id);
    setFormData({
      condicoes_pagamento: proposta.condicoes_pagamento || '',
      prazo_entrega: proposta.prazo_entrega?.toString() || '',
      validade_proposta: proposta.validade_proposta?.split('T')[0] || '',
      frete_tipo: proposta.frete_tipo || 'CIF',
      frete_valor: proposta.frete_valor?.toString() || '',
      observacoes: proposta.observacoes || '',
    });
    setItensProposta(
      proposta.itens.map((item) => ({
        ...item,
        preco_unitario: item.preco_unitario,
        desconto_percentual: item.desconto_percentual || 0,
      }))
    );
    setIsModalOpen(true);
  };

  const openViewModal = (proposta: Proposta) => {
    setViewingProposta(proposta);
    setIsViewModalOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!editingProposta && selectedFornecedor === 0) {
      alert('Selecione um fornecedor');
      return;
    }

    const hasPrecos = itensProposta.every((item) => item.preco_unitario > 0);
    if (!hasPrecos) {
      alert('Preencha o preco de todos os itens');
      return;
    }

    const data = {
      condicoes_pagamento: formData.condicoes_pagamento || null,
      prazo_entrega: formData.prazo_entrega ? parseInt(formData.prazo_entrega) : null,
      validade_proposta: formData.validade_proposta || null,
      frete_tipo: formData.frete_tipo || null,
      frete_valor: formData.frete_valor ? parseFloat(formData.frete_valor) : null,
      observacoes: formData.observacoes || null,
      itens: itensProposta.map((item) => ({
        item_solicitacao_id: item.item_solicitacao_id,
        preco_unitario: item.preco_unitario,
        quantidade_disponivel: item.quantidade_disponivel,
        desconto_percentual: item.desconto_percentual || 0,
        prazo_entrega_item: item.prazo_entrega_item || null,
        observacoes: item.observacoes || null,
        marca_oferecida: item.marca_oferecida || null,
      })),
    };

    if (editingProposta) {
      updateMutation.mutate(data);
    } else {
      createMutation.mutate(data);
    }
  };

  const updateItemProposta = (index: number, field: string, value: any) => {
    const newItens = [...itensProposta];
    (newItens[index] as any)[field] = value;
    setItensProposta(newItens);
  };

  const calcularTotalProposta = () => {
    const totalItens = itensProposta.reduce((acc, item) => {
      const qtd = item.quantidade_disponivel || item.quantidade_solicitada || 0;
      const precoComDesconto = item.preco_unitario * (1 - (item.desconto_percentual || 0) / 100);
      return acc + qtd * precoComDesconto;
    }, 0);
    const frete = parseFloat(formData.frete_valor) || 0;
    return totalItens + frete;
  };

  // Fornecedores que ja tem proposta nesta solicitacao
  const fornecedoresComProposta = propostas.map((p) => p.fornecedor_id);
  const fornecedoresDisponiveis = fornecedores.filter(
    (f) => !fornecedoresComProposta.includes(f.id)
  );

  if (!solicitacaoId) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500">Solicitacao nao encontrada</p>
          <Button onClick={() => navigate('/cotacoes')} className="mt-4">
            Voltar
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-primary">Propostas de Fornecedores</h1>
            <p className="text-sm text-muted-foreground">{tenant?.nome_empresa}</p>
          </div>
          <Button onClick={() => navigate('/dashboard')} variant="outline">
            Voltar
          </Button>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto px-4 py-8 space-y-6">
        {/* Info da Solicitacao */}
        {solicitacao && (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-xl font-semibold">{solicitacao.numero}</h2>
                <p className="text-gray-600">{solicitacao.titulo}</p>
              </div>
              <div className="text-right">
                <span className={`px-3 py-1 rounded-full text-sm ${solicitacao.urgente ? 'bg-red-100 text-red-800' : 'bg-gray-100'}`}>
                  {solicitacao.urgente ? 'Urgente' : solicitacao.status}
                </span>
                {solicitacao.data_limite_proposta && (
                  <p className="text-sm text-gray-500 mt-1">
                    Limite: {new Date(solicitacao.data_limite_proposta).toLocaleDateString('pt-BR')}
                  </p>
                )}
              </div>
            </div>
            <div className="border-t pt-4">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Itens Solicitados:</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                {solicitacao.itens?.map((item) => (
                  <div key={item.id} className="bg-gray-50 p-2 rounded text-sm">
                    <span className="font-medium">{item.produto_codigo}</span> - {item.produto_nome}
                    <span className="block text-gray-500">{item.quantidade} {item.unidade_medida}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Acoes */}
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-medium">Propostas Recebidas ({propostas.length})</h3>
          {fornecedoresDisponiveis.length > 0 && solicitacao?.status !== 'FINALIZADA' && (
            <Button onClick={openCreateModal}>
              <PlusIcon className="h-5 w-5 mr-2" />
              Registrar Proposta
            </Button>
          )}
        </div>

        {/* Lista de Propostas */}
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fornecedor</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Valor Total</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Prazo</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validade</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acoes</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    Carregando...
                  </td>
                </tr>
              ) : propostas.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    Nenhuma proposta registrada
                  </td>
                </tr>
              ) : (
                propostas.map((proposta) => (
                  <tr key={proposta.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">{proposta.fornecedor_nome}</div>
                      <div className="text-sm text-gray-500">{proposta.fornecedor_cnpj}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColors[proposta.status]}`}>
                        {statusLabels[proposta.status]}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {proposta.valor_total?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                      </div>
                      {proposta.desconto_total > 0 && (
                        <div className="text-xs text-green-600">-{proposta.desconto_total}% desc.</div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {proposta.prazo_entrega ? `${proposta.prazo_entrega} dias` : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {proposta.validade_proposta
                        ? new Date(proposta.validade_proposta).toLocaleDateString('pt-BR')
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => openViewModal(proposta)}
                          className="text-gray-600 hover:text-gray-900"
                          title="Visualizar"
                        >
                          <EyeIcon className="h-5 w-5" />
                        </button>
                        {(proposta.status === 'PENDENTE' || proposta.status === 'RECEBIDA') && (
                          <button
                            onClick={() => openEditModal(proposta)}
                            className="text-blue-600 hover:text-blue-900"
                            title="Editar Proposta"
                          >
                            <CurrencyDollarIcon className="h-5 w-5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>

      {/* Modal Criar/Editar Proposta */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-5xl w-full max-h-[90vh] overflow-y-auto">
            <form onSubmit={handleSubmit}>
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">
                  {editingProposta ? 'Atualizar Proposta' : 'Registrar Nova Proposta'}
                </h3>
              </div>

              <div className="px-6 py-4 space-y-6">
                {/* Selecionar Fornecedor */}
                {!editingProposta && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Fornecedor *</label>
                    <select
                      value={selectedFornecedor}
                      onChange={(e) => setSelectedFornecedor(parseInt(e.target.value))}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                      required
                    >
                      <option value={0}>Selecione um fornecedor</option>
                      {fornecedoresDisponiveis.map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.razao_social} - {f.cnpj}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Dados Gerais */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Condicoes Pagamento</label>
                    <input
                      type="text"
                      value={formData.condicoes_pagamento}
                      onChange={(e) => setFormData({ ...formData, condicoes_pagamento: e.target.value })}
                      placeholder="Ex: 30/60/90 dias"
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Prazo Entrega (dias)</label>
                    <input
                      type="number"
                      value={formData.prazo_entrega}
                      onChange={(e) => setFormData({ ...formData, prazo_entrega: e.target.value })}
                      min="1"
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Validade Proposta</label>
                    <input
                      type="date"
                      value={formData.validade_proposta}
                      onChange={(e) => setFormData({ ...formData, validade_proposta: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Tipo Frete</label>
                    <select
                      value={formData.frete_tipo}
                      onChange={(e) => setFormData({ ...formData, frete_tipo: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                    >
                      <option value="CIF">CIF (Frete Incluso)</option>
                      <option value="FOB">FOB (Frete a Pagar)</option>
                    </select>
                  </div>
                </div>

                {formData.frete_tipo === 'FOB' && (
                  <div className="w-48">
                    <label className="block text-sm font-medium text-gray-700">Valor do Frete</label>
                    <input
                      type="number"
                      value={formData.frete_valor}
                      onChange={(e) => setFormData({ ...formData, frete_valor: e.target.value })}
                      step="0.01"
                      min="0"
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                    />
                  </div>
                )}

                {/* Itens da Proposta */}
                <div className="border-t pt-4">
                  <h4 className="text-sm font-medium text-gray-900 mb-4">Precos por Item *</h4>
                  <div className="space-y-4">
                    {itensProposta.map((item, index) => (
                      <div key={index} className="bg-gray-50 p-4 rounded-lg">
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <span className="font-medium">{item.produto_nome}</span>
                            <span className="text-gray-500 ml-2">
                              (Qtd solicitada: {item.quantidade_solicitada})
                            </span>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                          <div>
                            <label className="block text-xs text-gray-500">Preco Unitario *</label>
                            <input
                              type="number"
                              value={item.preco_unitario || ''}
                              onChange={(e) => updateItemProposta(index, 'preco_unitario', parseFloat(e.target.value) || 0)}
                              step="0.01"
                              min="0.01"
                              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
                              required
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500">Qtd Disponivel</label>
                            <input
                              type="number"
                              value={item.quantidade_disponivel || ''}
                              onChange={(e) => updateItemProposta(index, 'quantidade_disponivel', parseFloat(e.target.value) || undefined)}
                              step="0.01"
                              min="0"
                              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500">Desconto %</label>
                            <input
                              type="number"
                              value={item.desconto_percentual || ''}
                              onChange={(e) => updateItemProposta(index, 'desconto_percentual', parseFloat(e.target.value) || 0)}
                              step="0.01"
                              min="0"
                              max="100"
                              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500">Marca Oferecida</label>
                            <input
                              type="text"
                              value={item.marca_oferecida || ''}
                              onChange={(e) => updateItemProposta(index, 'marca_oferecida', e.target.value)}
                              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500">Prazo Item (dias)</label>
                            <input
                              type="number"
                              value={item.prazo_entrega_item || ''}
                              onChange={(e) => updateItemProposta(index, 'prazo_entrega_item', parseInt(e.target.value) || undefined)}
                              min="1"
                              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Observacoes */}
                <div>
                  <label className="block text-sm font-medium text-gray-700">Observacoes</label>
                  <textarea
                    value={formData.observacoes}
                    onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
                    rows={2}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                  />
                </div>

                {/* Total */}
                <div className="bg-primary-50 p-4 rounded-lg">
                  <div className="flex justify-between items-center">
                    <span className="text-lg font-medium">Total Estimado:</span>
                    <span className="text-2xl font-bold text-primary-600">
                      {calcularTotalProposta().toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                    </span>
                  </div>
                </div>
              </div>

              <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50"
                >
                  {createMutation.isPending || updateMutation.isPending ? 'Salvando...' : 'Salvar Proposta'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Visualizar */}
      {isViewModalOpen && viewingProposta && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-medium text-gray-900">Proposta de {viewingProposta.fornecedor_nome}</h3>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColors[viewingProposta.status]}`}>
                  {statusLabels[viewingProposta.status]}
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
                  <h4 className="text-sm font-medium text-gray-500">Condicoes Pagamento</h4>
                  <p className="text-gray-900">{viewingProposta.condicoes_pagamento || '-'}</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-500">Prazo Entrega</h4>
                  <p className="text-gray-900">{viewingProposta.prazo_entrega ? `${viewingProposta.prazo_entrega} dias` : '-'}</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-500">Validade Proposta</h4>
                  <p className="text-gray-900">
                    {viewingProposta.validade_proposta
                      ? new Date(viewingProposta.validade_proposta).toLocaleDateString('pt-BR')
                      : '-'}
                  </p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-500">Frete</h4>
                  <p className="text-gray-900">
                    {viewingProposta.frete_tipo}{' '}
                    {viewingProposta.frete_valor ? `- R$ ${viewingProposta.frete_valor.toFixed(2)}` : ''}
                  </p>
                </div>
              </div>

              <div className="border-t pt-4">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Itens da Proposta</h4>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Produto</th>
                        <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">Preco Unit.</th>
                        <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">Qtd</th>
                        <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">Desc.</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Marca</th>
                        <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {viewingProposta.itens.map((item) => {
                        const qtd = item.quantidade_disponivel || item.quantidade_solicitada || 0;
                        const total = qtd * item.preco_unitario * (1 - (item.desconto_percentual || 0) / 100);
                        return (
                          <tr key={item.id}>
                            <td className="px-3 py-2 text-sm">{item.produto_nome}</td>
                            <td className="px-3 py-2 text-sm text-right">
                              {item.preco_unitario.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                            </td>
                            <td className="px-3 py-2 text-sm text-right">{qtd}</td>
                            <td className="px-3 py-2 text-sm text-right">{item.desconto_percentual || 0}%</td>
                            <td className="px-3 py-2 text-sm">{item.marca_oferecida || '-'}</td>
                            <td className="px-3 py-2 text-sm text-right font-medium">
                              {total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="flex justify-between items-center">
                  <span className="text-lg font-medium">Valor Total:</span>
                  <span className="text-2xl font-bold">
                    {viewingProposta.valor_total?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </span>
                </div>
              </div>

              {viewingProposta.observacoes && (
                <div>
                  <h4 className="text-sm font-medium text-gray-500">Observacoes</h4>
                  <p className="text-gray-900">{viewingProposta.observacoes}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
