import { useState } from 'react';
import { Download, Play, Plus, RotateCcw, Trash2, Undo2 } from 'lucide-react';
import { Chart } from '../components/Chart';
import { lineOption } from '../lib/chartOptions';
import { ImageViewer } from '../components/ImageViewer';
import { DifferencePreview } from '../components/DifferencePreview';
import { Empty, Metric, Notice, NumberField, Section, Spinner } from '../components/UI';
import type { Workbench } from '../hooks/useWorkbench';
import { API, api, bytes, fmt } from '../lib/api';
import type { Experiment, TransformKind, TransformStep } from '../types';

function ExperimentResult({ result, w }: { result: Experiment; w: Workbench }) {
  const [zoom, setZoom] = useState(1);
  const original = w.images.find((i) => i.id === result.original_image_id);
  return (
    <>
      <div className="metrics-grid">
        <Metric
          accent
          label="Entropy change"
          value={result.entropy_after - result.entropy_before}
          unit="bits / 8-bit luma symbol"
        />
        <Metric label="Mean absolute error" value={result.mae} unit="RGB8 intensity units" />
        <Metric
          label="PSNR"
          value={result.mse === 0 ? '∞' : result.psnr}
          unit="dB · unavailable if unaligned"
        />
        <Metric label="SSIM" value={result.ssim} unit="RGB8 · window up to 7×7" />
      </div>
      <div className="two-columns">
        <Section title="Original" eyebrow="SYNCHRONIZED ZOOM">
          {original && <ImageViewer image={original} zoom={zoom} onZoom={setZoom} />}
        </Section>
        <Section
          title="Reconstruction"
          action={
            <a className="button" href={`${API}/images/${result.image.id}/download`} download>
              <Download size={14} />
              Download
            </a>
          }
        >
          <ImageViewer image={result.image} zoom={zoom} onZoom={setZoom} />
        </Section>
      </div>
      <div className="two-columns">
        <Section title="Difference field" eyebrow="NORMALIZED ABSOLUTE RGB ERROR">
          {result.difference_image ? (
            <DifferencePreview
              key={result.difference_image.id}
              imageId={result.difference_image.id}
              maximum={result.difference_display_max}
            />
          ) : (
            <Notice>
              Pixelwise differences require matching dimensions. Distribution statistics remain
              comparable.
            </Notice>
          )}
        </Section>
        <Section title="Before & after">
          <table>
            <thead>
              <tr>
                <th>Measurement</th>
                <th>Original</th>
                <th>Processed</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Entropy · bits/luma symbol</td>
                <td>{fmt(result.entropy_before)}</td>
                <td>{fmt(result.entropy_after)}</td>
              </tr>
              <tr>
                <td>Laplacian variance · intensity²</td>
                <td>{fmt(result.diagnostics_before.laplacian_variance)}</td>
                <td>{fmt(result.diagnostics_after.laplacian_variance)}</td>
              </tr>
              <tr>
                <td>Horizontal MI · bits</td>
                <td>{fmt(result.spatial_before.neighbours.horizontal?.mutual_information)}</td>
                <td>{fmt(result.spatial_after.neighbours.horizontal?.mutual_information)}</td>
              </tr>
              <tr>
                <td>RGB8 pixels equal</td>
                <td colSpan={2}>{result.pixel_equal ? 'Yes · exact decoded equality' : 'No'}</td>
              </tr>
              <tr>
                <td>Grayscale histograms equal</td>
                <td colSpan={2}>{result.histogram_equal ? 'Yes · measured bin by bin' : 'No'}</td>
              </tr>
              <tr>
                <td>Mean ΔE76 · Lab distance</td>
                <td colSpan={2}>{fmt(result.delta_e76_mean)}</td>
              </tr>
            </tbody>
          </table>
          <button
            className="primary mt"
            disabled={w.running}
            onClick={() => {
              w.addResultImage(result.image);
              w.setSelected(result.image.id);
              void w.analyse(result.image.id);
            }}
          >
            Add reconstruction to workspace
          </button>
        </Section>
      </div>
      <Notice>
        {result.notice} {result.evaluation}
      </Notice>
    </>
  );
}

