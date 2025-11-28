/**
 * Categorias - Página refatorada usando useCrudResource e FormField
 * Redução de ~60 linhas de código duplicado
 */
import { useState } from 'react';
import { useCrudResource } from '../hooks/useCrudResource';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { FormInput, FormTextarea, FormActions } from '../components/ui/form-field';

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

  // Hook genérico CRUD - elimina 40 linhas de código duplicado
  const { items, isLoading, create, update, remove } = useCrudResource<Categoria>({
    endpoint: '/categorias',
    queryKey: 'categorias',
    onCreateSuccess: () => setShowForm(false),
    onUpdateSuccess: () => { setShowForm(false); setEditando(null); },
  });

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const dados = {
      nome: formData.get('nome') as string,
      descricao: formData.get('descricao') as string || null,
      codigo: formData.get('codigo') as string || null,
    };

    if (editando) {
      update.mutate({ id: editando.id, data: dados });
    } else {
      create.mutate(dados);
    }
  };

  const handleDelete = (id: number) => {
    if (confirm('Deseja excluir esta categoria?')) {
      remove.mutate(id);
    }
  };

  if (isLoading) return <div className="p-6">Carregando...</div>;

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
              <FormInput
                name="nome"
                label="Nome"
                required
                defaultValue={editando?.nome}
              />
              <FormInput
                name="codigo"
                label="Codigo"
                defaultValue={editando?.codigo || ''}
              />
              <FormTextarea
                name="descricao"
                label="Descricao"
                rows={3}
                defaultValue={editando?.descricao || ''}
              />
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
        {items.map((categoria) => (
          <Card key={categoria.id}>
            <CardContent className="p-4">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold">{categoria.nome}</h3>
                  {categoria.codigo && <p className="text-sm text-gray-500">Codigo: {categoria.codigo}</p>}
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
                    disabled={remove.isPending}
                    onClick={() => handleDelete(categoria.id)}
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
