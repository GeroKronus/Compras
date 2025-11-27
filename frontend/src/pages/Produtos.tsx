import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Modal } from '../components/Modal';
import { useNavigate } from 'react-router-dom';
import { EnvelopeIcon, CheckCircleIcon, ExclamationCircleIcon, UserGroupIcon, PlusIcon, XMarkIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';

interface Produto {
  id: number;
  codigo: string;
  nome: string;
  descricao: string | null;
  categoria_id: number | null;
  unidade_medida: string;
  estoque_minimo: number;
  estoque_maximo: number | null;
  estoque_atual: number;
  preco_referencia: number | null;
  especificacoes: any;
  ativo: boolean;
  tenant_id: number;
  created_at: string;
  updated_at: string;
}

interface Categoria {
  id: number;
  nome: string;
}

interface Fornecedor {
  id: number;
  razao_social: string;
  nome_fantasia: string | null;
  cnpj: string;
  email: string | null;
  telefone: string | null;
}

interface CotacaoEmailResult {
  solicitacao_id: number;
  solicitacao_numero: string;
  produto: string;
  quantidade: number;
  emails_enviados: number;
  fornecedores_notificados: string[];
  falhas: string[];
  status: string;
  mensagem: string;
}

export function Produtos() {
  const [showForm, setShowForm] = useState(false);
  const [editando, setEditando] = useState<Produto | null>(null);
  const [showCotacaoModal, setShowCotacaoModal] = useState(false);
  const [produtoCotacao, setProdutoCotacao] = useState<Produto | null>(null);
  const [quantidade, setQuantidade] = useState<number>(1);
  const [observacoes, setObservacoes] = useState<string>('');
  const [cotacaoResult, setCotacaoResult] = useState<CotacaoEmailResult | null>(null);
  const [showFornecedoresModal, setShowFornecedoresModal] = useState(false);
  const [produtoFornecedores, setProdutoFornecedores] = useState<Produto | null>(null);
  const [fornecedoresSelecionados, setFornecedoresSelecionados] = useState<number[]>([]);
  const [fornecedorSearchTerm, setFornecedorSearchTerm] = useState('');
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ['produtos'],
    queryFn: async () => {
      const response = await api.get('/produtos/');
      return response.data;
    }
  });

  const { data: categorias } = useQuery({
    queryKey: ['categorias'],
    queryFn: async () => {
      const response = await api.get('/categorias/');
      return response.data;
    }
  });

  // Lista de todos os fornecedores disponíveis
  const { data: todosFornecedores } = useQuery({
    queryKey: ['fornecedores'],
    queryFn: async () => {
      const response = await api.get('/fornecedores/');
      return response.data;
    }
  });

  // Fornecedores do produto selecionado
  const { data: fornecedoresDoProduto, refetch: refetchFornecedores } = useQuery({
    queryKey: ['produto-fornecedores', produtoFornecedores?.id],
    queryFn: async () => {
      if (!produtoFornecedores) return null;
      const response = await api.get(`/produtos/${produtoFornecedores.id}/fornecedores`);
      return response.data;
    },
    enabled: !!produtoFornecedores
  });

  const criarMutation = useMutation({
    mutationFn: async (dados: any) => {
      return await api.post('/produtos/', dados);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['produtos'] });
      setShowForm(false);
    }
  });

  const atualizarMutation = useMutation({
    mutationFn: async ({ id, dados }: { id: number; dados: any }) => {
      return await api.put(`/produtos/${id}`, dados);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['produtos'] });
      setShowForm(false);
      setEditando(null);
    }
  });

  const deletarMutation = useMutation({
    mutationFn: async (id: number) => {
      return await api.delete(`/produtos/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['produtos'] });
    }
  });

  const cotacaoEmailMutation = useMutation({
    mutationFn: async ({ produto_id, quantidade, observacoes }: { produto_id: number; quantidade: number; observacoes?: string }) => {
      const params = new URLSearchParams();
      params.append('produto_id', produto_id.toString());
      params.append('quantidade', quantidade.toString());
      if (observacoes) params.append('observacoes', observacoes);
      return await api.post(`/cotacoes/solicitar-por-email?${params.toString()}`);
    },
    onSuccess: (response) => {
      setCotacaoResult(response.data);
      queryClient.invalidateQueries({ queryKey: ['cotacoes'] });
    }
  });

  const abrirModalCotacao = (produto: Produto) => {
    setProdutoCotacao(produto);
    setQuantidade(produto.estoque_minimo > 0 ? produto.estoque_minimo : 1);
    setObservacoes('');
    setCotacaoResult(null);
    setShowCotacaoModal(true);
  };

  const enviarCotacaoEmail = () => {
    if (!produtoCotacao || quantidade <= 0) return;
    cotacaoEmailMutation.mutate({
      produto_id: produtoCotacao.id,
      quantidade,
      observacoes: observacoes || undefined
    });
  };

  const fecharModalCotacao = () => {
    setShowCotacaoModal(false);
    setProdutoCotacao(null);
    setCotacaoResult(null);
  };

  // Mutation para salvar fornecedores do produto
  const salvarFornecedoresMutation = useMutation({
    mutationFn: async ({ produtoId, fornecedoresIds }: { produtoId: number; fornecedoresIds: number[] }) => {
      return await api.put(`/produtos/${produtoId}/fornecedores`, fornecedoresIds);
    },
    onSuccess: () => {
      refetchFornecedores();
      queryClient.invalidateQueries({ queryKey: ['produtos'] });
    }
  });

  const abrirModalFornecedores = (produto: Produto) => {
    setProdutoFornecedores(produto);
    setFornecedoresSelecionados([]);
    setShowFornecedoresModal(true);
  };

  const fecharModalFornecedores = () => {
    setShowFornecedoresModal(false);
    setProdutoFornecedores(null);
    setFornecedoresSelecionados([]);
    setFornecedorSearchTerm('');
  };

  const toggleFornecedor = (fornecedorId: number) => {
    setFornecedoresSelecionados(prev =>
      prev.includes(fornecedorId)
        ? prev.filter(id => id !== fornecedorId)
        : [...prev, fornecedorId]
    );
  };

  const salvarFornecedores = () => {
    if (!produtoFornecedores) return;

    // Combinar fornecedores atuais com os novos selecionados
    const atuais = fornecedoresDoProduto?.fornecedores?.map((f: Fornecedor) => f.id) || [];
    const todos = [...new Set([...atuais, ...fornecedoresSelecionados])];

    salvarFornecedoresMutation.mutate({
      produtoId: produtoFornecedores.id,
      fornecedoresIds: todos
    });
    setFornecedoresSelecionados([]);
  };

  const removerFornecedor = (fornecedorId: number) => {
    if (!produtoFornecedores) return;

    const atuais = fornecedoresDoProduto?.fornecedores?.map((f: Fornecedor) => f.id) || [];
    const novos = atuais.filter((id: number) => id !== fornecedorId);

    salvarFornecedoresMutation.mutate({
      produtoId: produtoFornecedores.id,
      fornecedoresIds: novos
    });
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const dados = {
      codigo: formData.get('codigo'),
      nome: formData.get('nome'),
      descricao: formData.get('descricao') || null,
      categoria_id: formData.get('categoria_id') ? parseInt(formData.get('categoria_id') as string) : null,
      unidade_medida: formData.get('unidade_medida') || 'UN',
      estoque_minimo: parseFloat(formData.get('estoque_minimo') as string) || 0,
      estoque_maximo: formData.get('estoque_maximo') ? parseFloat(formData.get('estoque_maximo') as string) : null,
      estoque_atual: parseFloat(formData.get('estoque_atual') as string) || 0,
      preco_referencia: formData.get('preco_referencia') ? parseFloat(formData.get('preco_referencia') as string) : null,
      ativo: formData.get('ativo') === 'true',
    };

    if (editando) {
      atualizarMutation.mutate({ id: editando.id, dados });
    } else {
      criarMutation.mutate(dados);
    }
  };

  if (isLoading) return <div>Carregando...</div>;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-primary">Produtos</h1>
            <p className="text-sm text-muted-foreground">Gerenciamento de produtos</p>
          </div>
          <Button onClick={() => navigate('/dashboard')} variant="outline">
            Voltar ao Dashboard
          </Button>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold">Lista de Produtos</h2>
          <Button onClick={() => { setShowForm(true); setEditando(null); }}>
            Novo Produto
          </Button>
        </div>

        {showForm && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>{editando ? 'Editar' : 'Novo'} Produto</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Código *</label>
                    <input
                      name="codigo"
                      defaultValue={editando?.codigo}
                      required
                      className="w-full border rounded px-3 py-2"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Nome *</label>
                    <input
                      name="nome"
                      defaultValue={editando?.nome}
                      required
                      className="w-full border rounded px-3 py-2"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Descrição</label>
                  <textarea
                    name="descricao"
                    defaultValue={editando?.descricao || ''}
                    className="w-full border rounded px-3 py-2"
                    rows={3}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Categoria</label>
                    <select
                      name="categoria_id"
                      defaultValue={editando?.categoria_id || ''}
                      className="w-full border rounded px-3 py-2"
                    >
                      <option value="">Sem categoria</option>
                      {categorias?.items?.map((cat: Categoria) => (
                        <option key={cat.id} value={cat.id}>{cat.nome}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Unidade de Medida</label>
                    <select
                      name="unidade_medida"
                      defaultValue={editando?.unidade_medida || 'UN'}
                      className="w-full border rounded px-3 py-2"
                    >
                      <option value="UN">Unidade</option>
                      <option value="KG">Quilograma</option>
                      <option value="MT">Metro</option>
                      <option value="LT">Litro</option>
                      <option value="CX">Caixa</option>
                      <option value="PC">Peça</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Estoque Mínimo</label>
                    <input
                      type="number"
                      step="0.01"
                      name="estoque_minimo"
                      defaultValue={editando?.estoque_minimo || 0}
                      className="w-full border rounded px-3 py-2"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Estoque Máximo</label>
                    <input
                      type="number"
                      step="0.01"
                      name="estoque_maximo"
                      defaultValue={editando?.estoque_maximo || ''}
                      className="w-full border rounded px-3 py-2"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Estoque Atual</label>
                    <input
                      type="number"
                      step="0.01"
                      name="estoque_atual"
                      defaultValue={editando?.estoque_atual || 0}
                      className="w-full border rounded px-3 py-2"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Preço Referência</label>
                    <input
                      type="number"
                      step="0.01"
                      name="preco_referencia"
                      defaultValue={editando?.preco_referencia || ''}
                      className="w-full border rounded px-3 py-2"
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Status</label>
                    <select
                      name="ativo"
                      defaultValue={editando?.ativo !== false ? 'true' : 'false'}
                      className="w-full border rounded px-3 py-2"
                    >
                      <option value="true">Ativo</option>
                      <option value="false">Inativo</option>
                    </select>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button type="submit">Salvar</Button>
                  <Button type="button" variant="outline" onClick={() => { setShowForm(false); setEditando(null); }}>
                    Cancelar
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        <div className="grid gap-4">
          {data?.items?.map((produto: Produto) => (
            <Card key={produto.id}>
              <CardContent className="p-4">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-semibold text-lg">{produto.nome}</h3>
                      <span className="text-sm text-gray-500">({produto.codigo})</span>
                      {!produto.ativo && (
                        <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded">Inativo</span>
                      )}
                    </div>
                    {produto.descricao && <p className="text-sm text-gray-600 mb-2">{produto.descricao}</p>}
                    <div className="grid grid-cols-4 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">Unidade:</span>
                        <span className="ml-1 font-medium">{produto.unidade_medida}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Estoque Atual:</span>
                        <span className="ml-1 font-medium">{produto.estoque_atual}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Estoque Mín:</span>
                        <span className="ml-1 font-medium">{produto.estoque_minimo}</span>
                      </div>
                      {produto.preco_referencia && (
                        <div>
                          <span className="text-gray-500">Preço Ref:</span>
                          <span className="ml-1 font-medium">R$ {Number(produto.preco_referencia).toFixed(2)}</span>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="default"
                      onClick={() => abrirModalFornecedores(produto)}
                      className="bg-purple-600 hover:bg-purple-700"
                    >
                      <UserGroupIcon className="h-4 w-4 mr-1" />
                      Fornecedores
                    </Button>
                    <Button
                      size="sm"
                      variant="default"
                      onClick={() => abrirModalCotacao(produto)}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      <EnvelopeIcon className="h-4 w-4 mr-1" />
                      Cotar
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => { setEditando(produto); setShowForm(true); }}
                    >
                      Editar
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => {
                        if (confirm('Deseja excluir este produto?')) {
                          deletarMutation.mutate(produto.id);
                        }
                      }}
                    >
                      Excluir
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Modal de Cotação por Email */}
        <Modal
          isOpen={showCotacaoModal}
          title="Solicitar Cotação por Email"
          subtitle={produtoCotacao ? `Produto: ${produtoCotacao.nome}` : ''}
          onClose={fecharModalCotacao}
          size="lg"
          footer={
            cotacaoResult ? (
              <button
                onClick={fecharModalCotacao}
                className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
              >
                Fechar
              </button>
            ) : (
              <div className="flex gap-3">
                <button
                  onClick={fecharModalCotacao}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  onClick={enviarCotacaoEmail}
                  disabled={cotacaoEmailMutation.isPending || quantidade <= 0}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                >
                  <EnvelopeIcon className="h-5 w-5" />
                  {cotacaoEmailMutation.isPending ? 'Enviando...' : 'Enviar para Fornecedores'}
                </button>
              </div>
            )
          }
        >
          {cotacaoResult ? (
            // Resultado do envio
            <div className="space-y-4">
              {cotacaoResult.emails_enviados > 0 ? (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-green-800 mb-2">
                    <CheckCircleIcon className="h-6 w-6" />
                    <span className="font-semibold">Emails Enviados com Sucesso!</span>
                  </div>
                  <p className="text-green-700">{cotacaoResult.mensagem}</p>
                </div>
              ) : (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-red-800 mb-2">
                    <ExclamationCircleIcon className="h-6 w-6" />
                    <span className="font-semibold">Nenhum email enviado</span>
                  </div>
                  <p className="text-red-700">Verifique se há fornecedores cadastrados com email.</p>
                </div>
              )}

              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                <p><strong>Solicitação:</strong> {cotacaoResult.solicitacao_numero}</p>
                <p><strong>Produto:</strong> {cotacaoResult.produto}</p>
                <p><strong>Quantidade:</strong> {cotacaoResult.quantidade}</p>
                <p><strong>Status:</strong> {cotacaoResult.status}</p>
              </div>

              {cotacaoResult.fornecedores_notificados.length > 0 && (
                <div>
                  <p className="font-medium mb-2">Fornecedores notificados:</p>
                  <ul className="list-disc list-inside text-sm text-gray-600">
                    {cotacaoResult.fornecedores_notificados.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              )}

              {cotacaoResult.falhas.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <p className="font-medium text-yellow-800 mb-1">Falhas no envio:</p>
                  <ul className="list-disc list-inside text-sm text-yellow-700">
                    {cotacaoResult.falhas.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="text-sm text-gray-500 pt-2 border-t">
                Os fornecedores receberão um email solicitando cotação.
                Acompanhe as respostas na seção de Cotações.
              </div>
            </div>
          ) : (
            // Formulário
            <div className="space-y-4">
              {cotacaoEmailMutation.isError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-red-700">
                    Erro ao enviar cotação. Verifique se o serviço de email está configurado.
                  </p>
                </div>
              )}

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-blue-800 text-sm">
                  <strong>Como funciona:</strong> O sistema enviará um email de solicitação de cotação
                  para todos os fornecedores cadastrados. As respostas serão lidas automaticamente
                  e analisadas pela IA.
                </p>
              </div>

              {produtoCotacao && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-medium mb-2">Detalhes do Produto</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <p><span className="text-gray-500">Código:</span> {produtoCotacao.codigo}</p>
                    <p><span className="text-gray-500">Unidade:</span> {produtoCotacao.unidade_medida}</p>
                    <p><span className="text-gray-500">Estoque Atual:</span> {produtoCotacao.estoque_atual}</p>
                    <p><span className="text-gray-500">Estoque Mínimo:</span> {produtoCotacao.estoque_minimo}</p>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Quantidade a Cotar *
                </label>
                <input
                  type="number"
                  min="1"
                  value={quantidade}
                  onChange={(e) => setQuantidade(parseInt(e.target.value) || 0)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Observações (opcional)
                </label>
                <textarea
                  value={observacoes}
                  onChange={(e) => setObservacoes(e.target.value)}
                  placeholder="Ex: Urgente, precisamos em até 5 dias..."
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
                  rows={3}
                />
              </div>
            </div>
          )}
        </Modal>

        {/* Modal de Gerenciamento de Fornecedores */}
        <Modal
          isOpen={showFornecedoresModal}
          title="Fornecedores do Produto"
          subtitle={produtoFornecedores ? `${produtoFornecedores.nome} (${produtoFornecedores.codigo})` : ''}
          onClose={fecharModalFornecedores}
          size="xl"
          footer={
            <button
              onClick={fecharModalFornecedores}
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
            >
              Fechar
            </button>
          }
        >
          <div className="space-y-6">
            {/* Fornecedores Atuais */}
            <div>
              <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                <UserGroupIcon className="h-5 w-5 text-purple-600" />
                Fornecedores Cadastrados
              </h4>

              {fornecedoresDoProduto?.fornecedores?.length > 0 ? (
                <div className="space-y-2">
                  {fornecedoresDoProduto.fornecedores.map((fornecedor: Fornecedor) => (
                    <div
                      key={fornecedor.id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border"
                    >
                      <div>
                        <p className="font-medium">{fornecedor.razao_social}</p>
                        <p className="text-sm text-gray-500">
                          {fornecedor.email || 'Sem email'} • {fornecedor.telefone || 'Sem telefone'}
                        </p>
                      </div>
                      <button
                        onClick={() => removerFornecedor(fornecedor.id)}
                        className="p-1 text-red-600 hover:bg-red-50 rounded"
                        title="Remover fornecedor"
                      >
                        <XMarkIcon className="h-5 w-5" />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-6 bg-yellow-50 rounded-lg border border-yellow-200">
                  <ExclamationCircleIcon className="h-8 w-8 text-yellow-500 mx-auto mb-2" />
                  <p className="text-yellow-700 font-medium">Nenhum fornecedor cadastrado</p>
                  <p className="text-yellow-600 text-sm">Adicione fornecedores abaixo para poder solicitar cotações</p>
                </div>
              )}
            </div>

            {/* Adicionar Fornecedores */}
            <div className="border-t pt-4">
              <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                <PlusIcon className="h-5 w-5 text-green-600" />
                Adicionar Fornecedores
              </h4>

              {todosFornecedores?.items?.length > 0 ? (
                <>
                  {/* Campo de busca amplo */}
                  <div className="relative mb-3">
                    <MagnifyingGlassIcon className="h-5 w-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                    <input
                      type="text"
                      placeholder="Buscar por razao social, nome fantasia, CNPJ, email ou telefone..."
                      value={fornecedorSearchTerm}
                      onChange={(e) => setFornecedorSearchTerm(e.target.value)}
                      className="pl-10 w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500"
                    />
                  </div>

                  {/* Contadores */}
                  {(() => {
                    const fornecedoresDisponiveis = todosFornecedores.items
                      .filter((f: any) => !fornecedoresDoProduto?.fornecedores?.some((fp: Fornecedor) => fp.id === f.id));
                    const fornecedoresFiltrados = fornecedoresDisponiveis.filter((f: any) => {
                      if (!fornecedorSearchTerm) return true;
                      const termo = fornecedorSearchTerm.toLowerCase();
                      return (
                        f.razao_social?.toLowerCase().includes(termo) ||
                        f.nome_fantasia?.toLowerCase().includes(termo) ||
                        f.cnpj?.includes(termo) ||
                        f.email_principal?.toLowerCase().includes(termo) ||
                        f.telefone?.includes(termo)
                      );
                    });

                    return (
                      <>
                        <div className="flex justify-between text-sm text-gray-500 px-1 mb-2">
                          <span>{fornecedoresFiltrados.length} de {fornecedoresDisponiveis.length} fornecedores disponiveis</span>
                          {fornecedoresSelecionados.length > 0 && (
                            <span className="text-purple-600 font-medium">{fornecedoresSelecionados.length} selecionado(s)</span>
                          )}
                        </div>

                        <div className="max-h-60 overflow-y-auto space-y-2 border rounded-lg p-2">
                          {fornecedoresFiltrados.length === 0 ? (
                            <p className="text-sm text-gray-500 text-center py-4">Nenhum fornecedor encontrado</p>
                          ) : (
                            fornecedoresFiltrados.map((fornecedor: any) => (
                              <label
                                key={fornecedor.id}
                                className={`flex items-start p-3 rounded-lg cursor-pointer transition-colors ${
                                  fornecedoresSelecionados.includes(fornecedor.id)
                                    ? 'bg-purple-50 border-purple-300 border-2'
                                    : 'bg-white border border-gray-200 hover:bg-gray-50'
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  checked={fornecedoresSelecionados.includes(fornecedor.id)}
                                  onChange={() => toggleFornecedor(fornecedor.id)}
                                  className="h-4 w-4 text-purple-600 rounded mr-3 mt-1"
                                />
                                <div className="flex-1">
                                  <p className="font-medium">{fornecedor.razao_social}</p>
                                  {fornecedor.nome_fantasia && (
                                    <p className="text-sm text-gray-600">{fornecedor.nome_fantasia}</p>
                                  )}
                                  <p className="text-sm text-gray-500">CNPJ: {fornecedor.cnpj}</p>
                                  <div className="flex flex-wrap gap-2 mt-1">
                                    {fornecedor.email_principal && (
                                      <span className="text-xs text-gray-500">{fornecedor.email_principal}</span>
                                    )}
                                    {fornecedor.telefone && (
                                      <span className="text-xs text-gray-500">{fornecedor.telefone}</span>
                                    )}
                                  </div>
                                </div>
                              </label>
                            ))
                          )}
                        </div>
                      </>
                    );
                  })()}

                  {fornecedoresSelecionados.length > 0 && (
                    <button
                      onClick={salvarFornecedores}
                      disabled={salvarFornecedoresMutation.isPending}
                      className="mt-3 w-full px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      <PlusIcon className="h-5 w-5" />
                      {salvarFornecedoresMutation.isPending
                        ? 'Adicionando...'
                        : `Adicionar ${fornecedoresSelecionados.length} fornecedor(es)`}
                    </button>
                  )}
                </>
              ) : (
                <div className="text-center py-4 bg-gray-50 rounded-lg">
                  <p className="text-gray-500">Nenhum fornecedor disponível</p>
                  <p className="text-sm text-gray-400">Cadastre fornecedores na seção de Fornecedores</p>
                </div>
              )}
            </div>
          </div>
        </Modal>
      </main>
    </div>
  );
}
