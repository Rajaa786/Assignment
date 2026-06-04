import { ArrowLeft, Trash2 } from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useDeleteEmployee, useEmployee, useUpdateEmployee } from "@/api/hooks";
import { EmployeeForm } from "@/components/EmployeeForm";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMoney } from "@/lib/format";

/** View and edit a single employee, with soft-delete. */
export function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const employeeId = Number(id);
  const navigate = useNavigate();
  const { data: employee, isLoading, error } = useEmployee(employeeId);
  const update = useUpdateEmployee(employeeId);
  const remove = useDeleteEmployee();
  const [editing, setEditing] = useState(false);

  if (isLoading) return <p className="text-muted-foreground">Loading…</p>;
  if (error || !employee) return <p className="text-destructive">{error?.message ?? "Not found."}</p>;

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <Button variant="ghost" onClick={() => navigate("/employees")}>
        <ArrowLeft className="h-4 w-4" /> Back to employees
      </Button>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>
              {employee.first_name} {employee.last_name}
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              {employee.employee_code} · {employee.job_title}
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setEditing((value) => !value)}>
              {editing ? "Cancel" : "Edit"}
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (confirm("Soft-delete this employee?")) {
                  remove.mutate(employeeId, { onSuccess: () => navigate("/employees") });
                }
              }}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {editing ? (
            <EmployeeForm
              submitLabel="Save changes"
              submitting={update.isPending}
              errorMessage={update.error?.message}
              defaultValues={{
                first_name: employee.first_name,
                last_name: employee.last_name,
                email: employee.email,
                department: employee.department,
                job_title: employee.job_title,
                level: employee.level,
                employment_type: employee.employment_type,
                country: employee.country,
                base_salary_amount: employee.base_salary.amount,
                hire_date: employee.hire_date,
              }}
              onSubmit={(values) => update.mutate(values, { onSuccess: () => setEditing(false) })}
            />
          ) : (
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <Detail label="Department" value={employee.department} />
              <Detail label="Level" value={employee.level} />
              <Detail label="Country" value={employee.country_name} />
              <Detail label="Employment" value={employee.employment_type} />
              <Detail label="Email" value={employee.email} />
              <Detail label="Hire date" value={employee.hire_date} />
              <Detail label="Salary (local)" value={formatMoney(employee.base_salary)} />
              <Detail label="Salary (USD)" value={formatMoney(employee.base_salary_usd)} />
            </dl>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}
