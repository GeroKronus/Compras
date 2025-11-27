import { useState, useEffect } from 'react';
import { authService } from '@/services/api';
import { Usuario, Tenant } from '@/types';

export function useAuth() {
  const [user, setUser] = useState<Usuario | null>(null);
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Carregar dados do localStorage na inicialização
    const storedUser = authService.getStoredUser();
    const storedTenant = authService.getStoredTenant();
    const isAuth = authService.isAuthenticated();

    if (storedUser && storedTenant && isAuth) {
      setUser(storedUser);
      setTenant(storedTenant);
      setIsAuthenticated(true);
    }

    setIsLoading(false);
  }, []);

  const logout = () => {
    authService.logout();
    setUser(null);
    setTenant(null);
    setIsAuthenticated(false);
  };

  return {
    user,
    tenant,
    isAuthenticated,
    isLoading,
    logout,
  };
}
