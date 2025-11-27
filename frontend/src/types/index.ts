// Tipos base do sistema

export interface Usuario {
  id: number;
  tenant_id: number;
  nome_completo: string;
  email: string;
  tipo: 'admin' | 'gerente' | 'comprador' | 'almoxarife' | 'visualizador';
  ativo: boolean;
  telefone?: string;
  setor?: string;
  created_at: string;
  updated_at: string;
}

export interface Tenant {
  id: number;
  nome_empresa: string;
  razao_social: string;
  cnpj: string;
  slug: string;
  ativo: boolean;
  plano: 'trial' | 'basic' | 'pro' | 'enterprise';
  ia_habilitada: boolean;
  ia_auto_aprovacao?: boolean;
  email_contato: string;
  telefone?: string;
}

export interface LoginRequest {
  email: string;
  senha: string;
  cnpj: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: Usuario;
  tenant: Tenant;
}

export interface ApiError {
  detail: string;
}
