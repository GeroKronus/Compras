/**
 * PageLayout - Layout padrão para páginas do sistema
 * Elimina duplicação de estrutura header + main em todas as páginas
 */
import { useNavigate } from 'react-router-dom';
import { Button } from './ui/button';
import { useAuth } from '../hooks/useAuth';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';

interface PageLayoutProps {
  /** Título principal da página */
  title: string;
  /** Subtítulo opcional (se não informado, usa nome da empresa) */
  subtitle?: string;
  /** Mostrar botão de voltar (default: true) */
  showBackButton?: boolean;
  /** URL de destino do botão voltar (default: /dashboard) */
  backUrl?: string;
  /** Texto do botão voltar (default: "Voltar") */
  backText?: string;
  /** Ações adicionais no header (botões, etc.) */
  headerActions?: React.ReactNode;
  /** Conteúdo da página */
  children: React.ReactNode;
  /** Classes adicionais para o main */
  mainClassName?: string;
}

export function PageLayout({
  title,
  subtitle,
  showBackButton = true,
  backUrl = '/dashboard',
  backText = 'Voltar',
  headerActions,
  children,
  mainClassName = '',
}: PageLayoutProps) {
  const navigate = useNavigate();
  const { tenant } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-primary">{title}</h1>
            <p className="text-sm text-muted-foreground">
              {subtitle || tenant?.nome_empresa}
            </p>
          </div>
          <div className="flex gap-2 items-center">
            {headerActions}
            {showBackButton && (
              <Button onClick={() => navigate(backUrl)} variant="outline">
                <ArrowLeftIcon className="h-4 w-4 mr-2" />
                {backText}
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className={`container mx-auto px-4 py-8 ${mainClassName}`}>
        {children}
      </main>
    </div>
  );
}

/**
 * PageSection - Seção dentro de uma página
 */
interface PageSectionProps {
  title?: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function PageSection({
  title,
  description,
  actions,
  children,
  className = '',
}: PageSectionProps) {
  return (
    <div className={`space-y-4 ${className}`}>
      {(title || actions) && (
        <div className="flex justify-between items-center">
          <div>
            {title && <h2 className="text-lg font-semibold">{title}</h2>}
            {description && (
              <p className="text-sm text-muted-foreground">{description}</p>
            )}
          </div>
          {actions && <div className="flex gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
}
