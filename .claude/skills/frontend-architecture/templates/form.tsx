// features/visa-save-status/ui/VisaStatusForm.tsx — RHF + Zod, translated errors, server error codes.
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";
import { ApiError, errorMessage, send } from "@/shared/api/client";
import { Button } from "@/shared/ui/button/Button";

const STATUSES = ["tokutei_gino_1", "tokutei_gino_2", "gijinkoku", "student", "dependent"] as const;

// Zod messages are i18n KEYS ("ns:key"), translated at render time.
const schema = z.object({
  residence_status: z.enum(STATUSES, { message: "visa:form.status_required" }),
  expires_on: z.string().min(1, "visa:form.expiry_required"),
});
type Values = z.infer<typeof schema>;

export function VisaStatusForm({ onSaved }: { onSaved: () => void }) {
  const { t } = useTranslation(["visa", "errors"]);
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { expires_on: "" } });
  const { errors } = form.formState;

  const save = useMutation({
    mutationFn: (v: Values) => send("PUT", "/visa/status", v),
    onSuccess: onSaved,
    onError: (err) => {
      if (err instanceof ApiError && err.code === "visa.expiry_in_past") {
        form.setError("expires_on", { message: `errors:${err.code}` }, { shouldFocus: true });
      } else {
        form.setError("root", { message: errorMessage(t, err) });
      }
    },
  });

  // Error lines always exist with a min-height → appearing errors don't push the layout.
  const errorLine = "min-h-5 text-sm text-shu";

  return (
    <form onSubmit={form.handleSubmit((v) => save.mutate(v))} noValidate className="flex flex-col gap-4">
      <label className="flex flex-col gap-1">
        <span className="text-sm font-semibold text-muted">{t("visa:form.status_label")}</span>
        <select {...form.register("residence_status")} defaultValue="" aria-invalid={!!errors.residence_status}>
          <option value="" disabled>
            {t("visa:form.status_placeholder")}
          </option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {t(`visa:status.${s}`)}
            </option>
          ))}
        </select>
        <span role="alert" className={errorLine}>
          {errors.residence_status?.message ? t(errors.residence_status.message) : null}
        </span>
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-sm font-semibold text-muted">{t("visa:form.expiry_label")}</span>
        <input type="date" {...form.register("expires_on")} aria-invalid={!!errors.expires_on} />
        <span role="alert" className={errorLine}>
          {errors.expires_on?.message ? t(errors.expires_on.message) : null}
        </span>
      </label>

      <p role="alert" className={errorLine}>
        {errors.root?.message ?? null}
      </p>
      {/* type="submit" is explicit; loading keeps the button's size */}
      <Button type="submit" loading={save.isPending} fullWidth>
        {t("visa:form.save")}
      </Button>
    </form>
  );
}
