import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { api } from '@/services/api';
import {
  Users,
  UserPlus,
  Search,
  Building2,
  Shield,
  ShoppingCart,
  Package,
  Eye,
  ToggleLeft,
  ToggleRight,
  Key,
  FileText,
  Settings,
  MessageSquare,
  Phone,
  Save,
  CheckCircle,
  XCircle,
} from 'lucide-react';

interface Usuario {
  id: number;
  nome_completo: string;
  email: string;
  tipo: string;
  ativo: boolean;
  telefone?: string;
  setor?: string;
  created_at: string;
}

interface UsuarioListResponse {
  items: Usuario[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

const TIPO_LABELS: Record<string, string> = {
  MASTER: 'Master',
  ADMIN: 'Administrador',
  GERENTE: 'Gerente',
  COMPRADOR: 'Comprador',
  ALMOXARIFE: 'Almoxarife',
  VISUALIZADOR: 'Visualizador',
};

const TIPO_ICONS: Record<string, typeof Users> = {
  MASTER: Shield,
  ADMIN: Shield,
  GERENTE: Building2,
  COMPRADOR: ShoppingCart,
  ALMOXARIFE: Package,
  VISUALIZADOR: Eye,
};

type TabType = 'usuarios' | 'configuracoes' | 'auditoria';

interface TenantConfig {
  whatsapp_enabled: boolean;
  twilio_account_sid: string;
  twilio_auth_token: string;
  twilio_whatsapp_from: string;
  telegram_enabled: boolean;
  telegram_bot_token: string;
  telegram_chat_id: string;
}

export default function AdminDashboard() {
  const { user, tenant, logout } = useAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabType>('usuarios');
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showResetPasswordModal, setShowResetPasswordModal] = useState<Usuario | null>(null);
  const [newUser, setNewUser] = useState({
    nome_completo: '',
    email: '',
    senha: '',
    tipo: 'COMPRADOR',
    telefone: '',
    setor: '',
  });
  const [newPassword, setNewPassword] = useState('');
  const [configSaved, setConfigSaved] = useState(false);
  const [tenantConfig, setTenantConfig] = useState<TenantConfig>({
    whatsapp_enabled: false,
    twilio_account_sid: '',
    twilio_auth_token: '',
    twilio_whatsapp_from: '',
    telegram_enabled: false,
    telegram_bot_token: '',
    telegram_chat_id: '',
  });

  // Carregar configurações do tenant
  const { data: tenantData, refetch: refetchTenant } = useQuery({
    queryKey: ['tenant-config'],
    queryFn: async () => {
      const response = await api.get('/tenants/me');
      return response.data;
    },
    enabled: activeTab === 'configuracoes',
  });

  // Atualizar state quando dados do tenant carregarem
  useEffect(() => {
    if (tenantData) {
      setTenantConfig(prev => ({
        ...prev,
        whatsapp_enabled: tenantData.whatsapp_enabled || false,
        twilio_whatsapp_from: tenantData.twilio_whatsapp_from || '',
        telegram_enabled: tenantData.telegram_enabled || false,
        telegram_chat_id: tenantData.telegram_chat_id || '',
      }));
    }
  }, [tenantData]);

  // Salvar configurações
  const saveConfigMutation = useMutation({
    mutationFn: async (config: Partial<TenantConfig>) => {
      // Remover campos vazios para não sobrescrever
      const dataToSend: Record<string, any> = {};
      if (config.whatsapp_enabled !== undefined) dataToSend.whatsapp_enabled = config.whatsapp_enabled;
      if (config.twilio_account_sid) dataToSend.twilio_account_sid = config.twilio_account_sid;
      if (config.twilio_auth_token) dataToSend.twilio_auth_token = config.twilio_auth_token;
      if (config.twilio_whatsapp_from) dataToSend.twilio_whatsapp_from = config.twilio_whatsapp_from;
      if (config.telegram_enabled !== undefined) dataToSend.telegram_enabled = config.telegram_enabled;
      if (config.telegram_bot_token) dataToSend.telegram_bot_token = config.telegram_bot_token;
      if (config.telegram_chat_id) dataToSend.telegram_chat_id = config.telegram_chat_id;

      const response = await api.patch('/tenants/me', dataToSend);
      return response.data;
    },
    onSuccess: () => {
      setConfigSaved(true);
      refetchTenant();
      setTimeout(() => setConfigSaved(false), 3000);
    },
  });

  // Buscar usuarios
  const { data: usuariosData, isLoading } = useQuery<UsuarioListResponse>({
    queryKey: ['usuarios', searchTerm],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      const response = await api.get(`/usuarios?${params.toString()}`);
      return response.data;
    },
  });

