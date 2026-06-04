import { useState } from "react";

import { useImportCsv } from "@/api/hooks";
import type { ImportResult } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const COLUMNS =
  "first_name, last_name, email, department, job_title, level, employment_type, country, base_salary_amount, hire_date";

/** Bulk-import employees from a CSV, with a dry-run preview before committing. */
export function ImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const importer = useImportCsv();

  const run = (dryRun: boolean) => {
    if (!file) return;
    importer.mutate({ file, dryRun }, { onSuccess: setResult });
  };

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-2xl font-semibold tracking-tight">Import employees</h1>

      <Card>
        <CardHeader>
          <CardTitle>Upload CSV</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Expected columns: <code className="text-xs">{COLUMNS}</code>. Validate first to preview
            errors; nothing is saved unless every row is valid.
          </p>
          <input
            type="file"
            accept=".csv"
            aria-label="CSV file"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null);
              setResult(null);
            }}
            className="block text-sm"
          />
          <div className="flex gap-2">
            <Button variant="outline" disabled={!file || importer.isPending} onClick={() => run(true)}>
              Validate (dry-run)
            </Button>
            <Button disabled={!file || importer.isPending} onClick={() => run(false)}>
              {importer.isPending ? "Working…" : "Import"}
            </Button>
          </div>
          {importer.error && <p className="text-sm text-destructive">{importer.error.message}</p>}
        </CardContent>
      </Card>

      {result && <ImportSummary result={result} />}
    </div>
  );
}

function ImportSummary({ result }: { result: ImportResult }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {result.dry_run ? "Dry-run preview" : "Import complete"}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-6 text-sm">
          <span>Total: <strong>{result.total}</strong></span>
          <span className="text-emerald-700">Valid: <strong>{result.valid}</strong></span>
          <span className="text-red-700">Failed: <strong>{result.failed}</strong></span>
          <span>Inserted: <strong>{result.inserted}</strong></span>
        </div>
        {result.errors.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Row</TableHead>
                <TableHead>Field</TableHead>
                <TableHead>Problem</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {result.errors.map((error) => (
                <TableRow key={`${error.row_number}-${error.field}`}>
                  <TableCell>{error.row_number}</TableCell>
                  <TableCell className="font-mono text-xs">{error.field ?? "—"}</TableCell>
                  <TableCell>{error.message}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
