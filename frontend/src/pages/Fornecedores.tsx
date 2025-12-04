/**
 * Fornecedores - Página refatorada usando useCrudResource e FormField
 * Redução de ~100 linhas de código duplicado
 */
import { useState, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useCrudResource } from '../hooks/useCrudResource';
import { api } from '../services/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { FormInput, FormSelect, FormRow, FormActions } from '../components/ui/form-field';
import { useNavigate } from 'react-router-dom';

interface Categoria {
  id: number;
  nome: string;
}

interface Fornecedor {
  id: number;
  razao_social: string;
  nome_fantasia: string | null;
  cnpj: string;
  email_principal: string | null;
  telefone_principal: string | null;
  whatsapp: string | null;
  endereco_logradouro: string | null;
  endereco_cidade: string | null;
  endereco_estado: string | null;
  endereco_cep: string | null;
  contatos: any;
  categorias_produtos: string[];
  categorias: Categoria[];
  condicoes_pagamento: string | null;
  rating: number | string;
  total_compras: number;
  aprovado: boolean;
  ativo: boolean;
  tenant_id: number;
  created_at: string;
  updated_at: string;
}

export function Fornecedores() {
  const [showForm, setShowForm] = useState(false);
  const [editando, setEditando] = useState<Fornecedor | null>(null);
  const [categoriasSelecionadas, setCategoriasSelecionadas] = useState<number[]>([]);
  const navigate = useNavigate();

  // Buscar categorias disponíveis
  const { data: categoriasData, isLoading: loadingCategorias, error: errorCategorias } = useQuery({
    queryKey: ['categorias-fornecedores'],
    queryFn: async () => {
      console.log('[Fornecedores] Buscando categorias...');
      const response = await api.get('/categorias?page_size=100');
      console.log('[Fornecedores] Categorias recebidas:', response.data);
      return response.data.items as Categoria[];
    },
    staleTime: 1000 * 60 * 5, // 5 minutos
  });
  const categorias = categoriasData || [];

  // Debug: log do estado das categorias
  console.log('[Fornecedores] Estado categorias:', { categorias, loadingCategorias, errorCategorias });

  // Hook genérico CRUD - elimina 50 linhas de código duplicado
  const { items, isLoading, create, update, remove, invalidate } = useCrudResource<Fornecedor>({
    endpoint: '/fornecedores',
    queryKey: 'fornecedores',
    onCreateSuccess: () => { setShowForm(false); setCategoriasSelecionadas([]); },
    onUpdateSuccess: () => { setShowForm(false); setEditando(null); setCategoriasSelecionadas([]); },
  });

  // Sincronizar categorias quando editando
  useEffect(() => {
    if (editando?.categorias) {
      setCategoriasSelecionadas(editando.categorias.map(c => c.id));
    } else {
      setCategoriasSelecionadas([]);
    }
  }, [editando]);

  // Operações específicas (não cobertas pelo CRUD genérico)
  const aprovarMutation = useMutation({
    mutationFn: (id: number) => api.patch(`/fornecedores/${id}/aprovar`),
    onSuccess: () => invalidate(),
  });

  const reprovarMutation = useMutation({
    mutationFn: (id: number) => api.patch(`/fornecedores/${id}/reprovar`),
    onSuccess: () => invalidate(),
  });

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const dados = {
      razao_social: formData.get('razao_social') as string,
      nome_fantasia: formData.get('nome_fantasia') as string || null,
      cnpj: formData.get('cnpj') as string,
      email_principal: formData.get('email_principal') as string || null,
      telefone_principal: formData.get('telefone_principal') as string || null,
      whatsapp: formData.get('whatsapp') as string || null,
      endereco_logradouro: formData.get('endereco_logradouro') as string || null,
      endereco_cidade: formData.get('endereco_cidade') as string || null,
      endereco_estado: formData.get('endereco_estado') as string || null,
      endereco_cep: formData.get('endereco_cep') as string || null,
      condicoes_pagamento: formData.get('condicoes_pagamento') as string || null,
      ativo: formData.get('ativo') === 'true',
      categorias_ids: categoriasSelecionadas,
    };

    if (editando) {
      update.mutate({ id: editando.id, data: dados });
    } else {
      create.mutate(dados);
    }
  };

  const toggleCategoria = (categoriaId: number) => {
    setCategoriasSelecionadas(prev =>
      prev.includes(categoriaId)
        ? prev.filter(id => id !== categoriaId)
        : [...prev, categoriaId]
    );
  };

  const handleDelete = (id: number) => {
    if (confirm('Deseja excluir este fornecedor?')) {
      remove.mutate(id);
    }
  };

  // Helper para formatar CNPJ (DRY - função pura)
  const formatCnpj = (cnpj: string) =>
    cnpj.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');

  if (isLoading) return <div className="p-6">Carregando...</div>;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-primary">Fornecedores</h1>
            <p className="text-sm text-muted-foreground">Gerenciamento de fornecedores</p>
          </div>
          <Button onClick={() => navigate(-1)} variant="outline">
            Voltar
          </Button>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold">Lista de Fornecedores</h2>
          <Button onClick={() => { setShowForm(true); setEditando(null); }}>
            Novo Fornecedor
          </Button>
        </div>

        {showForm && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>{editando ? 'Editar' : 'Novo'} Fornecedor</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <FormRow>
                  <FormInput
                    name="razao_social"
                    label="Razao Social"
                    required
                    defaultValue={editando?.razao_social}
                  />
                  <FormInput
                    name="nome_fantasia"
                    label="Nome Fantasia"
                    defaultValue={editando?.nome_fantasia || ''}
                  />
                </FormRow>

                <FormRow>
                  <FormInput
                    name="cnpj"
                    label="CNPJ (14 digitos)"
                    required
                    pattern="\d{14}"
                    maxLength={14}
                    placeholder="00000000000000"
                    defaultValue={editando?.cnpj}
                  />
                  <FormInput
                    name="email_principal"
                    label="Email Principal"
                    type="email"
                    required
                    placeholder="contato@empresa.com"
                    defaultValue={editando?.email_principal || ''}
                  />
                </FormRow>

                <FormRow>
                  <FormInput
                    name="telefone_principal"
                    label="Telefone Principal"
                    placeholder="(11) 99999-9999"
                    defaultValue={editando?.telefone_principal || ''}
                  />
                  <FormInput
                    name="whatsapp"
                    label="WhatsApp"
                    placeholder="11999999999 (apenas números)"
                    defaultValue={editando?.whatsapp || ''}
                  />
                </FormRow>

                <FormRow>
                  <FormInput
                    name="endereco_cep"
                    label="CEP"
                    pattern="\d{8}"
                    maxLength={8}
                    placeholder="00000000"
                    defaultValue={editando?.endereco_cep || ''}
                  />
                </FormRow>

                <FormInput
                  name="endereco_logradouro"
                  label="Endereco"
                  defaultValue={editando?.endereco_logradouro || ''}
                />

                <FormRow>
                  <FormInput
                    name="endereco_cidade"
                    label="Cidade"
                    defaultValue={editando?.endereco_cidade || ''}
                  />
                  <FormInput
                    name="endereco_estado"
                    label="Estado (UF)"
                    maxLength={2}
                    placeholder="SP"
                    defaultValue={editando?.endereco_estado || ''}
                  />
                </FormRow>

                <FormInput
                  name="condicoes_pagamento"
                  label="Condicoes de Pagamento"
                  placeholder="Ex: 30/60 dias"
                  defaultValue={editando?.condicoes_pagamento || ''}
                />

                <FormSelect
                  name="ativo"
                  label="Status"
                  defaultValue={editando?.ativo !== false ? 'true' : 'false'}
                  options={[
                    { value: 'true', label: 'Ativo' },
                    { value: 'false', label: 'Inativo' },
                  ]}
                />

                {/* Multi-select de Categorias */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Categorias que Atende</label>
                  <div className="border rounded-md p-3 max-h-48 overflow-y-auto">
                    {loadingCategorias ? (
                      <p className="text-sm text-gray-500">Carregando categorias...</p>
                    ) : errorCategorias ? (
                      <p className="text-sm text-red-500">Erro ao carregar categorias</p>
                    ) : categorias.length === 0 ? (
                      <p className="text-sm text-gray-500">Nenhuma categoria cadastrada. <a href="/categorias" className="text-blue-600 underline">Cadastrar categorias</a></p>
                    ) : (
                      <div className="grid grid-cols-2 gap-2">
                        {categorias.map((cat) => (
                          <label key={cat.id} className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
                            <input
                              type="checkbox"
                              checked={categoriasSelecionadas.includes(cat.id)}
                              onChange={() => toggleCategoria(cat.id)}
                              className="rounded border-gray-300"
                            />
                            <span className="text-sm">{cat.nome}</span>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                  {categoriasSelecionadas.length > 0 && (
                    <p className="text-xs text-gray-500">
                      {categoriasSelecionadas.length} categoria(s) selecionada(s)
                    </p>
                  )}
                </div>

                <FormActions>
                  <Button type="submit" disabled={create.isPending || update.isPending}>
                    {create.isPending || update.isPending ? 'Salvando...' : 'Salvar'}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => { setShowForm(false); setEditando(null); }}
                  >
                    Cancelar
                  </Button>
                </FormActions>
              </form>
            </CardContent>
          </Card>
        )}

        <div className="grid gap-4">
          {items.map((fornecedor) => (
            <Card key={fornecedor.id}>
              <CardContent className="p-4">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-semibold text-lg">{fornecedor.razao_social}</h3>
                      {fornecedor.nome_fantasia && (
                        <span className="text-sm text-gray-500">({fornecedor.nome_fantasia})</span>
                      )}
                      {fornecedor.aprovado && (
                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">Aprovado</span>
                      )}
                      {!fornecedor.ativo && (
                        <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded">Inativo</span>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm mb-2">
                      <div>
                        <span className="text-gray-500">CNPJ:</span>
                        <span className="ml-1 font-medium">{formatCnpj(fornecedor.cnpj)}</span>
                      </div>
                      {fornecedor.email_principal && (
                        <div>
                          <span className="text-gray-500">Email:</span>
                          <span className="ml-1 font-medium">{fornecedor.email_principal}</span>
                        </div>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm mb-2">
                      {fornecedor.telefone_principal && (
                        <div>
                          <span className="text-gray-500">Telefone:</span>
                          <span className="ml-1 font-medium">{fornecedor.telefone_principal}</span>
                        </div>
                      )}
                      {fornecedor.whatsapp && (
                        <div>
                          <span className="text-gray-500">WhatsApp:</span>
                          <span className="ml-1 font-medium text-green-600">{fornecedor.whatsapp}</span>
                        </div>
                      )}
                      {Number(fornecedor.rating) > 0 && (
                        <div>
                          <span className="text-gray-500">Avaliacao:</span>
                          <span className="ml-1 font-medium">{Number(fornecedor.rating).toFixed(2)} / 5.00</span>
                        </div>
                      )}
                    </div>

                    {(fornecedor.endereco_logradouro || fornecedor.endereco_cidade) && (
                      <div className="text-sm text-gray-600 mb-2">
                        {fornecedor.endereco_logradouro && <span>{fornecedor.endereco_logradouro}</span>}
                        {fornecedor.endereco_cidade && fornecedor.endereco_estado && (
                          <span className="ml-2">{fornecedor.endereco_cidade}/{fornecedor.endereco_estado}</span>
                        )}
                      </div>
                    )}

                    {fornecedor.condicoes_pagamento && (
                      <div className="text-sm">
                        <span className="text-gray-500">Condicoes:</span>
                        <span className="ml-1">{fornecedor.condicoes_pagamento}</span>
                      </div>
                    )}

                    {fornecedor.categorias && fornecedor.categorias.length > 0 && (
                      <div className="text-sm mt-2">
                        <span className="text-gray-500">Categorias:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {fornecedor.categorias.map((cat) => (
                            <span key={cat.id} className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                              {cat.nome}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2 flex-wrap">
                    {!fornecedor.aprovado ? (
                      <Button
                        size="sm"
                        variant="default"
                        className="bg-green-600 hover:bg-green-700"
                        disabled={aprovarMutation.isPending}
                        onClick={() => aprovarMutation.mutate(fornecedor.id)}
                      >
                        Aprovar
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-red-600 text-red-600 hover:bg-red-50"
                        disabled={reprovarMutation.isPending}
                        onClick={() => reprovarMutation.mutate(fornecedor.id)}
                      >
                        Reprovar
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => { setEditando(fornecedor); setShowForm(true); }}
                    >
                      Editar
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={remove.isPending}
                      onClick={() => handleDelete(fornecedor.id)}
                    >
                      Excluir
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </div>
  );
}
