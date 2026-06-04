// Categorical vocabularies mirroring the backend enums. Small and stable, so kept
// client-side to populate filters and form selects without an extra round-trip.

export const DEPARTMENTS = [
  "Engineering",
  "Product",
  "Sales",
  "Marketing",
  "Finance",
  "Human Resources",
  "Support",
  "Operations",
] as const;

export const LEVELS = ["L1", "L2", "L3", "L4", "L5", "L6", "L7"] as const;

export const EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Contract"] as const;

export const COUNTRIES: { code: string; name: string }[] = [
  { code: "US", name: "United States" },
  { code: "GB", name: "United Kingdom" },
  { code: "DE", name: "Germany" },
  { code: "FR", name: "France" },
  { code: "IN", name: "India" },
  { code: "JP", name: "Japan" },
  { code: "CA", name: "Canada" },
  { code: "AU", name: "Australia" },
  { code: "SG", name: "Singapore" },
  { code: "BR", name: "Brazil" },
  { code: "AE", name: "United Arab Emirates" },
  { code: "ZA", name: "South Africa" },
];
