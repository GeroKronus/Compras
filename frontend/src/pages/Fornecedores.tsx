import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { useNavigate } from 'react-router-dom';

interface Fornecedor {
  id: number;
  razao_social: string;
  nome_fantasia: string | null;
  cnpj: string;
  email_principal: string | null;
  telefone_principal: string | null;
  endereco_logradouro: string | null;
  endereco_cidade: string | null;
  endereco_estado: string | null;
  endereco_cep: string | null;
  contatos: any;
  categorias_produtos: string[];
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
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ['fornecedores'],
    queryFn: async () => {
      const response = await api.get('/fornecedores/');
      return response.data;
    }
  });

  const criarMutation = useMutation({
    mutationFn: async (dados: any) => {
      return await api.post('/fornecedores/', dados);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fornecedores'] });
      setShowForm(false);
    }
  });

  const atualizarMutation = useMutation({
    mutationFn: async ({ id, dados }: { id: number; dados: any }) => {
      return await api.put(`/fornecedores/${id}`, dados);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fornecedores'] });
      setShowForm(false);
      setEditando(null);
    }
  });

  const deletarMutation = useMutation({
    mutationFn: async (id: number) => {
      return await api.delete(`/fornecedores/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fornecedores'] });
    }
  });

  const aprovarMutation = useMutation({
    mutationFn: async (id: number) => {
      return await api.patch(`/fornecedores/${id}/aprovar`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fornecedores'] });
    }
  });

  const reprovarMutation = useMutation({
    mutationFn: async (id: number) => {
      return await api.patch(`/fornecedores/${id}/reprovar`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fornecedores'] });
    }
  });

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const dados = {
      razao_social: formData.get('razao_social'),
      nome_fantasia: formData.get('nome_fantasia') || null,
      cnpj: formData.get('cnpj'),
      email_principal: formData.get('email_principal') || null,
      telefone_principal: formData.get('telefone_principal') || null,
      endereco_logradouro: formData.get('endereco_logradouro') || null,
      endereco_cidade: formData.get('endereco_cidade') || null,
      endereco_estado: formData.get('endereco_estado') || null,
      endereco_cep: formData.get('endereco_cep') || null,
      condicoes_pagamento: formData.get('condicoes_pagamento') || null,
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
            <h1 className="text-2xl font-bold text-primary">Fornecedores</h1>
            <p className="text-sm text-muted-foreground">Gerenciamento de fornecedores</p>
          </div>
          <Button onClick={() => navigate('/dashboard')} variant="outline">
            Voltar ao Dashboard
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
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Razão Social *</label>
                    <input
                      name="razao_social"
                      defaultValue={editando?.razao_social}
                      required
                      className="w-full border rounded px-3 py-2"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Nome Fantasia</label>
                    <input
                      name="nome_fantasia"
                      defaultValue={editando?.nome_fantasia || ''}
                      className="w-full border rounded px-3 py-2"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">CNPJ * (14 dígitos)</label>
                    <input
                      name="cnpj"
                      defaultValue={editando?.cnpj}
                      required
                      pattern="\d{14}"
                      maxLength={14}
                      className="w-full border rounded px-3 py-2"
                      placeholder="00000000000000"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Email Principal *</label>
                    <input
                      name="email_principal"
                      type="email"
                      defaultValue={editando?.email_principal || ''}
                      required
                      className="w-full border rounded px-3 py-2"
                      placeholder="contato@empresa.com"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Telefone Principal</label>
                    <input
                      name="telefone_principal"
                      defaultValue={editando?.telefone_principal || ''}
                      className="w-full border rounded px-3 py-2"
                      placeholder="(11) 99999-9999"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">CEP</label>
                    <input
                      name="endereco_cep"
                      defaultValue={editando?.endereco_cep || ''}
                      pattern="\d{8}"
                      maxLength={8}
                      className="w-full border rounded px-3 py-2"
                      placeholder="00000000"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Endereço</label>
                  <input
                    name="endereco_logradouro"
                    defaultValue={editando?.endereco_logradouro || ''}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Cidade</label>
                    <input
                      name="endereco_cidade"
                      defaultValue={editando?.endereco_cidade || ''}
                      className="w-full border rounded px-3 py-2"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Estado (UF)</label>
                    <input
                      name="endereco_estado"
                      defaultValue={editando?.endereco_estado || ''}
                      maxLength={2}
                      className="w-full border rounded px-3 py-2"
                      placeholder="SP"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Condições de Pagamento</label>
                  <input
                    name="condicoes_pagamento"
                    defaultValue={editando?.condicoes_pagamento || ''}
                    className="w-full border rounded px-3 py-2"
                    placeholder="Ex: 30/60 dias"
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
          {data?.items?.map((fornecedor: Fornecedor) => (
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
                        <span className="ml-1 font-medium">{fornecedor.cnpj.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5')}</span>
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
                      {Number(fornecedor.rating) > 0 && (
                        <div>
                          <span className="text-gray-500">Avaliação:</span>
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
                        <span className="text-gray-500">Condições:</span>
                        <span className="ml-1">{fornecedor.condicoes_pagamento}</span>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2 flex-wrap">
                    {!fornecedor.aprovado ? (
                      <Button
                        size="sm"
                        variant="default"
                        className="bg-green-600 hover:bg-green-700"
                        onClick={() => aprovarMutation.mutate(fornecedor.id)}
                      >
                        Aprovar
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-red-600 text-red-600 hover:bg-red-50"
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
                      onClick={() => {
                        if (confirm('Deseja excluir este fornecedor?')) {
                          deletarMutation.mutate(fornecedor.id);
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
      </main>
    </div>
  );
}
