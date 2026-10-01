// entities/entitlement + features/paywall — UI gate for paid features (the server still enforces).
import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { get } from "@/shared/api/client";
import { fmt, type Locale } from "@/shared/i18n";
import { Button } from "@/shared/ui/button/Button";
// Real types come from the generated OpenAPI schema (make api-types):
// import type { components } from "@/shared/api/generated/schema";
// type Product = components["schemas"]["ProductOut"]; type Entitlements = components["schemas"]["EntitlementsOut"];
type Entitlements = { keys: string[] };
type Price = { amount_minor: number; currency: string };
type Product = { id: string; title: string; includes: string[]; price: Price; delivery: string | null };

/** National (UZS) vs international currency: user's choice, else UZS for uz locale / Uzbek phone, else USD. */
export function useCheckoutCurrency(): string {
  // Real implementation reads the user's saved preference (entities/user); kept simple in this template.
  return "UZS";
}

export function useEntitlement(key: string) {
  const q = useQuery({
    queryKey: ["billing", "entitlements"],
    queryFn: ({ signal }) => get<Entitlements>("/billing/entitlements", signal),
    staleTime: 60_000,
  });
  return { allowed: q.data?.keys.includes(key) ?? false, isLoading: q.isLoading };
}

/** Same footprint as the paywall card / gated content → no jump while loading. */
function GateSkeleton() {
  return <div className="h-48 animate-pulse rounded-lg bg-sunken" aria-busy="true" />;
}

export function Gate({ entitlement, productId, children }: { entitlement: string; productId: string; children: ReactNode }) {
  const { allowed, isLoading } = useEntitlement(entitlement);
  if (isLoading) return <GateSkeleton />;
  return allowed ? <>{children}</> : <PaywallCard productId={productId} />;
}

function PaywallCard({ productId }: { productId: string }) {
  const { t, i18n } = useTranslation("billing");
  const currency = useCheckoutCurrency(); // UZS for national users, USD/JPY for international

  const { data: p } = useQuery({
    queryKey: ["catalog", productId, currency, i18n.language], // localized + priced by the server
    queryFn: ({ signal }) => get<Product>(`/catalog/products/${encodeURIComponent(productId)}?currency=${currency}`, signal),
  });
  if (!p) return <GateSkeleton />;
  return (
    <section className="flex flex-col gap-3 rounded-lg bg-surface p-4">
      <h3 className="font-bold">{p.title}</h3>
      <ul className="flex flex-col gap-1">
        {p.includes.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      <p className="font-bold tabular">{fmt.money(p.price.amount_minor, p.price.currency, i18n.language as Locale)}</p>
      <Button onClick={() => {/* open checkout sheet: features/checkout-pay */}}>{t("billing:paywall.buy")}</Button>
    </section>
  );
}
