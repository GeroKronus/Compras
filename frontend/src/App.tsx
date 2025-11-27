import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import Login from '@/pages/auth/Login';
import Dashboard from '@/pages/Dashboard';
import { Categorias } from '@/pages/Categorias';
import { Produtos } from '@/pages/Produtos';
import { Fornecedores } from '@/pages/Fornecedores';
import Cotacoes from '@/pages/Cotacoes';
import Propostas from '@/pages/Propostas';
import MapaComparativo from '@/pages/MapaComparativo';
import Pedidos from '@/pages/Pedidos';
import EmailsRevisao from '@/pages/EmailsRevisao';
import IACreditos from '@/pages/IACreditos';

// Criar cliente do React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Componente para proteger rotas
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Carregando...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/categorias"
            element={
              <ProtectedRoute>
                <Categorias />
              </ProtectedRoute>
            }
          />
          <Route
            path="/produtos"
            element={
              <ProtectedRoute>
                <Produtos />
              </ProtectedRoute>
            }
          />
          <Route
            path="/fornecedores"
            element={
              <ProtectedRoute>
                <Fornecedores />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cotacoes"
            element={
              <ProtectedRoute>
                <Cotacoes />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cotacoes/:solicitacaoId/propostas"
            element={
              <ProtectedRoute>
                <Propostas />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cotacoes/:solicitacaoId/mapa"
            element={
              <ProtectedRoute>
                <MapaComparativo />
              </ProtectedRoute>
            }
          />
          <Route
            path="/pedidos"
            element={
              <ProtectedRoute>
                <Pedidos />
              </ProtectedRoute>
            }
          />
          <Route
            path="/emails"
            element={
              <ProtectedRoute>
                <EmailsRevisao />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ia-creditos"
            element={
              <ProtectedRoute>
                <IACreditos />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
