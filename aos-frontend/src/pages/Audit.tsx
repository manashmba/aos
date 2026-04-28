import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ShieldCheck, ShieldAlert, Shield } from "lucide-react";
import { AuditAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { formatTime } from "@/lib/utils";

export function AuditPage() {
  const { t } = useTranslation();
  const events = useQuery({
    queryKey: ["audit", "events"],
    queryFn: () => AuditAPI.listEvents({ limit: 100 }).then((r) => r.data),
  });
  const verify = useQuery({
    queryKey: ["audit", "verify"],
    queryFn: () => AuditAPI.verify().then((r) => r.data),
    enabled: false,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">{t("audit.title")}</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("audit.subtitle", "Tamper-evident hash-chained log of every business action.")}
          </p>
        </div>
        <Button variant="outline" onClick={() => verify.refetch()}>
          <Shield className="mr-2 h-4 w-4" />
          {t("audit.verify")}
        </Button>
      </div>

      {verify.data && (
        <Card
          className={
            verify.data.verified
              ? "border-emerald-200 bg-emerald-50/40"
              : "border-destructive/40 bg-destructive/5"
          }
        >
          <CardContent className="flex items-center gap-3 p-4">
            {verify.data.verified ? (
              <ShieldCheck className="h-5 w-5 text-emerald-600" />
            ) : (
              <ShieldAlert className="h-5 w-5 text-destructive" />
            )}
            <div className="text-sm">
              {verify.data.verified
                ? t("audit.integrityOk", { count: verify.data.checked })
                : t("audit.broken", { where: verify.data.broken_at, count: verify.data.checked })}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">{t("audit.recent")}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {events.isLoading ? (
            <p className="p-6 text-sm text-muted-foreground">{t("common.loading")}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">{t("audit.colTime")}</th>
                    <th className="px-4 py-2 text-left font-medium">{t("audit.colEvent")}</th>
                    <th className="px-4 py-2 text-left font-medium">{t("audit.colActor")}</th>
                    <th className="px-4 py-2 text-left font-medium">{t("audit.colEntity")}</th>
                    <th className="px-4 py-2 text-left font-medium">{t("audit.colOutcome")}</th>
                  </tr>
                </thead>
                <tbody>
                  {(events.data as any[] | undefined)?.map((e) => (
                    <tr key={e.id} className="border-t hover:bg-muted/30">
                      <td className="px-4 py-2 font-mono text-xs text-muted-foreground">
                        {formatTime(e.timestamp)}
                      </td>
                      <td className="px-4 py-2 font-medium">{e.event_type}</td>
                      <td className="px-4 py-2">
                        {e.actor?.name ?? e.actor?.id ?? "—"}
                        <span className="ml-1 text-xs text-muted-foreground">({e.actor?.type})</span>
                      </td>
                      <td className="px-4 py-2">
                        <span className="font-mono text-xs text-muted-foreground">{e.entity?.type}:</span>{" "}
                        {e.entity?.display ?? e.entity?.id ?? "—"}
                      </td>
                      <td className="px-4 py-2">
                        <OutcomeBadge outcome={e.outcome} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function OutcomeBadge({ outcome }: { outcome: string }) {
  const tone =
    outcome === "success"
      ? "bg-emerald-100 text-emerald-800"
      : outcome === "blocked"
        ? "bg-destructive/10 text-destructive"
        : outcome === "pending"
          ? "bg-amber-100 text-amber-900"
          : "bg-muted text-muted-foreground";
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}>
      {outcome}
    </span>
  );
}
