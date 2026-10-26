import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';
import type { Analysis, AnalysisOptions, Health, ImageInfo, Job } from '../types';

const defaults: AnalysisOptions = {
  mode: 'exact',
  preview_size: 512,
  alpha: 2,
  levels: 16,
  window: 9,
  stride: 4,
  local_method: 'sliding',
  scales: [3, 9, 21],
  palette_size: 6,
  region: null,
  save_history: false,
};
export function useWorkbench() {
  const [health, setHealth] = useState<Health | null>(null);
  const [images, setImages] = useState<ImageInfo[]>([]);
  const [selected, setSelected] = useState<string>('');
  const [results, setResults] = useState<Record<string, Analysis>>({});
  const [options, setOptions] = useState<AnalysisOptions>(() => {
    try {
      return {
        ...defaults,
        ...JSON.parse(localStorage.getItem('iea-options') ?? '{}'),
        region: null,
        save_history: false,
      };
    } catch {
      return defaults;
    }
  });
  const [job, setJob] = useState<Job<Analysis | Analysis[]> | null>(null);
  const [lastJob, setLastJob] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    let stopped = false;
    let failures = 0;
    let healthTimer: ReturnType<typeof setTimeout>;
    const check = async () => {
      let delay = 20000;
      try {
        const status = await api<Health>('/health');
        if (stopped) return;
        setHealth(status);
        failures = 0;
        setError((old) => (old.startsWith('Backend unavailable.') ? '' : old));
      } catch (e) {
        if (stopped) return;
        setHealth(null);
        delay = 3000;
        if (++failures === 3)
          setError(`Backend unavailable. Start FastAPI on port 8000. ${String(e)}`);
      }
      if (!stopped) healthTimer = setTimeout(() => void check(), delay);
    };
    void check();
    return () => {
      stopped = true;
      clearTimeout(healthTimer);
      mounted.current = false;
      clearTimeout(timer.current);
    };
  }, []);
  useEffect(() => {
    try {
      localStorage.setItem('iea-options', JSON.stringify(options));
    } catch {
      /* Browser persistence is optional; keep the in-memory workspace usable. */
    }
  }, [options]);

  const watch = useCallback((initial: Job<Analysis | Analysis[]>) => {
    setJob(initial);
    setLastJob(initial.id);
    const poll = async () => {
      try {
        const current = await api<Job<Analysis | Analysis[]>>(`/jobs/${initial.id}/results`);
        if (!mounted.current) return;
        setJob(current);
        if (current.status === 'completed' && current.result) {
          const analyses = Array.isArray(current.result) ? current.result : [current.result];
          setResults((old) => ({
            ...old,
            ...Object.fromEntries(analyses.map((a) => [a.image.id, a])),
          }));
        } else if (current.status === 'failed') setError(current.error ?? 'Analysis failed.');
        else if (current.status !== 'cancelled') timer.current = setTimeout(() => void poll(), 350);
      } catch (e) {
        if (mounted.current) {
          setError(String(e));
          setJob(null);
        }
      }
    };
    clearTimeout(timer.current);
    timer.current = setTimeout(() => void poll(), 150);
  }, []);

  const analyse = useCallback(
    async (id: string, override?: AnalysisOptions) => {
      setError('');
      try {
        watch(
          await api<Job<Analysis>>('/jobs/analysis', {
            image_id: id,
            options: override ?? options,
          }),
        );
      } catch (e) {
        setError(String(e));
      }
    },
    [options, watch],
  );

  const addDemo = async (kind = 'landscape') => {
    setBusy(true);
    setError('');
    try {
      const image = await api<ImageInfo>(`/demo?kind=${kind}`, {});
      setImages((old) => [...old, image]);
      setSelected(image.id);
      await analyse(image.id);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  const upload = async (files: FileList | File[]) => {
    setBusy(true);
    setError('');
    let first = '';
    try {
      if (images.length + files.length > 24)
        throw new Error(
          'Keep up to 24 images in one workspace. Remove images before uploading more.',
        );
      for (const file of Array.from(files)) {
        if (file.size > (health?.limits.max_upload_mb ?? 24) * 1048576)
          throw new Error(`${file.name} exceeds upload limit.`);
        const form = new FormData();
        form.append('file', file);
        const image = await api<ImageInfo>('/images', form);
        setImages((old) => [...old, image]);
        if (!first) first = image.id;
      }
      if (first) {
        setSelected(first);
        await analyse(first);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  const remove = async (id: string) => {
    try {
      await api(`/images/${id}`, undefined, 'DELETE');
      setImages((old) => old.filter((i) => i.id !== id));
      if (selected === id) setSelected(images.find((i) => i.id !== id)?.id ?? '');
      setResults((old) => {
        const next = { ...old };
        delete next[id];
        return next;
      });
    } catch (e) {
      setError(String(e));
    }
  };
  const batch = async (ids: string[]) => {
    setError('');
    try {
      watch(
        await api<Job<Analysis[]>>('/jobs/batch', {
          image_ids: ids,
          options: { ...options, region: null },
        }),
      );
    } catch (e) {
      setError(String(e));
    }
  };
  const addResultImage = (image: ImageInfo) =>
    setImages((old) => (old.some((i) => i.id === image.id) ? old : [...old, image]));
  const openSaved = (result: Analysis, available: boolean) => {
    setResults((old) => ({ ...old, [result.image.id]: result }));
    if (available) addResultImage(result.image);
    setSelected(result.image.id);
  };
  const running = job?.status === 'queued' || job?.status === 'running';
  const selectFrame = async (index: number) => {
    setBusy(true);
    setError('');
    try {
      const image = await api<ImageInfo>(`/images/${selected}/frame?index=${index}`, {});
      addResultImage(image);
      setSelected(image.id);
      const next = { ...options, region: null };
      setOptions(next);
      await analyse(image.id, next);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  return {
    health,
    images,
    selected,
    setSelected,
    results,
    result: results[selected],
    image: images.find((i) => i.id === selected),
    options,
    setOptions,
    job,
    lastJob,
    busy,
    running,
    error,
    setError,
    analyse,
    addDemo,
    selectFrame,
    upload,
    remove,
    batch,
    addResultImage,
    openSaved,
    cancel: async () => {
      if (job) {
        try {
          setJob(await api<Job<Analysis | Analysis[]>>(`/jobs/${job.id}`, undefined, 'DELETE'));
        } catch (e) {
          setError(String(e));
        }
      }
    },
  };
}
export type Workbench = ReturnType<typeof useWorkbench>;
