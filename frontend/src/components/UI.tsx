import { useEffect, useState, type ReactNode } from 'react';
import { Info, LoaderCircle } from 'lucide-react';
import { fmt } from '../lib/api';

export function Section({
  title,
  eyebrow,
  children,
  action,
}: {
  title: string;
  eyebrow?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="section">
      <div className="section-heading">
        <div>
          {eyebrow && <span className="eyebrow">{eyebrow}</span>}
          <h2>{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Metric({
  label,
  value,
  unit,
  hint,
  accent = false,
}: {
  label: string;
  value: number | string | null | undefined;
  unit?: string;
  hint?: string;
  accent?: boolean;
}) {
  return (
    <div className={`metric ${accent ? 'accent' : ''}`}>
      <div className="metric-label">
        {label}
        {hint && (
          <span tabIndex={0} className="hint" aria-label={hint} title={hint}>
            <Info size={12} />
          </span>
        )}
      </div>
      <div className="metric-value">{typeof value === 'number' ? fmt(value) : (value ?? '—')}</div>
      {unit && <span className="metric-unit">{unit}</span>}
    </div>
  );
}
export function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="notice">
      <Info size={15} />
      <div>{children}</div>
    </div>
  );
}
export function Empty({
  children = 'Select an image and run analysis to explore this view.',
}: {
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-symbol">∑</div>
      <h2>Make room for discovery.</h2>
      <p>{children}</p>
    </div>
  );
}
export function Spinner() {
  return <LoaderCircle size={16} className="spin" aria-label="Loading" />;
}
export function NumberField({
  label,
  value,
  onChange,
  min = 0,
  max = 4096,
  step = 1,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  const [text, setText] = useState(String(value));
  useEffect(() => setText(String(value)), [value]);
  return (
    <label className="field">
      {label}
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          const n = e.target.valueAsNumber;
          if (Number.isFinite(n)) onChange(n);
        }}
        onBlur={() => {
          const parsed = text.trim() ? Number(text) : value;
          const next = Math.max(min, Math.min(max, Number.isFinite(parsed) ? parsed : value));
          setText(String(next));
          if (next !== value) onChange(next);
        }}
      />
    </label>
  );
}
