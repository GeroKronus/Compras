/**
 * Modal - Componente de modal reutilizável
 * Elimina duplicação de estrutura de modal em todas as páginas
 */
import { XMarkIcon } from '@heroicons/react/24/outline';

type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl' | '5xl' | 'full';
type SubmitColor = 'primary' | 'green' | 'red' | 'blue';

interface ModalProps {
  /** Se o modal está aberto */
  isOpen: boolean;
  /** Título do modal */
  title: string;
  /** Subtítulo opcional */
  subtitle?: string;
  /** Callback ao fechar */
  onClose: () => void;
  /** Callback ao submeter (se não informado, não mostra botões de ação) */
  onSubmit?: () => void;
  /** Texto do botão de submit (default: "Confirmar") */
  submitLabel?: string;
  /** Botão submit desabilitado */
  submitDisabled?: boolean;
  /** Botão submit em loading */
  submitLoading?: boolean;
  /** Cor do botão submit */
  submitColor?: SubmitColor;
  /** Texto do botão cancelar (default: "Cancelar") */
  cancelLabel?: string;
  /** Tamanho do modal */
  size?: ModalSize;
  /** Mostrar botão X no header */
  showCloseButton?: boolean;
  /** Conteúdo do modal */
  children: React.ReactNode;
  /** Footer customizado (substitui os botões padrão) */
  footer?: React.ReactNode;
}

const sizeClasses: Record<ModalSize, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
  '3xl': 'max-w-3xl',
  '4xl': 'max-w-4xl',
  '5xl': 'max-w-5xl',
  full: 'max-w-full mx-4',
};

const colorClasses: Record<SubmitColor, string> = {
  primary: 'bg-primary-600 hover:bg-primary-700',
  green: 'bg-green-600 hover:bg-green-700',
  red: 'bg-red-600 hover:bg-red-700',
  blue: 'bg-blue-600 hover:bg-blue-700',
};

export function Modal({
  isOpen,
  title,
  subtitle,
  onClose,
  onSubmit,
  submitLabel = 'Confirmar',
  submitDisabled = false,
  submitLoading = false,
  submitColor = 'primary',
  cancelLabel = 'Cancelar',
  size = 'lg',
  showCloseButton = true,
  children,
  footer,
}: ModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
      <div
        className={`bg-white rounded-lg shadow-xl ${sizeClasses[size]} w-full max-h-[90vh] overflow-hidden flex flex-col`}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-start">
          <div>
            <h3 className="text-lg font-medium text-gray-900">{title}</h3>
            {subtitle && (
              <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
            )}
          </div>
          {showCloseButton && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500 transition-colors"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto flex-1">{children}</div>

        {/* Footer */}
        {(footer || onSubmit) && (
          <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
            {footer || (
              <>
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  {cancelLabel}
                </button>
                <button
                  onClick={onSubmit}
                  disabled={submitDisabled || submitLoading}
                  className={`px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${colorClasses[submitColor]} disabled:opacity-50`}
                >
                  {submitLoading ? 'Processando...' : submitLabel}
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * ConfirmModal - Modal de confirmação simplificado
 */
interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmLabel?: string;
  cancelLabel?: string;
  isDangerous?: boolean;
  isLoading?: boolean;
}

export function ConfirmModal({
  isOpen,
  title,
  message,
  onConfirm,
  onCancel,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  isDangerous = false,
  isLoading = false,
}: ConfirmModalProps) {
  return (
    <Modal
      isOpen={isOpen}
      title={title}
      onClose={onCancel}
      onSubmit={onConfirm}
      submitLabel={confirmLabel}
      cancelLabel={cancelLabel}
      submitColor={isDangerous ? 'red' : 'primary'}
      submitLoading={isLoading}
      size="sm"
      showCloseButton={false}
    >
      <p className="text-sm text-gray-600">{message}</p>
      {isDangerous && (
        <p className="mt-2 text-sm text-red-600">
          Esta ação não pode ser desfeita.
        </p>
      )}
    </Modal>
  );
}

/**
 * ViewModal - Modal apenas para visualização (sem botões de ação)
 */
interface ViewModalProps {
  isOpen: boolean;
  title: string;
  subtitle?: string;
  onClose: () => void;
  size?: ModalSize;
  children: React.ReactNode;
}

export function ViewModal({
  isOpen,
  title,
  subtitle,
  onClose,
  size = '2xl',
  children,
}: ViewModalProps) {
  return (
    <Modal
      isOpen={isOpen}
      title={title}
      subtitle={subtitle}
      onClose={onClose}
      size={size}
      footer={<></>}
    >
      {children}
    </Modal>
  );
}
