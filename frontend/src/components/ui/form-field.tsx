/**
 * FormField - Componente reutilizável para campos de formulário
 * Elimina duplicação de estrutura label+input em todos os formulários
 */
import { forwardRef, InputHTMLAttributes, TextareaHTMLAttributes, SelectHTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

// Estilo base do input (DRY - usado em todos os campos)
const inputBaseClass = "w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary/50";

interface BaseFieldProps {
  /** Label do campo */
  label?: string;
  /** Campo obrigatório */
  required?: boolean;
  /** Texto de ajuda abaixo do campo */
  helper?: string;
  /** Mensagem de erro */
  error?: string;
  /** Classes CSS adicionais para o container */
  containerClassName?: string;
}

// ============ INPUT ============
interface FormInputProps extends BaseFieldProps, Omit<InputHTMLAttributes<HTMLInputElement>, 'className'> {
  inputClassName?: string;
}

export const FormInput = forwardRef<HTMLInputElement, FormInputProps>(
  ({ label, required, helper, error, containerClassName, inputClassName, ...props }, ref) => {
    return (
      <div className={cn("space-y-1", containerClassName)}>
        {label && (
          <label className="block text-sm font-medium mb-1">
            {label} {required && <span className="text-red-500">*</span>}
          </label>
        )}
        <input
          ref={ref}
          required={required}
          className={cn(inputBaseClass, error && "border-red-500", inputClassName)}
          {...props}
        />
        {helper && !error && (
          <p className="text-xs text-gray-500">{helper}</p>
        )}
        {error && (
          <p className="text-xs text-red-500">{error}</p>
        )}
      </div>
    );
  }
);
FormInput.displayName = 'FormInput';

// ============ TEXTAREA ============
interface FormTextareaProps extends BaseFieldProps, Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'className'> {
  textareaClassName?: string;
}

export const FormTextarea = forwardRef<HTMLTextAreaElement, FormTextareaProps>(
  ({ label, required, helper, error, containerClassName, textareaClassName, ...props }, ref) => {
    return (
      <div className={cn("space-y-1", containerClassName)}>
        {label && (
          <label className="block text-sm font-medium mb-1">
            {label} {required && <span className="text-red-500">*</span>}
          </label>
        )}
        <textarea
          ref={ref}
          required={required}
          className={cn(inputBaseClass, error && "border-red-500", textareaClassName)}
          {...props}
        />
        {helper && !error && (
          <p className="text-xs text-gray-500">{helper}</p>
        )}
        {error && (
          <p className="text-xs text-red-500">{error}</p>
        )}
      </div>
    );
  }
);
FormTextarea.displayName = 'FormTextarea';

// ============ SELECT ============
interface FormSelectProps extends BaseFieldProps, Omit<SelectHTMLAttributes<HTMLSelectElement>, 'className'> {
  selectClassName?: string;
  options: Array<{ value: string | number; label: string }>;
  placeholder?: string;
}

export const FormSelect = forwardRef<HTMLSelectElement, FormSelectProps>(
  ({ label, required, helper, error, containerClassName, selectClassName, options, placeholder, ...props }, ref) => {
    return (
      <div className={cn("space-y-1", containerClassName)}>
        {label && (
          <label className="block text-sm font-medium mb-1">
            {label} {required && <span className="text-red-500">*</span>}
          </label>
        )}
        <select
          ref={ref}
          required={required}
          className={cn(inputBaseClass, error && "border-red-500", selectClassName)}
          {...props}
        >
          {placeholder && <option value="">{placeholder}</option>}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {helper && !error && (
          <p className="text-xs text-gray-500">{helper}</p>
        )}
        {error && (
          <p className="text-xs text-red-500">{error}</p>
        )}
      </div>
    );
  }
);
FormSelect.displayName = 'FormSelect';

// ============ CHECKBOX ============
interface FormCheckboxProps extends BaseFieldProps, Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'className'> {
  checkboxClassName?: string;
}

export const FormCheckbox = forwardRef<HTMLInputElement, FormCheckboxProps>(
  ({ label, helper, error, containerClassName, checkboxClassName, ...props }, ref) => {
    return (
      <div className={cn("space-y-1", containerClassName)}>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            ref={ref}
            type="checkbox"
            className={cn("rounded border-gray-300", checkboxClassName)}
            {...props}
          />
          {label && <span className="text-sm font-medium">{label}</span>}
        </label>
        {helper && !error && (
          <p className="text-xs text-gray-500">{helper}</p>
        )}
        {error && (
          <p className="text-xs text-red-500">{error}</p>
        )}
      </div>
    );
  }
);
FormCheckbox.displayName = 'FormCheckbox';

// ============ FORM ROW (para layouts grid) ============
interface FormRowProps {
  children: React.ReactNode;
  cols?: 1 | 2 | 3 | 4;
  className?: string;
}

export function FormRow({ children, cols = 2, className }: FormRowProps) {
  const gridCols = {
    1: 'grid-cols-1',
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
  };

  return (
    <div className={cn("grid gap-4", gridCols[cols], className)}>
      {children}
    </div>
  );
}

// ============ FORM ACTIONS ============
interface FormActionsProps {
  children: React.ReactNode;
  className?: string;
}

export function FormActions({ children, className }: FormActionsProps) {
  return (
    <div className={cn("flex gap-2 pt-4", className)}>
      {children}
    </div>
  );
}
