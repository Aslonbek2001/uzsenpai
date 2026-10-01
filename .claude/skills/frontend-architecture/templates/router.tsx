// app/router.tsx — lazy routes, one shell, scroll restoration.
import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter, Outlet, ScrollRestoration } from "react-router";

const HomePage = lazy(() => import("@/pages/home").then((m) => ({ default: m.HomePage })));
const ResumeStepPage = lazy(() => import("@/pages/career/resume-step").then((m) => ({ default: m.ResumeStepPage })));
const VisaPage = lazy(() => import("@/pages/visa").then((m) => ({ default: m.VisaPage })));
const LearnPage = lazy(() => import("@/pages/learn").then((m) => ({ default: m.LearnPage })));

/** Skeleton has the same footprint as the page → no jump when the chunk arrives. */
function PageSkeleton() {
  return <div className="min-h-dvh animate-pulse bg-bg" aria-busy="true" />;
}

function page(node: ReactNode) {
  return <Suspense fallback={<PageSkeleton />}>{node}</Suspense>;
}

function RootLayout() {
  return (
    <>
      {/* AppShell = bottom tab bar (mobile) / rail (tablet) / sidebar (desktop) */}
      <Outlet />
      <ScrollRestoration />
    </>
  );
}

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      { index: true, element: page(<HomePage />) },
      { path: "career/resume/:step", element: <div data-space="career">{page(<ResumeStepPage />)}</div> },
      { path: "visa", element: <div data-space="visa">{page(<VisaPage />)}</div> },
      { path: "learn", element: <div data-space="learn">{page(<LearnPage />)}</div> },
    ],
  },
]);

// Tabs/filters inside a page must not scroll to top:
// <Link to="?tab=active" preventScrollReset>…</Link>
