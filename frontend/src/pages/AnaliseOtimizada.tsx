import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { Button } from '../components/ui/button';
import { useAuth } from '../hooks/useAuth';
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  ShoppingCartIcon,
  ScaleIcon,
  CurrencyDollarIcon,
  TruckIcon,
  DocumentDuplicateIcon,
  LightBulbIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

interface PrecoFornecedor {
  fornecedor_id: number;
  fornecedor_nome: string;
  proposta_id: number;
  item_proposta_id: number;
  preco_unitario: number;
  desconto_percentual: number;
  preco_final: number;
  preco_total: number;
  prazo_entrega?: number;
  condicoes_pagamento?: string;
  marca_oferecida?: string;
  is_menor_preco: boolean;
  diferenca_percentual?: number;
}

interface ItemAnalise {
  item_solicitacao_id: number;
  produto_id: number;
  produto_nome: string;
  produto_codigo?: string;
  quantidade: number;
  unidade_medida: string;
  precos_fornecedores: PrecoFornecedor[];
  menor_preco_unitario?: number;
  menor_preco_total?: number;
  fornecedor_menor_preco_id?: number;
  fornecedor_menor_preco_nome?: string;
}

interface ResumoFornecedor {
  fornecedor_id: number;
  fornecedor_nome: string;
  proposta_id: number;
  valor_total: number;
  prazo_entrega?: number;
  condicoes_pagamento?: string;
  qtd_itens_cotados: number;
  qtd_itens_menor_preco: number;
}

interface ItemOtimizado {
  item_solicitacao_id: number;
  produto_id: number;
  produto_nome: string;
  quantidade: number;
  fornecedor_id: number;
  fornecedor_nome: string;
  proposta_id: number;
  item_proposta_id: number;
  preco_unitario: number;
  preco_total: number;
}

interface CompraOtimizada {
  fornecedor_id: number;
  fornecedor_nome: string;
  proposta_id: number;
  itens: ItemOtimizado[];
  valor_total: number;
  prazo_entrega?: number;
  condicoes_pagamento?: string;
}

interface AnaliseOtimizadaData {
  solicitacao_id: number;
  solicitacao_numero: string;
  solicitacao_titulo: string;
  itens: ItemAnalise[];
  resumo_fornecedores: ResumoFornecedor[];
  menor_valor_global: number;
  fornecedor_menor_global_id: number;
  fornecedor_menor_global_nome: string;
  valor_otimizado: number;
  economia_otimizada: number;
  economia_percentual: number;
  compra_otimizada: CompraOtimizada[];
  recomendacao: 'COMPRA_UNICA' | 'COMPRA_OTIMIZADA';
  justificativa: string;
}

interface OCGerada {
  pedido_id: number;
  pedido_numero: string;
  fornecedor_id: number;
  fornecedor_nome: string;
  valor_total: number;
  qtd_itens: number;
}

