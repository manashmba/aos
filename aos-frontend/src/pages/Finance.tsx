import { useQuery } from "@tanstack/react-query";
import { FinanceAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { formatINR } from "@/lib/utils";

export function FinancePage() {
  const tb = useQuery({
    queryKey: ["trial-balance"],
    queryFn: () => FinanceAPI.trialBalance().then((r) => r.data),
  });

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Trial Balance</h2>
      <Card>
        <CardHeader>
          <CardTitle>As of today</CardTitle>
        </CardHeader>
        <CardContent>
          {tb.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-muted-foreground">
                <tr className="border-b">
                  <th className="py-2 text-left font-medium">Code</th>
                  <th className="py-2 text-left font-medium">Account</th>
                  <th className="py-2 text-left font-medium">Type</th>
                  <th className="py-2 text-right font-medium">Debits</th>
                  <th className="py-2 text-right font-medium">Credits</th>
                  <th className="py-2 text-right font-medium">Balance</th>
                </tr>
              </thead>
              <tbody>
                {(tb.data as any[] | undefined)?.map((r, i) => (
                  <tr key={i} className="border-b">
                    <td className="py-2 font-mono">{r.code}</td>
                    <td className="py-2">{r.name}</td>
                    <td className="py-2">{r.type}</td>
                    <td className="py-2 text-right">{formatINR(r.debits)}</td>
                    <td className="py-2 text-right">{formatINR(r.credits)}</td>
                    <td className="py-2 text-right font-medium">{formatINR(r.balance)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
