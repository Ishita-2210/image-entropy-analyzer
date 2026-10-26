import { useRef, useState } from 'react';
import {
  Activity,
  ArrowDownToLine,
  Blocks,
  ChevronRight,
  CircleHelp,
  Fingerprint,
  FlaskConical,
  History,
  Image,
  Layers,
  LayoutDashboard,
  Menu,
  Palette,
  ScanLine,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Upload,
  X,
} from 'lucide-react';
import { useWorkbench } from './hooks/useWorkbench';
import {
  Overview,
  SingleAnalysis,
  SpatialView,
  ColourView,
  DiagnosticsView,
} from './features/AnalysisViews';
import { CompressionView, TransformView } from './features/ExperimentViews';
import { BatchView, HistoryView, SettingsView, SimilarityView } from './features/WorkspaceViews';
import { Notice, Spinner } from './components/UI';
import { bytes, downloadJSON } from './lib/api';

const pages = [
  {
    id: 'overview',
    name: 'Overview',
    icon: LayoutDashboard,
    group: 'WORKSPACE',
    subtitle: 'A little curiosity. A lot of information.',
  },
  {
    id: 'analysis',
    name: 'Image analysis',
    icon: ScanLine,
    group: '',
    subtitle: 'Understand the information carried by intensity and colour.',
  },
  {
    id: 'spatial',
    name: 'Spatial & frequency',
    icon: Layers,
    group: 'EXPLORE',
    subtitle: 'Look beyond the histogram. Find structure in space and scale.',
  },
  {
    id: 'colour',
    name: 'Colour & information',
    icon: Palette,
    group: '',
    subtitle: 'Channel relationships, perceptual palettes and colour distributions.',
  },
  {
    id: 'diagnostics',
    name: 'Image diagnostics',
    icon: Activity,
    group: '',
    subtitle: 'Classical measurements for brightness, detail and degradation.',
  },
  {
    id: 'compression',
    name: 'Compression lab',
    icon: FlaskConical,
    group: 'EXPERIMENT',
    subtitle: 'Measure the real trade-off between size and reconstruction.',
  },
  {
    id: 'transforms',
    name: 'Transform playground',
    icon: SlidersHorizontal,
    group: '',
    subtitle: 'Change the image. Observe the information.',
  },
  {
    id: 'batch',
    name: 'Batch workspace',
    icon: Blocks,
    group: 'COLLECTION',
    subtitle: 'Analyse a collection, compare measurements and export results.',
  },
  {
    id: 'similarity',
    name: 'Similarity & duplicates',
    icon: Fingerprint,
    group: '',
    subtitle: 'Compare distributions. Investigate visual relationships.',
  },
  {
    id: 'history',
    name: 'Analysis history',
    icon: History,
    group: '',
    subtitle: 'Return to your measurements, with their original configuration.',
  },
  {
    id: 'settings',
    name: 'Settings',
    icon: Settings2,
    group: 'PREFERENCES',
    subtitle: 'Choose how you measure. Know where your data lives.',
  },
];
export default function App() {
  const w = useWorkbench();
  const [page, setPage] = useState('overview');
  const [visited, setVisited] = useState(new Set(['overview']));
  const [menu, setMenu] = useState(false);
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const navigate = (id: string) => {
    setPage(id);
    setVisited((old) => new Set([...old, id]));
    setMenu(false);
    window.scrollTo({ top: 0 });
  };
  const current = pages.find((p) => p.id === page)!;
  return (
    <div
      className="app-shell"
      onDragOver={(e) => {
        e.preventDefault();
        if (e.dataTransfer.types.includes('Files')) setDragging(true);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (e.dataTransfer.files.length) void w.upload(e.dataTransfer.files);
      }}
    >
      <aside className={`sidebar ${menu ? 'open' : ''}`}>
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate('overview');
          }}
        >
          <span className="brand-mark">
            <span />
            <span />
            <span />
            <span />
          </span>
          <span>
            Image Entropy
            <br />
            <b>Analyzer</b>
            <small>THE INTELLIGENCE WORKBENCH</small>
          </span>
        </a>
        <nav aria-label="Main navigation">
          {pages.map((p) => (
            <div key={p.id}>
              {p.group && <div className="nav-group">{p.group}</div>}
              <button
                className={`nav-item ${page === p.id ? 'selected' : ''}`}
                aria-current={page === p.id ? 'page' : undefined}
                onClick={() => navigate(p.id)}
              >
                <p.icon size={17} strokeWidth={1.6} />
                <span>{p.name}</span>
                {page === p.id && <span className="nav-dot" />}
              </button>
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <ShieldCheck size={18} />
          <div>
            <b>Your images. Your workspace.</b>
            <small>Local processing · no API keys</small>
          </div>
          <span className="version">v2.0</span>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            <button
              className="mobile-menu"
              aria-label="Toggle navigation"
              onClick={() => setMenu(!menu)}
            >
              <Menu size={19} />
            </button>
            <span>Workbench</span>
            <ChevronRight size={13} />
            <b>{current.name}</b>
          </div>
          <div>
            <span className={`connection ${w.health ? 'online' : ''}`}>
              <i />
              {w.health ? 'Local engine connected' : 'Connecting to engine'}
            </span>
            <button aria-label="Open settings and help" onClick={() => navigate('settings')}>
              <CircleHelp size={17} />
            </button>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <span className="eyebrow">
                IMAGE INTELLIGENCE / {String(pages.indexOf(current) + 1).padStart(2, '0')}
              </span>
              <h1>
                {current.name}
                <span className="title-dot">.</span>
              </h1>
              <p>{current.subtitle}</p>
            </div>
            <button onClick={() => input.current?.click()} disabled={w.busy}>
              <Upload size={15} />
              {w.busy ? 'Importing…' : 'Import images'}
            </button>
            <input
              ref={input}
              className="sr-only"
              type="file"
              aria-label="Upload images"
              multiple
              accept="image/*,.tif,.tiff"
              onChange={(e) => {
                if (e.target.files) void w.upload(e.target.files);
                e.target.value = '';
              }}
            />
          </div>
          {w.error && (
            <div className="error-banner" role="alert">
              <span>{w.error}</span>
              <button aria-label="Dismiss error" onClick={() => w.setError('')}>
                <X size={16} />
              </button>
            </div>
          )}
          {w.images.length > 0 && (
            <div className="workspace-toolbar">
              <div className="toolbar-source">
                <Image size={17} />
                <label className="sr-only" htmlFor="source-image">
                  Selected source image
                </label>
                <select
                  id="source-image"
                  value={w.selected}
                  onChange={(e) => {
                    w.setSelected(e.target.value);
                    w.setOptions((o) => ({ ...o, region: null }));
                  }}
                >
                  {w.images.map((i) => (
                    <option value={i.id} key={i.id}>
                      {i.filename}
                    </option>
                  ))}
                </select>
                {w.image && w.image.frames > 1 && (
                  <label className="field">
                    Frame
                    <select
                      aria-label="Select image frame"
                      value={w.image.frame}
                      disabled={w.busy || w.running}
                      onChange={(e) => void w.selectFrame(Number(e.target.value))}
                    >
                      {Array.from({ length: Math.min(w.image.frames, 100) }, (_, index) => (
                        <option key={index} value={index}>
                          {index + 1} / {w.image!.frames}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                {w.image && (
                  <small>
                    {w.image.width} × {w.image.height} · {bytes(w.image.bytes)}
                  </small>
                )}
              </div>
              <div className="toolbar-actions">
                <label className="sr-only" htmlFor="analysis-mode">
                  Analysis mode
                </label>
                <select
                  id="analysis-mode"
                  value={w.options.mode}
                  onChange={(e) =>
                    w.setOptions((o) => ({ ...o, mode: e.target.value as 'exact' | 'preview' }))
                  }
                >
                  <option value="exact">Exact analysis</option>
                  <option value="preview">Preview analysis</option>
                </select>
                <button
                  className="primary"
                  disabled={w.running || !w.image}
                  onClick={() => void w.analyse(w.selected)}
                >
                  {w.running ? <Spinner /> : <Activity size={14} />}Run analysis
                </button>
                <button
                  aria-label="Export selected analysis JSON"
                  disabled={!w.result}
                  onClick={() => downloadJSON(w.result, 'analysis.json')}
                >
                  <ArrowDownToLine size={16} />
                </button>
              </div>
            </div>
          )}
          {w.running && w.job && (
            <div className="job-progress" role="status">
              <div>
                <Spinner />
                <span>{w.job.stage}</span>
                <b>{Math.round(w.job.progress * 100)}%</b>
                <button onClick={() => void w.cancel()}>Cancel</button>
              </div>
              <progress max={1} value={w.job.progress} aria-label="Analysis progress" />
            </div>
          )}
          {w.result && page !== 'overview' && (
            <div className="measurement-strip">
              <span className="status-tag">
                {w.result.configuration.mode === 'exact'
                  ? 'EXACT SOURCE MEASUREMENT'
                  : 'EXPLICIT PREVIEW MEASUREMENT'}
              </span>
              <span>
                {w.result.measurement.width} × {w.result.measurement.height} analysed ·{' '}
                {w.result.configuration.region ? 'selected region' : 'whole image'} ·{' '}
                {w.result.version}
              </span>
            </div>
          )}
          {w.image?.warnings.map((warning, i) => (
            <Notice key={i}>{warning}</Notice>
          ))}
          {pages
            .filter((p) => visited.has(p.id))
            .map((p) => (
              <div key={p.id} hidden={p.id !== page}>
                {p.id === 'overview' ? (
                  <Overview w={w} navigate={navigate} />
                ) : p.id === 'analysis' ? (
                  <SingleAnalysis w={w} />
                ) : p.id === 'spatial' ? (
                  <SpatialView w={w} />
                ) : p.id === 'colour' ? (
                  <ColourView w={w} />
                ) : p.id === 'diagnostics' ? (
                  <DiagnosticsView w={w} />
                ) : p.id === 'compression' ? (
                  <CompressionView w={w} />
                ) : p.id === 'transforms' ? (
                  <TransformView w={w} />
                ) : p.id === 'batch' ? (
                  <BatchView w={w} />
                ) : p.id === 'similarity' ? (
                  <SimilarityView w={w} />
                ) : p.id === 'history' ? (
                  <HistoryView w={w} active={page === 'history'} navigate={navigate} />
                ) : (
                  <SettingsView w={w} />
                )}
              </div>
            ))}
          <footer>
            <span>IMAGE ENTROPY ANALYZER</span>
            <span>Built for a closer look.</span>
            <span>Scientific measurements. Thoughtful experiments.</span>
          </footer>
        </main>
      </div>
      {dragging && (
        <div className="drop-overlay" onDragLeave={() => setDragging(false)}>
          <Upload size={35} />
          <h2>Bring your images into focus.</h2>
          <p>Drop one image or a collection to start analysing.</p>
        </div>
      )}
    </div>
  );
}
