import type { ReactNode } from "react";

type FormFieldProps = {
  id: string;
  label: string;
  required?: boolean;
  error?: string | null;
  hint?: string;
  children: ReactNode;
};

export function FormField({ id, label, required, error, hint, children }: FormFieldProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className="block text-sm">
      <label htmlFor={id} className="font-medium text-slate-800">
        {label}
        {required ? (
          <span className="text-red-800" aria-hidden="true">
            {" "}
            *
          </span>
        ) : null}
        {required ? <span className="sr-only"> (required)</span> : null}
      </label>
      <div
        className="mt-1"
        aria-describedby={describedBy}
        aria-invalid={error ? true : undefined}
      >
        {children}
      </div>
      {hint ? (
        <p id={hintId} className="mt-1 text-xs text-slate-600">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} role="alert" className="mt-1 text-sm text-red-800">
          {error}
        </p>
      ) : null}
    </div>
  );
}