export default function AnaliseOtimizada() {
  const { tenant } = useAuth();
  const navigate = useNavigate();
  const { solicitacaoId } = useParams();
  const queryClient = useQueryClient();

  // Estado para seleções customizadas (item -> fornecedor)
  const [selecoes, setSelecoes] = useState<{
    [itemId: number]: {
      fornecedor_id: number;
      item_proposta_id: number;
      proposta_id: number;
    };
  }>({});

  const [modoSelecao, setModoSelecao] = useState<'otimizado' | 'unico' | 'manual'>('otimizado');
  const [fornecedorUnico, setFornecedorUnico] = useState<number | null>(null);
  const [justificativa, setJustificativa] = useState('');
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  // Query
  const { data: analise, isLoading, refetch } = useQuery<AnaliseOtimizadaData>({
    queryKey: ['analise-otimizada', solicitacaoId],
    queryFn: async () => {
      const response = await api.get(`/cotacoes/solicitacoes/${solicitacaoId}/analise-otimizada`);
      return response.data;
    },
    enabled: !!solicitacaoId,
  });

  // Inicializar seleções quando dados carregam
  useMemo(() => {
    if (analise && Object.keys(selecoes).length === 0) {
      const novasSelecoes: typeof selecoes = {};
      analise.itens.forEach((item) => {
        const melhor = item.precos_fornecedores.find((p) => p.is_menor_preco);
        if (melhor) {
          novasSelecoes[item.item_solicitacao_id] = {
            fornecedor_id: melhor.fornecedor_id,
            item_proposta_id: melhor.item_proposta_id,
            proposta_id: melhor.proposta_id,
          };
        }
      });
      setSelecoes(novasSelecoes);
    }
  }, [analise]);

  // Mutation para gerar OCs
  const gerarOCsMutation = useMutation({
    mutationFn: async (data: { selecoes: any[]; justificativa: string }) => {
      const response = await api.post(
        `/cotacoes/solicitacoes/${solicitacaoId}/gerar-ocs-otimizadas`,
        {
          solicitacao_id: Number(solicitacaoId),
          selecoes: data.selecoes,
          justificativa: data.justificativa,
        }
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['analise-otimizada', solicitacaoId] });
      queryClient.invalidateQueries({ queryKey: ['solicitacoes'] });
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });

      const ocsGeradas = data.ocs_geradas as OCGerada[];
      const numeros = ocsGeradas.map((oc) => oc.pedido_numero).join(', ');

      alert(
        `${ocsGeradas.length} Ordem(ns) de Compra gerada(s) com sucesso!\n\nNumeros: ${numeros}\nValor Total: ${data.valor_total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}`
      );

      navigate('/pedidos');
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || 'Erro ao gerar ordens de compra');
    },
  });

  // Calcular valores baseado nas seleções
  const calculoAtual = useMemo(() => {
    if (!analise) return null;

    let valorTotal = 0;
    const porFornecedor: { [id: number]: { nome: string; itens: any[]; valor: number } } = {};

    Object.entries(selecoes).forEach(([itemId, sel]) => {
      const item = analise.itens.find((i) => i.item_solicitacao_id === Number(itemId));
      if (!item) return;

      const preco = item.precos_fornecedores.find((p) => p.fornecedor_id === sel.fornecedor_id);
      if (!preco) return;

      const precoTotal = Number(preco.preco_total) || 0;
      valorTotal += precoTotal;

      if (!porFornecedor[sel.fornecedor_id]) {
        porFornecedor[sel.fornecedor_id] = {
          nome: preco.fornecedor_nome,
          itens: [],
          valor: 0,
        };
      }
      porFornecedor[sel.fornecedor_id].itens.push({
        item_solicitacao_id: item.item_solicitacao_id,
        item_proposta_id: sel.item_proposta_id,
        fornecedor_id: sel.fornecedor_id,
      });
      porFornecedor[sel.fornecedor_id].valor += precoTotal;
    });

    // Referência é o valor otimizado (melhor preço por item)
    const valorOtimizado = Number(analise.valor_otimizado) || 0;
    const economia = valorOtimizado - valorTotal;
    const economiaPercentual =
      valorOtimizado > 0 ? (economia / valorOtimizado) * 100 : 0;

    return {
      valorTotal,
      porFornecedor,
      qtdFornecedores: Object.keys(porFornecedor).length,
      economia,
      economiaPercentual,
    };
  }, [selecoes, analise]);

  // Aplicar modo de seleção
  const aplicarModo = (modo: 'otimizado' | 'unico', fornId?: number) => {
    if (!analise) return;

    const novasSelecoes: typeof selecoes = {};

    if (modo === 'otimizado') {
      analise.itens.forEach((item) => {
        const melhor = item.precos_fornecedores.find((p) => p.is_menor_preco);
        if (melhor) {
          novasSelecoes[item.item_solicitacao_id] = {
            fornecedor_id: melhor.fornecedor_id,
            item_proposta_id: melhor.item_proposta_id,
            proposta_id: melhor.proposta_id,
          };
        }
      });
      setModoSelecao('otimizado');
      setFornecedorUnico(null);
    } else if (modo === 'unico' && fornId) {
      analise.itens.forEach((item) => {
        const preco = item.precos_fornecedores.find((p) => p.fornecedor_id === fornId);
        if (preco) {
          novasSelecoes[item.item_solicitacao_id] = {
            fornecedor_id: preco.fornecedor_id,
            item_proposta_id: preco.item_proposta_id,
            proposta_id: preco.proposta_id,
          };
        }
      });
      setModoSelecao('unico');
      setFornecedorUnico(fornId);
    }

    setSelecoes(novasSelecoes);
  };

  // Selecionar fornecedor para item específico
  const selecionarFornecedor = (itemId: number, preco: PrecoFornecedor) => {
    setSelecoes((prev) => ({
      ...prev,
      [itemId]: {
        fornecedor_id: preco.fornecedor_id,
        item_proposta_id: preco.item_proposta_id,
        proposta_id: preco.proposta_id,
      },
    }));
    setModoSelecao('manual');
  };

  // Confirmar e gerar OCs
  const confirmarGeracaoOCs = () => {

    const selecoesArray = Object.entries(selecoes).map(([itemId, sel]) => ({
      item_solicitacao_id: Number(itemId),
      fornecedor_id: sel.fornecedor_id,
      item_proposta_id: sel.item_proposta_id,
    }));

    gerarOCsMutation.mutate({
      selecoes: selecoesArray,
      justificativa,
    });
  };

  // Formatar moeda
  const formatCurrency = (value: number | string) =>
    Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

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
      <header className="bg-white border-b shadow-sm">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
              <ScaleIcon className="h-7 w-7" />
              Analise Otimizada de Propostas
            </h1>
            <p className="text-sm text-muted-foreground">{tenant?.nome_empresa}</p>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => refetch()} variant="outline" size="sm">
              <ArrowPathIcon className="h-4 w-4 mr-1" />
              Atualizar
            </Button>
            <Button onClick={() => navigate(-1)} variant="outline">
              <ArrowLeftIcon className="h-4 w-4 mr-2" />
              Voltar
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto px-4 py-6 space-y-6">
        {isLoading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-500">Analisando propostas...</p>
          </div>
        ) : !analise ? (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <p className="text-gray-500">Nenhuma proposta recebida para analise</p>
            <Button onClick={() => navigate('/cotacoes')} className="mt-4">
              Voltar para Cotacoes
            </Button>
          </div>
        ) : (
          <>
            {/* Info da Solicitacao */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-xl font-semibold">{analise.solicitacao_numero}</h2>
                  <p className="text-gray-600">{analise.solicitacao_titulo}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-500">{analise.itens.length} itens</p>
                  <p className="text-sm text-gray-500">
                    {analise.resumo_fornecedores.length} fornecedor(es)
                  </p>
                </div>
              </div>
            </div>

            {/* Painel de Recomendacao */}
            <div
              className={`rounded-lg shadow p-6 ${
                analise.recomendacao === 'COMPRA_OTIMIZADA'
                  ? 'bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200'
                  : 'bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200'
              }`}
            >
              <div className="flex items-center mb-4">
                <LightBulbIcon
                  className={`h-6 w-6 mr-2 ${
                    analise.recomendacao === 'COMPRA_OTIMIZADA'
                      ? 'text-green-600'
                      : 'text-blue-600'
                  }`}
                />
                <h3
                  className={`text-lg font-semibold ${
                    analise.recomendacao === 'COMPRA_OTIMIZADA'
                      ? 'text-green-800'
                      : 'text-blue-800'
                  }`}
                >
                  Recomendacao: {analise.recomendacao === 'COMPRA_OTIMIZADA' ? 'Compra Otimizada' : 'Compra Unica'}
                </h3>
              </div>

              <p className="text-gray-700 mb-4">{analise.justificativa}</p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <p className="text-xs text-gray-500 uppercase">Menor Global (Compra Unica)</p>
                  <p className="text-xl font-bold">{formatCurrency(analise.menor_valor_global)}</p>
                  <p className="text-sm text-gray-600">{analise.fornecedor_menor_global_nome}</p>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <p className="text-xs text-gray-500 uppercase">Valor Otimizado (Split)</p>
                  <p className="text-xl font-bold text-green-600">
                    {formatCurrency(analise.valor_otimizado)}
                  </p>
                  <p className="text-sm text-gray-600">
                    {analise.compra_otimizada.length} fornecedor(es)
                  </p>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <p className="text-xs text-gray-500 uppercase">Economia Potencial</p>
                  <p
                    className={`text-xl font-bold ${
                      analise.economia_otimizada > 0 ? 'text-green-600' : 'text-gray-600'
                    }`}
                  >
                    {formatCurrency(analise.economia_otimizada)}
                  </p>
                  <p className="text-sm text-gray-600">
                    {Number(analise.economia_percentual).toFixed(1)}% de economia
                  </p>
                </div>
              </div>
            </div>

            {/* Modos de Selecao */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Modo de Selecao</h3>
              <div className="flex flex-wrap gap-3">
                <Button
                  variant={modoSelecao === 'otimizado' ? 'default' : 'outline'}
                  onClick={() => aplicarModo('otimizado')}
                  className={modoSelecao === 'otimizado' ? 'bg-green-600 hover:bg-green-700' : ''}
                >
                  <CurrencyDollarIcon className="h-4 w-4 mr-2" />
                  Melhor Preco por Item
                </Button>

                {analise.resumo_fornecedores.map((forn) => (
                  <Button
                    key={forn.fornecedor_id}
                    variant={
                      modoSelecao === 'unico' && fornecedorUnico === forn.fornecedor_id
                        ? 'default'
                        : 'outline'
                    }
                    onClick={() => aplicarModo('unico', forn.fornecedor_id)}
                  >
                    <ShoppingCartIcon className="h-4 w-4 mr-2" />
                    Tudo de {forn.fornecedor_nome}
                  </Button>
                ))}
              </div>

              {modoSelecao === 'manual' && (
                <p className="mt-2 text-sm text-amber-600">
                  Modo manual - voce customizou as selecoes
                </p>
              )}
            </div>

            {/* Resumo da Selecao Atual */}
            {calculoAtual && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">Resumo da Selecao Atual</h3>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase">Valor Total</p>
                    <p className="text-2xl font-bold text-primary">
                      {formatCurrency(calculoAtual.valorTotal)}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase">OCs a Gerar</p>
                    <p className="text-2xl font-bold">{calculoAtual.qtdFornecedores}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase">
                      {calculoAtual.economia >= 0 ? 'Economia vs Melhor Preco' : 'Custo Adicional'}
                    </p>
                    <p
                      className={`text-2xl font-bold ${
                        calculoAtual.economia > 0 ? 'text-green-600' : calculoAtual.economia < 0 ? 'text-red-600' : 'text-gray-600'
                      }`}
                    >
                      {calculoAtual.economia < 0 ? '+' : ''}{formatCurrency(Math.abs(calculoAtual.economia))}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase">
                      {calculoAtual.economiaPercentual >= 0 ? '% Economia' : '% Acima do Menor'}
                    </p>
                    <p
                      className={`text-2xl font-bold ${
                        calculoAtual.economiaPercentual > 0 ? 'text-green-600' : calculoAtual.economiaPercentual < 0 ? 'text-red-600' : 'text-gray-600'
                      }`}
                    >
                      {calculoAtual.economiaPercentual < 0 ? '+' : ''}{Math.abs(calculoAtual.economiaPercentual).toFixed(1)}%
                    </p>
                  </div>
                </div>

                {/* Detalhamento por fornecedor */}
                <div className="border-t pt-4">
                  <p className="text-sm font-medium text-gray-700 mb-2">
                    Ordens de Compra a serem geradas:
                  </p>
                  <div className="space-y-2">
                    {Object.entries(calculoAtual.porFornecedor).map(([id, data]) => (
                      <div
                        key={id}
                        className="flex justify-between items-center bg-gray-50 rounded px-4 py-2"
                      >
                        <div>
                          <span className="font-medium">{data.nome}</span>
                          <span className="text-gray-500 text-sm ml-2">
                            ({data.itens.length} {data.itens.length === 1 ? 'item' : 'itens'})
                          </span>
                        </div>
                        <span className="font-semibold">{formatCurrency(data.valor)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Matriz Item x Fornecedor */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b bg-gray-50">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <DocumentDuplicateIcon className="h-5 w-5" />
                  Matriz Comparativa por Item
                </h3>
                <p className="text-sm text-gray-500">
                  Clique em um preco para selecionar o fornecedor para aquele item
                </p>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase sticky left-0 bg-gray-50 z-10">
                        Item / Produto
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                        Qtd
                      </th>
                      {analise.resumo_fornecedores.map((forn) => (
                        <th
                          key={forn.fornecedor_id}
                          className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase min-w-[180px]"
                        >
                          <div>{forn.fornecedor_nome}</div>
                          <div className="text-[10px] font-normal text-gray-400">
                            {forn.qtd_itens_menor_preco}/{forn.qtd_itens_cotados} menores
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {analise.itens.map((item) => {
                      const selecaoAtual = selecoes[item.item_solicitacao_id];
                      return (
                        <tr key={item.item_solicitacao_id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 sticky left-0 bg-white z-10">
                            <div className="font-medium text-sm">{item.produto_codigo || '-'}</div>
                            <div className="text-xs text-gray-500 max-w-[200px] truncate">
                              {item.produto_nome}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-center text-sm">
                            {item.quantidade} {item.unidade_medida}
                          </td>
                          {analise.resumo_fornecedores.map((forn) => {
                            const preco = item.precos_fornecedores.find(
                              (p) => p.fornecedor_id === forn.fornecedor_id
                            );

                            if (!preco) {
                              return (
                                <td
                                  key={forn.fornecedor_id}
                                  className="px-4 py-3 text-center text-gray-400 text-sm"
                                >
                                  -
                                </td>
                              );
                            }

                            const isSelected =
                              selecaoAtual?.fornecedor_id === preco.fornecedor_id;
                            const isMenor = preco.is_menor_preco;

                            return (
                              <td
                                key={forn.fornecedor_id}
                                className={`px-2 py-2 text-center cursor-pointer transition-all ${
                                  isSelected
                                    ? 'bg-blue-100 ring-2 ring-blue-500 ring-inset'
                                    : isMenor
                                    ? 'bg-green-50'
                                    : 'hover:bg-gray-100'
                                }`}
                                onClick={() => selecionarFornecedor(item.item_solicitacao_id, preco)}
                              >
                                <div
                                  className={`text-sm font-semibold ${
                                    isMenor ? 'text-green-700' : ''
                                  }`}
                                >
                                  {formatCurrency(preco.preco_final)}
                                </div>
                                <div className="text-xs text-gray-500">
                                  Total: {formatCurrency(preco.preco_total)}
                                </div>
                                {preco.diferenca_percentual !== undefined &&
                                  Number(preco.diferenca_percentual) > 0 && (
                                    <div className="text-xs text-red-500">
                                      +{Number(preco.diferenca_percentual).toFixed(1)}%
                                    </div>
                                  )}
                                {isMenor && (
                                  <div className="text-[10px] text-green-600 font-medium">
                                    MENOR
                                  </div>
                                )}
                                {isSelected && (
                                  <CheckCircleIcon className="h-4 w-4 text-blue-600 mx-auto mt-1" />
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}

                    {/* Linha de Total por Fornecedor */}
                    <tr className="bg-gray-100 font-semibold">
                      <td className="px-4 py-3 sticky left-0 bg-gray-100 z-10">TOTAL PROPOSTA</td>
                      <td></td>
                      {analise.resumo_fornecedores.map((forn) => (
                        <td key={forn.fornecedor_id} className="px-4 py-3 text-center">
                          <div>{formatCurrency(forn.valor_total)}</div>
                          {forn.prazo_entrega && (
                            <div className="text-xs text-gray-500 flex items-center justify-center gap-1">
                              <TruckIcon className="h-3 w-3" />
                              {forn.prazo_entrega}d
                            </div>
                          )}
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Botao de Acao */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                  <h3 className="text-lg font-semibold">Gerar Ordens de Compra</h3>
                  <p className="text-sm text-gray-500">
                    {calculoAtual?.qtdFornecedores === 1
                      ? '1 OC sera gerada'
                      : `${calculoAtual?.qtdFornecedores || 0} OCs serao geradas`}
                  </p>
                </div>
                <Button
                  size="lg"
                  onClick={() => setShowConfirmModal(true)}
                  className="bg-green-600 hover:bg-green-700"
                >
                  <ShoppingCartIcon className="h-5 w-5 mr-2" />
                  Confirmar e Gerar OC(s)
                </Button>
              </div>
            </div>
          </>
        )}
      </main>

      {/* Modal de Confirmacao */}
      {showConfirmModal && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Confirmar Geracao de OCs</h3>
            </div>

            <div className="px-6 py-4 space-y-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-2">Resumo:</p>
                <div className="space-y-1 text-sm">
                  <p>
                    <strong>OCs a gerar:</strong> {calculoAtual?.qtdFornecedores}
                  </p>
                  <p>
                    <strong>Valor total:</strong> {formatCurrency(calculoAtual?.valorTotal || 0)}
                  </p>
                  {calculoAtual && calculoAtual.economia > 0 && (
                    <p className="text-green-600">
                      <strong>Economia:</strong> {formatCurrency(calculoAtual.economia)} (
                      {calculoAtual.economiaPercentual.toFixed(1)}%)
                    </p>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Justificativa
                </label>
                <textarea
                  value={justificativa}
                  onChange={(e) => setJustificativa(e.target.value)}
                  rows={3}
                  placeholder="Descreva os motivos da escolha (opcional)"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                />
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
              <Button
                variant="outline"
                onClick={() => {
                  setShowConfirmModal(false);
                  setJustificativa('');
                }}
              >
                Cancelar
              </Button>
              <Button
                onClick={confirmarGeracaoOCs}
                disabled={gerarOCsMutation.isPending}
                className="bg-green-600 hover:bg-green-700"
              >
                {gerarOCsMutation.isPending ? 'Gerando...' : 'Confirmar e Gerar'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
