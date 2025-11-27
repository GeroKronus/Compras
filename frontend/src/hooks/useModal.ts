/**
 * useModal - Hook para gerenciamento de estado de modais
 * Elimina duplicação de useState para isOpen, data, etc.
 */
import { useState, useCallback } from 'react';

interface UseModalReturn<T> {
  /** Se o modal está aberto */
  isOpen: boolean;
  /** Dados associados ao modal */
  data: T | null;
  /** Abre o modal (opcionalmente com dados) */
  open: (data?: T) => void;
  /** Fecha o modal e limpa os dados */
  close: () => void;
  /** Alterna o estado do modal */
  toggle: () => void;
  /** Atualiza os dados sem fechar */
  setData: (data: T | null) => void;
}

/**
 * Hook para gerenciar estado de um modal
 *
 * @example
 * const viewModal = useModal<Pedido>();
 * // Abrir com dados
 * viewModal.open(pedido);
 * // No componente
 * {viewModal.isOpen && <Modal data={viewModal.data} onClose={viewModal.close} />}
 */
export function useModal<T = null>(): UseModalReturn<T> {
  const [isOpen, setIsOpen] = useState(false);
  const [data, setData] = useState<T | null>(null);

  const open = useCallback((itemData?: T) => {
    if (itemData !== undefined) {
      setData(itemData);
    }
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    setData(null);
  }, []);

  const toggle = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  return {
    isOpen,
    data,
    open,
    close,
    toggle,
    setData,
  };
}

/**
 * Hook para gerenciar múltiplos modais de uma vez
 *
 * @example
 * const modals = useModals(['create', 'edit', 'view', 'delete']);
 * modals.create.open();
 * modals.edit.open(item);
 */
export function useModals<T = any>(
  modalNames: string[]
): Record<string, UseModalReturn<T>> {
  const modals: Record<string, UseModalReturn<T>> = {};

  modalNames.forEach((name) => {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    modals[name] = useModal<T>();
  });

  return modals;
}
