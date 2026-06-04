import { Sparkles } from "lucide-react";
import { useState } from "react";

import { useAsk } from "@/api/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const EXAMPLES = [
  "What is the average salary by department?",
  "How many employees are in each country?",
  "Which level has the highest median pay?",
];

/** Ask plain-English questions about pay; answered by guarded, read-only SQL. */
export function AskPage() {
  const [question, setQuestion] = useState("");
  const ask = useAsk();

  const submit = () => {
    if (question.trim().length >= 3) ask.mutate(question.trim());
  };

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Ask about pay</h1>
        <p className="text-sm text-muted-foreground">
          Ask in plain English. We translate it to a safe, read-only query and run it.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-3 p-4">
          <Textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="e.g. What is the median salary by country?"
            aria-label="Your question"
          />
          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={submit} disabled={ask.isPending}>
              <Sparkles className="h-4 w-4" />
              {ask.isPending ? "Thinking…" : "Ask"}
            </Button>
            {EXAMPLES.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => setQuestion(example)}
                className="rounded-full border px-3 py-1 text-xs text-muted-foreground hover:bg-accent"
              >
                {example}
              </button>
            ))}
          </div>
          {ask.error && <p className="text-sm text-destructive">{ask.error.message}</p>}
        </CardContent>
      </Card>

      {ask.data && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Answer</CardTitle>
            <pre className="mt-2 overflow-auto rounded-md bg-muted p-3 text-xs">{ask.data.sql}</pre>
          </CardHeader>
          <CardContent>
            {ask.data.rows.length === 0 ? (
              <p className="text-sm text-muted-foreground">No rows.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    {ask.data.columns.map((column) => (
                      <TableHead key={column}>{column}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ask.data.rows.map((row, index) => (
                    <TableRow key={index}>
                      {ask.data!.columns.map((column) => (
                        <TableCell key={column}>{String(row[column] ?? "")}</TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
            {ask.data.truncated && (
              <p className="mt-2 text-xs text-muted-foreground">Results capped at 1000 rows.</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
