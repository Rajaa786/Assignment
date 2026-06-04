import { Download, Plus, Search } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useEmployees, type EmployeeListParams } from "@/api/hooks";
import { buildQuery } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatCount, formatMoney } from "@/lib/format";
import { COUNTRIES, DEPARTMENTS, LEVELS } from "@/lib/reference";
import { useDebouncedValue } from "@/lib/useDebouncedValue";

const SORTS: { value: string; label: string }[] = [
  { value: "id", label: "Newest" },
  { value: "name", label: "Name" },
  { value: "salary", label: "Salary (USD)" },
  { value: "hire_date", label: "Hire date" },
];

/** Server-paginated, filterable, sortable employee directory. */
export function EmployeesPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [country, setCountry] = useState("");
  const [level, setLevel] = useState("");
  const [sortBy, setSortBy] = useState("id");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const debouncedSearch = useDebouncedValue(search);
  const params: EmployeeListParams = {
    q: debouncedSearch || undefined,
    department: department || undefined,
    country: country || undefined,
    level: level || undefined,
    sort_by: sortBy,
    sort_dir: sortDir,
    limit: 25,
  };

  const query = useEmployees(params);
  const employees = query.data?.pages.flatMap((page) => page.items) ?? [];
  const total = query.data?.pages[0]?.total ?? 0;

  const exportHref = `/api/v1/employees/export${buildQuery({
    q: params.q,
    department: params.department,
    country: params.country,
    level: params.level,
  })}`;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Employees</h1>
        <div className="flex gap-2">
          <a href={exportHref}>
            <Button variant="outline">
              <Download className="h-4 w-4" /> Export CSV
            </Button>
          </a>
          <Button onClick={() => navigate("/employees/new")}>
            <Plus className="h-4 w-4" /> Add employee
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-end gap-3 p-4">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="Search name, email, or code"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Search employees"
            />
          </div>
          <Select value={department} onChange={(event) => setDepartment(event.target.value)} className="w-44" aria-label="Filter by department">
            <option value="">All departments</option>
            {DEPARTMENTS.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </Select>
          <Select value={country} onChange={(event) => setCountry(event.target.value)} className="w-40" aria-label="Filter by country">
            <option value="">All countries</option>
            {COUNTRIES.map(({ code, name }) => (
              <option key={code} value={code}>
                {name}
              </option>
            ))}
          </Select>
          <Select value={level} onChange={(event) => setLevel(event.target.value)} className="w-28" aria-label="Filter by level">
            <option value="">All levels</option>
            {LEVELS.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </Select>
          <Select value={sortBy} onChange={(event) => setSortBy(event.target.value)} className="w-36" aria-label="Sort by">
            {SORTS.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
          <Button
            variant="outline"
            onClick={() => setSortDir((dir) => (dir === "asc" ? "desc" : "asc"))}
            aria-label="Toggle sort direction"
          >
            {sortDir === "asc" ? "↑ Asc" : "↓ Desc"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Level</TableHead>
                <TableHead>Country</TableHead>
                <TableHead className="text-right">Salary (local)</TableHead>
                <TableHead className="text-right">Salary (USD)</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {employees.map((employee) => (
                <TableRow
                  key={employee.id}
                  className="cursor-pointer"
                  onClick={() => navigate(`/employees/${employee.id}`)}
                >
                  <TableCell className="font-mono text-xs">{employee.employee_code}</TableCell>
                  <TableCell className="font-medium">
                    {employee.first_name} {employee.last_name}
                    <div className="text-xs text-muted-foreground">{employee.email}</div>
                  </TableCell>
                  <TableCell>{employee.department}</TableCell>
                  <TableCell>{employee.level}</TableCell>
                  <TableCell>{employee.country_name}</TableCell>
                  <TableCell className="text-right">{formatMoney(employee.base_salary)}</TableCell>
                  <TableCell className="text-right font-medium">{formatMoney(employee.base_salary_usd)}</TableCell>
                </TableRow>
              ))}
              {query.isLoading && (
                <TableRow>
                  <TableCell colSpan={7} className="py-10 text-center text-muted-foreground">
                    Loading…
                  </TableCell>
                </TableRow>
              )}
              {!query.isLoading && employees.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="py-10 text-center text-muted-foreground">
                    No employees match these filters.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Showing {formatCount(employees.length)} of {formatCount(total)}
        </span>
        {query.hasNextPage && (
          <Button variant="outline" onClick={() => void query.fetchNextPage()} disabled={query.isFetchingNextPage}>
            {query.isFetchingNextPage ? "Loading…" : "Load more"}
          </Button>
        )}
      </div>
    </div>
  );
}
