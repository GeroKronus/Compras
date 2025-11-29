import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import { Modal } from '@/components/Modal';
import {
  EnvelopeIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  CpuChipIcon,
  BellAlertIcon,
  ArrowRightIcon,
  XMarkIcon,
  SparklesIcon,
  TrophyIcon,
  ArrowPathIcon,
  HomeIcon,
  ShoppingCartIcon,
  FolderIcon,
  Cog6ToothIcon,
  DocumentTextIcon,
  CubeIcon,
  TruckIcon,
  TagIcon,
} from '@heroicons/react/24/outline';

interface Alerta {
  tipo: string;
  prioridade: 'alta' | 'media' | 'baixa';
  titulo: string;
  mensagem: string;
  link?: string;
  dados?: Record<string, any>;
  created_at: string;
}

interface SolicitacaoComRespostas {
  id: number;
  numero: string;
  titulo: string;
  status: string;
  total_fornecedores: number;
  propostas_recebidas: number;
  propostas_pendentes: number;
  melhor_proposta?: {
    fornecedor_id: number;
    fornecedor_nome: string;
    valor_total: number;
    prazo_entrega?: string;
    condicoes_pagamento?: string;
  };
  data_limite?: string;
  created_at: string;
}

interface DashboardStats {
  cotacoes_pendentes: number;
  cotacoes_em_andamento: number;
  cotacoes_finalizadas: number;
  emails_pendentes: number;
  emails_classificados: number;
  fornecedores_ativos: number;
  produtos_cadastrados: number;
  total_compras_mes: number;
}

interface AlertasResponse {
  alertas: Alerta[];
  solicitacoes_com_respostas: SolicitacaoComRespostas[];
  stats: DashboardStats;
}

type TabType = 'resumo' | 'compras' | 'cadastros' | 'config';

