/**
 * Formata um valor numérico para exibição como moeda (R$).
 * 
 * - Valores >= 1 bilhão: exibe em bilhões (Bi) com 1-2 casas decimais
 * - Valores >= 1 milhão: exibe em milhões (Mi) com 1-2 casas decimais
 * - Valores >= 1 mil: exibe em milhares (mil) com 1-2 casas decimais
 * - Valores < 1 mil: exibe o valor completo com 2 casas decimais
 */
export function formatCurrency(value: number | undefined | null): string {
  if (value === undefined || value === null || isNaN(value)) return "--"
  
  if (value >= 1000000000) {
    return `R$ ${(value / 1000000000).toLocaleString('pt-BR', { maximumFractionDigits: 2, minimumFractionDigits: 1 })} Bi`
  }
  if (value >= 1000000) {
    return `R$ ${(value / 1000000).toLocaleString('pt-BR', { maximumFractionDigits: 2, minimumFractionDigits: 1 })} Mi`
  }
  if (value >= 1000) {
    return `R$ ${(value / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 2, minimumFractionDigits: 1 })} mil`
  }
  return `R$ ${value.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
}
