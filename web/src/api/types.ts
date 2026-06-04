// Transport types mirroring the backend Pydantic schemas. Kept hand-written and small
// rather than generated, so the contract is readable in one place.

export interface Money {
  amount: string; // exact decimal, serialized as a string
  currency: string;
  minor_units: number;
}

export interface Employee {
  id: number;
  employee_code: string;
  first_name: string;
  last_name: string;
  email: string;
  department: string;
  job_title: string;
  level: string;
  employment_type: string;
  country: string;
  country_name: string;
  base_salary: Money;
  base_salary_usd: Money;
  hire_date: string;
  created_at: string;
  updated_at: string;
}

export interface Page<T> {
  items: T[];
  next_cursor: string | null;
  total: number;
}

export interface EmployeeCreate {
  first_name: string;
  last_name: string;
  email: string;
  department: string;
  job_title: string;
  level: string;
  employment_type: string;
  country: string;
  base_salary_amount: string;
  hire_date: string;
}

export type EmployeeUpdate = Partial<EmployeeCreate>;

export type Dimension = "department" | "country" | "level";

export interface SummaryResponse {
  headcount: number;
  total_payroll_usd: Money;
  average_salary_usd: Money;
  median_salary_usd: Money;
}

export interface DimensionStat {
  key: string;
  count: number;
  average_usd: Money;
  median_usd: Money;
  min_usd: Money;
  max_usd: Money;
  total_usd: Money;
}

export interface ByDimensionResponse {
  dimension: Dimension;
  groups: DimensionStat[];
}

export interface DistributionBucket {
  lower_usd: number;
  upper_usd: number | null;
  count: number;
}

export interface DistributionResponse {
  buckets: DistributionBucket[];
}

export interface PayEquityGroup {
  key: string;
  count: number;
  median_usd: Money;
  min_usd: Money;
  max_usd: Money;
  gap_vs_overall_pct: number;
}

export interface PayEquityResponse {
  dimension: Dimension;
  overall_median_usd: Money;
  groups: PayEquityGroup[];
}

export interface ImportRowError {
  row_number: number;
  field: string | null;
  message: string;
}

export interface ImportResult {
  total: number;
  valid: number;
  failed: number;
  inserted: number;
  dry_run: boolean;
  errors: ImportRowError[];
}

export interface QueryAnswer {
  question: string;
  sql: string;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  truncated: boolean;
}

export interface ApiErrorBody {
  error: { code: string; message: string; details: Record<string, unknown> };
}
