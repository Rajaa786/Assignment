import { describe, expect, it } from "vitest";

import { formatMoney, formatSignedPercent } from "@/lib/format";

describe("formatMoney", () => {
  it("renders USD with a dollar sign and cents", () => {
    const formatted = formatMoney({ amount: "95000", currency: "USD", minor_units: 9_500_000 });
    expect(formatted).toContain("$");
    expect(formatted).toContain("95,000");
  });

  it("renders a zero-decimal currency without a decimal point", () => {
    const formatted = formatMoney({ amount: "6500000", currency: "JPY", minor_units: 6_500_000 });
    expect(formatted).toContain("¥");
    expect(formatted).not.toContain(".");
  });
});

describe("formatSignedPercent", () => {
  it("prefixes a plus sign for positive gaps", () => {
    expect(formatSignedPercent(12.5)).toBe("+12.5%");
  });

  it("keeps the minus sign for negative gaps", () => {
    expect(formatSignedPercent(-3)).toBe("-3.0%");
  });

  it("shows zero without a sign", () => {
    expect(formatSignedPercent(0)).toBe("0.0%");
  });
});
