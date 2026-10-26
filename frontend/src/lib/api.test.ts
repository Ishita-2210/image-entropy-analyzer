import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, bytes, fmt } from './api';

afterEach(() => vi.unstubAllGlobals());
describe('API boundary', () => {
  it('sends typed JSON options to the versioned API', async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });
    vi.stubGlobal('fetch', fetcher);
    await expect(api('/analysis', { image_id: 'abc' })).resolves.toEqual({ ok: true });
    expect(fetcher).toHaveBeenCalledWith(
      '/api/v1/analysis',
      expect.objectContaining({ method: 'POST', body: '{"image_id":"abc"}' }),
    );
  });
  it('surfaces sanitized server errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ error: { message: 'Image exceeds pixel limit.' } }),
      }),
    );
    await expect(api('/images')).rejects.toThrow('Image exceeds pixel limit.');
  });
  it('reports non-JSON connection failures meaningfully', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        json: async () => {
          throw new Error('html');
        },
      }),
    );
    await expect(api('/health')).rejects.toThrow('Request failed (502).');
  });
  it('formats absent measurements separately and actual byte units', () => {
    expect(fmt(null)).toBe('—');
    expect(fmt(0)).toBe('0.000');
    expect(bytes(1048576)).toBe('1.00 MB');
  });
});
