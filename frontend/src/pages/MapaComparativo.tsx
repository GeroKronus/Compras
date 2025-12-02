import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { Button } from '../components/ui/button';
import { useAuth } from '../hooks/useAuth';
import {
  CheckCircleIcon,
  SparklesIcon,
  ArrowLeftIcon,
  DocumentPlusIcon,
} from '@heroicons/react/24/outline';

interface PropostaItem {
  proposta_id: number;
  fornecedor_nome: string;
  fornecedor_cnpj: string;
  preco_unitario: number;
  quantidade_disponivel: number;
  desconto_percentual: number;
  preco_final: number;
  marca_oferecida?: string;
  prazo_entrega_item?: number;
}

interface ItemMapa {
  item_solicitacao_id: number;
  produto_id: number;
  produto_nome: string;
  produto_codigo: string;
  quantidade_solicitada: number;
  propostas: PropostaItem[];
}

interface MapaComparativo {
  solicitacao_id: number;
  solicitacao_numero: string;
  solicitacao_titulo: string;
  itens: ItemMapa[];
  resumo: {
    [fornecedorId: string]: {
      fornecedor_nome: string;
      fornecedor_cnpj: string;
      valor_total: number;
      itens_cotados: number;
      prazo_medio: number;
      condicoes_pagamento?: string;
    };
  };
}

interface SugestaoIA {
  proposta_sugerida_id: number;
  fornecedor_nome: string;
  score_total: number;
  motivos: string[];
  economia_estimada?: number;
  alertas: string[];
}

