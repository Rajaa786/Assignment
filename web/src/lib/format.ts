import type { Money } from "@/api/types";

/**
 * Format a {@link Money} value for display using the browser's locale rules.
 *
 * Uses `Intl.NumberFormat` with the money's own currency so amounts render with the
 * right symbol and decimal places (e.g. `$95,000.00`, `¥6,500,000`).
 */
export function formatMoney(money: Money): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: money.currency,
    maximumFractionDigits: 2,
  }).format(Number(money.amount));
}

/** Format an integer count with locale grouping (e.g. `10,000`). */
export function formatCount(value: number): string {
  return new Intl.NumberFormat().format(value);
}

/** Format a signed percentage with one decimal (e.g. `+12.5%`, `-3.0%`). */
export function formatSignedPercent(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}
