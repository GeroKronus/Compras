/**
 * Configuracao centralizada de status de pedidos
 * Elimina duplicacao de mapeamentos em multiplos componentes
 */

export type PedidoStatus =
  | 'RASCUNHO'
  | 'AGUARDANDO_APROVACAO'
  | 'APROVADO'
  | 'ENVIADO_FORNECEDOR'
  | 'CONFIRMADO'
  | 'EM_TRANSITO'
  | 'ENTREGUE_PARCIAL'
  | 'ENTREGUE'
  | 'CANCELADO';

interface StatusConfig {
  label: string;
  color: string;
  bgColor: string;
  textColor: string;
}

export const STATUS_CONFIG: Record<PedidoStatus, StatusConfig> = {
  RASCUNHO: {
    label: 'Rascunho',
    color: 'gray',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-800',
  },
  AGUARDANDO_APROVACAO: {
    label: 'Aguardando Aprovacao',
    color: 'yellow',
    bgColor: 'bg-yellow-100',
    textColor: 'text-yellow-800',
  },
  APROVADO: {
    label: 'Aprovado',
    color: 'blue',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-800',
  },
  ENVIADO_FORNECEDOR: {
    label: 'Enviado ao Fornecedor',
    color: 'indigo',
    bgColor: 'bg-indigo-100',
    textColor: 'text-indigo-800',
  },
  CONFIRMADO: {
    label: 'Confirmado',
    color: 'purple',
    bgColor: 'bg-purple-100',
    textColor: 'text-purple-800',
  },
  EM_TRANSITO: {
    label: 'Em Transito',
    color: 'orange',
    bgColor: 'bg-orange-100',
    textColor: 'text-orange-800',
  },
  ENTREGUE_PARCIAL: {
    label: 'Entregue Parcial',
    color: 'teal',
    bgColor: 'bg-teal-100',
    textColor: 'text-teal-800',
  },
  ENTREGUE: {
    label: 'Entregue',
    color: 'green',
    bgColor: 'bg-green-100',
    textColor: 'text-green-800',
  },
  CANCELADO: {
    label: 'Cancelado',
    color: 'red',
    bgColor: 'bg-red-100',
    textColor: 'text-red-800',
  },
};

// Helpers para compatibilidade com o codigo existente
export const statusColors: Record<string, string> = Object.fromEntries(
  Object.entries(STATUS_CONFIG).map(([key, config]) => [
    key,
    `${config.bgColor} ${config.textColor}`,
  ])
);

export const statusLabels: Record<string, string> = Object.fromEntries(
  Object.entries(STATUS_CONFIG).map(([key, config]) => [key, config.label])
);

// Lista ordenada para timeline de progresso
export const STATUS_FLOW: PedidoStatus[] = [
  'RASCUNHO',
  'AGUARDANDO_APROVACAO',
  'APROVADO',
  'ENVIADO_FORNECEDOR',
  'CONFIRMADO',
  'EM_TRANSITO',
  'ENTREGUE',
];

// Funcoes utilitarias
export function getStatusLabel(status: string): string {
  return STATUS_CONFIG[status as PedidoStatus]?.label || status;
}

export function getStatusClass(status: string): string {
  const config = STATUS_CONFIG[status as PedidoStatus];
  return config ? `${config.bgColor} ${config.textColor}` : 'bg-gray-100 text-gray-800';
}

export function getStatusIndex(status: PedidoStatus): number {
  return STATUS_FLOW.indexOf(status);
}

export function isStatusPast(currentStatus: PedidoStatus, checkStatus: PedidoStatus): boolean {
  return getStatusIndex(currentStatus) > getStatusIndex(checkStatus);
}
