import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Metric, NumberField } from './UI';

describe('Scientific metric display', () => {
  it('distinguishes undefined values from a measured zero and exposes definitions', () => {
    render(
      <>
        <Metric label="Undefined correlation" value={null} />
        <Metric label="Measured entropy" value={0} hint="Bits per intensity symbol" />
      </>,
    );
    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.getByText('0.000')).toBeInTheDocument();
    expect(screen.getByLabelText('Bits per intensity symbol')).toHaveAttribute('tabindex', '0');
  });
  it('allows keyboard editing and keeps invalid empty values out of numeric state', async () => {
    const change = vi.fn();
    render(<NumberField label="Rényi order" value={2} min={0} max={100} onChange={change} />);
    const input = screen.getByRole('spinbutton', { name: 'Rényi order' });
    await userEvent.clear(input);
    expect(change).not.toHaveBeenCalled();
    await userEvent.type(input, '3');
    expect(change).toHaveBeenCalledWith(3);
  });
});
