import { useEffect, useRef, useState } from 'react';
import { Crop, Hand, Maximize, Pipette, ZoomIn, ZoomOut } from 'lucide-react';
import { api, preview } from '../lib/api';
import type { ImageInfo, Region } from '../types';

export function ImageViewer({
  image,
  onRegion,
  zoom: linkedZoom,
  onZoom,
}: {
  image: ImageInfo;
  onRegion?: (r: Region | null) => void;
  zoom?: number;
  onZoom?: (zoom: number) => void;
}) {
  const [localZoom, setLocalZoom] = useState(1);
  const zoom = linkedZoom ?? localZoom;
  const setZoom = (n: number) => {
    setLocalZoom(n);
    onZoom?.(n);
  };
  const [mode, setMode] = useState<'inspect' | 'region' | 'pan'>('inspect');
  const [sample, setSample] = useState<{ rgb: number[]; hex: string } | null>(null);
  const [point, setPoint] = useState({ x: 0, y: 0 });
  const [region, setRegion] = useState<Region | null>(null);
  const [native, setNative] = useState('');
  const [loadError, setLoadError] = useState(false);
  const img = useRef<HTMLImageElement>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const worker = useRef<Worker | null>(null);
  const drag = useRef<{
    x: number;
    y: number;
    clientX: number;
    clientY: number;
    left: number;
    top: number;
  } | null>(null);
  useEffect(() => {
    const w = new Worker(new URL('../workers/pixels.ts', import.meta.url), { type: 'module' });
    worker.current = w;
    w.onmessage = (e) => setSample(e.data);
    return () => {
      w.terminate();
      worker.current = null;
    };
  }, []);
  useEffect(() => {
    setRegion(null);
    setNative('');
    setLoadError(false);
  }, [image.id]);
  const coordinates = (e: React.PointerEvent) => {
    const box = img.current!.getBoundingClientRect();
    return {
      x: Math.max(
        0,
        Math.min(image.width - 1, Math.floor(((e.clientX - box.left) / box.width) * image.width)),
      ),
      y: Math.max(
        0,
        Math.min(image.height - 1, Math.floor(((e.clientY - box.top) / box.height) * image.height)),
      ),
    };
  };
  const loaded = () => {
    const element = img.current!;
    const canvas = document.createElement('canvas');
    canvas.width = element.naturalWidth;
    canvas.height = element.naturalHeight;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    if (ctx) {
      ctx.drawImage(element, 0, 0);
      const buffer = ctx.getImageData(0, 0, canvas.width, canvas.height).data.buffer;
      worker.current?.postMessage({ type: 'init', buffer, width: canvas.width }, [buffer]);
    }
  };
  const move = (e: React.PointerEvent) => {
    if (!img.current) return;
    const p = coordinates(e);
    setPoint(p);
    worker.current?.postMessage({
      type: 'sample',
      x: Math.floor((p.x / image.width) * img.current.naturalWidth),
      y: Math.floor((p.y / image.height) * img.current.naturalHeight),
    });
    if (drag.current && mode === 'pan') {
      scroller.current!.scrollLeft = drag.current.left - (e.clientX - drag.current.clientX);
      scroller.current!.scrollTop = drag.current.top - (e.clientY - drag.current.clientY);
    }
    if (drag.current && mode === 'region') {
      const d = drag.current;
      setRegion({
        x: Math.min(p.x, d.x),
        y: Math.min(p.y, d.y),
        width: Math.abs(p.x - d.x) + 1,
        height: Math.abs(p.y - d.y) + 1,
      });
    }
  };
  const up = async () => {
    if (!drag.current) return;
    drag.current = null;
    if (mode === 'region') onRegion?.(region);
    if (mode === 'inspect') {
      try {
        const p = await api<{ native: number | number[]; bits: number }>(
          `/images/${image.id}/pixel?x=${point.x}&y=${point.y}`,
        );
        setNative(
          `${p.bits}-bit source: ${Array.isArray(p.native) ? p.native.join(', ') : p.native}`,
        );
      } catch (e) {
        setNative(String(e));
      }
    }
  };
  return (
    <div className="image-viewer">
      <div className="viewer-toolbar">
        <div className="button-group">
          <button
            className={mode === 'inspect' ? 'active' : ''}
            title="Inspect pixel"
            aria-label="Inspect pixel"
            onClick={() => setMode('inspect')}
          >
            <Pipette size={15} />
          </button>
          <button
            className={mode === 'pan' ? 'active' : ''}
            title="Pan"
            aria-label="Pan image"
            onClick={() => setMode('pan')}
          >
            <Hand size={15} />
          </button>
          {onRegion && (
            <button
              className={mode === 'region' ? 'active' : ''}
              title="Select region"
              aria-label="Select region"
              onClick={() => setMode('region')}
            >
              <Crop size={15} />
            </button>
          )}
        </div>
        <div className="button-group">
          <button aria-label="Zoom out" onClick={() => setZoom(Math.max(0.25, zoom / 1.4))}>
            <ZoomOut size={15} />
          </button>
          <span>{Math.round(zoom * 100)}%</span>
          <button aria-label="Zoom in" onClick={() => setZoom(Math.min(8, zoom * 1.4))}>
            <ZoomIn size={15} />
          </button>
          <button title="Fit image" aria-label="Fit image" onClick={() => setZoom(1)}>
            <Maximize size={15} />
          </button>
          <button onClick={() => setZoom(image.width / Math.min(620, image.width))}>1:1</button>
        </div>
      </div>
      <div className={`image-stage ${mode}`} ref={scroller}>
        {loadError ? (
          <p>Source expired or unavailable. Upload it again to inspect pixels.</p>
        ) : (
          <div
            className="image-surface"
            style={{ width: `${zoom * 100}%` }}
            onPointerMove={move}
            onPointerDown={(e) => {
              if (!img.current) return;
              const p = coordinates(e);
              setPoint(p);
              drag.current = {
                ...p,
                clientX: e.clientX,
                clientY: e.clientY,
                left: scroller.current!.scrollLeft,
                top: scroller.current!.scrollTop,
              };
              e.currentTarget.setPointerCapture(e.pointerId);
            }}
            onPointerUp={() => void up()}
            onPointerCancel={() => {
              drag.current = null;
            }}
          >
            <img
              ref={img}
              src={preview(image.id)}
              alt={image.filename}
              draggable={false}
              onLoad={loaded}
              onError={() => setLoadError(true)}
            />
            {region && (
              <div
                className="region-selection"
                style={{
                  left: `${(region.x / image.width) * 100}%`,
                  top: `${(region.y / image.height) * 100}%`,
                  width: `${(region.width / image.width) * 100}%`,
                  height: `${(region.height / image.height) * 100}%`,
                }}
              />
            )}
          </div>
        )}
      </div>
      <div className="viewer-status">
        <span>
          {image.width} × {image.height} · {image.native_bits}-bit
        </span>
        <span>
          x {point.x} · y {point.y}
        </span>
        {sample && (
          <span className="sample">
            <i style={{ backgroundColor: sample.hex }} />
            {sample.hex}
          </span>
        )}
      </div>
      <div className="viewer-caption">
        {native ||
          'Hover: 8-bit preview sampler. Click: native source values. Preview capped at 1024 px; coordinates map to source.'}
      </div>
      {region && (
        <div className="region-caption">
          Region: ({region.x}, {region.y}) · {region.width} × {region.height}
          <button
            onClick={() => {
              setRegion(null);
              onRegion?.(null);
            }}
          >
            Clear selection
          </button>
        </div>
      )}
    </div>
  );
}
