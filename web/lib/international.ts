import type { LocaleCode } from "./types";

/** Locale-aware currency presentation only; this never performs conversion. */
export function currencyDisplayToken(currency: string, locale: LocaleCode): string {
  const code = currency.trim().toUpperCase();
  if (!/^[A-Z]{3}$/.test(code)) return currency;
  try {
    const parts = new Intl.NumberFormat(locale, {
      style: "currency",
      currency: code,
      currencyDisplay: "narrowSymbol",
      maximumFractionDigits: 0,
    }).formatToParts(0);
    return parts.find((part) => part.type === "currency")?.value || code;
  } catch {
    return code;
  }
}

/** Institution-local display helper. Analytics/cohort timestamps stay UTC. */
export function formatInstitutionDate(
  value: Date | string | number,
  locale: LocaleCode,
  timezone: string,
): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: timezone }).format(new Date(value));
}
