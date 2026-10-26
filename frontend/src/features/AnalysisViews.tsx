import { useState } from 'react';
import { ArrowUpRight, Download } from 'lucide-react';
import { Chart } from '../components/Chart';
import { heatOption, lineOption } from '../lib/chartOptions';
import { ImageViewer } from '../components/ImageViewer';
import { Empty, Metric, Notice, NumberField, Section } from '../components/UI';
import { downloadJSON, fmt } from '../lib/api';
import type { Workbench } from '../hooks/useWorkbench';
import type { Analysis } from '../types';

export function Overview({ w, navigate }: { w: Workbench; navigate: (page: string) => void }) {
  const a = w.result;
  return (
    <>
      <div className="welcome">
        <div>
          <span className="eyebrow">A CLOSER LOOK AT YOUR PIXELS</span>
          <h2>
            Every image has
            <br />a story in its <em>statistics.</em>
          </h2>
          <p>
            Explore information, colour and structure.
            <br />
            Measure what changes. Understand what stays.
          </p>
          <button
            className="primary"
            disabled={w.busy || w.running || !w.health}
            onClick={() => void w.addDemo()}
          >
            Explore a synthetic landscape <ArrowUpRight size={16} />
          </button>
        </div>
        <div className="welcome-art" aria-hidden="true">
          <div className="art-sun" />
          <div className="art-hill far" />
          <div className="art-hill near" />
          <div className="art-grid" />
          <span>PROCEDURAL LANDSCAPE / SEED 42</span>
        </div>
      </div>
      <div className="overview-strip">
        <span>
          <b>01</b> Start with an image
        </span>
        <span>
          <b>02</b> Explore its structure
        </span>
        <span>
          <b>03</b> Run an experiment
        </span>
      </div>
      {a ? (
        <>
          <div className="metrics-grid">
            <Metric
              accent
              label="Shannon entropy"
              value={a.entropy.shannon}
              unit={a.entropy.unit}
            />
            <Metric
              label="Observed states"
              value={String(a.entropy.unique_symbols.toLocaleString())}
              unit={`of 2^${a.measurement.native_entropy_bits} possible`}
            />
            <Metric
              label="Local entropy · mean"
              value={a.local.mean}
              unit="bits / patch intensity symbol"
            />
            <Metric
              label="Analysis time"
              value={`${fmt(a.elapsed_ms, 0)} ms`}
              unit={`${a.measurement.mode} · ${a.measurement.width} × ${a.measurement.height}`}
            />
          </div>
          <div className="two-columns">
            <Section title="Intensity, in perspective" eyebrow="DISTRIBUTION">
              <Chart
                label="Grayscale intensity histogram"
                option={lineOption(
                  a.histogram.values,
                  [{ name: 'Pixel count', values: a.histogram.counts }],
                  'Intensity symbol',
                  'Pixel count',
                )}
              />
            </Section>
            <Section
              title="The colours within"
              eyebrow="APPROXIMATE CIELAB PALETTE"
              action={
                <button onClick={() => navigate('colour')}>
                  Explore <ArrowUpRight size={14} />
                </button>
              }
            >
              <Palette a={a} />
              <p className="muted small">{a.colour.palette_method}</p>
            </Section>
          </div>
        </>
      ) : (
        <Section title="A workbench for curious eyes" eyebrow="BUILT FOR EXPLORATION">
          <div className="feature-grid">
            {[
              [
                'analysis',
                'Information theory',
                'Eight entropy measures. Exact sparse RGB tuples. Quantization experiments.',
              ],
              [
                'spatial',
                'Structure & space',
                'Local entropy maps, neighbour dependence, co-occurrence and frequency.',
              ],
              [
                'compression',
                'Real experiments',
                'Encode. Decode. Measure actual file sizes and reconstruction differences.',
              ],
            ].map(([key, title, text]) => (
              <button className="feature-link" key={key} onClick={() => navigate(key)}>
                <span className="feature-number">
                  {key === 'analysis' ? 'H(X)' : key === 'spatial' ? '∇' : '↔'}
                </span>
                <h3>
                  {title}
                  <ArrowUpRight size={17} />
                </h3>
                <p>{text}</p>
              </button>
            ))}
          </div>
        </Section>
      )}
      <Section title="Controlled inputs. Reproducible discoveries." eyebrow="SYNTHETIC EXPERIMENTS">
        <div className="demo-grid">
          {[
            ['constant', 'Constant', 'One symbol. Zero uncertainty.'],
            ['gradient', 'Gradient', 'Smooth structure, broad distribution.'],
            ['checkerboard', 'Checkerboard', 'Two values, strong dependence.'],
            ['noise', 'Random noise', 'Independent RGB values, seed 42.'],
          ].map(([kind, title, text]) => (
            <button
              key={kind}
              className="demo-button"
              disabled={w.busy || w.running || !w.health}
              onClick={() => void w.addDemo(kind)}
            >
              <span className={`demo-swatch ${kind}`} />
              <span>
                <b>{title}</b>
                <small>{text}</small>
              </span>
              <ArrowUpRight size={16} />
            </button>
          ))}
        </div>
      </Section>
    </>
  );
}

