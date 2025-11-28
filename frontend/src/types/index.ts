// Tipos base do sistema

export interface Usuario {
  id: number;
  tenant_id: number;
  nome_completo: string;
  email: string;
  tipo: 'MASTER' | 'ADMIN' | 'GERENTE' | 'COMPRADOR' | 'ALMOXARIFE' | 'VISUALIZADOR';
  ativo: boolean;
  telefone?: string;
  setor?: string;
  created_at: string;
  updated_at: string;
}

export interface TenantListItem {
  id: number;
  nome_empresa: string;
  razao_social: string;
  cnpj: string;
  slug: string;
  ativo: boolean;
  plano: 'trial' | 'basic' | 'pro' | 'enterprise';
  ia_habilitada: boolean;
  email_contato: string;
  telefone?: string;
  total_usuarios: number;
  created_at: string;
}

export interface CreateTenantRequest {
  nome_empresa: string;
  razao_social: string;
  cnpj: string;
  email_contato: string;
  telefone?: string;
  plano: 'trial' | 'basic' | 'pro' | 'enterprise';
  admin_nome: string;
  admin_email: string;
  admin_senha: string;
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
