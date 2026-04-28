import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { FinanceAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { formatINR } from "@/lib/utils";

export function FinancePage() {
  const { t } = useTranslation();
  const tb = useQuery({
    queryKey: ["trial-balance"],
    queryFn: () => FinanceAPI.trialBalance().then((r) => r.data),
  });

  const rows = (tb.data as any[] | undefined) ?? [];
  const totalDr = rows.reduce((s, r) => s + Number(r.debits || 0), 0);
  const totalCr = rows.reduce((s, r) => s + Number(r.credits || 0), 0);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">{t("finance.title")}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{t("finance.asOfToday")}</p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">
            {t("finance.title")}
            <span className="ml-3 text-xs font-normal text-muted-foreground">
              Dr {formatINR(totalDr)} · Cr {formatINR(totalCr)}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {tb.isLoading ? (
            <p className="p-6 text-sm text-muted-foreground">{t("common.loading")}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">{t("finance.colCode")}</th>
                    <th className="px-4 py-2 text-left font-medium">{t("finance.colAccount")}</th>
                    <th className="px-4 py-2 text-left font-medium">{t("finance.colType")}</th>
                    <th className="px-4 py-2 text-right font-medium">{t("finance.colDebits")}</th>
                    <th className="px-4 py-2 text-right font-medium">{t("finance.colCredits")}</th>
                    <th className="px-4 py-2 text-right font-medium">{t("finance.colBalance")}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i} className="border-t hover:bg-muted/30">
                      <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{r.code}</td>
                      <td className="px-4 py-2">{r.name}</td>
                      <td className="px-4 py-2">
                        <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                          {r.type}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">{formatINR(r.debits)}</td>
                      <td className="px-4 py-2 text-right tabular-nums">{formatINR(r.credits)}</td>
                      <td className="px-4 py-2 text-right font-medium tabular-nums">{formatINR(r.balance)}</td>
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
