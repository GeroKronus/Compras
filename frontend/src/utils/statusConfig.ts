/**
 * Status Config - Configuração centralizada de status por entidade
 * Elimina duplicação de statusColors e statusLabels em todas as páginas
 */

export interface StatusConfig {
  color: string;
  label: string;
  bgColor?: string;
  textColor?: string;
}

// ============ SOLICITAÇÃO DE COTAÇÃO ============
export const SOLICITACAO_STATUS: Record<string, StatusConfig> = {
  RASCUNHO: {
    color: 'bg-gray-100 text-gray-800',
    label: 'Rascunho',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-800',
  },
  ENVIADA: {
    color: 'bg-blue-100 text-blue-800',
    label: 'Enviada',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-800',
  },
  EM_COTACAO: {
    color: 'bg-yellow-100 text-yellow-800',
    label: 'Em Cotação',
    bgColor: 'bg-yellow-100',
    textColor: 'text-yellow-800',
  },
  FINALIZADA: {
    color: 'bg-green-100 text-green-800',
    label: 'Finalizada',
    bgColor: 'bg-green-100',
    textColor: 'text-green-800',
  },
  CANCELADA: {
    color: 'bg-red-100 text-red-800',
    label: 'Cancelada',
    bgColor: 'bg-red-100',
    textColor: 'text-red-800',
  },
};

// ============ PROPOSTA DE FORNECEDOR ============
export const PROPOSTA_STATUS: Record<string, StatusConfig> = {
  PENDENTE: {
    color: 'bg-yellow-100 text-yellow-800',
    label: 'Pendente',
    bgColor: 'bg-yellow-100',
    textColor: 'text-yellow-800',
  },
  RECEBIDA: {
    color: 'bg-blue-100 text-blue-800',
    label: 'Recebida',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-800',
  },
  APROVADA: {
    color: 'bg-green-100 text-green-800',
    label: 'Aprovada',
    bgColor: 'bg-green-100',
    textColor: 'text-green-800',
  },
  REJEITADA: {
    color: 'bg-red-100 text-red-800',
    label: 'Rejeitada',
    bgColor: 'bg-red-100',
    textColor: 'text-red-800',
  },
  VENCEDORA: {
    color: 'bg-purple-100 text-purple-800',
    label: 'Vencedora',
    bgColor: 'bg-purple-100',
    textColor: 'text-purple-800',
  },
};

// ============ PEDIDO DE COMPRA ============
export const PEDIDO_STATUS: Record<string, StatusConfig> = {
  RASCUNHO: {
    color: 'bg-gray-100 text-gray-800',
    label: 'Rascunho',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-800',
  },
  AGUARDANDO_APROVACAO: {
    color: 'bg-yellow-100 text-yellow-800',
    label: 'Aguardando Aprovação',
    bgColor: 'bg-yellow-100',
    textColor: 'text-yellow-800',
  },
  APROVADO: {
    color: 'bg-blue-100 text-blue-800',
    label: 'Aprovado',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-800',
  },
  ENVIADO_FORNECEDOR: {
    color: 'bg-indigo-100 text-indigo-800',
    label: 'Enviado ao Fornecedor',
    bgColor: 'bg-indigo-100',
    textColor: 'text-indigo-800',
  },
  CONFIRMADO: {
    color: 'bg-purple-100 text-purple-800',
    label: 'Confirmado',
    bgColor: 'bg-purple-100',
    textColor: 'text-purple-800',
  },
  EM_TRANSITO: {
    color: 'bg-orange-100 text-orange-800',
    label: 'Em Trânsito',
    bgColor: 'bg-orange-100',
    textColor: 'text-orange-800',
  },
  ENTREGUE_PARCIAL: {
    color: 'bg-teal-100 text-teal-800',
    label: 'Entregue Parcial',
    bgColor: 'bg-teal-100',
    textColor: 'text-teal-800',
  },
  ENTREGUE: {
    color: 'bg-green-100 text-green-800',
    label: 'Entregue',
    bgColor: 'bg-green-100',
    textColor: 'text-green-800',
  },
  CANCELADO: {
    color: 'bg-red-100 text-red-800',
    label: 'Cancelado',
    bgColor: 'bg-red-100',
    textColor: 'text-red-800',
  },
};

// ============ TIPO ENTIDADE ============
export type StatusEntity = 'solicitacao' | 'proposta' | 'pedido';

const STATUS_MAPS: Record<StatusEntity, Record<string, StatusConfig>> = {
  solicitacao: SOLICITACAO_STATUS,
  proposta: PROPOSTA_STATUS,
  pedido: PEDIDO_STATUS,
};

// ============ FUNÇÕES HELPER ============

/**
 * Obtém a cor CSS do status
 * @param entity - Tipo de entidade
 * @param status - Valor do status
 * @returns Classes CSS para o badge
 */
export function getStatusColor(entity: StatusEntity, status: string): string {
  return STATUS_MAPS[entity]?.[status]?.color || 'bg-gray-100 text-gray-800';
}

/**
 * Obtém o label do status
 * @param entity - Tipo de entidade
 * @param status - Valor do status
 * @returns Label legível
 */
export function getStatusLabel(entity: StatusEntity, status: string): string {
  return STATUS_MAPS[entity]?.[status]?.label || status;
}

/**
 * Obtém configuração completa do status
 * @param entity - Tipo de entidade
 * @param status - Valor do status
 * @returns Objeto StatusConfig
 */
export function getStatusConfig(entity: StatusEntity, status: string): StatusConfig {
  return STATUS_MAPS[entity]?.[status] || {
    color: 'bg-gray-100 text-gray-800',
    label: status,
  };
}

/**
 * Retorna array de opções para select
 * @param entity - Tipo de entidade
 * @returns Array de { value, label }
 */
export function getStatusOptions(entity: StatusEntity): Array<{ value: string; label: string }> {
  const map = STATUS_MAPS[entity];
  return Object.entries(map).map(([value, config]) => ({
    value,
    label: config.label,
  }));
}
