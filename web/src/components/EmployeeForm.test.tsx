import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EmployeeForm } from "@/components/EmployeeForm";

describe("EmployeeForm", () => {
  it("blocks submission and shows errors when required fields are empty", async () => {
    const onSubmit = vi.fn();
    render(<EmployeeForm submitLabel="Create" submitting={false} onSubmit={onSubmit} />);

    await userEvent.click(screen.getByRole("button", { name: /create/i }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByText(/enter a valid email/i)).toBeInTheDocument();
  });

  it("submits the entered values when the form is valid", async () => {
    const onSubmit = vi.fn();
    render(<EmployeeForm submitLabel="Create" submitting={false} onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText("First name"), "Grace");
    await userEvent.type(screen.getByLabelText("Last name"), "Hopper");
    await userEvent.type(screen.getByLabelText("Email"), "grace@acme.test");
    await userEvent.type(screen.getByLabelText("Job title"), "Engineer");
    await userEvent.type(screen.getByLabelText(/base salary/i), "150000");
    await userEvent.type(screen.getByLabelText("Hire date"), "2021-06-01");

    await userEvent.click(screen.getByRole("button", { name: /create/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      first_name: "Grace",
      email: "grace@acme.test",
      base_salary_amount: "150000",
    });
  });
});
