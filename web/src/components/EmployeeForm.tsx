import { zodResolver } from "@hookform/resolvers/zod";
import type { ReactNode } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { COUNTRIES, DEPARTMENTS, EMPLOYMENT_TYPES, LEVELS } from "@/lib/reference";

const schema = z.object({
  first_name: z.string().min(1, "Required"),
  last_name: z.string().min(1, "Required"),
  email: z.string().regex(/^[^@\s]+@[^@\s]+\.[^@\s]+$/, "Enter a valid email"),
  department: z.string().min(1),
  job_title: z.string().min(1, "Required"),
  level: z.string().min(1),
  employment_type: z.string().min(1),
  country: z.string().length(2),
  base_salary_amount: z.string().regex(/^\d+(\.\d{1,2})?$/, "Enter an amount, e.g. 95000"),
  hire_date: z.string().min(1, "Required"),
});

export type EmployeeFormValues = z.infer<typeof schema>;

interface EmployeeFormProps {
  defaultValues?: Partial<EmployeeFormValues>;
  onSubmit: (values: EmployeeFormValues) => void;
  submitting: boolean;
  submitLabel: string;
  errorMessage?: string;
}

const BLANK: EmployeeFormValues = {
  first_name: "",
  last_name: "",
  email: "",
  department: DEPARTMENTS[0],
  job_title: "",
  level: LEVELS[0],
  employment_type: EMPLOYMENT_TYPES[0],
  country: "US",
  base_salary_amount: "",
  hire_date: "",
};

/** Create/edit form for an employee, validated with zod. */
export function EmployeeForm({
  defaultValues,
  onSubmit,
  submitting,
  submitLabel,
  errorMessage,
}: EmployeeFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<EmployeeFormValues>({
    resolver: zodResolver(schema),
    defaultValues: { ...BLANK, ...defaultValues },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="First name" error={errors.first_name?.message}>
          <Input {...register("first_name")} />
        </Field>
        <Field label="Last name" error={errors.last_name?.message}>
          <Input {...register("last_name")} />
        </Field>
        <Field label="Email" error={errors.email?.message}>
          <Input type="email" {...register("email")} />
        </Field>
        <Field label="Job title" error={errors.job_title?.message}>
          <Input {...register("job_title")} />
        </Field>
        <Field label="Department">
          <Select {...register("department")}>
            {DEPARTMENTS.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </Select>
        </Field>
        <Field label="Level">
          <Select {...register("level")}>
            {LEVELS.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </Select>
        </Field>
        <Field label="Employment type">
          <Select {...register("employment_type")}>
            {EMPLOYMENT_TYPES.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </Select>
        </Field>
        <Field label="Country">
          <Select {...register("country")}>
            {COUNTRIES.map(({ code, name }) => (
              <option key={code} value={code}>
                {name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Base salary (local currency)" error={errors.base_salary_amount?.message}>
          <Input inputMode="decimal" placeholder="95000" {...register("base_salary_amount")} />
        </Field>
        <Field label="Hire date" error={errors.hire_date?.message}>
          <Input type="date" {...register("hire_date")} />
        </Field>
      </div>

      {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}

      <Button type="submit" disabled={submitting}>
        {submitting ? "Saving…" : submitLabel}
      </Button>
    </form>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium leading-none">{label}</span>
      {children}
      {error && <span className="block text-xs text-destructive">{error}</span>}
    </label>
  );
}
