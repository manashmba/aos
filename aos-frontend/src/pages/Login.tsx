import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Mail, Phone, ShieldCheck, Sparkles, MessageSquareText } from "lucide-react";
import { api, DEMO_MODE } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { cn } from "@/lib/utils";

type Mode = "email" | "phone";

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);

  const [mode, setMode] = useState<Mode>("email");
  const [email, setEmail] = useState(DEMO_MODE ? "admin@acme.in" : "");
  const [password, setPassword] = useState(DEMO_MODE ? "demo" : "");
  const [phone, setPhone] = useState(DEMO_MODE ? "9811122233" : "");
  const [otp, setOtp] = useState(DEMO_MODE ? "123456" : "");
  const [otpSent, setOtpSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const creds =
        mode === "email" ? { email, password } : { email: `${phone}@phone.aos.in`, password: otp };
      const { data } = await api.post("/auth/login", creds);
      const user =
        data.user ?? {
          id: data.user_id,
          email: creds.email,
          name: data.name ?? creds.email.split("@")[0],
          role: data.role,
          org_id: data.org_id,
        };
      login(data.access_token, user);
      navigate("/chat");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? t("auth.failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-5">
      {/* ── Hero panel ─────────────────────────────────────────── */}
      <aside className="relative hidden overflow-hidden bg-hero lg:col-span-2 lg:flex lg:flex-col lg:justify-between lg:p-10">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
            <Sparkles className="h-4 w-4" />
          </div>
          <span className="text-lg font-semibold tracking-tight">{t("brand.name", "AOS")}</span>
        </div>

        <div className="space-y-6">
          <h1 className="text-3xl font-semibold leading-tight tracking-tight lg:text-4xl">
            {t("brand.tagline")}
          </h1>
          <p className="max-w-md text-base text-muted-foreground">{t("brand.pitch")}</p>

          <div className="space-y-2 text-sm text-muted-foreground">
            <Feature icon={<MessageSquareText className="h-4 w-4" />} label="Chat-first ERP · WhatsApp + web" />
            <Feature icon={<ShieldCheck className="h-4 w-4" />} label="Hash-chained audit · RBI-aligned" />
            <Feature icon={<Sparkles className="h-4 w-4" />} label="Claude Sonnet + GPT-4o fallback" />
          </div>
        </div>

        <p className="text-xs text-muted-foreground">{t("auth.footer")}</p>
      </aside>

      {/* ── Form panel ─────────────────────────────────────────── */}
      <main className="relative flex flex-col justify-center p-6 lg:col-span-3 lg:p-12">
        <div className="absolute right-6 top-6 lg:right-12 lg:top-8">
          <LanguageSwitcher variant="inline" />
        </div>

        <div className="mx-auto w-full max-w-md space-y-6">
          <header className="space-y-1">
            <h2 className="text-2xl font-semibold tracking-tight">{t("auth.welcomeBack")}</h2>
            <p className="text-sm text-muted-foreground">{t("auth.subtitle")}</p>
          </header>

          {DEMO_MODE && (
            <div className="rounded-lg border border-amber-300/70 bg-amber-50 px-3 py-2 text-xs text-amber-900">
              {t("auth.demoBanner")}
            </div>
          )}

          {/* Mode tabs: email vs mobile OTP — the Indian mid-market reality */}
          <div className="inline-flex rounded-lg border border-border bg-muted/60 p-1 text-sm">
            <TabButton active={mode === "email"} onClick={() => setMode("email")} icon={<Mail className="h-3.5 w-3.5" />}>
              {t("auth.continueWithEmail")}
            </TabButton>
            <TabButton active={mode === "phone"} onClick={() => setMode("phone")} icon={<Phone className="h-3.5 w-3.5" />}>
              {t("auth.continueWithPhone")}
            </TabButton>
          </div>

          <form onSubmit={submit} className="space-y-4">
            {mode === "email" ? (
              <>
                <Field label={t("auth.email")}>
                  <Input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                </Field>
                <Field label={t("auth.password")}>
                  <Input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
                </Field>
              </>
            ) : (
              <>
                <Field label={t("auth.phone")}>
                  <div className="flex items-center gap-2">
                    <span className="rounded-md border border-border bg-muted px-3 py-2 text-sm text-muted-foreground">+91</span>
                    <Input
                      type="tel"
                      inputMode="numeric"
                      pattern="[0-9]{10}"
                      maxLength={10}
                      value={phone}
                      onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))}
                      required
                    />
                  </div>
                </Field>
                {otpSent || DEMO_MODE ? (
                  <Field label={t("auth.otp")}>
                    <Input type="text" inputMode="numeric" maxLength={6} value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))} required />
                  </Field>
                ) : (
                  <Button type="button" variant="outline" className="w-full" disabled={phone.length !== 10} onClick={() => setOtpSent(true)}>
                    {t("auth.sendOtp", "Send OTP")}
                  </Button>
                )}
              </>
            )}

            {error && <p className="text-sm text-destructive">{error}</p>}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? t("auth.signingIn") : t("auth.signIn")}
            </Button>
          </form>
        </div>
      </main>
    </div>
  );
}

function Feature({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="flex h-6 w-6 items-center justify-center rounded-md bg-white/70 text-primary shadow-sm">
        {icon}
      </span>
      <span>{label}</span>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition",
        active ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
      )}
    >
      {icon}
      {children}
    </button>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium">{label}</span>
      {children}
    </label>
  );
}
