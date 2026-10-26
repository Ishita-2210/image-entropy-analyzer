import { useEffect, useRef, useState } from 'react';
import { Download, RefreshCw, Search, Trash2 } from 'lucide-react';
import { Chart } from '../components/Chart';
import { heatOption } from '../lib/chartOptions';
import { Empty, Metric, Notice, NumberField, Section, Spinner } from '../components/UI';
import type { Workbench } from '../hooks/useWorkbench';
import { API, api, bytes, downloadJSON, fmt, preview } from '../lib/api';
import type { Analysis, Comparison, HistoryRecord, Job } from '../types';

export function BatchView({ w }: { w: Workbench }) {
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState('filename');
  const [excluded, setExcluded] = useState<string[]>([]);
  const [format, setFormat] = useState('all');
  const images = w.images
    .filter(
      (i) =>
        `${i.filename} ${i.format} ${i.mode} ${i.width}x${i.height}`
          .toLowerCase()
          .includes(query.toLowerCase()) &&
        (format === 'all' || i.format === format),
    )
    .sort((a, b) =>
      sort === 'filename'
        ? a.filename.localeCompare(b.filename)
        : sort === 'pixels'
          ? b.width * b.height - a.width * a.height
          : (w.results[b.id]?.entropy.shannon ?? -1) - (w.results[a.id]?.entropy.shannon ?? -1),
    );
  const ids = images.filter((i) => !excluded.includes(i.id)).map((i) => i.id);
  return (
    <>
      <div className="controls">
        <label className="field search-field">
          <span>
            <Search size={13} />
            Search filename or metadata
          </span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. PNG, RGB, landscape…"
          />
        </label>
        <label className="field">
          Format
          <select value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="all">All formats</option>
            {[...new Set(w.images.map((i) => i.format))].map((f) => (
              <option key={f}>{f}</option>
            ))}
          </select>
        </label>
        <label className="field">
          Sort by
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="filename">Filename</option>
            <option value="pixels">Resolution ↓</option>
            <option value="entropy">Entropy ↓</option>
          </select>
        </label>
        <button
          className="primary"
          disabled={!ids.length || w.running}
          onClick={() => void w.batch(ids)}
        >
          Analyse {ids.length} selected
        </button>
      </div>
      {w.images.length ? (
        <Section
          title="The image collection"
          eyebrow={`${w.images.length} IMAGES IN MEMORY`}
          action={
            <div className="button-group">
              {w.lastJob && (
                <>
                  <a
                    className="button"
                    href={`${API}/jobs/${w.lastJob}/export?format=csv`}
                    download
                  >
                    <Download size={14} />
                    CSV
                  </a>
                  <a
                    className="button"
                    href={`${API}/jobs/${w.lastJob}/export?format=json`}
                    download
                  >
                    JSON
                  </a>
                </>
              )}
            </div>
          }
        >
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Select</th>
                  <th>Image</th>
                  <th>Source</th>
                  <th>Resolution</th>
                  <th>Size</th>
                  <th>Entropy</th>
                  <th>Measurement</th>
                  <th>Remove</th>
                </tr>
              </thead>
              <tbody>
                {images.map((i) => (
                  <tr key={i.id}>
                    <td>
                      <input
                        type="checkbox"
                        aria-label={`Select ${i.filename}`}
                        checked={!excluded.includes(i.id)}
                        onChange={(e) =>
                          setExcluded((old) =>
                            e.target.checked ? old.filter((id) => id !== i.id) : [...old, i.id],
                          )
                        }
                      />
                    </td>
                    <td>
                      <button className="file-cell" onClick={() => w.setSelected(i.id)}>
                        <img src={preview(i.id, 64)} alt="" />
                        <span>{i.filename}</span>
                      </button>
                    </td>
                    <td>
                      {i.format} · {i.native_bits}-bit
                      <br />
                      <small>
                        {i.mode}
                        {i.frames > 1 ? ` · frame ${i.frame + 1}/${i.frames}` : ''}
                      </small>
                    </td>
                    <td>
                      {i.width} × {i.height}
                    </td>
                    <td>{bytes(i.bytes)}</td>
                    <td>{fmt(w.results[i.id]?.entropy.shannon)}</td>
                    <td>
                      {w.results[i.id]
                        ? `${w.results[i.id].configuration.mode} · bits/intensity symbol`
                        : 'Pending analysis'}
                    </td>
                    <td>
                      <button
                        aria-label={`Remove ${i.filename}`}
                        onClick={() => void w.remove(i.id)}
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Notice>
            Batch options match the toolbar and Settings. Region selection is reset for batch
            processing. CSV and JSON export the most recent completed analysis job.
          </Notice>
        </Section>
      ) : (
        <Empty>Upload multiple images or add synthetic demos to create a collection.</Empty>
      )}
    </>
  );
}

export function SimilarityView({ w }: { w: Workbench }) {
  const [metric, setMetric] = useState('js_distance');
  const [distribution, setDistribution] = useState('gray');
  const [threshold, setThreshold] = useState(8);
  const [levels, setLevels] = useState(16);
  const [result, setResult] = useState<Comparison | null>(null);
  const [job, setJob] = useState<Job<Comparison> | null>(null);
  const [pair, setPair] = useState(0);
  const timeout = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timeout.current), []);
  const run = async () => {
    w.setError('');
    try {
      const started = await api<Job<Comparison>>('/jobs/compare', {
        image_ids: w.images.map((i) => i.id),
        metric,
        distribution,
        near_threshold: threshold,
        levels,
      });
      setJob(started);
      const poll = async () => {
        try {
          const current = await api<Job<Comparison>>(`/jobs/${started.id}/results`);
          setJob(current);
          if (current.status === 'completed' && current.result) {
            setResult(current.result);
            setPair(0);
          } else if (current.status === 'failed') w.setError(current.error ?? 'Comparison failed.');
          else if (current.status !== 'cancelled')
            timeout.current = setTimeout(() => void poll(), 300);
        } catch (e) {
          w.setError(String(e));
          setJob(null);
        }
      };
      timeout.current = setTimeout(() => void poll(), 150);
    } catch (e) {
      w.setError(String(e));
    }
  };
  const running = job?.status === 'running' || job?.status === 'queued';
  const selected = result?.pairs[pair];
  const measuredMetric = result?.configuration.metric ?? metric;
  return (
    <>
      <div className="controls">
        <label className="field">
          Distribution
          <select
            value={distribution}
            aria-label="Distribution"
            onChange={(e) => {
              setDistribution(e.target.value);
              if (e.target.value === 'rgb' && metric === 'wasserstein') setMetric('js_distance');
            }}
          >
            {[
              ['gray', 'Grayscale'],
              ['red', 'Red channel'],
              ['green', 'Green channel'],
              ['blue', 'Blue channel'],
              ['rgb', 'Quantized RGB tuples'],
            ].map(([v, label]) => (
              <option value={v} key={v}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Matrix distance
          <select
            aria-label="Matrix distance"
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
          >
            {[
              ['js_distance', 'Jensen–Shannon distance'],
              ['hellinger', 'Hellinger distance'],
              ['total_variation', 'Total variation'],
              ['wasserstein', 'Wasserstein · intensity steps'],
            ]
              .filter(([v]) => v !== 'wasserstein' || distribution !== 'rgb')
              .map(([v, label]) => (
                <option value={v} key={v}>
                  {label}
                </option>
              ))}
          </select>
        </label>
        <NumberField
          label="Near-duplicate pHash threshold"
          value={threshold}
          max={64}
          onChange={setThreshold}
        />
        {distribution === 'rgb' && (
          <NumberField
            label="RGB levels per channel"
            value={levels}
            min={2}
            max={32}
            onChange={setLevels}
          />
        )}
        <button
          className="primary"
          disabled={w.images.length < 2 || running}
          onClick={() => void run()}
        >
          {running ? <Spinner /> : null}Compare collection
        </button>
        {running && (
          <button
            onClick={() => {
              void api(`/jobs/${job.id}`, undefined, 'DELETE').catch((e) => w.setError(String(e)));
            }}
          >
            Cancel comparison
          </button>
        )}
      </div>
      {!result ? (
        <Empty>
          Add at least two images, then compare measured distributions and explore duplicate
          candidates.
        </Empty>
      ) : (
        <>
          <Section
            title="Distribution distance matrix"
            eyebrow="SMALLER MEANS CLOSER"
            action={
              <button onClick={() => downloadJSON(result, 'comparison.json')}>
                <Download size={14} />
                Export
              </button>
            }
          >
            <Chart
              height={Math.min(600, 220 + result.images.length * 20)}
              label="Pairwise image distribution distance matrix"
              option={heatOption(
                result.matrix,
                result.images.map((_, i) => `#${i + 1}`),
                result.images.map((_, i) => `#${i + 1}`),
                Math.max(...result.matrix.flat()),
                measuredMetric,
              )}
              onSelect={([x, y]) => {
                const i = result.pairs.findIndex(
                  (p) =>
                    (p.left === result.images[x].id && p.right === result.images[y].id) ||
                    (p.right === result.images[x].id && p.left === result.images[y].id),
                );
                if (i >= 0) setPair(i);
              }}
            />
            <div className="inline-stats">
              {result.images.map((i, n) => (
                <span key={i.id}>
                  #{n + 1} {i.filename}
                </span>
              ))}
            </div>
            <p className="muted small">{result.definition}</p>
            <p className="muted small">
              Measured configuration: {result.configuration.distribution} · {measuredMetric}
              {result.configuration.distribution === 'rgb'
                ? ` · ${result.configuration.levels} levels/channel`
                : ' · 256 intensity bins'}
              {' · '}pHash threshold {result.configuration.near_threshold}. Controls apply to the
              next comparison.
            </p>
          </Section>
          <Section title="Candidate pairs & ranking">
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Pair</th>
                    <th>Distance · {measuredMetric}</th>
                    <th>pHash / 64</th>
                    <th>dHash / 64</th>
                    <th>Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {result.pairs.map((p, i) => (
                    <tr key={`${p.left}-${p.right}`} className={i === pair ? 'selected-row' : ''}>
                      <td>
                        <button onClick={() => setPair(i)}>
                          {p.left_name} ↔ {p.right_name}
                        </button>
                      </td>
                      <td>{fmt(p.distances[measuredMetric] as number)}</td>
                      <td>{p.phash_distance}</td>
                      <td>{p.dhash_distance}</td>
                      <td>
                        {p.byte_duplicate
                          ? 'SHA-256 byte duplicate'
                          : p.near_candidate
                            ? 'Perceptual candidate'
                            : 'Distinct candidate'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Notice>
              SHA-256 compares original file bytes, including metadata. Perceptual hashes compare
              visual structure heuristically. Identical histograms do not imply identical images.{' '}
              {result.groups.length} candidate groups formed by transitive threshold links.
            </Notice>
          </Section>
          {selected && (
            <Section title="Inspect the selected pair">
              <div className="comparison-previews">
                <figure>
                  <img src={preview(selected.left)} alt={selected.left_name} />
                  <figcaption>{selected.left_name}</figcaption>
                </figure>
                <figure>
                  <img src={preview(selected.right)} alt={selected.right_name} />
                  <figcaption>{selected.right_name}</figcaption>
                </figure>
              </div>
              <table>
                <tbody>
                  {Object.entries(selected.distances)
                    .filter(([, v]) => typeof v === 'number' || v === null)
                    .map(([key, value]) => (
                      <tr key={key}>
                        <td>{key.replaceAll('_', ' ')}</td>
                        <td>
                          {value === null && key.startsWith('kl')
                            ? '+∞'
                            : typeof value === 'number'
                              ? fmt(value, 5)
                              : 'Unavailable'}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
              <p className="muted small">
                {String(selected.distances.units)} {String(selected.distances.symmetry)}
              </p>
            </Section>
          )}
        </>
      )}
    </>
  );
}

export function HistoryView({
  w,
  active,
  navigate,
}: {
  w: Workbench;
  active: boolean;
  navigate: (page: string) => void;
}) {
  const { setError } = w;
  const [records, setRecords] = useState<HistoryRecord[]>([]);
  const [confirmClear, setConfirmClear] = useState(false);
  const refresh = async () => {
    try {
      const h = await api<{ records: HistoryRecord[] }>('/history');
      setRecords(h.records);
    } catch (e) {
      w.setError(String(e));
    }
  };
  useEffect(() => {
    if (active) {
      api<{ records: HistoryRecord[] }>('/history')
        .then((h) => setRecords(h.records))
        .catch((e) => setError(String(e)));
    }
  }, [active, setError]);
  const open = async (id: string, download = false) => {
    try {
      const r = await api<{ result: Analysis; source_available: boolean }>(`/history/${id}`);
      if (download) downloadJSON(r.result, 'saved-analysis.json');
      else {
        w.openSaved(r.result, r.source_available);
        navigate('analysis');
      }
    } catch (e) {
      w.setError(String(e));
    }
  };
  return (
    <>
      <Notice>
        {w.health?.history_enabled
          ? 'History is enabled. Saving is opt-in per analysis using the Settings checkbox. Stored records contain filenames, hashes, configuration and measured results; no images or EXIF. Charts include derived distributions and entropy fields.'
          : 'History is disabled by default. Set IEA_HISTORY=true before starting FastAPI to enable a local SQLite database. Source images remain in server memory only.'}
      </Notice>
      <Section
        title="Previous analyses"
        action={
          <div className="button-group">
            <button onClick={() => void refresh()}>
              <RefreshCw size={14} />
              Refresh
            </button>
            {w.health?.history_enabled && (
              <button disabled={!records.length} onClick={() => setConfirmClear(true)}>
                <Trash2 size={14} />
                Clear all
              </button>
            )}
          </div>
        }
      >
        {confirmClear && (
          <div className="confirm-box">
            <p>Delete every saved analysis result from the local database?</p>
            <button onClick={() => setConfirmClear(false)}>Keep records</button>
            <button
              className="danger"
              onClick={() => {
                void api('/history', undefined, 'DELETE')
                  .then(() => {
                    setConfirmClear(false);
                    void refresh();
                  })
                  .catch((e) => w.setError(String(e)));
              }}
            >
              Delete all records
            </button>
          </div>
        )}
        {records.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Saved at</th>
                  <th>SHA-256</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <button onClick={() => void open(r.id)}>{r.filename}</button>
                    </td>
                    <td>{new Date(r.created).toLocaleString()}</td>
                    <td>
                      <code>{r.sha256.slice(0, 16)}…</code>
                    </td>
                    <td>
                      <div className="button-group">
                        <button
                          aria-label={`Export ${r.filename}`}
                          onClick={() => void open(r.id, true)}
                        >
                          <Download size={14} />
                        </button>
                        <button
                          aria-label={`Delete record ${r.filename}`}
                          onClick={() => {
                            void api(`/history/${r.id}`, undefined, 'DELETE')
                              .then(refresh)
                              .catch((e) => w.setError(String(e)));
                          }}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">
            No saved results yet. Enable history and opt in when running an analysis.
          </p>
        )}
        <p className="muted small mt">
          Reopening a saved result restores measurements. Pixel inspection requires the source to
          remain in memory or be uploaded again. A hash cannot reconstruct an image. Shows the
          latest 200 records.
        </p>
      </Section>
    </>
  );
}

export function SettingsView({ w }: { w: Workbench }) {
  return (
    <>
      <Section title="Analysis configuration" eyebrow="PERSISTED IN THIS BROWSER">
        <div className="controls">
          <NumberField
            label="Rényi order α (0–100)"
            value={w.options.alpha}
            max={100}
            step={0.1}
            onChange={(alpha) => w.setOptions((o) => ({ ...o, alpha }))}
          />
          <NumberField
            label="Joint / spatial quantization levels"
            value={w.options.levels}
            min={2}
            max={256}
            onChange={(levels) => w.setOptions((o) => ({ ...o, levels }))}
          />
          <NumberField
            label="Preview maximum side"
            value={w.options.preview_size}
            min={64}
            max={1024}
            onChange={(preview_size) => w.setOptions((o) => ({ ...o, preview_size }))}
          />
          <NumberField
            label="Palette clusters"
            value={w.options.palette_size}
            min={2}
            max={12}
            onChange={(palette_size) => w.setOptions((o) => ({ ...o, palette_size }))}
          />
        </div>
        <label className="field">
          Multiscale windows (choose up to five)
          <div className="button-group">
            {[3, 5, 9, 15, 21, 31, 63].map((s) => (
              <label className="check" key={s}>
                <input
                  type="checkbox"
                  checked={w.options.scales.includes(s)}
                  disabled={
                    (!w.options.scales.includes(s) && w.options.scales.length >= 5) ||
                    (w.options.scales.includes(s) && w.options.scales.length === 1)
                  }
                  onChange={(e) =>
                    w.setOptions((o) => ({
                      ...o,
                      scales: e.target.checked
                        ? [...o.scales, s].sort((a, b) => a - b)
                        : o.scales.filter((v) => v !== s),
                    }))
                  }
                />
                {s}×{s}
              </label>
            ))}
          </div>
        </label>
        <label className="check mt">
          <input
            type="checkbox"
            disabled={!w.health?.history_enabled}
            checked={w.options.save_history}
            onChange={(e) => w.setOptions((o) => ({ ...o, save_history: e.target.checked }))}
          />
          Save subsequent analyses to local history
        </label>
        <Notice>
          Configuration changes apply when you run analysis again. Exact mode processes the selected
          full-resolution image. Preview mode explicitly reports native-symbol subsampling and an
          8-bit Lanczos spatial preview.
        </Notice>
      </Section>
      {w.health && (
        <>
          <Section title="Resource controls" eyebrow="SERVER STARTUP CONFIGURATION">
            <div className="metrics-grid">
              <Metric label="Maximum upload" value={`${w.health.limits.max_upload_mb} MB`} />
              <Metric
                label="Decoded pixel limit"
                value={`${fmt(w.health.limits.max_pixels / 1e6, 1)} MP`}
                unit={`${fmt(w.health.limits.max_analysis_pixels / 1e6, 1)} MP working budget`}
              />
              <Metric label="Source memory budget" value={`${w.health.limits.store_mb} MB`} />
              <Metric
                label="CPU workers"
                value={String(w.health.limits.workers)}
                unit={`${w.health.limits.job_seconds}s cooperative job deadline`}
              />
            </div>
            <p className="muted small">
              Adjust IEA_MAX_UPLOAD_MB, IEA_MAX_PIXELS, IEA_MAX_ANALYSIS_PIXELS, IEA_STORE_MB,
              IEA_WORKERS and IEA_JOB_SECONDS before starting the backend. Expensive exact local
              windows can be rejected with a request to select preview mode.
            </p>
          </Section>
          <Section title="Installed codec capabilities">
            <p>
              <b>Decoders:</b> {w.health.capabilities.decode_formats.join(', ')}
            </p>
            <p>
              <b>Encoders:</b> {w.health.capabilities.encode_formats.join(', ')}
            </p>
          </Section>
          <Section title="Privacy & reproducibility">
            <p>{w.health.privacy}</p>
            <p>
              Browser uploads go to your running server. When hosted remotely, images leave the
              browser device. No external image processing services, paid APIs, downloadable models,
              or telemetry are required by the application.
            </p>
            <p className="muted small">
              Analysis version {w.health.version}. Colour conversion assumes sRGB / D65. Synthetic
              demo and processing seeds are deterministic. Run one backend process; image IDs and
              jobs are memory-local.
            </p>
            <a className="button" href="/api/v1/docs" target="_blank" rel="noreferrer">
              Interactive API reference ↗
            </a>
          </Section>
        </>
      )}
    </>
  );
}