  // Criar usuario
  const createMutation = useMutation({
    mutationFn: async (data: typeof newUser) => {
      const response = await api.post('/usuarios', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['usuarios'] });
      setShowCreateModal(false);
      setNewUser({
        nome_completo: '',
        email: '',
        senha: '',
        tipo: 'COMPRADOR',
        telefone: '',
        setor: '',
      });
    },
  });

  // Toggle ativo
  const toggleMutation = useMutation({
    mutationFn: async ({ id, ativo }: { id: number; ativo: boolean }) => {
      const endpoint = ativo ? `/usuarios/${id}/ativar` : `/usuarios/${id}/desativar`;
      const response = await api.post(endpoint);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['usuarios'] });
    },
  });

  // Resetar senha
  const resetPasswordMutation = useMutation({
    mutationFn: async ({ id, nova_senha }: { id: number; nova_senha: string }) => {
      const response = await api.post(`/usuarios/${id}/resetar-senha`, { nova_senha });
      return response.data;
    },
    onSuccess: () => {
      setShowResetPasswordModal(null);
      setNewPassword('');
    },
  });

  const handleCreateUser = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(newUser);
  };

  const handleResetPassword = (e: React.FormEvent) => {
    e.preventDefault();
    if (showResetPasswordModal) {
      resetPasswordMutation.mutate({ id: showResetPasswordModal.id, nova_senha: newPassword });
    }
  };

  const usuarios = usuariosData?.items || [];
  const totalUsuarios = usuariosData?.total || 0;
  const usuariosAtivos = usuarios.filter(u => u.ativo).length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Administracao da Empresa</h1>
            <p className="text-sm text-gray-500">{tenant?.nome_empresa}</p>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">{user?.nome_completo}</span>
            <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
              {user?.tipo}
            </span>
            <Button variant="outline" size="sm" onClick={logout}>
              Sair
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">
                Total de Usuarios
              </CardTitle>
              <Users className="h-5 w-5 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalUsuarios}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">
                Usuarios Ativos
              </CardTitle>
              <ToggleRight className="h-5 w-5 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{usuariosAtivos}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">
                Plano
              </CardTitle>
              <Building2 className="h-5 w-5 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold capitalize">{tenant?.plano}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">
                IA Habilitada
              </CardTitle>
              <Shield className="h-5 w-5 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {tenant?.ia_habilitada ? 'Sim' : 'Nao'}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Navigation Tabs */}
        <div className="flex gap-4 mb-6 border-b">
          <button
            className={`px-4 py-2 border-b-2 ${activeTab === 'usuarios' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'} font-medium`}
            onClick={() => setActiveTab('usuarios')}
          >
            <Users className="inline-block w-4 h-4 mr-2" />
            Usuarios
          </button>
          <button
            className={`px-4 py-2 border-b-2 ${activeTab === 'configuracoes' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'} font-medium`}
            onClick={() => setActiveTab('configuracoes')}
          >
            <Settings className="inline-block w-4 h-4 mr-2" />
            Configuracoes
          </button>
          <button
            className={`px-4 py-2 border-b-2 ${activeTab === 'auditoria' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'} font-medium`}
            onClick={() => setActiveTab('auditoria')}
          >
            <FileText className="inline-block w-4 h-4 mr-2" />
            Auditoria
          </button>
        </div>

        {/* Users Management */}
        {activeTab === 'usuarios' && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Usuarios da Empresa</CardTitle>
            <Button onClick={() => setShowCreateModal(true)}>
              <UserPlus className="w-4 h-4 mr-2" />
              Novo Usuario
            </Button>
          </CardHeader>
          <CardContent>
            {/* Search */}
            <div className="flex gap-4 mb-6">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <input
                  type="text"
                  placeholder="Buscar por nome ou email..."
                  className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>

            {/* Users Table */}
            {isLoading ? (
              <div className="text-center py-8">Carregando...</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      <th className="text-left py-3 px-4 font-medium text-gray-600">Nome</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-600">Email</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-600">Tipo</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-600">Setor</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-600">Status</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-600">Acoes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usuarios.map((usuario) => {
                      const IconComponent = TIPO_ICONS[usuario.tipo] || Users;
                      return (
                        <tr key={usuario.id} className="border-b hover:bg-gray-50">
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              <IconComponent className="w-4 h-4 text-gray-400" />
                              {usuario.nome_completo}
                            </div>
                          </td>
                          <td className="py-3 px-4 text-gray-600">{usuario.email}</td>
                          <td className="py-3 px-4">
                            <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                              {TIPO_LABELS[usuario.tipo] || usuario.tipo}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-gray-600">{usuario.setor || '-'}</td>
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-1 text-xs rounded-full ${
                                usuario.ativo
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-red-100 text-red-800'
                              }`}
                            >
                              {usuario.ativo ? 'Ativo' : 'Inativo'}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setShowResetPasswordModal(usuario)}
                                title="Resetar Senha"
                              >
                                <Key className="w-4 h-4" />
                              </Button>
                              {usuario.tipo !== 'ADMIN' && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() =>
                                    toggleMutation.mutate({
                                      id: usuario.id,
                                      ativo: !usuario.ativo,
                                    })
                                  }
                                  title={usuario.ativo ? 'Desativar' : 'Ativar'}
                                >
                                  {usuario.ativo ? (
                                    <ToggleRight className="w-4 h-4 text-green-600" />
                                  ) : (
                                    <ToggleLeft className="w-4 h-4 text-gray-400" />
                                  )}
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
        )}

        {/* Configuracoes */}
        {activeTab === 'configuracoes' && (
          <div className="space-y-6">
            {/* WhatsApp / Twilio */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-green-600" />
                  WhatsApp (Twilio)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <p className="font-medium">Envio por WhatsApp</p>
                    <p className="text-sm text-gray-500">Permite enviar cotacoes via WhatsApp</p>
                  </div>
                  <button
                    onClick={() => setTenantConfig(prev => ({ ...prev, whatsapp_enabled: !prev.whatsapp_enabled }))}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      tenantConfig.whatsapp_enabled ? 'bg-green-600' : 'bg-gray-300'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        tenantConfig.whatsapp_enabled ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Account SID</label>
                    <input
                      type="text"
                      placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                      className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                      value={tenantConfig.twilio_account_sid}
                      onChange={(e) => setTenantConfig(prev => ({ ...prev, twilio_account_sid: e.target.value }))}
                    />
                    <p className="text-xs text-gray-500 mt-1">Encontre em console.twilio.com</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Auth Token</label>
                    <input
                      type="password"
                      placeholder="••••••••••••••••"
                      className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                      value={tenantConfig.twilio_auth_token}
                      onChange={(e) => setTenantConfig(prev => ({ ...prev, twilio_auth_token: e.target.value }))}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Numero WhatsApp (From)</label>
                  <input
                    type="text"
                    placeholder="whatsapp:+5511999999999"
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    value={tenantConfig.twilio_whatsapp_from}
                    onChange={(e) => setTenantConfig(prev => ({ ...prev, twilio_whatsapp_from: e.target.value }))}
                  />
                  <p className="text-xs text-gray-500 mt-1">Formato: whatsapp:+5511999999999</p>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-blue-800">
                    <strong>Como configurar:</strong><br />
                    1. Crie uma conta em <a href="https://www.twilio.com" target="_blank" rel="noopener noreferrer" className="underline">twilio.com</a><br />
                    2. Ative o WhatsApp Sandbox ou solicite um numero<br />
                    3. Copie o Account SID e Auth Token do console<br />
                    4. Custo: ~R$0,03 por mensagem
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Telegram */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Phone className="w-5 h-5 text-blue-500" />
                  Telegram (Notificacoes)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <p className="font-medium">Notificacoes Telegram</p>
                    <p className="text-sm text-gray-500">Receba alertas de novas propostas</p>
                  </div>
                  <button
                    onClick={() => setTenantConfig(prev => ({ ...prev, telegram_enabled: !prev.telegram_enabled }))}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      tenantConfig.telegram_enabled ? 'bg-blue-600' : 'bg-gray-300'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        tenantConfig.telegram_enabled ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Bot Token</label>
                    <input
                      type="password"
                      placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
                      className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      value={tenantConfig.telegram_bot_token}
                      onChange={(e) => setTenantConfig(prev => ({ ...prev, telegram_bot_token: e.target.value }))}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Chat ID</label>
                    <input
                      type="text"
                      placeholder="-1001234567890"
                      className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      value={tenantConfig.telegram_chat_id}
                      onChange={(e) => setTenantConfig(prev => ({ ...prev, telegram_chat_id: e.target.value }))}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Botao Salvar */}
            <div className="flex justify-end gap-4">
              {configSaved && (
                <div className="flex items-center gap-2 text-green-600">
                  <CheckCircle className="w-5 h-5" />
                  Configuracoes salvas!
                </div>
              )}
              <Button
                onClick={() => saveConfigMutation.mutate(tenantConfig)}
                disabled={saveConfigMutation.isPending}
                className="bg-green-600 hover:bg-green-700"
              >
                <Save className="w-4 h-4 mr-2" />
                {saveConfigMutation.isPending ? 'Salvando...' : 'Salvar Configuracoes'}
              </Button>
            </div>

            {saveConfigMutation.isError && (
              <div className="flex items-center gap-2 text-red-600 bg-red-50 p-4 rounded-lg">
                <XCircle className="w-5 h-5" />
                Erro ao salvar: {(saveConfigMutation.error as any)?.response?.data?.detail || 'Erro desconhecido'}
              </div>
            )}
          </div>
        )}

        {/* Auditoria */}
        {activeTab === 'auditoria' && (
          <Card>
            <CardContent className="py-8 text-center text-gray-500">
              <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>Logs de auditoria em breve...</p>
            </CardContent>
          </Card>
        )}
      </main>

      {/* Create User Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Novo Usuario</h2>
            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Nome Completo</label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={newUser.nome_completo}
                  onChange={(e) => setNewUser({ ...newUser, nome_completo: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Email</label>
                <input
                  type="email"
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Senha</label>
                <input
                  type="password"
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={newUser.senha}
                  onChange={(e) => setNewUser({ ...newUser, senha: e.target.value })}
                  required
                  minLength={8}
                />
                <p className="text-xs text-gray-500 mt-1">Minimo 8 caracteres</p>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Tipo</label>
                <select
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={newUser.tipo}
                  onChange={(e) => setNewUser({ ...newUser, tipo: e.target.value })}
                >
                  <option value="COMPRADOR">Comprador</option>
                  <option value="GERENTE">Gerente</option>
                  <option value="ALMOXARIFE">Almoxarife</option>
                  <option value="VISUALIZADOR">Visualizador</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Setor (opcional)</label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={newUser.setor}
                  onChange={(e) => setNewUser({ ...newUser, setor: e.target.value })}
                />
              </div>
              <div className="flex gap-2 justify-end">
                <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Criando...' : 'Criar Usuario'}
                </Button>
              </div>
              {createMutation.isError && (
                <p className="text-red-500 text-sm">
                  {(createMutation.error as any)?.response?.data?.detail || 'Erro ao criar usuario'}
                </p>
              )}
            </form>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {showResetPasswordModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Resetar Senha</h2>
            <p className="text-gray-600 mb-4">
              Usuario: <strong>{showResetPasswordModal.nome_completo}</strong>
            </p>
            <form onSubmit={handleResetPassword} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Nova Senha</label>
                <input
                  type="password"
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                />
                <p className="text-xs text-gray-500 mt-1">Minimo 8 caracteres</p>
              </div>
              <div className="flex gap-2 justify-end">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setShowResetPasswordModal(null);
                    setNewPassword('');
                  }}
                >
                  Cancelar
                </Button>
                <Button type="submit" disabled={resetPasswordMutation.isPending}>
                  {resetPasswordMutation.isPending ? 'Resetando...' : 'Resetar Senha'}
                </Button>
              </div>
              {resetPasswordMutation.isError && (
                <p className="text-red-500 text-sm">
                  {(resetPasswordMutation.error as any)?.response?.data?.detail ||
                    'Erro ao resetar senha'}
                </p>
              )}
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