export function CompressionView({ w }: { w: Workbench }) {
  const [codec, setCodec] = useState('JPEG');
  const [quality, setQuality] = useState(80);
  const [level, setLevel] = useState(6);
  const [lossless, setLossless] = useState(false);
  const [busy, setBusy] = useState(false);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [active, setActive] = useState(0);
  const run = async () => {
    if (!w.image) return;
    setBusy(true);
    w.setError('');
    try {
      const result = await api<Experiment>('/compression', {
        image_id: w.image.id,
        codec,
        quality,
        lossless,
        compress_level: level,
      });
      setExperiments((old) => [result, ...old]);
      setActive(0);
    } catch (e) {
      w.setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <Notice>
        Real bytes, real reconstruction. Encoders run locally on the server. A broad histogram does
        not predict an encoder's file size.
      </Notice>
      <div className="controls">
        <label className="field">
          Encoder
          <select value={codec} onChange={(e) => setCodec(e.target.value)}>
            {['JPEG', 'PNG', 'WEBP']
              .filter((c) => w.health?.capabilities.encode_formats.includes(c))
              .map((c) => (
                <option key={c}>{c}</option>
              ))}
          </select>
        </label>
        {codec === 'PNG' ? (
          <NumberField
            label="PNG compression level"
            value={level}
            min={0}
            max={9}
            onChange={setLevel}
          />
        ) : (
          <label className="field range-field">
            Quality · {quality}
            <input
              type="range"
              min={1}
              max={100}
              value={quality}
              onChange={(e) => setQuality(+e.target.value)}
            />
          </label>
        )}
        {codec === 'WEBP' && (
          <label className="check">
            <input
              type="checkbox"
              checked={lossless}
              onChange={(e) => setLossless(e.target.checked)}
            />
            Lossless WebP
          </label>
        )}
        <button
          className="primary"
          disabled={!w.image || busy || w.running}
          onClick={() => void run()}
        >
          {busy ? <Spinner /> : <Play size={14} />}Encode & measure
        </button>
      </div>
      {!experiments.length ? (
        <Empty>Choose an image, select an encoder, then run a real compression experiment.</Empty>
      ) : (
        <>
          <Section title="Experiment notebook" eyebrow="ACTUAL ENCODED RESULTS">
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Source</th>
                    <th>Encoded</th>
                    <th>Output / source</th>
                    <th>Encode / decode</th>
                    <th>Mode</th>
                    <th>Pixel equal</th>
                  </tr>
                </thead>
                <tbody>
                  {experiments.map((r, i) => (
                    <tr key={r.image.id} className={i === active ? 'selected-row' : ''}>
                      <td>
                        <button onClick={() => setActive(i)}>
                          {r.codec} · #{experiments.length - i}
                        </button>
                      </td>
                      <td>{bytes(r.source_bytes!)}</td>
                      <td>{bytes(r.encoded_bytes!)}</td>
                      <td>{fmt(r.size_ratio, 3)}×</td>
                      <td>
                        {fmt(r.encode_ms, 1)} / {fmt(r.decode_ms, 1)} ms
                      </td>
                      <td>{r.lossless_encoding ? 'Lossless RGB8 encoding' : 'Lossy'}</td>
                      <td>{r.source_pixel_equal ? 'Yes' : 'No'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
          {experiments.length > 1 && (
            <Section title="Rate & distortion">
              <Chart
                label="Compression size and error by run"
                option={lineOption(
                  experiments.map((_, i) => `${experiments.length - i}`),
                  [{ name: 'MAE · intensity units', values: experiments.map((r) => r.mae ?? 0) }],
                  'Experiment number',
                  'RGB8 MAE',
                )}
              />
            </Section>
          )}
          <ExperimentResult key={experiments[active].image.id} result={experiments[active]} w={w} />
        </>
      )}
    </>
  );
}

const kindLabels: Record<TransformKind, string> = {
  grayscale: 'Grayscale',
  resize: 'Resize',
  crop: 'Crop region',
  blur: 'Gaussian blur',
  sharpen: 'Sharpen',
  noise: 'Gaussian noise',
  denoise: 'Median denoise',
  brightness: 'Brightness',
  contrast: 'Contrast',
  saturation: 'Saturation',
  gamma: 'Gamma exponent',
  equalize: 'Histogram equalization',
  quantize: 'Intensity quantization',
  shuffle: 'Shuffle pixels',
  rotate: 'Rotate',
  flip: 'Flip',
  hsv: 'HSV component view',
  lab: 'Lab component view',
};
const noValue = new Set<TransformKind>(['grayscale', 'denoise', 'equalize', 'hsv', 'lab']);
export function TransformView({ w }: { w: Workbench }) {
  const [steps, setSteps] = useState<TransformStep[]>([]);
  const [kind, setKind] = useState<TransformKind>('shuffle');
  const [result, setResult] = useState<Experiment | null>(null);
  const [busy, setBusy] = useState(false);
  const [undo, setUndo] = useState<TransformStep[][]>([]);
  const change = (next: TransformStep[]) => {
    setUndo((old) => [...old.slice(-19), steps]);
    setSteps(next);
  };
  const add = () =>
    change([
      ...steps,
      {
        kind,
        value:
          kind === 'quantize'
            ? 8
            : kind === 'noise'
              ? 15
              : kind === 'blur'
                ? 2
                : kind === 'rotate'
                  ? 90
                  : 1,
        width: Math.min(w.image?.width ?? 256, 512),
        height: Math.min(w.image?.height ?? 256, 512),
        x: 0,
        y: 0,
        seed: 42,
        resampling: 'lanczos',
      },
    ]);
  const update = (index: number, partial: Partial<TransformStep>) =>
    change(steps.map((s, i) => (i === index ? { ...s, ...partial } : s)));
  const run = async () => {
    if (!w.image) return;
    setBusy(true);
    w.setError('');
    try {
      setResult(await api<Experiment>('/transforms', { image_id: w.image.id, steps }));
    } catch (e) {
      w.setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <Notice>
        An explicit processing pipeline, applied in order to the selected original. Most edits are
        lossy; shuffle is a deterministic pixel permutation. A fixed seed makes noise and shuffle
        reproducible.
      </Notice>
      <Section
        title="Build a transformation"
        eyebrow="ORDERED PIPELINE"
        action={
          <div className="button-group">
            <button
              disabled={!undo.length}
              onClick={() => {
                setSteps(undo[undo.length - 1]);
                setUndo((old) => old.slice(0, -1));
              }}
            >
              <Undo2 size={14} />
              Undo
            </button>
            <button
              disabled={!steps.length}
              onClick={() => {
                change([]);
                setResult(null);
              }}
            >
              <RotateCcw size={14} />
              Reset
            </button>
          </div>
        }
      >
        <div className="controls">
          <label className="field">
            Transformation
            <select value={kind} onChange={(e) => setKind(e.target.value as TransformKind)}>
              {Object.entries(kindLabels).map(([key, label]) => (
                <option value={key} key={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <button disabled={steps.length >= 16} onClick={add}>
            <Plus size={14} />
            Add step
          </button>
          <button
            className="primary"
            disabled={!w.image || !steps.length || busy || w.running}
            onClick={() => void run()}
          >
            {busy ? <Spinner /> : <Play size={14} />}Apply pipeline
          </button>
        </div>
        <div className="pipeline">
          {steps.map((step, index) => (
            <div className="pipeline-step" key={index}>
              <span className="step-index">{String(index + 1).padStart(2, '0')}</span>
              <div>
                <h3>{kindLabels[step.kind]}</h3>
                <div className="controls compact">
                  {!noValue.has(step.kind) &&
                    !['resize', 'crop', 'shuffle'].includes(step.kind) && (
                      <NumberField
                        label={
                          step.kind === 'flip'
                            ? '0 horizontal / 1 vertical'
                            : step.kind === 'noise'
                              ? 'Noise σ (0–100)'
                              : step.kind === 'quantize'
                                ? 'Levels (2–256)'
                                : 'Value'
                        }
                        value={step.value}
                        min={step.kind === 'gamma' ? 0.01 : 0}
                        step={
                          [
                            'gamma',
                            'brightness',
                            'contrast',
                            'saturation',
                            'blur',
                            'sharpen',
                          ].includes(step.kind)
                            ? 0.1
                            : 1
                        }
                        onChange={(value) => update(index, { value })}
                      />
                    )}
                  {['resize', 'crop'].includes(step.kind) && (
                    <>
                      <NumberField
                        label="Width"
                        value={step.width}
                        min={1}
                        onChange={(width) => update(index, { width })}
                      />
                      <NumberField
                        label="Height"
                        value={step.height}
                        min={1}
                        onChange={(height) => update(index, { height })}
                      />
                    </>
                  )}
                  {step.kind === 'resize' && (
                    <label className="field">
                      Resampling
                      <select
                        value={step.resampling}
                        onChange={(e) =>
                          update(index, {
                            resampling: e.target.value as TransformStep['resampling'],
                          })
                        }
                      >
                        {['nearest', 'bilinear', 'bicubic', 'lanczos'].map((r) => (
                          <option key={r}>{r}</option>
                        ))}
                      </select>
                    </label>
                  )}
                  {step.kind === 'crop' && (
                    <>
                      <NumberField
                        label="X origin"
                        value={step.x}
                        onChange={(x) => update(index, { x })}
                      />
                      <NumberField
                        label="Y origin"
                        value={step.y}
                        onChange={(y) => update(index, { y })}
                      />
                    </>
                  )}
                  {['shuffle', 'noise'].includes(step.kind) && (
                    <NumberField
                      label="Random seed"
                      value={step.seed}
                      max={4294967295}
                      onChange={(seed) => update(index, { seed })}
                    />
                  )}
                </div>
              </div>
              <button
                aria-label={`Remove step ${index + 1}`}
                onClick={() => change(steps.filter((_, i) => i !== index))}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
        {!steps.length && (
          <p className="muted">
            Add a step to begin. Try pixel shuffle to separate statistical uncertainty from spatial
            structure.
          </p>
        )}
      </Section>
      {result && <ExperimentResult key={result.image.id} result={result} w={w} />}
    </>
  );
}
