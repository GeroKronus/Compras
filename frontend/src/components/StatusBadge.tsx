/**
 * StatusBadge - Badge de status reutilizável
 * Usa a configuração centralizada de statusConfig.ts
 */
import { getStatusColor, getStatusLabel, StatusEntity } from '../utils/statusConfig';

interface StatusBadgeProps {
  /** Tipo de entidade */
  entity: StatusEntity;
  /** Valor do status */
  status: string;
  /** Tamanho do badge */
  size?: 'sm' | 'md' | 'lg';
  /** Classes adicionais */
  className?: string;
}

const sizeClasses = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-xs',
  lg: 'px-3 py-1.5 text-sm',
};

export function StatusBadge({
  entity,
  status,
  size = 'md',
  className = '',
}: StatusBadgeProps) {
  const color = getStatusColor(entity, status);
  const label = getStatusLabel(entity, status);

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full ${color} ${sizeClasses[size]} ${className}`}
    >
      {label}
    </span>
  );
}
