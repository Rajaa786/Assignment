import { BarChart3, FileUp, MessageSquareText, Users } from "lucide-react";
import { NavLink, Route, Routes } from "react-router-dom";

import { cn } from "@/lib/utils";
import { AskPage } from "@/pages/AskPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { EmployeeDetailPage } from "@/pages/EmployeeDetailPage";
import { EmployeeNewPage } from "@/pages/EmployeeNewPage";
import { EmployeesPage } from "@/pages/EmployeesPage";
import { ImportPage } from "@/pages/ImportPage";

const NAV = [
  { to: "/", label: "Dashboard", icon: BarChart3, end: true },
  { to: "/employees", label: "Employees", icon: Users, end: false },
  { to: "/import", label: "Import", icon: FileUp, end: false },
  { to: "/ask", label: "Ask", icon: MessageSquareText, end: false },
];

function App() {
  return (
    <div className="min-h-screen bg-muted/30">
      <header className="border-b bg-background">
        <div className="mx-auto flex max-w-7xl items-center gap-6 px-6 py-3">
          <span className="text-lg font-semibold tracking-tight">ACME Salary</span>
          <nav className="flex items-center gap-1">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive ? "bg-secondary text-secondary-foreground" : "text-muted-foreground hover:text-foreground",
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/employees" element={<EmployeesPage />} />
          <Route path="/employees/new" element={<EmployeeNewPage />} />
          <Route path="/employees/:id" element={<EmployeeDetailPage />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/ask" element={<AskPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
