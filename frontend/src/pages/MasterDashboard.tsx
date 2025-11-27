import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import { Modal } from '@/components/Modal';
import { TenantListItem, CreateTenantRequest } from '@/types';
import {
  BuildingOfficeIcon,
  UserGroupIcon,
  PlusIcon,
  CheckCircleIcon,
  XCircleIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

interface MasterStats {
  total_tenants: number;
  tenants_ativos: number;
  total_usuarios: number;
  tenants_trial: number;
}

const PLANOS = [
  { value: 'trial', label: 'Trial (14 dias)', color: 'bg-gray-100 text-gray-800' },
  { value: 'basic', label: 'Basic', color: 'bg-blue-100 text-blue-800' },
  { value: 'pro', label: 'Pro', color: 'bg-purple-100 text-purple-800' },
  { value: 'enterprise', label: 'Enterprise', color: 'bg-orange-100 text-orange-800' },
];

export default function MasterDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [showCriarTenant, setShowCriarTenant] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [formData, setFormData] = useState<CreateTenantRequest>({
    nome_empresa: '',
    razao_social: '',
    cnpj: '',
    email_contato: '',
    telefone: '',
    plano: 'trial',
    admin_nome: '',
    admin_email: '',
    admin_senha: '',
  });
  const [formError, setFormError] = useState('');

  // Query para buscar estatisticas do MASTER
  const { data: stats } = useQuery<MasterStats>({
    queryKey: ['master-stats'],
    queryFn: async () => (await api.get('/tenants/master/stats')).data,
  });

  // Query para buscar lista de tenants
  const { data: tenants, isLoading: loadingTenants, refetch: refetchTenants } = useQuery<TenantListItem[]>({
    queryKey: ['master-tenants'],
    queryFn: async () => (await api.get('/tenants/master/list')).data,
  });

  // Mutation para criar novo tenant
  const createTenantMutation = useMutation({
    mutationFn: async (data: CreateTenantRequest) => {
      const response = await api.post('/tenants/master/create', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['master-tenants'] });
      queryClient.invalidateQueries({ queryKey: ['master-stats'] });
      setShowCriarTenant(false);
      resetForm();
    },
    onError: (error: any) => {
      setFormError(error.response?.data?.detail || 'Erro ao criar empresa');
    },
  });

  // Mutation para ativar/desativar tenant
  const toggleTenantMutation = useMutation({
    mutationFn: async ({ tenantId, ativo }: { tenantId: number; ativo: boolean }) => {
      const response = await api.patch(`/tenants/master/${tenantId}/toggle`, { ativo });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['master-tenants'] });
      queryClient.invalidateQueries({ queryKey: ['master-stats'] });
    },
  });

  const resetForm = () => {
    setFormData({
      nome_empresa: '',
      razao_social: '',
      cnpj: '',
      email_contato: '',
      telefone: '',
      plano: 'trial',
      admin_nome: '',
      admin_email: '',
      admin_senha: '',
    });
    setFormError('');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');

    // Validacoes basicas
    if (formData.admin_senha.length < 8) {
      setFormError('Senha deve ter pelo menos 8 caracteres');
      return;
    }
    if (!formData.cnpj || formData.cnpj.replace(/\D/g, '').length !== 14) {
      setFormError('CNPJ deve ter 14 digitos');
      return;
    }

    createTenantMutation.mutate(formData);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const formatCNPJ = (cnpj: string) => {
    const digits = cnpj.replace(/\D/g, '');
    if (digits.length <= 14) {
      return digits
        .replace(/(\d{2})(\d)/, '$1.$2')
        .replace(/(\d{3})(\d)/, '$1.$2')
        .replace(/(\d{3})(\d)/, '$1/$2')
        .replace(/(\d{4})(\d)/, '$1-$2');
    }
    return cnpj;
  };

  const filteredTenants = tenants?.filter(t =>
    t.nome_empresa.toLowerCase().includes(searchTerm.toLowerCase()) ||
    t.cnpj.includes(searchTerm.replace(/\D/g, '')) ||
    t.email_contato.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  const getPlanoStyle = (plano: string) => {
    const found = PLANOS.find(p => p.value === plano);
    return found?.color || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg">
        <div className="container mx-auto px-4 py-6 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold">Painel Master</h1>
            <p className="text-indigo-200">Administracao do Sistema Multi-Tenant</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="font-medium">{user?.nome_completo}</p>
              <p className="text-sm text-indigo-200">Administrador Master</p>
            </div>
            <Button onClick={handleLogout} variant="outline" className="text-white border-white hover:bg-white/20">
              Sair
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* Cards de Estatisticas */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-white">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-500">Total de Empresas</p>
                  <p className="text-3xl font-bold text-indigo-600">{stats?.total_tenants || 0}</p>
                </div>
                <div className="h-12 w-12 bg-indigo-100 rounded-full flex items-center justify-center">
                  <BuildingOfficeIcon className="h-6 w-6 text-indigo-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-500">Empresas Ativas</p>
                  <p className="text-3xl font-bold text-green-600">{stats?.tenants_ativos || 0}</p>
                </div>
                <div className="h-12 w-12 bg-green-100 rounded-full flex items-center justify-center">
                  <CheckCircleIcon className="h-6 w-6 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-500">Total de Usuarios</p>
                  <p className="text-3xl font-bold text-blue-600">{stats?.total_usuarios || 0}</p>
                </div>
                <div className="h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center">
                  <UserGroupIcon className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-500">Em Trial</p>
                  <p className="text-3xl font-bold text-orange-600">{stats?.tenants_trial || 0}</p>
                </div>
                <div className="h-12 w-12 bg-orange-100 rounded-full flex items-center justify-center">
                  <BuildingOfficeIcon className="h-6 w-6 text-orange-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Lista de Tenants */}
        <Card className="bg-white">
          <CardHeader className="pb-4">
            <div className="flex justify-between items-center">
              <CardTitle className="text-lg">Empresas Cadastradas</CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => refetchTenants()}>
                  <ArrowPathIcon className={`h-4 w-4 mr-1 ${loadingTenants ? 'animate-spin' : ''}`} />
                  Atualizar
                </Button>
                <Button size="sm" onClick={() => setShowCriarTenant(true)}>
                  <PlusIcon className="h-4 w-4 mr-1" />
                  Nova Empresa
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* Busca */}
            <div className="mb-4">
              <div className="relative">
                <MagnifyingGlassIcon className="h-5 w-5 absolute left-3 top-2.5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Buscar por nome, CNPJ ou email..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>

            {/* Tabela */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">Empresa</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">CNPJ</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">Email</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">Plano</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">Usuarios</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">Status</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">Acoes</th>
                  </tr>
                </thead>
                <tbody>
                  {loadingTenants ? (
                    <tr>
                      <td colSpan={7} className="text-center py-8 text-gray-500">
                        Carregando...
                      </td>
                    </tr>
                  ) : filteredTenants.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="text-center py-8 text-gray-500">
                        {searchTerm ? 'Nenhuma empresa encontrada' : 'Nenhuma empresa cadastrada'}
                      </td>
                    </tr>
                  ) : (
                    filteredTenants.map((tenant) => (
                      <tr key={tenant.id} className="border-b hover:bg-gray-50">
                        <td className="py-3 px-4">
                          <div>
                            <p className="font-medium text-gray-900">{tenant.nome_empresa}</p>
                            <p className="text-xs text-gray-500">{tenant.razao_social}</p>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-sm text-gray-600">
                          {formatCNPJ(tenant.cnpj)}
                        </td>
                        <td className="py-3 px-4 text-sm text-gray-600">
                          {tenant.email_contato}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPlanoStyle(tenant.plano)}`}>
                            {tenant.plano.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-sm text-gray-600">
                          {tenant.total_usuarios}
                        </td>
                        <td className="py-3 px-4">
                          {tenant.ativo ? (
                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              <CheckCircleIcon className="h-3 w-3" />
                              Ativo
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                              <XCircleIcon className="h-3 w-3" />
                              Inativo
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => toggleTenantMutation.mutate({
                              tenantId: tenant.id,
                              ativo: !tenant.ativo
                            })}
                            disabled={toggleTenantMutation.isPending}
                          >
                            {tenant.ativo ? 'Desativar' : 'Ativar'}
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </main>

      {/* Modal Criar Tenant */}
      <Modal
        isOpen={showCriarTenant}
        title="Nova Empresa"
        subtitle="Cadastre uma nova empresa e seu administrador"
        onClose={() => { setShowCriarTenant(false); resetForm(); }}
        size="lg"
        footer={
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => { setShowCriarTenant(false); resetForm(); }}>
              Cancelar
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createTenantMutation.isPending}
            >
              {createTenantMutation.isPending ? 'Criando...' : 'Criar Empresa'}
            </Button>
          </div>
        }
      >
        <form onSubmit={handleSubmit} className="space-y-6">
          {formError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {formError}
            </div>
          )}

          {/* Dados da Empresa */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <BuildingOfficeIcon className="h-4 w-4" />
              Dados da Empresa
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome Fantasia *
                </label>
                <input
                  type="text"
                  required
                  value={formData.nome_empresa}
                  onChange={(e) => setFormData({ ...formData, nome_empresa: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Ex: Empresa XYZ"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Razao Social *
                </label>
                <input
                  type="text"
                  required
                  value={formData.razao_social}
                  onChange={(e) => setFormData({ ...formData, razao_social: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Ex: Empresa XYZ Ltda"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  CNPJ *
                </label>
                <input
                  type="text"
                  required
                  value={formData.cnpj}
                  onChange={(e) => setFormData({ ...formData, cnpj: formatCNPJ(e.target.value) })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="00.000.000/0000-00"
                  maxLength={18}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Plano *
                </label>
                <select
                  required
                  value={formData.plano}
                  onChange={(e) => setFormData({ ...formData, plano: e.target.value as any })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  {PLANOS.map((plano) => (
                    <option key={plano.value} value={plano.value}>
                      {plano.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email de Contato *
                </label>
                <input
                  type="email"
                  required
                  value={formData.email_contato}
                  onChange={(e) => setFormData({ ...formData, email_contato: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="contato@empresa.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Telefone
                </label>
                <input
                  type="text"
                  value={formData.telefone}
                  onChange={(e) => setFormData({ ...formData, telefone: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="(00) 00000-0000"
                />
              </div>
            </div>
          </div>

          {/* Dados do Admin */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <UserGroupIcon className="h-4 w-4" />
              Administrador da Empresa
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome Completo *
                </label>
                <input
                  type="text"
                  required
                  value={formData.admin_nome}
                  onChange={(e) => setFormData({ ...formData, admin_nome: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Nome do administrador"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email do Admin *
                </label>
                <input
                  type="email"
                  required
                  value={formData.admin_email}
                  onChange={(e) => setFormData({ ...formData, admin_email: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="admin@empresa.com"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Senha do Admin *
                </label>
                <input
                  type="password"
                  required
                  value={formData.admin_senha}
                  onChange={(e) => setFormData({ ...formData, admin_senha: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Minimo 8 caracteres"
                  minLength={8}
                />
                <p className="text-xs text-gray-500 mt-1">
                  O administrador usara este email e senha para fazer login
                </p>
              </div>
            </div>
          </div>
        </form>
      </Modal>
    </div>
  );
}
