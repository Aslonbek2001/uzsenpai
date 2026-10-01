// shared/i18n/index.ts — uz (default), ru, en, ja. Namespaces load on demand through an inline backend,
// so `useTranslation("billing")` suspends until the JSON is there (no raw keys flashing on screen).
// Key convention: t("ns:key.path") — e.g. t("visa:form.save"), t("errors:visa.expiry_in_past");
// inside visa.json the keys have NO namespace prefix ({ "form": { "save": "…" } }).
import i18n, { type BackendModule, type ReadCallback } from "i18next";
import { initReactI18next } from "react-i18next";

export const LOCALES = ["uz", "ru", "en", "ja"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "uz";

/** Names shown in the language picker — each in its own language, never flags. */
export const LOCALE_NAMES: Record<Locale, string> = { uz: "Oʻzbekcha", ru: "Русский", en: "English", ja: "日本語" };

/** Intl tags: Uzbek Latin explicitly. */
export const INTL_TAG: Record<Locale, string> = { uz: "uz-Latn-UZ", ru: "ru-RU", en: "en-US", ja: "ja-JP" };

const loaders = import.meta.glob<{ default: Record<string, unknown> }>("./locales/*/*.json");

const lazyJsonBackend: BackendModule = {
  type: "backend",
  init() {},
  read(language: string, namespace: string, callback: ReadCallback) {
    const load = loaders[`./locales/${language}/${namespace}.json`];
    if (!load) {
      callback(new Error(`missing locale file ${language}/${namespace}`), false);
      return;
    }
    load().then(
      (m) => callback(null, m.default),
      (err: Error) => callback(err, false),
    );
  },
};

function isLocale(v: string | null | undefined): v is Locale {
  return !!v && (LOCALES as readonly string[]).includes(v);
}

function detectInitial(): Locale {
  try {
    const saved = localStorage.getItem("locale");
    if (isLocale(saved)) return saved;
  } catch {
    /* storage blocked — fine */
  }
  const nav = navigator.language.slice(0, 2);
  return isLocale(nav) ? nav : DEFAULT_LOCALE;
}

export async function initI18n() {
  await i18n
    .use(lazyJsonBackend)
    .use(initReactI18next)
    .init({
      lng: detectInitial(),
      fallbackLng: DEFAULT_LOCALE,
      supportedLngs: [...LOCALES],
      ns: ["common", "errors"], // preloaded; others load when a component asks for them
      defaultNS: "common",
      interpolation: { escapeValue: false },
      react: { useSuspense: true },
    });
  document.documentElement.lang = i18n.language;
}

/** Called by features/switch-language, which also PATCHes /users/me and invalidates queries. */
export async function changeLocale(lng: Locale) {
  await i18n.changeLanguage(lng);
  document.documentElement.lang = lng;
  try {
    localStorage.setItem("locale", lng);
  } catch {
    /* ignore */
  }
}

/** UZS unit per locale (Intl's UZS display is inconsistent across languages); other currencies use Intl. */
const SUM: Record<Locale, (n: string) => string> = {
  uz: (n) => `${n} soʻm`,
  ru: (n) => `${n} сум`,
  en: (n) => `${n} UZS`,
  ja: (n) => `${n} スム`,
};

/** Formatters — dates, numbers and money always per locale. */
export const fmt = {
  date: (d: Date | string, lng: Locale) =>
    new Intl.DateTimeFormat(INTL_TAG[lng], { dateStyle: "long" }).format(new Date(d)),
  number: (n: number, lng: Locale) => new Intl.NumberFormat(INTL_TAG[lng]).format(n),
  /**
   * Money from the API: integer minor units + ISO currency (national UZS or international USD/JPY/EUR).
   * fmt.money(15_000_000, "UZS", "uz") → "150 000 soʻm"; fmt.money(1200, "JPY", "ja") → "￥1,200".
   */
  money: (amountMinor: number, currency: string, lng: Locale) => {
    const tag = INTL_TAG[lng];
    const exponent = new Intl.NumberFormat("en", { style: "currency", currency }).resolvedOptions()
      .maximumFractionDigits ?? 2;
    const major = amountMinor / 10 ** exponent;
    if (currency === "UZS") {
      return SUM[lng](new Intl.NumberFormat(tag, { maximumFractionDigits: 0 }).format(Math.round(major)));
    }
    return new Intl.NumberFormat(tag, { style: "currency", currency }).format(major);
  },
};

export default i18n;
