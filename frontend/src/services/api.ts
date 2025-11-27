import axios, { AxiosError } from 'axios';
import { LoginRequest, LoginResponse } from '@/types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Instância do Axios
export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para adicionar token em todas as requisições
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para tratar erros
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expirado ou inválido
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      localStorage.removeItem('tenant');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Serviços de autenticação
export const authService = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const { data } = await api.post<LoginResponse>('/auth/login', credentials);
    // Salvar token e dados do usuário
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    localStorage.setItem('tenant', JSON.stringify(data.tenant));
    return data;
  },

  logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('tenant');
  },

  getStoredUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  getStoredTenant() {
    const tenantStr = localStorage.getItem('tenant');
    return tenantStr ? JSON.parse(tenantStr) : null;
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('token');
  },
};

// Serviços de tenant
export const tenantService = {
  async getMyTenant() {
    const { data } = await api.get('/tenants/me');
    return data;
  },

  async getStats() {
    const { data } = await api.get('/tenants/stats');
    return data;
  },
};
