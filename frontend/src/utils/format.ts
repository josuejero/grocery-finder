export function formatCurrency(value: number, locale: string = "en-US", currency: string = "USD"): string {
  return new Intl.NumberFormat(locale, { style: "currency", currency }).format(value);
}

export function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
}
