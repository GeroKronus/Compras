/**
 * useCrudResource - Hook genérico para operações CRUD
 * Elimina duplicação de useQuery/useMutation em todas as páginas
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';

interface UseCrudOptions<T> {
  /** Endpoint base da API (ex: "/produtos") */
  endpoint: string;
  /** Chave para o React Query */
  queryKey: string;
  /** Callback após criar com sucesso */
  onCreateSuccess?: (data: T) => void;
  /** Callback após atualizar com sucesso */
  onUpdateSuccess?: (data: T) => void;
  /** Callback após deletar com sucesso */
  onDeleteSuccess?: () => void;
  /** Callback de erro */
  onError?: (error: any) => void;
  /** Parâmetros de query para listagem */
  queryParams?: Record<string, any>;
  /** Se deve buscar automaticamente (default: true) */
  enabled?: boolean;
}

interface ListResponse<T> {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
}

interface UseCrudReturn<T> {
  /** Dados da listagem */
  data: ListResponse<T> | undefined;
  /** Lista de itens (atalho para data?.items) */
  items: T[];
  /** Total de itens */
  total: number;
  /** Se está carregando */
  isLoading: boolean;
  /** Se está revalidando */
  isFetching: boolean;
  /** Erro da query */
  error: any;
  /** Mutation de criação */
  create: {
    mutate: (data: Partial<T>) => void;
    mutateAsync: (data: Partial<T>) => Promise<T>;
    isPending: boolean;
  };
  /** Mutation de atualização */
  update: {
    mutate: (params: { id: number; data: Partial<T> }) => void;
    mutateAsync: (params: { id: number; data: Partial<T> }) => Promise<T>;
    isPending: boolean;
  };
  /** Mutation de deleção */
  remove: {
    mutate: (id: number) => void;
    mutateAsync: (id: number) => Promise<void>;
    isPending: boolean;
  };
  /** Recarrega os dados */
  refetch: () => void;
  /** Invalida o cache */
  invalidate: () => void;
}

/**
 * Hook genérico para operações CRUD
 *
 * @example
 * const { items, isLoading, create, update, remove } = useCrudResource<Produto>({
 *   endpoint: '/produtos',
 *   queryKey: 'produtos',
 *   onCreateSuccess: () => setShowForm(false),
 * });
 */
export function useCrudResource<T extends { id?: number }>({
  endpoint,
  queryKey,
  onCreateSuccess,
  onUpdateSuccess,
  onDeleteSuccess,
  onError,
  queryParams = {},
  enabled = true,
}: UseCrudOptions<T>): UseCrudReturn<T> {
  const queryClient = useQueryClient();

  // Constrói query string
  const buildQueryString = () => {
    const params = new URLSearchParams();
    Object.entries(queryParams).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, String(value));
      }
    });
    const qs = params.toString();
    return qs ? `?${qs}` : '';
  };

  // Query de listagem
  const query = useQuery<ListResponse<T>>({
    queryKey: [queryKey, queryParams],
    queryFn: async () => {
      const response = await api.get(`${endpoint}/${buildQueryString()}`);
      return response.data;
    },
    enabled,
  });

  // Mutation de criação
  const createMutation = useMutation({
    mutationFn: async (data: Partial<T>) => {
      const response = await api.post(`${endpoint}/`, data);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: [queryKey] });
      onCreateSuccess?.(data);
    },
    onError,
  });

  // Mutation de atualização
  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: Partial<T> }) => {
      const response = await api.put(`${endpoint}/${id}`, data);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: [queryKey] });
      onUpdateSuccess?.(data);
    },
    onError,
  });

  // Mutation de deleção
  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`${endpoint}/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [queryKey] });
      onDeleteSuccess?.();
    },
    onError,
  });

  return {
    data: query.data,
    items: query.data?.items || [],
    total: query.data?.total || 0,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error,
    create: {
      mutate: createMutation.mutate,
      mutateAsync: createMutation.mutateAsync,
      isPending: createMutation.isPending,
    },
    update: {
      mutate: updateMutation.mutate,
      mutateAsync: updateMutation.mutateAsync,
      isPending: updateMutation.isPending,
    },
    remove: {
      mutate: deleteMutation.mutate,
      mutateAsync: deleteMutation.mutateAsync,
      isPending: deleteMutation.isPending,
    },
    refetch: query.refetch,
    invalidate: () => queryClient.invalidateQueries({ queryKey: [queryKey] }),
  };
}

/**
 * Hook para buscar um único item
 */
export function useCrudItem<T>(
  endpoint: string,
  queryKey: string,
  id: number | string | undefined
) {
  return useQuery<T>({
    queryKey: [queryKey, id],
    queryFn: async () => {
      const response = await api.get(`${endpoint}/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}
