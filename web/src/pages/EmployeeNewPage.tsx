import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useCreateEmployee } from "@/api/hooks";
import { EmployeeForm } from "@/components/EmployeeForm";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/** Create a new employee. */
export function EmployeeNewPage() {
  const navigate = useNavigate();
  const create = useCreateEmployee();

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <Button variant="ghost" onClick={() => navigate("/employees")}>
        <ArrowLeft className="h-4 w-4" /> Back to employees
      </Button>
      <Card>
        <CardHeader>
          <CardTitle>Add employee</CardTitle>
        </CardHeader>
        <CardContent>
          <EmployeeForm
            submitLabel="Create employee"
            submitting={create.isPending}
            errorMessage={create.error?.message}
            onSubmit={(values) =>
              create.mutate(values, { onSuccess: (employee) => navigate(`/employees/${employee.id}`) })
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}