export default function MapaComparativo() {
  const { tenant } = useAuth();
  const navigate = useNavigate();
  const { solicitacaoId } = useParams();
  const queryClient = useQueryClient();

  const [isEscolherModalOpen, setIsEscolherModalOpen] = useState(false);
  const [selectedPropostaId, setSelectedPropostaId] = useState<number | null>(null);
  const [justificativa, setJustificativa] = useState('');
  const [showSugestao, setShowSugestao] = useState(false);

  // Queries
  const { data: mapaData, isLoading } = useQuery<MapaComparativo>({
    queryKey: ['mapa-comparativo', solicitacaoId],
    queryFn: async () => {
      const response = await api.get(`/cotacoes/solicitacoes/${solicitacaoId}/mapa-comparativo`);
      return response.data;
    },
    enabled: !!solicitacaoId,
  });

  const { data: sugestaoData, isLoading: isLoadingSugestao } = useQuery<SugestaoIA>({
    queryKey: ['sugestao-ia', solicitacaoId],
    queryFn: async () => {
      const response = await api.get(`/cotacoes/solicitacoes/${solicitacaoId}/sugestao-ia`);
      return response.data;
    },
    enabled: !!solicitacaoId && showSugestao,
  });

  // Mutation para escolher vencedor
  const [gerarPedido, setGerarPedido] = useState(true);

  const escolherVencedorMutation = useMutation({
    mutationFn: (data: { proposta_id: number; justificativa: string }) =>
      api.post(`/cotacoes/solicitacoes/${solicitacaoId}/escolher-vencedor`, data),
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: ['mapa-comparativo', solicitacaoId] });
      queryClient.invalidateQueries({ queryKey: ['solicitacoes'] });

      if (gerarPedido && selectedPropostaId) {
        try {
          const response = await api.post('/pedidos/from-cotacao', {
            proposta_id: selectedPropostaId,
            observacoes: `Gerado a partir da cotacao ${solicitacaoId}`
          });
          alert(`Fornecedor vencedor selecionado e Pedido ${response.data.numero} gerado com sucesso!`);
          navigate('/pedidos');
        } catch (error: any) {
          alert(`Vencedor selecionado! Erro ao gerar pedido: ${error.response?.data?.detail || 'Erro desconhecido'}`);
          navigate('/cotacoes');
        }
      } else {
        alert('Fornecedor vencedor selecionado com sucesso!');
        navigate('/cotacoes');
      }

      setIsEscolherModalOpen(false);
      setSelectedPropostaId(null);
      setJustificativa('');
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || 'Erro ao selecionar vencedor');
    },
  });

  const handleEscolherVencedor = () => {
    if (!selectedPropostaId) {
      alert('Selecione uma proposta');
      return;
    }
    escolherVencedorMutation.mutate({
      proposta_id: selectedPropostaId,
      justificativa,
    });
  };

  const openEscolherModal = (propostaId: number) => {
    setSelectedPropostaId(propostaId);
    setJustificativa(gerarJustificativaAutomatica(propostaId));
    setIsEscolherModalOpen(true);
  };

  // Identificar menor preco por item
  const getMenorPreco = (propostas: PropostaItem[]): number | null => {
    if (propostas.length === 0) return null;
    return Math.min(...propostas.map((p) => p.preco_final));
  };

  // Identificar fornecedores unicos
  const fornecedores = mapaData
    ? Object.entries(mapaData.resumo).map(([id, data]) => ({
        id: parseInt(id),
        ...data,
      }))
    : [];

  // Identificar melhor proposta (menor valor total)
  const melhorProposta = fornecedores.length > 0
    ? fornecedores.reduce((melhor, atual) =>
        atual.valor_total < melhor.valor_total ? atual : melhor
      )
    : null;

  // Gerar justificativa automatica
  const gerarJustificativaAutomatica = (fornecedorId: number): string => {
    const fornecedor = fornecedores.find(f => f.id === fornecedorId);
    if (!fornecedor) return '';

    const isMelhorPreco = melhorProposta?.id === fornecedorId;
    const _economia = melhorProposta && fornecedor.id !== melhorProposta.id
      ? fornecedor.valor_total - melhorProposta.valor_total
      : 0;
    void _economia; // Variável reservada para uso futuro

    let justificativa = '';

    if (isMelhorPreco) {
      const segundoMelhor = fornecedores
        .filter(f => f.id !== fornecedorId)
        .sort((a, b) => a.valor_total - b.valor_total)[0];

      if (segundoMelhor) {
        const economiaValor = segundoMelhor.valor_total - fornecedor.valor_total;
        const economiaPct = ((economiaValor / segundoMelhor.valor_total) * 100).toFixed(1);
        justificativa = `Fornecedor selecionado por apresentar o menor valor total (${fornecedor.valor_total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}), representando uma economia de ${economiaValor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })} (${economiaPct}%) em relacao ao segundo colocado.`;
      } else {
        justificativa = `Fornecedor selecionado por apresentar o menor valor total (${fornecedor.valor_total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}).`;
      }

      if (fornecedor.prazo_medio) {
        justificativa += ` Prazo de entrega: ${fornecedor.prazo_medio} dias.`;
      }
    } else {
      justificativa = `Fornecedor ${fornecedor.fornecedor_nome} selecionado. Valor total: ${fornecedor.valor_total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}.`;
      if (fornecedor.prazo_medio) {
        justificativa += ` Prazo de entrega: ${fornecedor.prazo_medio} dias.`;
      }
    }

    return justificativa;
  };

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
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-primary">Mapa Comparativo</h1>
            <p className="text-sm text-muted-foreground">{tenant?.nome_empresa}</p>
          </div>
          <Button onClick={() => navigate(-1)} variant="outline">
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Voltar
          </Button>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto px-4 py-8 space-y-6">
        {isLoading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-500">Carregando mapa comparativo...</p>
          </div>
        ) : !mapaData ? (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <p className="text-gray-500">Nenhuma proposta recebida ainda</p>
            <Button onClick={() => navigate(`/cotacoes/${solicitacaoId}/propostas`)} className="mt-4">
              Registrar Propostas
            </Button>
          </div>
        ) : (
          <>
            {/* Info da Solicitacao */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-semibold">{mapaData.solicitacao_numero}</h2>
                  <p className="text-gray-600">{mapaData.solicitacao_titulo}</p>
                </div>
                <div className="flex gap-2">
                  <Button onClick={() => setShowSugestao(true)} variant="outline">
                    <SparklesIcon className="h-5 w-5 mr-2" />
                    Sugestao IA
                  </Button>
                </div>
              </div>
            </div>

            {/* Sugestao IA */}
            {showSugestao && (
              <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg shadow p-6 border border-purple-200">
                <div className="flex items-center mb-4">
                  <SparklesIcon className="h-6 w-6 text-purple-600 mr-2" />
                  <h3 className="text-lg font-medium text-purple-800">Sugestao da Inteligencia Artificial</h3>
                </div>
                {isLoadingSugestao ? (
                  <p className="text-gray-500">Analisando propostas...</p>
                ) : sugestaoData ? (
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="font-medium text-lg">{sugestaoData.fornecedor_nome}</p>
                        <p className="text-sm text-gray-600">Score: {sugestaoData.score_total.toFixed(2)}</p>
                      </div>
                      {sugestaoData.economia_estimada && (
                        <div className="text-right">
                          <p className="text-sm text-gray-500">Economia estimada</p>
                          <p className="text-lg font-bold text-green-600">
                            {sugestaoData.economia_estimada.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                          </p>
                        </div>
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-700 mb-1">Motivos:</p>
                      <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                        {sugestaoData.motivos.map((motivo, i) => (
                          <li key={i}>{motivo}</li>
                        ))}
                      </ul>
                    </div>
                    {sugestaoData.alertas.length > 0 && (
                      <div className="mt-2 p-2 bg-yellow-50 rounded border border-yellow-200">
                        <p className="text-sm font-medium text-yellow-800">Alertas:</p>
                        <ul className="list-disc list-inside text-sm text-yellow-700">
                          {sugestaoData.alertas.map((alerta, i) => (
                            <li key={i}>{alerta}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <Button
                      onClick={() => openEscolherModal(sugestaoData.proposta_sugerida_id)}
                      className="mt-4"
                    >
                      <CheckCircleIcon className="h-5 w-5 mr-2" />
                      Aceitar Sugestao
                    </Button>
                  </div>
                ) : (
                  <p className="text-gray-500">Nao foi possivel gerar sugestao. Verifique se ha propostas recebidas.</p>
                )}
              </div>
            )}

            {/* Resumo por Fornecedor */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium mb-4">Resumo por Fornecedor</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {fornecedores.map((fornecedor) => {
                  const isMelhor = melhorProposta?.id === fornecedor.id;
                  return (
                    <div
                      key={fornecedor.id}
                      className={`border-2 rounded-lg p-4 hover:shadow-md transition-shadow relative ${
                        isMelhor
                          ? 'border-green-500 bg-green-50 ring-2 ring-green-200'
                          : 'border-gray-200'
                      }`}
                    >
                      {isMelhor && (
                        <div className="absolute -top-3 left-4 bg-green-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                          RECOMENDADO - MENOR PRECO
                        </div>
                      )}
                      <div className="flex justify-between items-start mb-2 mt-2">
                        <div>
                          <h4 className={`font-medium ${isMelhor ? 'text-green-800' : ''}`}>
                            {fornecedor.fornecedor_nome}
                          </h4>
                          <p className="text-sm text-gray-500">{fornecedor.fornecedor_cnpj}</p>
                        </div>
                        <Button
                          size="sm"
                          variant={isMelhor ? 'default' : 'outline'}
                          onClick={() => openEscolherModal(fornecedor.id)}
                          className={isMelhor ? 'bg-green-600 hover:bg-green-700' : ''}
                        >
                          <CheckCircleIcon className="h-4 w-4 mr-1" />
                          {isMelhor ? 'Selecionar' : ''}
                        </Button>
                      </div>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-500">Valor Total:</span>
                          <span className={`font-bold ${isMelhor ? 'text-green-700 text-lg' : 'font-medium'}`}>
                            {fornecedor.valor_total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Itens Cotados:</span>
                          <span>{fornecedor.itens_cotados}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Prazo Entrega:</span>
                          <span>{fornecedor.prazo_medio ? `${fornecedor.prazo_medio} dias` : '-'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Pagamento:</span>
                          <span>{fornecedor.condicoes_pagamento || '-'}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Tabela Comparativa */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b">
                <h3 className="text-lg font-medium">Comparativo por Item</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase sticky left-0 bg-gray-50">
                        Produto
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                        Qtd
                      </th>
                      {fornecedores.map((f) => (
                        <th
                          key={f.id}
                          className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase min-w-[150px]"
                        >
                          {f.fornecedor_nome}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {mapaData.itens.map((item) => {
                      const menorPreco = getMenorPreco(item.propostas);
                      return (
                        <tr key={item.item_solicitacao_id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 sticky left-0 bg-white">
                            <div className="font-medium text-sm">{item.produto_codigo}</div>
                            <div className="text-xs text-gray-500">{item.produto_nome}</div>
                          </td>
                          <td className="px-4 py-3 text-center text-sm">
                            {item.quantidade_solicitada}
                          </td>
                          {fornecedores.map((f) => {
                            const proposta = item.propostas.find(
                              (p) => p.proposta_id === f.id
                            );
                            if (!proposta) {
                              return (
                                <td key={f.id} className="px-4 py-3 text-center text-gray-400 text-sm">
                                  -
                                </td>
                              );
                            }
                            const isMenor = proposta.preco_final === menorPreco;
                            return (
                              <td
                                key={f.id}
                                className={`px-4 py-3 text-center ${isMenor ? 'bg-green-50' : ''}`}
                              >
                                <div className={`text-sm font-medium ${isMenor ? 'text-green-700' : ''}`}>
                                  {proposta.preco_final.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                                </div>
                                {proposta.desconto_percentual > 0 && (
                                  <div className="text-xs text-green-600">
                                    -{proposta.desconto_percentual}%
                                  </div>
                                )}
                                {proposta.marca_oferecida && (
                                  <div className="text-xs text-gray-500">{proposta.marca_oferecida}</div>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                    {/* Linha de Total */}
                    <tr className="bg-gray-100 font-medium">
                      <td className="px-4 py-3 sticky left-0 bg-gray-100">TOTAL</td>
                      <td></td>
                      {fornecedores.map((f) => (
                        <td key={f.id} className="px-4 py-3 text-center">
                          {f.valor_total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </main>

      {/* Modal Escolher Vencedor */}
      {isEscolherModalOpen && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">
                Confirmar Fornecedor Vencedor
              </h3>
            </div>

            <div className="px-6 py-4 space-y-4">
              <p className="text-sm text-gray-600">
                Ao confirmar, esta solicitacao sera finalizada e o fornecedor selecionado
                sera marcado como vencedor.
              </p>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Justificativa da Escolha
                </label>
                <textarea
                  value={justificativa}
                  onChange={(e) => setJustificativa(e.target.value)}
                  rows={4}
                  placeholder="Descreva os motivos da escolha deste fornecedor (opcional)"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                />
              </div>
              <div className="flex items-center bg-blue-50 p-3 rounded-lg">
                <input
                  type="checkbox"
                  id="gerarPedido"
                  checked={gerarPedido}
                  onChange={(e) => setGerarPedido(e.target.checked)}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <label htmlFor="gerarPedido" className="ml-2 text-sm text-gray-700">
                  <DocumentPlusIcon className="h-4 w-4 inline mr-1" />
                  Gerar Pedido de Compra automaticamente
                </label>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => {
                  setIsEscolherModalOpen(false);
                  setSelectedPropostaId(null);
                  setJustificativa('');
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleEscolherVencedor}
                disabled={escolherVencedorMutation.isPending}
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
              >
                {escolherVencedorMutation.isPending ? 'Confirmando...' : 'Confirmar Vencedor'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
