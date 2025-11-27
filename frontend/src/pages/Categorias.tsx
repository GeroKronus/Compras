import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

interface Categoria {
  id: number;
  nome: string;
  descricao: string | null;
  codigo: string | null;
  categoria_pai_id: number | null;
  tenant_id: number;
  created_at: string;
  updated_at: string;
}

export function Categorias() {
  const [showForm, setShowForm] = useState(false);
  const [editando, setEditando] = useState<Categoria | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['categorias'],
    queryFn: async () => {
      const response = await api.get('/categorias/');
      return response.data;
    }
  });

  const criarMutation = useMutation({
    mutationFn: async (dados: any) => {
      return await api.post('/categorias/', dados);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categorias'] });
      setShowForm(false);
    }
  });

  const atualizarMutation = useMutation({
    mutationFn: async ({ id, dados }: { id: number; dados: any }) => {
      return await api.put(`/categorias/${id}`, dados);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categorias'] });
      setShowForm(false);
      setEditando(null);
    }
  });

  const deletarMutation = useMutation({
    mutationFn: async (id: number) => {
      return await api.delete(`/categorias/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categorias'] });
    }
  });

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const dados = {
      nome: formData.get('nome'),
      descricao: formData.get('descricao') || null,
      codigo: formData.get('codigo') || null,
    };

    if (editando) {
      atualizarMutation.mutate({ id: editando.id, dados });
    } else {
      criarMutation.mutate(dados);
    }
  };

  if (isLoading) return <div>Carregando...</div>;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Categorias</h1>
        <Button onClick={() => { setShowForm(true); setEditando(null); }}>
          Nova Categoria
        </Button>
      </div>

      {showForm && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>{editando ? 'Editar' : 'Nova'} Categoria</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Nome *</label>
                <input
                  name="nome"
                  defaultValue={editando?.nome}
                  required
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Código</label>
                <input
                  name="codigo"
                  defaultValue={editando?.codigo || ''}
                  className="w-full border rounded px-3 py-2"
                />
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
        {data?.items?.map((categoria: Categoria) => (
          <Card key={categoria.id}>
            <CardContent className="p-4">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold">{categoria.nome}</h3>
                  {categoria.codigo && <p className="text-sm text-gray-500">Código: {categoria.codigo}</p>}
                  {categoria.descricao && <p className="text-sm mt-2">{categoria.descricao}</p>}
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => { setEditando(categoria); setShowForm(true); }}
                  >
                    Editar
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => {
                      if (confirm('Deseja excluir esta categoria?')) {
                        deletarMutation.mutate(categoria.id);
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
    </div>
  );
}
