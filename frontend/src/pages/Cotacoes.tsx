import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Button } from '../components/ui/button';
import { PageLayout } from '../components/PageLayout';
import { Modal, ViewModal } from '../components/Modal';
import { StatusBadge } from '../components/StatusBadge';
import { useModal } from '../hooks/useModal';
import { formatDate } from '../utils/formatters';
import { getStatusOptions } from '../utils/statusConfig';
import {
  PlusIcon,
  MagnifyingGlassIcon,
  PencilIcon,
  TrashIcon,
  PaperAirplaneIcon,
  XCircleIcon,
  EyeIcon,
  TrophyIcon,
  SparklesIcon,
  DocumentTextIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline';

interface ItemSolicitacao {
  id?: number;
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
  status: 'RASCUNHO' | 'ENVIADA' | 'EM_COTACAO' | 'FINALIZADA' | 'CANCELADA';
  data_abertura: string;
  data_limite_proposta?: string;
  data_fechamento?: string;
  urgente: boolean;
  motivo_urgencia?: string;
  observacoes?: string;
  condicoes_pagamento_desejadas?: string;
  prazo_entrega_desejado?: number;
  proposta_vencedora_id?: number;
  justificativa_escolha?: string;
  itens: ItemSolicitacao[];
  total_propostas?: number;
}

interface Produto {
  id: number;
  codigo: string;
  nome: string;
  unidade_medida: string;
}

interface Fornecedor {
  id: number;
  razao_social: string;
  nome_fantasia?: string;
  cnpj: string;
  email?: string;
  telefone?: string;
  cidade?: string;
  estado?: string;
  categorias?: string[];
}

const initialFormData = {
  titulo: '',
  descricao: '',
  data_limite_proposta: '',
  urgente: false,
  motivo_urgencia: '',
  observacoes: '',
  condicoes_pagamento_desejadas: '',
  prazo_entrega_desejado: '',
};

export default function Cotacoes() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Modais usando hook
  const editModal = useModal<Solicitacao>();
  const enviarModal = useModal<Solicitacao>();
  const viewModal = useModal<Solicitacao>();

  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [fornecedorSearchTerm, setFornecedorSearchTerm] = useState('');

  // Form state
  const [formData, setFormData] = useState(initialFormData);
  const [itens, setItens] = useState<ItemSolicitacao[]>([]);
  const [selectedFornecedores, setSelectedFornecedores] = useState<number[]>([]);
  const [enviarParaTodos, setEnviarParaTodos] = useState(false);
  const [fornecedoresProdutos, setFornecedoresProdutos] = useState<number[]>([]);
  const [carregandoFornecedoresProdutos, setCarregandoFornecedoresProdutos] = useState(false);

  // Refs para navegação entre campos
  const tituloRef = useRef<HTMLInputElement>(null);
  const descricaoRef = useRef<HTMLTextAreaElement>(null);

  // Foca no campo título quando o modal abre
  useEffect(() => {
    if (editModal.isOpen) {
      // Pequeno delay para garantir que o modal renderizou
      const timer = setTimeout(() => {
        tituloRef.current?.focus();
        tituloRef.current?.select();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [editModal.isOpen]);

  // Queries
  const { data: solicitacoesData, isLoading } = useQuery({
    queryKey: ['solicitacoes', searchTerm, statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (searchTerm) params.append('busca', searchTerm);
      if (statusFilter) params.append('status', statusFilter);
      return (await api.get(`/cotacoes/solicitacoes?${params}`)).data;
    },
  });

  const { data: produtosData } = useQuery({
    queryKey: ['produtos-list'],
    queryFn: async () => (await api.get('/produtos/')).data,
  });

  const { data: fornecedoresData } = useQuery({
    queryKey: ['fornecedores-list'],
    queryFn: async () => (await api.get('/fornecedores/')).data,
  });

  const solicitacoes: Solicitacao[] = solicitacoesData?.items || [];
  const produtos: Produto[] = produtosData?.items || [];
  const fornecedores: Fornecedor[] = fornecedoresData?.items || [];

  // Filtra fornecedores baseado no termo de busca
  const fornecedoresFiltrados = fornecedores.filter((f) => {
    if (!fornecedorSearchTerm) return true;
    const termo = fornecedorSearchTerm.toLowerCase();
    return (
      f.razao_social?.toLowerCase().includes(termo) ||
      f.nome_fantasia?.toLowerCase().includes(termo) ||
      f.cnpj?.includes(termo) ||
      f.email?.toLowerCase().includes(termo) ||
      f.telefone?.includes(termo) ||
      f.cidade?.toLowerCase().includes(termo) ||
      f.estado?.toLowerCase().includes(termo)
    );
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/cotacoes/solicitacoes', data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['solicitacoes'] }); closeEditModal(); },
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) => api.put(`/cotacoes/solicitacoes/${editModal.data?.id}`, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['solicitacoes'] }); closeEditModal(); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/cotacoes/solicitacoes/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['solicitacoes'] }),
  });

  const enviarMutation = useMutation({
    mutationFn: (data: { id: number; fornecedores_ids: number[] }) =>
      api.post(`/cotacoes/solicitacoes/${data.id}/enviar`, { fornecedores_ids: data.fornecedores_ids }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['solicitacoes'] });
      enviarModal.close();
      setSelectedFornecedores([]);
      setFornecedorSearchTerm('');
      setEnviarParaTodos(false);
      setFornecedoresProdutos([]);
    },
  });

  // Mutation para criar e abrir modal de envio
  const createAndOpenEnviarMutation = useMutation({
    mutationFn: (data: any) => api.post('/cotacoes/solicitacoes', data),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['solicitacoes'] });
      closeEditModal();
      // Abre o modal de envio com a solicitação criada
      const novaSolicitacao = response.data;
      setSelectedFornecedores([]);
      enviarModal.open(novaSolicitacao);
      // Busca fornecedores dos produtos automaticamente
      buscarFornecedoresProdutos(novaSolicitacao.itens || []);
    },
  });

  // Função para buscar fornecedores de todos os produtos dos itens
  // Busca por: 1) vínculo direto produto-fornecedor, 2) categoria dos produtos
  const buscarFornecedoresProdutos = async (itensLista: ItemSolicitacao[]) => {
    setCarregandoFornecedoresProdutos(true);
    try {
      const produtosIds = [...new Set(itensLista.map(item => item.produto_id).filter(id => id > 0))];
      const fornecedoresSet = new Set<number>();
      const categoriasSet = new Set<number>();

      // 1. Buscar fornecedores por vínculo direto produto-fornecedor
      for (const produtoId of produtosIds) {
        try {
          const response = await api.get(`/produtos/${produtoId}/fornecedores`);
          const fornecedoresDoProduto = response.data?.fornecedores || [];
          fornecedoresDoProduto.forEach((f: any) => fornecedoresSet.add(f.id));
        } catch (e) {
          // Ignora erros de produtos sem fornecedores
        }

        // Buscar categoria do produto
        try {
          const prodResponse = await api.get(`/produtos/${produtoId}`);
          if (prodResponse.data?.categoria_id) {
            categoriasSet.add(prodResponse.data.categoria_id);
          }
        } catch (e) {
          // Ignora erros
        }
      }

      // 2. Buscar fornecedores por categoria
      if (categoriasSet.size > 0) {
        try {
          const categoriasIds = Array.from(categoriasSet).join(',');
          const response = await api.get(`/fornecedores/por-categorias?categorias_ids=${categoriasIds}`);
          const fornecedoresCategorias = response.data?.fornecedores || [];
          fornecedoresCategorias.forEach((f: any) => fornecedoresSet.add(f.id));
        } catch (e) {
          console.error('Erro ao buscar fornecedores por categorias:', e);
        }
      }

      setFornecedoresProdutos(Array.from(fornecedoresSet));
    } catch (e) {
      console.error('Erro ao buscar fornecedores dos produtos:', e);
    } finally {
      setCarregandoFornecedoresProdutos(false);
    }
  };

  const cancelarMutation = useMutation({
    mutationFn: (id: number) => api.post(`/cotacoes/solicitacoes/${id}/cancelar`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['solicitacoes'] }),
  });

  // Handlers
  const closeEditModal = () => {
    editModal.close();
    setFormData(initialFormData);
    setItens([]);
    setSelectedFornecedores([]);
  };

  const openCreateModal = () => {
    closeEditModal();
    editModal.open();
  };

  const openEditModal = (solicitacao: Solicitacao) => {
    setFormData({
      titulo: solicitacao.titulo,
      descricao: solicitacao.descricao || '',
      data_limite_proposta: solicitacao.data_limite_proposta?.split('T')[0] || '',
      urgente: solicitacao.urgente,
      motivo_urgencia: solicitacao.motivo_urgencia || '',
      observacoes: solicitacao.observacoes || '',
      condicoes_pagamento_desejadas: solicitacao.condicoes_pagamento_desejadas || '',
      prazo_entrega_desejado: solicitacao.prazo_entrega_desejado?.toString() || '',
    });
    setItens(solicitacao.itens || []);
    editModal.open(solicitacao);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (itens.length === 0) { alert('Adicione pelo menos um item'); return; }

    const data = {
      ...formData,
      data_limite_proposta: formData.data_limite_proposta ? new Date(formData.data_limite_proposta).toISOString() : null,
      prazo_entrega_desejado: formData.prazo_entrega_desejado ? parseInt(formData.prazo_entrega_desejado) : null,
      itens: itens.map((item) => ({
        produto_id: item.produto_id,
        quantidade: item.quantidade,
        unidade_medida: item.unidade_medida,
        especificacoes: item.especificacoes,
      })),
      fornecedores_ids: selectedFornecedores,
    };

    editModal.data ? updateMutation.mutate(data) : createMutation.mutate(data);
  };

  const handleEnviar = () => {
    const fornecedoresParaEnviar = enviarParaTodos ? fornecedoresProdutos : selectedFornecedores;
    if (fornecedoresParaEnviar.length === 0) {
      alert('Selecione pelo menos um fornecedor ou marque "Enviar para todos os fornecedores dos produtos"');
      return;
    }
    if (enviarModal.data) {
      enviarMutation.mutate({ id: enviarModal.data.id, fornecedores_ids: fornecedoresParaEnviar });
    }
  };

  // Função para salvar e abrir modal de envio
  const handleSalvarEEnviar = () => {
    if (itens.length === 0) { alert('Adicione pelo menos um item'); return; }

    const data = {
      ...formData,
      data_limite_proposta: formData.data_limite_proposta ? new Date(formData.data_limite_proposta).toISOString() : null,
      prazo_entrega_desejado: formData.prazo_entrega_desejado ? parseInt(formData.prazo_entrega_desejado) : null,
      itens: itens.map((item) => ({
        produto_id: item.produto_id,
        quantidade: item.quantidade,
        unidade_medida: item.unidade_medida,
        especificacoes: item.especificacoes,
      })),
    };

    createAndOpenEnviarMutation.mutate(data);
  };

  // Função para selecionar/desselecionar todos os fornecedores dos produtos
  const toggleEnviarParaTodos = () => {
    if (!enviarParaTodos) {
      // Ativa o envio para todos
      setEnviarParaTodos(true);
      setSelectedFornecedores([]);
    } else {
      setEnviarParaTodos(false);
    }
  };

  // Quando abre o modal de envio para uma solicitação existente, busca os fornecedores dos produtos
  const abrirEnviarModal = (solicitacao: Solicitacao) => {
    setSelectedFornecedores([]);
    setEnviarParaTodos(false);
    setFornecedoresProdutos([]);
    enviarModal.open(solicitacao);
    buscarFornecedoresProdutos(solicitacao.itens || []);
  };

  const addItem = () => setItens([...itens, { produto_id: 0, quantidade: 1, unidade_medida: 'UN', especificacoes: '' }]);
  const removeItem = (index: number) => setItens(itens.filter((_, i) => i !== index));
  const updateItem = (index: number, field: string, value: any) => {
    const newItens = [...itens];
    (newItens[index] as any)[field] = value;
    if (field === 'produto_id') {
      const produto = produtos.find((p) => p.id === parseInt(value));
      if (produto) newItens[index].unidade_medida = produto.unidade_medida || 'UN';
    }
    setItens(newItens);
  };

  const toggleFornecedor = (id: number) => {
    setSelectedFornecedores((prev) => prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]);
  };

  return (
    <PageLayout
      title="Solicitacoes de Cotacao"
      headerActions={
        <Button onClick={openCreateModal}>
          <PlusIcon className="h-5 w-5 mr-2" />
          Nova Solicitacao
        </Button>
      }
    >
      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <div className="flex-1 relative">
          <MagnifyingGlassIcon className="h-5 w-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por numero ou titulo..."
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
          {getStatusOptions('solicitacao').map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Numero</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Titulo</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Itens</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Propostas</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Data</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acoes</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {isLoading ? (
              <tr><td colSpan={7} className="px-6 py-4 text-center text-gray-500">Carregando...</td></tr>
            ) : solicitacoes.length === 0 ? (
              <tr><td colSpan={7} className="px-6 py-4 text-center text-gray-500">Nenhuma solicitacao encontrada</td></tr>
            ) : (
              solicitacoes.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-medium text-gray-900">{s.numero}</span>
                    {s.urgente && <span className="ml-2 px-2 py-1 text-xs bg-red-100 text-red-800 rounded-full">Urgente</span>}
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900">{s.titulo}</div>
                    {s.descricao && <div className="text-sm text-gray-500 truncate max-w-xs">{s.descricao}</div>}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <StatusBadge entity="solicitacao" status={s.status} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{s.itens?.length || 0}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{s.total_propostas || 0}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDate(s.data_abertura)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div className="flex space-x-2">
                      <button onClick={() => viewModal.open(s)} className="text-gray-600 hover:text-gray-900" title="Visualizar">
                        <EyeIcon className="h-5 w-5" />
                      </button>
                      {s.status === 'RASCUNHO' && (
                        <>
                          <button onClick={() => openEditModal(s)} className="text-blue-600 hover:text-blue-900" title="Editar"><PencilIcon className="h-5 w-5" /></button>
                          <button onClick={() => abrirEnviarModal(s)} className="text-green-600 hover:text-green-900" title="Enviar"><PaperAirplaneIcon className="h-5 w-5" /></button>
                          <button onClick={() => confirm('Deseja excluir?') && deleteMutation.mutate(s.id)} className="text-red-600 hover:text-red-900" title="Excluir"><TrashIcon className="h-5 w-5" /></button>
                        </>
                      )}
                      {s.status === 'ENVIADA' && (
                        <>
                          <button onClick={() => abrirEnviarModal(s)} className="text-green-600 hover:text-green-900" title="Add Fornecedores"><PaperAirplaneIcon className="h-5 w-5" /></button>
                          <button onClick={() => navigate(`/cotacoes/${s.id}/propostas`)} className="text-purple-600 hover:text-purple-900" title="Propostas"><DocumentTextIcon className="h-5 w-5" /></button>
                        </>
                      )}
                      {s.status === 'EM_COTACAO' && (
                        <>
                          <button onClick={() => navigate(`/cotacoes/${s.id}/propostas`)} className="text-blue-600 hover:text-blue-900" title="Propostas"><DocumentTextIcon className="h-5 w-5" /></button>
                          <button onClick={() => navigate(`/cotacoes/${s.id}/mapa`)} className="text-purple-600 hover:text-purple-900" title="Mapa"><TrophyIcon className="h-5 w-5" /></button>
                          <button onClick={() => navigate(`/cotacoes/${s.id}/sugestao`)} className="text-yellow-600 hover:text-yellow-900" title="IA"><SparklesIcon className="h-5 w-5" /></button>
                        </>
                      )}
                      {['RASCUNHO', 'ENVIADA', 'EM_COTACAO'].includes(s.status) && (
                        <button onClick={() => confirm('Deseja cancelar?') && cancelarMutation.mutate(s.id)} className="text-red-600 hover:text-red-900" title="Cancelar"><XCircleIcon className="h-5 w-5" /></button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Modal Criar/Editar */}
      <Modal
        isOpen={editModal.isOpen}
        title={editModal.data ? 'Editar Solicitacao' : 'Nova Solicitacao de Cotacao'}
        onClose={closeEditModal}
        size="4xl"
        footer={
          <div className="flex justify-between w-full">
            <button
              type="button"
              onClick={closeEditModal}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Cancelar
            </button>
            <div className="flex gap-3">
              {/* Botão Salvar Rascunho - só aparece quando criando novo */}
              {!editModal.data && (
                <button
                  type="button"
                  onClick={handleSubmit as any}
                  disabled={createMutation.isPending || itens.length === 0}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Salvando...' : 'Salvar Rascunho'}
                </button>
              )}
              {/* Botão Salvar - só aparece quando editando */}
              {editModal.data && (
                <button
                  type="button"
                  onClick={handleSubmit as any}
                  disabled={updateMutation.isPending || itens.length === 0}
                  className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
                >
                  {updateMutation.isPending ? 'Salvando...' : 'Salvar'}
                </button>
              )}
              {/* Botão Salvar e Enviar - só aparece quando criando novo */}
              {!editModal.data && (
                <button
                  type="button"
                  onClick={handleSalvarEEnviar}
                  disabled={createAndOpenEnviarMutation.isPending || itens.length === 0}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                >
                  <PaperAirplaneIcon className="h-5 w-5" />
                  {createAndOpenEnviarMutation.isPending ? 'Salvando...' : 'Salvar e Enviar'}
                </button>
              )}
            </div>
          </div>
        }
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700">Titulo *</label>
              <input
                ref={tituloRef}
                type="text"
                required
                placeholder="Digite o título da solicitação..."
                value={formData.titulo}
                onChange={(e) => setFormData({ ...formData, titulo: e.target.value })}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    descricaoRef.current?.focus();
                  }
                }}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                style={{ caretColor: '#4f46e5' }}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700">Descricao</label>
              <textarea
                ref={descricaoRef}
                value={formData.descricao}
                onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
                rows={2}
                placeholder="Descreva os detalhes da solicitação..."
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                style={{ caretColor: '#4f46e5' }}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Data Limite</label>
              <input type="date" value={formData.data_limite_proposta} onChange={(e) => setFormData({ ...formData, data_limite_proposta: e.target.value })} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Prazo Entrega (dias)</label>
              <input type="number" value={formData.prazo_entrega_desejado} onChange={(e) => setFormData({ ...formData, prazo_entrega_desejado: e.target.value })} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Condicoes Pagamento</label>
              <input type="text" value={formData.condicoes_pagamento_desejadas} onChange={(e) => setFormData({ ...formData, condicoes_pagamento_desejadas: e.target.value })} placeholder="Ex: 30/60/90 dias" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" />
            </div>
            <div className="flex items-center">
              <input type="checkbox" checked={formData.urgente} onChange={(e) => setFormData({ ...formData, urgente: e.target.checked })} className="h-4 w-4 text-primary-600 border-gray-300 rounded" />
              <label className="ml-2 text-sm text-gray-700">Urgente</label>
            </div>
            {formData.urgente && (
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700">Motivo Urgencia</label>
                <input type="text" value={formData.motivo_urgencia} onChange={(e) => setFormData({ ...formData, motivo_urgencia: e.target.value })} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" />
              </div>
            )}
          </div>

          {/* Itens */}
          <div className="border-t pt-4">
            <div className="flex justify-between items-center mb-2">
              <h4 className="text-sm font-medium text-gray-900">Itens *</h4>
              <button type="button" onClick={addItem} className="text-sm text-primary-600 hover:text-primary-900">+ Adicionar Item</button>
            </div>
            {itens.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">Nenhum item adicionado</p>
            ) : (
              <div className="space-y-2">
                {itens.map((item, index) => (
                  <div key={index} className="flex gap-2 items-start bg-gray-50 p-2 rounded">
                    <select value={item.produto_id} onChange={(e) => updateItem(index, 'produto_id', parseInt(e.target.value))} className="flex-1 rounded-md border-gray-300 text-sm" required>
                      <option value={0}>Selecione produto</option>
                      {produtos.map((p) => <option key={p.id} value={p.id}>{p.codigo} - {p.nome}</option>)}
                    </select>
                    <input type="number" value={item.quantidade} onChange={(e) => updateItem(index, 'quantidade', parseFloat(e.target.value))} placeholder="Qtd" min="0.01" step="0.01" className="w-24 rounded-md border-gray-300 text-sm" required />
                    <input type="text" value={item.unidade_medida} onChange={(e) => updateItem(index, 'unidade_medida', e.target.value)} placeholder="UN" className="w-20 rounded-md border-gray-300 text-sm" />
                    <input type="text" value={item.especificacoes || ''} onChange={(e) => updateItem(index, 'especificacoes', e.target.value)} placeholder="Especificacoes" className="flex-1 rounded-md border-gray-300 text-sm" />
                    <button type="button" onClick={() => removeItem(index)} className="text-red-600"><TrashIcon className="h-5 w-5" /></button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Observacoes</label>
            <textarea value={formData.observacoes} onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })} rows={2} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" />
          </div>
        </form>
      </Modal>

      {/* Modal Enviar */}
      <Modal
        isOpen={enviarModal.isOpen}
        title="Enviar para Fornecedores"
        subtitle="Escolha como deseja enviar esta solicitacao"
        onClose={() => { enviarModal.close(); setSelectedFornecedores([]); setFornecedorSearchTerm(''); setEnviarParaTodos(false); setFornecedoresProdutos([]); }}
        onSubmit={handleEnviar}
        submitLabel={enviarParaTodos ? `Enviar para ${fornecedoresProdutos.length} fornecedor(es) dos produtos` : `Enviar para ${selectedFornecedores.length} fornecedor(es)`}
        submitDisabled={enviarParaTodos ? fornecedoresProdutos.length === 0 : selectedFornecedores.length === 0}
        submitLoading={enviarMutation.isPending}
        submitColor="green"
        size="lg"
      >
        {fornecedores.length === 0 ? (
          <p className="text-sm text-gray-500 text-center">Nenhum fornecedor cadastrado</p>
        ) : (
          <div className="space-y-4">
            {/* Opção: Enviar para todos os fornecedores dos produtos */}
            <div
              onClick={toggleEnviarParaTodos}
              className={`p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                enviarParaTodos
                  ? 'bg-green-50 border-green-500'
                  : 'bg-gray-50 border-gray-200 hover:border-green-300'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-full ${enviarParaTodos ? 'bg-green-100' : 'bg-gray-200'}`}>
                  <UserGroupIcon className={`h-6 w-6 ${enviarParaTodos ? 'text-green-600' : 'text-gray-500'}`} />
                </div>
                <div className="flex-1">
                  <p className={`font-medium ${enviarParaTodos ? 'text-green-800' : 'text-gray-700'}`}>
                    Enviar para todos os fornecedores dos produtos
                  </p>
                  <p className="text-sm text-gray-500">
                    {carregandoFornecedoresProdutos
                      ? 'Buscando fornecedores por produto e categoria...'
                      : fornecedoresProdutos.length > 0
                        ? `${fornecedoresProdutos.length} fornecedor(es) encontrado(s) (por produto ou categoria)`
                        : 'Nenhum fornecedor encontrado para os produtos ou categorias desta solicitacao'}
                  </p>
                </div>
                <input
                  type="radio"
                  checked={enviarParaTodos}
                  onChange={() => {}}
                  className="h-5 w-5 text-green-600"
                />
              </div>
            </div>

            {/* Opção: Selecionar fornecedores manualmente */}
            <div
              onClick={() => setEnviarParaTodos(false)}
              className={`p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                !enviarParaTodos
                  ? 'bg-blue-50 border-blue-500'
                  : 'bg-gray-50 border-gray-200 hover:border-blue-300'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-full ${!enviarParaTodos ? 'bg-blue-100' : 'bg-gray-200'}`}>
                  <MagnifyingGlassIcon className={`h-6 w-6 ${!enviarParaTodos ? 'text-blue-600' : 'text-gray-500'}`} />
                </div>
                <div className="flex-1">
                  <p className={`font-medium ${!enviarParaTodos ? 'text-blue-800' : 'text-gray-700'}`}>
                    Selecionar fornecedores manualmente
                  </p>
                  <p className="text-sm text-gray-500">
                    Escolha quais fornecedores devem receber esta solicitacao
                  </p>
                </div>
                <input
                  type="radio"
                  checked={!enviarParaTodos}
                  onChange={() => {}}
                  className="h-5 w-5 text-blue-600"
                />
              </div>
            </div>

            {/* Seleção manual de fornecedores - só aparece se não for "enviar para todos" */}
            {!enviarParaTodos && (
              <div className="space-y-3 pt-2">
                {/* Campo de busca amplo */}
                <div className="relative">
                  <MagnifyingGlassIcon className="h-5 w-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Buscar por razao social, nome fantasia, CNPJ, email, telefone, cidade ou estado..."
                    value={fornecedorSearchTerm}
                    onChange={(e) => setFornecedorSearchTerm(e.target.value)}
                    className="pl-10 w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                  />
                </div>

                {/* Contadores */}
                <div className="flex justify-between text-sm text-gray-500 px-1">
                  <span>{fornecedoresFiltrados.length} de {fornecedores.length} fornecedores</span>
                  {selectedFornecedores.length > 0 && (
                    <span className="text-primary-600 font-medium">{selectedFornecedores.length} selecionado(s)</span>
                  )}
                </div>

                {/* Lista de fornecedores */}
                <div className="space-y-2 max-h-60 overflow-y-auto border rounded-md p-2">
                  {fornecedoresFiltrados.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-4">Nenhum fornecedor encontrado</p>
                  ) : (
                    fornecedoresFiltrados.map((f) => (
                      <label key={f.id} className={`flex items-start p-3 rounded cursor-pointer transition-colors ${selectedFornecedores.includes(f.id) ? 'bg-primary-50 border border-primary-200' : 'hover:bg-gray-50 border border-transparent'}`}>
                        <input
                          type="checkbox"
                          checked={selectedFornecedores.includes(f.id)}
                          onChange={() => toggleFornecedor(f.id)}
                          className="h-4 w-4 text-primary-600 border-gray-300 rounded mt-1"
                        />
                        <div className="ml-3 flex-1">
                          <div className="text-sm font-medium text-gray-900">{f.razao_social}</div>
                          {f.nome_fantasia && <div className="text-sm text-gray-600">{f.nome_fantasia}</div>}
                          <div className="text-sm text-gray-500">{f.cnpj}</div>
                          <div className="flex flex-wrap gap-2 mt-1">
                            {f.email && <span className="text-xs text-gray-500">{f.email}</span>}
                            {f.telefone && <span className="text-xs text-gray-500">{f.telefone}</span>}
                            {(f.cidade || f.estado) && (
                              <span className="text-xs text-gray-500">{[f.cidade, f.estado].filter(Boolean).join(' - ')}</span>
                            )}
                          </div>
                        </div>
                      </label>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Modal de Visualização */}
      <ViewModal isOpen={viewModal.isOpen} title={viewModal.data?.numero || ''} onClose={viewModal.close}>
        {viewModal.data && (
          <div className="space-y-4">
            <StatusBadge entity="solicitacao" status={viewModal.data.status} />
            <div>
              <h4 className="text-sm font-medium text-gray-500">Titulo</h4>
              <p className="text-gray-900">{viewModal.data.titulo}</p>
            </div>
            {viewModal.data.descricao && (
              <div>
                <h4 className="text-sm font-medium text-gray-500">Descricao</h4>
                <p className="text-gray-900">{viewModal.data.descricao}</p>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="text-sm font-medium text-gray-500">Data Abertura</h4>
                <p className="text-gray-900">{formatDate(viewModal.data.data_abertura)}</p>
              </div>
              {viewModal.data.data_limite_proposta && (
                <div>
                  <h4 className="text-sm font-medium text-gray-500">Data Limite</h4>
                  <p className="text-gray-900">{formatDate(viewModal.data.data_limite_proposta)}</p>
                </div>
              )}
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-500 mb-2">Itens ({viewModal.data.itens?.length || 0})</h4>
              <div className="bg-gray-50 rounded p-3 space-y-2">
                {viewModal.data.itens?.map((item, index) => (
                  <div key={index} className="flex justify-between text-sm">
                    <span>{item.produto_nome || `Produto ${item.produto_id}`}</span>
                    <span className="text-gray-500">{item.quantidade} {item.unidade_medida}</span>
                  </div>
                ))}
              </div>
            </div>
            {viewModal.data.observacoes && (
              <div>
                <h4 className="text-sm font-medium text-gray-500">Observacoes</h4>
                <p className="text-gray-900">{viewModal.data.observacoes}</p>
              </div>
            )}
          </div>
        )}
      </ViewModal>
    </PageLayout>
  );
}
