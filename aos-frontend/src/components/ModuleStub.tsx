import { useTranslation } from "react-i18next";
import { MessageSquare, type LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";

interface Props {
  navKey: string;           // i18n key under `nav.*`
  icon: LucideIcon;
}

/**
 * Placeholder for module pages whose detailed tables/forms haven't shipped
 * yet. Keeps the module discoverable in the sidebar and nudges users toward
 * the chat-first workflow (the product thesis).
 */
export function ModuleStub({ navKey, icon: Icon }: Props) {
  const { t } = useTranslation();
  const moduleName = t(navKey);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">{moduleName}</h2>
      </div>

      <Card className="bg-hero">
        <CardContent className="flex flex-col items-center justify-center gap-3 p-12 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Icon className="h-5 w-5" />
          </div>
          <p className="max-w-md text-sm text-muted-foreground">
            {t("stub.body")}
          </p>
          <a
            href="/chat"
            className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground shadow-sm transition hover:opacity-90"
          >
            <MessageSquare className="h-3.5 w-3.5" />
            {t("nav.chat")}
          </a>
        </CardContent>
      </Card>
    </div>
  );
}
