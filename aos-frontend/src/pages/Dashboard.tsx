import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ArrowUpRight, TrendingUp, AlertTriangle, Wallet } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { FinanceAPI, InventoryAPI } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { formatINR } from "@/lib/utils";
import { cn } from "@/lib/utils";

export function DashboardPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);

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
      <header>
        <h2 className="text-2xl font-semibold tracking-tight">
          {t("dashboard.greeting", { name: (user?.name ?? "").split(" ")[0] || "👋" })}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">{t("dashboard.subtitle")}</p>
      </header>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi
          icon={<Wallet className="h-4 w-4" />}
          label={t("dashboard.totalReceivables")}
          value={formatINR(totalAR)}
          trend="+4.2%"
          tone="primary"
        />
        <Kpi
          icon={<TrendingUp className="h-4 w-4" />}
          label={t("dashboard.current")}
          value={formatINR(buckets["current"] ?? 0)}
        />
        <Kpi
          icon={<ArrowUpRight className="h-4 w-4" />}
          label={t("dashboard.days31_60")}
          value={formatINR(buckets["31-60"] ?? 0)}
        />
        <Kpi
          icon={<AlertTriangle className="h-4 w-4" />}
          label={t("dashboard.overdue90")}
          value={formatINR(buckets["90+"] ?? 0)}
          tone="danger"
        />
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle className="text-base">{t("dashboard.reorderTitle")}</CardTitle>
            <p className="text-xs text-muted-foreground">{t("dashboard.reorderSubtitle", "SKUs below reorder level")}</p>
          </div>
        </CardHeader>
        <CardContent>
          {reorder.isLoading ? (
            <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
          ) : (reorder.data as any[] | undefined)?.length ? (
            <div className="overflow-hidden rounded-md border">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">{t("dashboard.colProduct")}</th>
                    <th className="px-3 py-2 text-right font-medium">{t("dashboard.colOnHand")}</th>
                    <th className="px-3 py-2 text-right font-medium">{t("dashboard.colReorder")}</th>
                    <th className="px-3 py-2 text-right font-medium">{t("dashboard.colSuggested")}</th>
                  </tr>
                </thead>
                <tbody>
                  {(reorder.data as any[]).map((r, i) => (
                    <tr key={i} className="border-t">
                      <td className="px-3 py-2">{r.product_name ?? r.product_id}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{r.on_hand}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">{r.reorder_level}</td>
                      <td className="px-3 py-2 text-right font-medium tabular-nums">{r.suggested_qty}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{t("dashboard.healthy")}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Kpi({
  icon,
  label,
  value,
  trend,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  trend?: string;
  tone?: "default" | "danger" | "primary";
}) {
  return (
    <Card>
      <CardContent className="space-y-3 p-4">
        <div className="flex items-center justify-between">
          <div
            className={cn(
              "flex h-7 w-7 items-center justify-center rounded-md",
              tone === "danger"
                ? "bg-destructive/10 text-destructive"
                : tone === "primary"
                  ? "bg-primary/10 text-primary"
                  : "bg-muted text-muted-foreground",
            )}
          >
            {icon}
          </div>
          {trend && (
            <span className="text-[11px] font-medium text-emerald-600">{trend}</span>
          )}
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</div>
          <div
            className={cn(
              "mt-1 text-xl font-semibold tabular-nums",
              tone === "danger" && "text-destructive",
            )}
          >
            {value}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
