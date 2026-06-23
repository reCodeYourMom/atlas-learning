"use client";

import { ButtonHTMLAttributes, ReactNode } from "react";

export function cx(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(" ");
}

export function Card({
  children,
  className,
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: keyof JSX.IntrinsicElements;
}) {
  return (
    <Tag className={cx("rounded-2xl bg-white shadow-card ring-1 ring-sand-200/70", className)}>
      {children}
    </Tag>
  );
}

export function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold text-sand-800">{title}</h2>
      {subtitle && <p className="mt-0.5 text-sm text-sand-500">{subtitle}</p>}
    </div>
  );
}

type Variant = "primary" | "accent" | "ghost" | "outline";

export function Button({
  variant = "primary",
  className,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  const styles: Record<Variant, string> = {
    primary: "bg-brand-600 text-white hover:bg-brand-700 disabled:bg-brand-300",
    // Accent or = réservé aux CTA clés (un seul focal coloré par écran, Brief §5).
    accent: "bg-gold-400 text-sand-900 hover:bg-gold-500 disabled:opacity-60 font-semibold",
    ghost: "text-brand-700 hover:bg-brand-50",
    outline: "ring-1 ring-sand-300 text-sand-700 hover:bg-sand-50 bg-white",
  };
  return (
    <button
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium",
        "transition-colors disabled:cursor-not-allowed",
        styles[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function Chip({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <svg className={cx("h-5 w-5 animate-spin text-brand-500", className)} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path className="opacity-90" d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function Loading({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-sand-500">
      <Spinner />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function EmptyState({ title, body, icon }: { title: string; body: string; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-sand-300 bg-sand-25 px-6 py-14 text-center">
      <div className="text-brand-300">{icon ?? <DotsIcon />}</div>
      <h3 className="text-base font-semibold text-sand-700">{title}</h3>
      <p className="max-w-sm text-sm text-sand-500">{body}</p>
    </div>
  );
}

export function ErrorPanel({ detail }: { detail: string }) {
  return (
    <div className="rounded-2xl border border-danger/20 bg-danger/5 px-5 py-4 text-sm text-danger">
      {detail}
    </div>
  );
}

function DotsIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="5" cy="12" r="1.6" /><circle cx="12" cy="12" r="1.6" /><circle cx="19" cy="12" r="1.6" />
    </svg>
  );
}
