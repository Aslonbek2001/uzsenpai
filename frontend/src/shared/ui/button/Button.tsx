/**
 * Reference implementation for interaction quality — copy these patterns into every interactive component.
 * - fixed size while loading (no width jump), spinner overlays the hidden label
 * - press feedback via transform, hover only on hover-capable devices
 * - type="button" by default (no accidental form submit / page jump)
 * - no double submit, spinner appears only after 300ms (no flashing)
 */
import { useEffect, useState, type ButtonHTMLAttributes, type ReactNode, type Ref } from "react";
import { cn } from "@/shared/lib/cn";
import "./button.css";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  ref?: Ref<HTMLButtonElement>;
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  fullWidth?: boolean;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
};

function useDelayed(flag: boolean, ms = 300): boolean {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (!flag) {
      setShown(false);
      return;
    }
    const id = window.setTimeout(() => setShown(true), ms);
    return () => window.clearTimeout(id);
  }, [flag, ms]);
  return shown;
}

export function Button({
  ref,
  variant = "primary",
  size = "md",
  loading = false,
  fullWidth = false,
  disabled,
  type = "button",
  leadingIcon,
  trailingIcon,
  className,
  children,
  onClick,
  ...rest
}: ButtonProps) {
  const showSpinner = useDelayed(loading);

  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled}
      aria-disabled={loading || undefined}
      aria-busy={loading || undefined}
      data-loading={showSpinner || undefined}
      onClick={(e) => {
        if (loading) {
          e.preventDefault();
          return;
        }
        onClick?.(e);
      }}
      className={cn("btn", `btn--${variant}`, `btn--${size}`, fullWidth && "btn--full", className)}
      {...rest}
    >
      <span className="btn__label">
        {leadingIcon}
        {children}
        {trailingIcon}
      </span>
      {showSpinner && (
        <span className="btn__spinner" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="18" height="18">
            <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
            <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
          </svg>
        </span>
      )}
    </button>
  );
}
