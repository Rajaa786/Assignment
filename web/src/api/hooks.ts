import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type UseInfiniteQueryResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import { API_BASE, ApiError, apiFetch, buildQuery } from "@/api/client";
import type {
  ByDimensionResponse,
  Dimension,
  DistributionResponse,
  Employee,
  EmployeeCreate,
  EmployeeUpdate,
  ImportResult,
  Page,
  PayEquityResponse,
  QueryAnswer,
  SummaryResponse,
} from "@/api/types";

/** Filters and sort options for the employee list. */
export interface EmployeeListParams {
  q?: string;
  department?: string;
  country?: string;
  level?: string;
  salary_usd_min?: string;
  salary_usd_max?: string;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  limit?: number;
}

const keys = {
  employees: (params: EmployeeListParams) => ["employees", params] as const,
  employee: (id: number) => ["employee", id] as const,
  analytics: (name: string, dimension?: Dimension) => ["analytics", name, dimension] as const,
};

/**
 * Fetch the paginated employee list for the given filters.
 *
 * Uses an infinite query keyed on the cursor so "load more" appends pages without
 * refetching earlier ones. Server state is cached for 30s.
 */
export function useEmployees(
  params: EmployeeListParams,
): UseInfiniteQueryResult<{ pages: Page<Employee>[] }, ApiError> {
  return useInfiniteQuery({
    queryKey: keys.employees(params),
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) =>
      apiFetch<Page<Employee>>(
        `/employees${buildQuery({ ...params, cursor: pageParam })}`,
      ),
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  });
}

/** Fetch a single employee by id. */
export function useEmployee(id: number): UseQueryResult<Employee, ApiError> {
  return useQuery({
    queryKey: keys.employee(id),
    queryFn: () => apiFetch<Employee>(`/employees/${id}`),
  });
}

function useInvalidateEmployees(): () => void {
  const client = useQueryClient();
  return () => {
    void client.invalidateQueries({ queryKey: ["employees"] });
    void client.invalidateQueries({ queryKey: ["analytics"] });
  };
}

/** Create an employee, then refresh lists and analytics. */
export function useCreateEmployee() {
  const invalidate = useInvalidateEmployees();
  return useMutation({
    mutationFn: (payload: EmployeeCreate) =>
      apiFetch<Employee>("/employees", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: invalidate,
  });
}

/** Update an employee, then refresh lists and analytics. */
export function useUpdateEmployee(id: number) {
  const invalidate = useInvalidateEmployees();
  return useMutation({
    mutationFn: (payload: EmployeeUpdate) =>
      apiFetch<Employee>(`/employees/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
    onSuccess: invalidate,
  });
}

/** Soft-delete an employee, then refresh lists and analytics. */
export function useDeleteEmployee() {
  const invalidate = useInvalidateEmployees();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/employees/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
}

export function useSummary(): UseQueryResult<SummaryResponse, ApiError> {
  return useQuery({
    queryKey: keys.analytics("summary"),
    queryFn: () => apiFetch<SummaryResponse>("/analytics/summary"),
  });
}

export function useByDimension(dimension: Dimension): UseQueryResult<ByDimensionResponse, ApiError> {
  return useQuery({
    queryKey: keys.analytics("by-dimension", dimension),
    queryFn: () => apiFetch<ByDimensionResponse>(`/analytics/by-dimension?dimension=${dimension}`),
  });
}

export function useDistribution(): UseQueryResult<DistributionResponse, ApiError> {
  return useQuery({
    queryKey: keys.analytics("distribution"),
    queryFn: () => apiFetch<DistributionResponse>("/analytics/distribution"),
  });
}

export function usePayEquity(dimension: Dimension): UseQueryResult<PayEquityResponse, ApiError> {
  return useQuery({
    queryKey: keys.analytics("pay-equity", dimension),
    queryFn: () => apiFetch<PayEquityResponse>(`/analytics/pay-equity?dimension=${dimension}`),
  });
}

/** Ask a natural-language question about pay. */
export function useAsk() {
  return useMutation<QueryAnswer, ApiError, string>({
    mutationFn: (question: string) =>
      apiFetch<QueryAnswer>("/ask", { method: "POST", body: JSON.stringify({ question }) }),
  });
}

/** Upload a CSV for import (optionally a dry-run preview). */
export function useImportCsv() {
  const invalidate = useInvalidateEmployees();
  return useMutation<ImportResult, ApiError, { file: File; dryRun: boolean }>({
    mutationFn: async ({ file, dryRun }) => {
      const form = new FormData();
      form.append("file", file);
      const response = await fetch(`${API_BASE}/imports/employees?dry_run=${dryRun}`, {
        method: "POST",
        body: form,
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as
          | { error?: { code?: string; message?: string } }
          | null;
        throw new ApiError(
          response.status,
          body?.error?.code ?? "unknown",
          body?.error?.message ?? response.statusText,
        );
      }
      return (await response.json()) as ImportResult;
    },
    onSuccess: (result) => {
      if (!result.dry_run) invalidate();
    },
  });
}
