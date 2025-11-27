/**
 * Formatters - Funções de formatação reutilizáveis
 * Elimina duplicação de toLocaleString em todo o projeto
 */

/**
 * Formata valor para moeda brasileira (BRL)
 * @param value - Valor numérico
 * @returns String formatada (ex: "R$ 1.234,56")
 */
export function formatCurrency(value: number | undefined | null): string {
  if (value === undefined || value === null) return '-';
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

/**
 * Formata data para formato brasileiro
 * @param date - Data em string ISO ou objeto Date
 * @returns String formatada (ex: "21/11/2025")
 */
export function formatDate(date: string | Date | undefined | null): string {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('pt-BR');
}

/**
 * Formata data e hora para formato brasileiro
 * @param date - Data em string ISO ou objeto Date
 * @returns String formatada (ex: "21/11/2025 14:30")
 */
export function formatDateTime(date: string | Date | undefined | null): string {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Formata número com casas decimais
 * @param value - Valor numérico
 * @param decimals - Número de casas decimais (default: 2)
 * @returns String formatada (ex: "1.234,56")
 */
export function formatNumber(value: number | undefined | null, decimals: number = 2): string {
  if (value === undefined || value === null) return '-';
  return value.toLocaleString('pt-BR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Formata porcentagem
 * @param value - Valor numérico (ex: 15.5 para 15,50%)
 * @param decimals - Casas decimais (default: 2)
 * @returns String formatada (ex: "15,50%")
 */
export function formatPercent(value: number | undefined | null, decimals: number = 2): string {
  if (value === undefined || value === null) return '-';
  return `${value.toFixed(decimals).replace('.', ',')}%`;
}

/**
 * Formata CNPJ com máscara
 * @param cnpj - String com 14 dígitos
 * @returns String formatada (ex: "12.345.678/0001-90")
 */
export function formatCNPJ(cnpj: string | undefined | null): string {
  if (!cnpj) return '-';
  const cleaned = cnpj.replace(/\D/g, '');
  if (cleaned.length !== 14) return cnpj;
  return cleaned.replace(
    /^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/,
    '$1.$2.$3/$4-$5'
  );
}

/**
 * Formata CEP com máscara
 * @param cep - String com 8 dígitos
 * @returns String formatada (ex: "12345-678")
 */
export function formatCEP(cep: string | undefined | null): string {
  if (!cep) return '-';
  const cleaned = cep.replace(/\D/g, '');
  if (cleaned.length !== 8) return cep;
  return cleaned.replace(/^(\d{5})(\d{3})$/, '$1-$2');
}

/**
 * Formata telefone com máscara
 * @param phone - String com 10 ou 11 dígitos
 * @returns String formatada (ex: "(11) 98765-4321")
 */
export function formatPhone(phone: string | undefined | null): string {
  if (!phone) return '-';
  const cleaned = phone.replace(/\D/g, '');
  if (cleaned.length === 11) {
    return cleaned.replace(/^(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3');
  }
  if (cleaned.length === 10) {
    return cleaned.replace(/^(\d{2})(\d{4})(\d{4})$/, '($1) $2-$3');
  }
  return phone;
}

/**
 * Formata quantidade com unidade de medida
 * @param qty - Quantidade
 * @param unit - Unidade de medida
 * @returns String formatada (ex: "10 UN")
 */
export function formatQuantity(qty: number | undefined | null, unit: string = 'UN'): string {
  if (qty === undefined || qty === null) return '-';
  return `${formatNumber(qty)} ${unit}`;
}
