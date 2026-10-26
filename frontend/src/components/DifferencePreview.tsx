import { useState } from 'react';
import { fmt, preview } from '../lib/api';
import { Spinner } from './UI';

export function DifferencePreview({ imageId, maximum }: { imageId: string; maximum?: number }) {
  const [attempt, setAttempt] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  return (
    <>
      <div className="difference-frame" aria-busy={!loaded && !failed}>
        {failed ? (
          <div className="difference-error" role="alert">
            <p>The difference preview could not load.</p>
            <button
              onClick={() => {
                setFailed(false);
                setLoaded(false);
                setAttempt((value) => value + 1);
              }}
            >
              Retry preview
            </button>
            <small>If the image has expired, run the experiment again.</small>
          </div>
        ) : (
          <>
            {!loaded && (
              <div className="difference-loading" role="status">
                <Spinner />
                Loading difference preview…
              </div>
            )}
            <img
              className="difference-image"
              style={{ visibility: loaded ? 'visible' : 'hidden' }}
              src={`${preview(imageId)}&retry=${attempt}`}
              alt="Normalized absolute reconstruction difference"
              onLoad={() => setLoaded(true)}
              onError={() => setFailed(true)}
            />
          </>
        )}
      </div>
      <div className="difference-legend" aria-label="Difference colour scale">
        <span>0 · no error</span>
        <span className="difference-ramp" aria-hidden="true" />
        <span>{maximum == null ? 'Maximum error' : `${fmt(maximum, 2)} · maximum error`}</span>
      </div>
      <p className="muted small">
        Mean absolute RGB error per pixel, in 8-bit intensity units. Colours are scaled to this
        experiment’s maximum; black means zero error. Compare numeric MAE across experiments.
      </p>
    </>
  );
}
