import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { FinanceAPI, InventoryAPI } from "@/lib/api";
import { formatINR } from "@/lib/utils";

export function DashboardPage() {
  const ageing = useQuery({
    queryKey: ["ageing", "sales"],
    queryFn: () => FinanceAPI.ageing("sales").then((r) => r.data),
  });
  const reorder = useQuery({
    queryKey: ["reorder"],
    queryFn: () => InventoryAPI.reorderSuggestions().then((r) => r.data),
  });

  const buckets = ageing.data ?? {};
  const totalAR = Object.values(buckets).reduce(
    (acc: number, v: unknown) => acc + Number(v ?? 0),
    0,
  );

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Dashboard</h2>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <Kpi label="Total Receivables" value={formatINR(totalAR)} />
        <Kpi label="Current" value={formatINR(buckets["current"] ?? 0)} />
        <Kpi label="31–60 days" value={formatINR(buckets["31-60"] ?? 0)} />
        <Kpi label="90+ overdue" value={formatINR(buckets["90+"] ?? 0)} tone="danger" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Reorder Suggestions</CardTitle>
        </CardHeader>
        <CardContent>
          {reorder.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : (reorder.data as any[] | undefined)?.length ? (
            <table className="w-full text-sm">
              <thead className="text-muted-foreground">
                <tr className="border-b">
                  <th className="py-2 text-left font-medium">Product</th>
                  <th className="py-2 text-right font-medium">On hand</th>
                  <th className="py-2 text-right font-medium">Reorder level</th>
                  <th className="py-2 text-right font-medium">Suggested qty</th>
                </tr>
              </thead>
              <tbody>
                {(reorder.data as any[]).map((r, i) => (
                  <tr key={i} className="border-b">
                    <td className="py-2">{r.product_name ?? r.product_id}</td>
                    <td className="py-2 text-right">{r.on_hand}</td>
                    <td className="py-2 text-right">{r.reorder_level}</td>
                    <td className="py-2 text-right font-medium">{r.suggested_qty}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-muted-foreground">All stocks healthy.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Kpi({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "default" | "danger";
}) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
        <div
          className={`mt-2 text-2xl font-semibold ${tone === "danger" ? "text-destructive" : ""}`}
        >
          {value}
        </div>
      </CardContent>
    </Card>
  );
}
