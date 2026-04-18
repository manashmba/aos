import { useQuery } from "@tanstack/react-query";
import { AuditAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ShieldCheck, ShieldAlert } from "lucide-react";

export function AuditPage() {
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
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Audit Trail</h2>
        <Button variant="outline" onClick={() => verify.refetch()}>
          Verify chain
        </Button>
      </div>

      {verify.data && (
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            {verify.data.verified ? (
              <ShieldCheck className="h-5 w-5 text-green-600" />
            ) : (
              <ShieldAlert className="h-5 w-5 text-destructive" />
            )}
            <div className="text-sm">
              {verify.data.verified
                ? `Integrity OK — ${verify.data.checked} events verified.`
                : `Chain broken at ${verify.data.broken_at} (after ${verify.data.checked} events).`}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Recent events</CardTitle>
        </CardHeader>
        <CardContent>
          {events.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-muted-foreground">
                <tr className="border-b">
                  <th className="py-2 text-left">Time</th>
                  <th className="py-2 text-left">Event</th>
                  <th className="py-2 text-left">Actor</th>
                  <th className="py-2 text-left">Entity</th>
                  <th className="py-2 text-left">Outcome</th>
                </tr>
              </thead>
              <tbody>
                {(events.data as any[] | undefined)?.map((e) => (
                  <tr key={e.id} className="border-b">
                    <td className="py-2 font-mono text-xs">
                      {new Date(e.timestamp).toLocaleString("en-IN")}
                    </td>
                    <td className="py-2">{e.event_type}</td>
                    <td className="py-2">
                      {e.actor?.name ?? e.actor?.id ?? "—"}
                      <span className="ml-1 text-xs text-muted-foreground">({e.actor?.type})</span>
                    </td>
                    <td className="py-2">
                      {e.entity?.type}:{e.entity?.display ?? e.entity?.id ?? "—"}
                    </td>
                    <td className="py-2">{e.outcome}</td>
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