export default function Dashboard() {
  const { user, tenant, logout } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>('resumo');
  const [showTesteEmail, setShowTesteEmail] = useState(false);
  const [emailTeste, setEmailTeste] = useState('');
  const [testeResult, setTesteResult] = useState<{ sucesso: boolean; mensagem: string } | null>(null);
  const [alertasDismissed, setAlertasDismissed] = useState<string[]>([]);

  // Query para buscar alertas do dashboard
  const { data: dashboardData, isLoading: loadingAlertas, refetch: refetchAlertas } = useQuery<AlertasResponse>({
    queryKey: ['dashboard-alertas'],
    queryFn: async () => (await api.get('/dashboard/alertas')).data,
    refetchInterval: 30000,
  });

  const alertas = dashboardData?.alertas?.filter(a => !alertasDismissed.includes(a.tipo + a.titulo)) || [];
  const solicitacoesComRespostas = dashboardData?.solicitacoes_com_respostas || [];
  const stats = dashboardData?.stats;

  const dismissAlerta = (alerta: Alerta) => {
    setAlertasDismissed(prev => [...prev, alerta.tipo + alerta.titulo]);
  };

  const getPrioridadeColor = (prioridade: string) => {
    switch (prioridade) {
      case 'alta': return 'border-red-500 bg-red-50';
      case 'media': return 'border-yellow-500 bg-yellow-50';
      default: return 'border-blue-500 bg-blue-50';
    }
  };

  const getPrioridadeBadge = (prioridade: string) => {
    switch (prioridade) {
      case 'alta': return 'bg-red-100 text-red-800';
      case 'media': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-blue-100 text-blue-800';
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const testeEmailMutation = useMutation({
    mutationFn: async (email: string) => {
      const response = await api.post(`/cotacoes/teste-email?email_destino=${encodeURIComponent(email)}`);
      return response.data;
    },
    onSuccess: (data) => {
      setTesteResult({ sucesso: true, mensagem: data.mensagem });
    },
    onError: (error: any) => {
      setTesteResult({
        sucesso: false,
        mensagem: error.response?.data?.detail || 'Erro ao enviar email de teste'
      });
    }
  });

  // Mutation para processar emails manualmente
  const processarEmailsMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(`/setup/processar-emails/3?dias_atras=30`);
      return response.data;
    },
    onSuccess: () => {
      refetchAlertas();
    }
  });

  const enviarTestEmail = () => {
    if (!emailTeste || !emailTeste.includes('@')) return;
    setTesteResult(null);
    testeEmailMutation.mutate(emailTeste);
  };

  const fecharTesteEmail = () => {
    setShowTesteEmail(false);
    setEmailTeste('');
    setTesteResult(null);
  };

  const tabs = [
    { id: 'resumo' as TabType, label: 'Resumo', icon: HomeIcon },
    { id: 'compras' as TabType, label: 'Compras', icon: ShoppingCartIcon },
    { id: 'cadastros' as TabType, label: 'Cadastros', icon: FolderIcon },
    { id: 'config' as TabType, label: 'Configuracoes', icon: Cog6ToothIcon },
  ];

  const totalAlertas = alertas.length + solicitacoesComRespostas.length;

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Sistema de Compras</h1>
            <p className="text-sm text-gray-500">{tenant?.nome_empresa}</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="font-medium text-gray-900">{user?.nome_completo}</p>
              <p className="text-sm text-gray-500 capitalize">{user?.tipo}</p>
            </div>
            <Button onClick={handleLogout} variant="outline" size="sm">
              Sair
            </Button>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="container mx-auto px-4">
          <nav className="flex space-x-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                    isActive
                      ? 'border-blue-600 text-blue-600 bg-blue-50'
                      : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  {tab.label}
                  {tab.id === 'resumo' && totalAlertas > 0 && (
                    <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full min-w-[20px] text-center">
                      {totalAlertas}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Content */}
      <main className="container mx-auto px-4 py-6">
        {/* Tab: Resumo */}
        {activeTab === 'resumo' && (
          <div className="space-y-6">
            {/* Cards de Estatisticas */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card className="cursor-pointer hover:shadow-md transition-shadow bg-white" onClick={() => navigate('/cotacoes')}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-500">Cotacoes em Andamento</p>
                      <p className="text-3xl font-bold text-orange-600">{stats?.cotacoes_em_andamento || 0}</p>
                      <p className="text-xs text-gray-400 mt-1">{stats?.cotacoes_pendentes || 0} rascunhos</p>
                    </div>
                    <div className="h-12 w-12 bg-orange-100 rounded-full flex items-center justify-center">
                      <DocumentTextIcon className="h-6 w-6 text-orange-600" />
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="cursor-pointer hover:shadow-md transition-shadow bg-white" onClick={() => navigate('/emails')}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-500">Emails Pendentes</p>
                      <p className={`text-3xl font-bold ${(stats?.emails_pendentes || 0) > 0 ? 'text-yellow-600' : 'text-green-600'}`}>
                        {stats?.emails_pendentes || 0}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">{stats?.emails_classificados || 0} classificados</p>
                    </div>
                    <div className={`h-12 w-12 rounded-full flex items-center justify-center ${(stats?.emails_pendentes || 0) > 0 ? 'bg-yellow-100' : 'bg-green-100'}`}>
                      <EnvelopeIcon className={`h-6 w-6 ${(stats?.emails_pendentes || 0) > 0 ? 'text-yellow-600' : 'text-green-600'}`} />
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="cursor-pointer hover:shadow-md transition-shadow bg-white" onClick={() => navigate('/produtos')}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-500">Produtos</p>
                      <p className="text-3xl font-bold text-blue-600">{stats?.produtos_cadastrados || 0}</p>
                      <p className="text-xs text-gray-400 mt-1">Cadastrados</p>
                    </div>
                    <div className="h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center">
                      <CubeIcon className="h-6 w-6 text-blue-600" />
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="cursor-pointer hover:shadow-md transition-shadow bg-white" onClick={() => navigate('/fornecedores')}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-500">Fornecedores</p>
                      <p className="text-3xl font-bold text-purple-600">{stats?.fornecedores_ativos || 0}</p>
                      <p className="text-xs text-gray-400 mt-1">Ativos</p>
                    </div>
                    <div className="h-12 w-12 bg-purple-100 rounded-full flex items-center justify-center">
                      <TruckIcon className="h-6 w-6 text-purple-600" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Secao de Alertas */}
            {(alertas.length > 0 || solicitacoesComRespostas.length > 0) && (
              <Card className="bg-white">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <BellAlertIcon className="h-5 w-5 text-orange-500" />
                      <CardTitle className="text-lg">Notificacoes</CardTitle>
                      {alertas.length > 0 && (
                        <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                          {alertas.length}
                        </span>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => processarEmailsMutation.mutate()}
                        disabled={processarEmailsMutation.isPending}
                        className="bg-blue-50 hover:bg-blue-100 text-blue-700 border-blue-300"
                      >
                        <EnvelopeIcon className={`h-4 w-4 mr-1 ${processarEmailsMutation.isPending ? 'animate-pulse' : ''}`} />
                        {processarEmailsMutation.isPending ? 'Processando...' : 'Processar Emails'}
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => refetchAlertas()}>
                        <ArrowPathIcon className={`h-4 w-4 mr-1 ${loadingAlertas ? 'animate-spin' : ''}`} />
                        Atualizar
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Lista de Alertas */}
                  {alertas.length > 0 && (
                    <div className="space-y-2">
                      {alertas.map((alerta, index) => (
                        <div
                          key={index}
                          className={`border-l-4 rounded-lg p-3 cursor-pointer hover:shadow-sm transition-shadow ${getPrioridadeColor(alerta.prioridade)}`}
                          onClick={() => alerta.link && navigate(alerta.link)}
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getPrioridadeBadge(alerta.prioridade)}`}>
                                  {alerta.prioridade.toUpperCase()}
                                </span>
                                <h4 className="font-medium text-gray-900 text-sm">{alerta.titulo}</h4>
                              </div>
                              <p className="text-sm text-gray-600">{alerta.mensagem}</p>
                            </div>
                            <button
                              onClick={(e) => { e.stopPropagation(); dismissAlerta(alerta); }}
                              className="text-gray-400 hover:text-gray-600 p-1"
                            >
                              <XMarkIcon className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Cotacoes com Propostas */}
                  {solicitacoesComRespostas.length > 0 && (
                    <div className="pt-2">
                      <h4 className="text-sm font-semibold mb-3 flex items-center gap-2 text-gray-700">
                        <SparklesIcon className="h-4 w-4 text-purple-500" />
                        Cotacoes com Propostas Recebidas
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {solicitacoesComRespostas.map((sol) => (
                          <div key={sol.id} className="border rounded-lg p-3 hover:shadow-sm transition-shadow bg-gray-50">
                            <div className="flex justify-between items-start mb-2">
                              <div>
                                <p className="text-xs font-bold text-green-600">{sol.numero}</p>
                                <p className="font-medium text-sm text-gray-900">{sol.titulo}</p>
                              </div>
                              {sol.propostas_pendentes === 0 && (
                                <span className="bg-green-100 text-green-700 text-xs px-1.5 py-0.5 rounded flex items-center gap-1">
                                  <CheckCircleIcon className="h-3 w-3" />
                                  Completa
                                </span>
                              )}
                            </div>

                            <div className="mb-2">
                              <div className="flex justify-between text-xs mb-1">
                                <span className="text-gray-500">Propostas</span>
                                <span className="font-medium">{sol.propostas_recebidas}/{sol.total_fornecedores}</span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-1.5">
                                <div
                                  className="bg-green-500 h-1.5 rounded-full"
                                  style={{ width: `${(sol.propostas_recebidas / sol.total_fornecedores) * 100}%` }}
                                />
                              </div>
                            </div>

                            {sol.melhor_proposta && (
                              <div className="bg-green-50 rounded p-2 mb-2 border border-green-100">
                                <div className="flex items-center gap-1 text-green-700 text-xs font-medium">
                                  <TrophyIcon className="h-3 w-3" />
                                  Melhor: {formatCurrency(sol.melhor_proposta.valor_total)}
                                </div>
                                <p className="text-xs text-gray-600">{sol.melhor_proposta.fornecedor_nome}</p>
                              </div>
                            )}

                            <div className="flex gap-2">
                              <Button size="sm" variant="outline" className="flex-1 text-xs h-7" onClick={() => navigate(`/cotacoes/${sol.id}/propostas`)}>
                                Propostas
                              </Button>
                              <Button size="sm" className="flex-1 text-xs h-7 bg-green-600 hover:bg-green-700" onClick={() => navigate(`/cotacoes/${sol.id}/mapa`)}>
                                Comparar
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Info da Empresa */}
            <Card className="bg-white">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Informacoes da Empresa</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">Plano</p>
                    <p className="font-medium capitalize">{tenant?.plano}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">IA Habilitada</p>
                    <p className="font-medium">{tenant?.ia_habilitada ? 'Sim' : 'Nao'}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">CNPJ</p>
                    <p className="font-medium">{tenant?.cnpj}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Email</p>
                    <p className="font-medium">{tenant?.email_contato}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Tab: Compras */}
        {activeTab === 'compras' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <Card className="cursor-pointer hover:shadow-lg transition-all bg-white border-l-4 border-l-blue-500" onClick={() => navigate('/cotacoes')}>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <div className="h-14 w-14 bg-blue-100 rounded-lg flex items-center justify-center">
                      <DocumentTextIcon className="h-7 w-7 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">Solicitacoes de Cotacao</h3>
                      <p className="text-sm text-gray-500">Criar e gerenciar cotacoes</p>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t flex justify-between items-center">
                    <span className="text-2xl font-bold text-blue-600">{stats?.cotacoes_em_andamento || 0}</span>
                    <span className="text-xs text-gray-500">Em andamento</span>
                  </div>
                </CardContent>
              </Card>

              <Card className="cursor-pointer hover:shadow-lg transition-all bg-white border-l-4 border-l-purple-500" onClick={() => navigate('/emails')}>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <div className="h-14 w-14 bg-purple-100 rounded-lg flex items-center justify-center">
                      <EnvelopeIcon className="h-7 w-7 text-purple-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">Revisao de Emails</h3>
                      <p className="text-sm text-gray-500">Classificar propostas recebidas</p>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t flex justify-between items-center">
                    <span className={`text-2xl font-bold ${(stats?.emails_pendentes || 0) > 0 ? 'text-yellow-600' : 'text-green-600'}`}>
                      {stats?.emails_pendentes || 0}
                    </span>
                    <span className="text-xs text-gray-500">Pendentes</span>
                  </div>
                </CardContent>
              </Card>

              <Card className="cursor-pointer hover:shadow-lg transition-all bg-white border-l-4 border-l-green-500" onClick={() => navigate('/pedidos')}>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <div className="h-14 w-14 bg-green-100 rounded-lg flex items-center justify-center">
                      <ShoppingCartIcon className="h-7 w-7 text-green-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">Pedidos de Compra</h3>
                      <p className="text-sm text-gray-500">Gerenciar pedidos</p>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t flex justify-between items-center">
                    <ArrowRightIcon className="h-5 w-5 text-gray-400" />
                    <span className="text-xs text-gray-500">Acessar</span>
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card className="bg-white">
              <CardHeader>
                <CardTitle className="text-lg">Acoes Rapidas</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <Button variant="outline" className="h-16 flex flex-col gap-1" onClick={() => navigate('/cotacoes')}>
                    <DocumentTextIcon className="h-5 w-5" />
                    <span className="text-xs">Nova Cotacao</span>
                  </Button>
                  <Button variant="outline" className="h-16 flex flex-col gap-1" onClick={() => navigate('/emails')}>
                    <EnvelopeIcon className="h-5 w-5" />
                    <span className="text-xs">Ver Emails</span>
                  </Button>
                  <Button variant="outline" className="h-16 flex flex-col gap-1" onClick={() => navigate('/pedidos')}>
                    <ShoppingCartIcon className="h-5 w-5" />
                    <span className="text-xs">Ver Pedidos</span>
                  </Button>
                  <Button variant="outline" className="h-16 flex flex-col gap-1" disabled>
                    <DocumentTextIcon className="h-5 w-5" />
                    <span className="text-xs">Relatorios</span>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Tab: Cadastros */}
        {activeTab === 'cadastros' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="cursor-pointer hover:shadow-lg transition-all bg-white border-l-4 border-l-blue-500" onClick={() => navigate('/categorias')}>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <div className="h-14 w-14 bg-blue-100 rounded-lg flex items-center justify-center">
                      <TagIcon className="h-7 w-7 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">Categorias</h3>
                      <p className="text-sm text-gray-500">Organizar produtos</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="cursor-pointer hover:shadow-lg transition-all bg-white border-l-4 border-l-green-500" onClick={() => navigate('/produtos')}>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <div className="h-14 w-14 bg-green-100 rounded-lg flex items-center justify-center">
                      <CubeIcon className="h-7 w-7 text-green-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">Produtos</h3>
                      <p className="text-sm text-gray-500">{stats?.produtos_cadastrados || 0} cadastrados</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="cursor-pointer hover:shadow-lg transition-all bg-white border-l-4 border-l-purple-500" onClick={() => navigate('/fornecedores')}>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <div className="h-14 w-14 bg-purple-100 rounded-lg flex items-center justify-center">
                      <TruckIcon className="h-7 w-7 text-purple-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">Fornecedores</h3>
                      <p className="text-sm text-gray-500">{stats?.fornecedores_ativos || 0} ativos</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {/* Tab: Configuracoes */}
        {activeTab === 'config' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <Card className="cursor-pointer hover:shadow-lg transition-all bg-white" onClick={() => setShowTesteEmail(true)}>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <div className="h-14 w-14 bg-blue-100 rounded-lg flex items-center justify-center">
                      <EnvelopeIcon className="h-7 w-7 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">Testar Email</h3>
                      <p className="text-sm text-gray-500">Verificar configuracao SMTP</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="cursor-pointer hover:shadow-lg transition-all bg-white" onClick={() => navigate('/ia-creditos')}>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <div className="h-14 w-14 bg-purple-100 rounded-lg flex items-center justify-center">
                      <CpuChipIcon className="h-7 w-7 text-purple-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">Creditos de IA</h3>
                      <p className="text-sm text-gray-500">Gerenciar uso da IA</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-white opacity-60">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <div className="h-14 w-14 bg-gray-100 rounded-lg flex items-center justify-center">
                      <Cog6ToothIcon className="h-7 w-7 text-gray-400" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-500">Mais opcoes</h3>
                      <p className="text-sm text-gray-400">Em breve</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card className="bg-white">
              <CardHeader>
                <CardTitle className="text-lg">Dados da Empresa</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <p className="text-sm text-gray-500">Razao Social</p>
                      <p className="font-medium">{tenant?.nome_empresa}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">CNPJ</p>
                      <p className="font-medium">{tenant?.cnpj}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Email de Contato</p>
                      <p className="font-medium">{tenant?.email_contato}</p>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <p className="text-sm text-gray-500">Plano Atual</p>
                      <p className="font-medium capitalize">{tenant?.plano}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">IA Habilitada</p>
                      <p className="font-medium">{tenant?.ia_habilitada ? 'Sim' : 'Nao'}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Auto-aprovacao IA</p>
                      <p className="font-medium">{tenant?.ia_auto_aprovacao ? 'Ativa' : 'Inativa'}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </main>

      {/* Modal Teste de Email */}
      <Modal
        isOpen={showTesteEmail}
        title="Testar Servico de Email"
        subtitle="Verifique se o envio de emails esta funcionando"
        onClose={fecharTesteEmail}
        size="md"
        footer={
          testeResult ? (
            <button
              onClick={fecharTesteEmail}
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
            >
              Fechar
            </button>
          ) : (
            <div className="flex gap-3">
              <button
                onClick={fecharTesteEmail}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={enviarTestEmail}
                disabled={testeEmailMutation.isPending || !emailTeste.includes('@')}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                <EnvelopeIcon className="h-5 w-5" />
                {testeEmailMutation.isPending ? 'Enviando...' : 'Enviar Teste'}
              </button>
            </div>
          )
        }
      >
        {testeResult ? (
          <div className="space-y-4">
            {testeResult.sucesso ? (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center gap-2 text-green-800 mb-2">
                  <CheckCircleIcon className="h-6 w-6" />
                  <span className="font-semibold">Email Enviado!</span>
                </div>
                <p className="text-green-700">{testeResult.mensagem}</p>
              </div>
            ) : (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-center gap-2 text-red-800 mb-2">
                  <ExclamationCircleIcon className="h-6 w-6" />
                  <span className="font-semibold">Falha no Envio</span>
                </div>
                <p className="text-red-700">{testeResult.mensagem}</p>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-blue-800 text-sm">
                <strong>Teste de conectividade:</strong> Um email de teste sera enviado para
                verificar se as configuracoes SMTP estao corretas.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email de Destino *
              </label>
              <input
                type="email"
                value={emailTeste}
                onChange={(e) => setEmailTeste(e.target.value)}
                placeholder="seu-email@exemplo.com"
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
