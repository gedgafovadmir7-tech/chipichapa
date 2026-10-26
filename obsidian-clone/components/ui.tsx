import { forwardRef, type ButtonHTMLAttributes, type InputHTMLAttributes } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
const variants: Record<Variant, string> = {
  primary: 'bg-accent text-on-accent hover:opacity-90',
  secondary: 'bg-surface-2 text-text hover:opacity-80',
  ghost: 'bg-transparent text-text hover:bg-surface-2',
  danger: 'bg-danger text-bg hover:opacity-90',
};

export const Button = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }>(
  function Button({ variant = 'secondary', loading, disabled, className = '', children, ...rest }, ref) {
    return (
      <button
        ref={ref}
        type="button"
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${className}`}
        {...rest}
      >
        {children}
      </button>
    );
  },
);

/** Иконочная кнопка: aria-label обязателен. */
export function IconButton({ label, className = '', children, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button type="button" aria-label={label} title={label} className={`inline-flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-surface-2 hover:text-text ${className}`} {...rest}>
      {children}
    </button>
  );
}

export function TextInput({ label, error, id, className = '', ...rest }: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string }) {
  const inputId = id ?? `in-${label}`;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={inputId} className="text-sm text-muted">{label}</label>
      <input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${inputId}-err` : undefined}
        className={`rounded-md border bg-bg px-3 py-1.5 text-text ${error ? 'border-danger' : 'border-border-input'} ${className}`}
        {...rest}
      />
      {error && <p id={`${inputId}-err`} className="text-sm text-danger">{error}</p>}
    </div>
  );
}