export function Palette({ a }: { a: Analysis }) {
  return (
    <div className="palette">
      <div className="palette-bar">
        {a.colour.palette.map((c, i) => (
          <div
            key={i}
            style={{ background: c.hex, flex: c.proportion }}
            title={`${c.hex} · ${fmt(c.proportion * 100, 1)}%`}
          />
        ))}
      </div>
      <div className="palette-values">
        {a.colour.palette.map((c, i) => (
          <div key={i}>
            <i style={{ background: c.hex }} />
            <code>{c.hex}</code>
            <small>{fmt(c.proportion * 100, 1)}%</small>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SingleAnalysis({ w }: { w: Workbench }) {
  const a = w.result;
  if (!a) return <Empty />;
  return (
    <>
      <div className="metrics-grid">
        <Metric
          accent
          label="Shannon H(X)"
          value={a.entropy.shannon}
          unit={a.entropy.unit}
          hint="Expected self-information of an observed intensity symbol. Spatial order is ignored."
        />
        <Metric
          label="Theoretical maximum"
          value={a.entropy.maximum}
          unit="bits / intensity symbol"
          hint="log₂ K for K possible integer values, derived from the selected measurement bit depth."
        />
        <Metric
          label="Normalized entropy"
          value={a.entropy.normalized}
          unit="dimensionless · H / Hmax"
        />
        <Metric
          label="Effective states"
          value={a.entropy.effective_states}
          unit="2^H · perplexity"
        />
      </div>
      <div className="two-columns">
        <Section title="Source inspection" eyebrow={a.image.filename}>
          {w.image ? (
            <ImageViewer
              image={w.image}
              onRegion={(r) => w.setOptions((old) => ({ ...old, region: r }))}
            />
          ) : (
            <Notice>
              The saved result is available. Re-upload the source to use pixel inspection.
            </Notice>
          )}
          {w.options.region && (
            <button
              className="primary"
              disabled={w.running}
              onClick={() => void w.analyse(a.image.id)}
            >
              Analyse selected region
            </button>
          )}
        </Section>
        <Section
          title="Entropy family"
          action={
            <button onClick={() => downloadJSON(a, 'analysis.json')}>
              <Download size={14} />
              JSON
            </button>
          }
        >
          <table>
            <thead>
              <tr>
                <th>Measurement</th>
                <th>bits / intensity symbol</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['Shannon', a.entropy.shannon],
                ['Hartley · observed support', a.entropy.hartley],
                [`Rényi · α = ${a.entropy.alpha}`, a.entropy.renyi],
                ['Collision · Rényi α = 2', a.entropy.collision],
                ['Min-entropy · α → ∞', a.entropy.min_entropy],
                ['Entropy deficit · Hmax − H', a.entropy.entropy_deficit],
              ].map(([name, value]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td className="numeric">{fmt(value as number, 5)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Notice>
            Entropy deficit is relative to the selected alphabet. It is not a measurement of
            compression savings or visual quality.
          </Notice>
        </Section>
      </div>
      <Section
        title="Observed intensity distribution"
        eyebrow={`${a.measurement.native_entropy_bits}-BIT MEASUREMENT`}
      >
        <Chart
          label="Native intensity distribution"
          option={lineOption(
            a.histogram.values,
            [{ name: 'Observed count', values: a.histogram.counts }],
            'Intensity symbol',
            'Pixel count',
          )}
        />
        <p className="muted small">
          {a.measurement.native_definition} {a.histogram.display}
        </p>
      </Section>
      <Section
        title="What happens when we reduce the alphabet?"
        eyebrow="ENTROPY UNDER QUANTIZATION"
      >
        <Chart
          label="Entropy against quantization levels"
          option={lineOption(
            a.quantization.map((q) => q.levels),
            [
              { name: 'Measured entropy', values: a.quantization.map((q) => q.entropy) },
              { name: 'Theoretical maximum', values: a.quantization.map((q) => q.maximum) },
            ],
            'Quantization levels',
            'bits / quantized symbol',
          )}
        />
        <p className="muted small">{a.measurement.quantization_definition}</p>
      </Section>
    </>
  );
}

export function SpatialView({ w }: { w: Workbench }) {
  const a = w.result;
  const [patch, setPatch] = useState('Click a heatmap cell to inspect its measured value.');
  if (!a) return <Empty />;
  return (
    <>
      <div className="controls">
        <NumberField
          label="Window size (odd)"
          value={w.options.window}
          min={3}
          max={63}
          step={2}
          onChange={(window) => w.setOptions((o) => ({ ...o, window }))}
        />
        <NumberField
          label="Stride"
          value={w.options.stride}
          min={1}
          max={64}
          onChange={(stride) => w.setOptions((o) => ({ ...o, stride }))}
        />
        <label className="field">
          Method
          <select
            value={w.options.local_method}
            onChange={(e) =>
              w.setOptions((o) => ({ ...o, local_method: e.target.value as 'sliding' | 'block' }))
            }
          >
            <option value="sliding">Sliding windows</option>
            <option value="block">Non-overlapping blocks</option>
          </select>
        </label>
        <button
          className="primary"
          disabled={w.running || !w.image}
          onClick={() => void w.analyse(a.image.id)}
        >
          Recalculate maps
        </button>
      </div>
      <div className="metrics-grid">
        <Metric
          accent
          label="Local entropy · mean"
          value={a.local.mean}
          unit="bits / patch intensity symbol"
        />
        <Metric label="Local minimum" value={a.local.min} unit="bits / patch intensity symbol" />
        <Metric label="Local maximum" value={a.local.max} unit="bits / patch intensity symbol" />
        <Metric
          label="Spatial quantization"
          value={`${a.spatial.levels} levels`}
          unit="equal-width · 8-bit preview"
        />
      </div>
      <div className="two-columns">
        <Section
          title="Local entropy field"
          eyebrow={`${a.local.window} × ${a.local.window} WINDOW · ${a.local.method}`}
        >
          <Chart
            height={360}
            label="Local entropy heatmap aligned with image coordinates"
            option={heatOption(a.local.map, a.local.x, a.local.y, 8)}
            onSelect={([x, y, v]) =>
              setPatch(
                `Source measurement coordinate (${a.local.x[x]}, ${a.local.y[y]}): ${fmt(v, 5)} bits / patch intensity symbol.`,
              )
            }
          />
          <p className="small">{patch}</p>
          <p className="muted small">
            {a.local.boundary} Grid uses nearest cell display. Map display decimation:{' '}
            {a.local.display_decimation}×. Coordinates refer to {a.measurement.width} ×{' '}
            {a.measurement.height} analysis input.
          </p>
        </Section>
        <Section title="Structure across scales" eyebrow="MULTISCALE PROFILE">
          <Chart
            label="Mean local entropy by window size"
            option={lineOption(
              a.multiscale.map((s) => `${s.window}×${s.window}`),
              [
                { name: 'Mean local entropy', values: a.multiscale.map((s) => s.mean) },
                { name: 'Maximum local entropy', values: a.multiscale.map((s) => s.max) },
              ],
              'Window size',
              'bits / patch intensity symbol',
            )}
          />
          <Notice>
            Shuffle the pixels in the transformation lab. The histogram can stay exactly the same
            while local entropy and neighbour dependence change.
          </Notice>
        </Section>
      </div>
      <Section title="The information between neighbours" eyebrow="DIRECTED PIXEL PAIRS">
        <Chart
          label="Spatial dependence at coarser resolutions"
          option={lineOption(
            a.multiscale.map((s) => `1/${s.window}`),
            [
              {
                name: 'Horizontal mutual information',
                values: a.multiscale.map((s) => s.coarse_neighbour_mi ?? null),
              },
            ],
            'Area-averaged image scale',
            'Mutual information · bits',
          )}
        />
        <p className="muted small">
          {a.multiscale[0]?.coarse_definition} Undefined neighbour statistics for one-pixel-wide
          results are shown as gaps in the profile.
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Direction / lag</th>
                <th>Joint H(X,Y) · bits/pair</th>
                <th>I(X;Y) · bits</th>
                <th>H(Y|X) · bits/value</th>
                <th>Correlation</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(a.spatial.neighbours).map(([key, v]) => (
                <tr key={key}>
                  <td>{key.replaceAll('_', ' ')}</td>
                  <td>{fmt(v?.joint_entropy)}</td>
                  <td>{fmt(v?.mutual_information)}</td>
                  <td>{fmt(v?.conditional_y_given_x)}</td>
                  <td>{fmt(v?.correlation)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small">{a.spatial.definition}</p>
      </Section>
      {a.spatial.glcm && (
        <Section title="Gray-level co-occurrence">
          <div className="metrics-grid compact">
            {Object.entries(a.spatial.glcm).map(([key, value]) => (
              <Metric key={key} label={key} value={value} />
            ))}
          </div>
        </Section>
      )}
      <div className="two-columns">
        <Section title="Log power spectrum" eyebrow="FREQUENCY DOMAIN">
          <Chart
            height={340}
            label="2D Fourier log power spectrum"
            option={heatOption(
              a.frequency.log_power,
              a.frequency.fx.map((v) => fmt(v, 2)),
              a.frequency.fy.map((v) => fmt(v, 2)),
              Math.max(...a.frequency.log_power.flat()),
              'ln(1 + power)',
            )}
          />
          <p className="muted small">
            Axes: cycles / pixel. Spectrum display decimated for plotting.
          </p>
        </Section>
        <Section title="Radial energy profile">
          <Metric
            label="Spectral entropy"
            value={a.frequency.spectral_entropy}
            unit="bits / frequency-bin distribution"
          />
          <Chart
            label="Radial frequency energy"
            option={lineOption(
              a.frequency.radial_frequency.map((v) => fmt(v, 2)),
              [{ name: 'Energy fraction', values: a.frequency.radial_energy }],
              'Radial frequency · cycles/pixel',
              'Fraction of AC energy',
            )}
          />
          <div className="inline-stats">
            {Object.entries(a.frequency.energy).map(([k, v]) => (
              <span key={k}>
                {k}: <b>{fmt(v * 100, 1)}%</b>
              </span>
            ))}
          </div>
        </Section>
      </div>
      <Notice>{a.frequency.definition}</Notice>
    </>
  );
}

export function ColourView({ w }: { w: Workbench }) {
  const a = w.result;
  const [distribution, setDistribution] = useState('hue');
  if (!a) return <Empty />;
  const d = a.colour.distributions[distribution];
  return (
    <>
      <div className="metrics-grid">
        <Metric
          accent
          label="Joint RGB entropy"
          value={a.rgb.joint_exact}
          unit="bits / observed colour tuple"
        />
        <Metric
          label="Joint theoretical maximum"
          value={a.rgb.joint_maximum}
          unit={`bits / ${a.measurement.native_rgb_bits}-bit RGB tuple`}
        />
        <Metric
          label="Total correlation"
          value={a.rgb.total_correlation_quantized}
          unit={`bits · ${a.rgb.levels} levels/channel`}
          hint="Sum of quantized marginal entropies minus quantized RGB joint entropy."
        />
        <Metric
          label="Linear relative luminance"
          value={a.colour.linear_luminance_mean}
          unit="mean · [0,1] · sRGB transfer decoded"
        />
      </div>
      <Notice>
        {a.rgb.source}. {a.rgb.mode}
      </Notice>
      <div className="two-columns">
        <Section title="RGB distributions" eyebrow="8-BIT STANDARDIZED COLOUR">
          <Chart
            label="RGB channel histograms"
            option={{
              ...lineOption(
                Array.from({ length: 256 }, (_, i) => i),
                Object.entries(a.colour.rgb_histograms).map(([name, values]) => ({ name, values })),
                'Channel value',
                'Pixel count',
              ),
              color: ['#b16b61', '#6c8c70', '#66869e'],
            }}
          />
        </Section>
        <Section title="Marginal channel information">
          <div className="metrics-grid compact">
            {Object.entries(a.rgb.marginal).map(([key, v]) => (
              <Metric key={key} label={`${key} entropy`} value={v} unit="bits / channel value" />
            ))}
          </div>
          <table>
            <thead>
              <tr>
                <th>Quantized channel pair</th>
                <th>MI · bits</th>
                <th>H(X|Y) · bits/value</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(a.rgb.pairs).map(([key, v]) => (
                <tr key={key}>
                  <td>{key}</td>
                  <td>{fmt(v.mutual_information)}</td>
                  <td>{fmt(v.conditional_x_given_y)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      </div>
      <Section
        title="A perceptual palette"
        eyebrow={`CIELAB CLUSTERING · ${a.colour.palette_sample.toLocaleString()} SAMPLED PIXELS`}
      >
        <Palette a={a} />
        <p className="muted small">{a.colour.palette_method}</p>
      </Section>
      <Section
        title="Beyond red, green and blue"
        action={
          <label className="field">
            Distribution
            <select value={distribution} onChange={(e) => setDistribution(e.target.value)}>
              {Object.keys(a.colour.distributions).map((k) => (
                <option key={k}>{k}</option>
              ))}
            </select>
          </label>
        }
      >
        <Chart
          label={`${distribution} distribution`}
          option={lineOption(
            d.centres.map((v) => fmt(v, 2)),
            [{ name: distribution, values: d.counts }],
            distribution,
            'Pixel count',
          )}
        />
        <div className="inline-stats">
          <span>
            Mean: <b>{fmt(d.mean)}</b>
          </span>
          <span>
            Standard deviation: <b>{fmt(d.std)}</b>
          </span>
          <span>
            Colourfulness heuristic: <b>{fmt(a.colour.colourfulness)}</b>
          </span>
        </div>
      </Section>
      <Section title="Channel correlations">
        <Chart
          height={240}
          label="RGB Pearson correlation matrix"
          option={heatOption(
            a.colour.channel_correlations,
            ['R', 'G', 'B'],
            ['R', 'G', 'B'],
            1,
            'Pearson r',
            -1,
          )}
        />
        <p className="muted small">
          Constant-channel correlations are undefined and omitted from this chart. The colour scale
          spans −1 to +1.
        </p>
      </Section>
      {a.colour.alpha && (
        <Section title="Transparency">
          <div className="metrics-grid">
            <Metric
              label="Alpha entropy"
              value={a.colour.alpha.entropy}
              unit="bits / alpha value"
            />
            <Metric
              label="Fully transparent"
              value={`${fmt(a.colour.alpha.transparent_ratio * 100, 1)}%`}
            />
            <Metric label="Fully opaque" value={`${fmt(a.colour.alpha.opaque_ratio * 100, 1)}%`} />
          </div>
        </Section>
      )}
      <Notice>{a.colour.assumption}</Notice>
    </>
  );
}

export function DiagnosticsView({ w }: { w: Workbench }) {
  const a = w.result;
  if (!a) return <Empty />;
  const d = a.diagnostics;
  return (
    <>
      <Notice>
        Classical measurements, with context. Sharpness, exposure and noise estimates depend on
        image content. None is a verdict on visual quality.
      </Notice>
      <div className="metrics-grid">
        <Metric accent label="Mean brightness" value={d.mean} unit="8-bit encoded luma" />
        <Metric label="Brightness standard deviation" value={d.std} unit="intensity units" />
        <Metric
          label="Dynamic range"
          value={String(d.dynamic_range)}
          unit={`${d.min} → ${d.max} intensity`}
        />
        <Metric label="RMS contrast" value={d.rms_contrast} unit="standard deviation / 255" />
      </div>
      <div className="two-columns">
        <Section title="Exposure & clipping">
          <table>
            <thead>
              <tr>
                <th>Measurement</th>
                <th>Pixel fraction</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['Near black · ≤5', d.underexposed_ratio],
                ['Near white · ≥250', d.overexposed_ratio],
                ['Black clipped · exactly 0', d.black_clipped_ratio],
                ['White clipped · exactly 255', d.white_clipped_ratio],
              ].map(([name, v]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td>{fmt((v as number) * 100, 2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
        <Section title="Edges, detail & noise">
          <div className="metrics-grid compact">
            <Metric
              label="Laplacian variance"
              value={d.laplacian_variance}
              unit="intensity² · sharpness proxy"
            />
            <Metric
              label="Edge density"
              value={`${fmt(d.edge_density * 100, 2)}%`}
              unit="Canny edge pixels"
            />
            <Metric
              label="Noise σ estimate"
              value={d.noise_sigma}
              unit="intensity · Haar detail MAD"
            />
          </div>
        </Section>
      </div>
      <Section title="Gradient magnitude distribution">
        <Chart
          label="Sobel gradient magnitude histogram"
          option={lineOption(
            d.gradient_histogram.centres.map((v) => fmt(v, 0)),
            [{ name: 'Pixel count', values: d.gradient_histogram.counts }],
            'Sobel gradient magnitude',
            'Pixel count',
          )}
        />
      </Section>
      <Section title="How to read these measurements">
        <div className="definition-list">
          {Object.entries(d.definitions).map(([key, text]) => (
            <div key={key}>
              <h3>{key.replaceAll('_', ' ')}</h3>
              <p>{text}</p>
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}
