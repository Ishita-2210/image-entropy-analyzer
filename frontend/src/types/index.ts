export interface ImageInfo {
  id: string;
  filename: string;
  width: number;
  height: number;
  mode: string;
  format: string;
  frames: number;
  frame: number;
  bytes: number;
  sha256: string;
  native_bits: number;
  has_alpha: boolean;
  warnings: string[];
}
export interface Region {
  x: number;
  y: number;
  width: number;
  height: number;
}
export interface AnalysisOptions {
  mode: 'exact' | 'preview';
  preview_size: number;
  alpha: number;
  levels: number;
  window: number;
  stride: number;
  local_method: 'sliding' | 'block';
  scales: number[];
  palette_size: number;
  region: Region | null;
  save_history: boolean;
}
export interface Entropy {
  shannon: number;
  hartley: number;
  renyi: number;
  alpha: number;
  collision: number;
  min_entropy: number;
  maximum: number;
  normalized: number;
  effective_states: number;
  unique_symbols: number;
  entropy_deficit: number;
  unit: string;
}
export interface PairInformation {
  h_x: number;
  h_y: number;
  joint_entropy: number;
  mutual_information: number;
  conditional_y_given_x: number;
  conditional_x_given_y: number;
  correlation: number | null;
}
export interface Diagnostics {
  mean: number;
  std: number;
  min: number;
  max: number;
  dynamic_range: number;
  underexposed_ratio: number;
  overexposed_ratio: number;
  black_clipped_ratio: number;
  white_clipped_ratio: number;
  rms_contrast: number;
  laplacian_variance: number;
  edge_density: number;
  noise_sigma: number | null;
  gradient_histogram: { counts: number[]; centres: number[] };
  definitions: Record<string, string>;
}
export interface Analysis {
  version: string;
  image: ImageInfo;
  configuration: AnalysisOptions;
  measurement: {
    mode: string;
    width: number;
    height: number;
    native_entropy_bits: number;
    native_rgb_bits: number;
    spatial_colour_diagnostics_bits: number;
    native_definition: string;
    quantization_definition: string;
    preview_resampling: string | null;
  };
  entropy: Entropy;
  histogram: { values: number[]; counts: number[]; display: string };
  quantization: { levels: number; entropy: number; maximum: number }[];
  rgb: {
    marginal: Record<string, number>;
    joint_exact: number;
    joint_maximum: number;
    joint_quantized: number;
    pairs: Record<string, PairInformation>;
    levels: number;
    total_correlation_quantized: number;
    source: string;
    mode: string;
  };
  spatial: {
    neighbours: Record<string, PairInformation | null>;
    glcm: Record<string, number | null> | null;
    definition: string;
    levels: number;
  };
  local: {
    map: number[][];
    x: number[];
    y: number[];
    mean: number;
    std: number;
    min: number;
    max: number;
    window: number;
    stride: number;
    method: string;
    boundary: string;
    display_decimation: number;
  };
  multiscale: {
    window: number;
    mean: number;
    std: number;
    min: number;
    max: number;
    coarse_neighbour_mi: number | null;
    coarse_neighbour_correlation: number | null;
    coarse_definition: string;
  }[];
  frequency: {
    spectral_entropy: number | null;
    maximum: number;
    log_power: number[][];
    fx: number[];
    fy: number[];
    radial_frequency: number[];
    radial_energy: number[];
    energy: Record<string, number>;
    definition: string;
    unit: string;
  };
  colour: {
    rgb_histograms: Record<string, number[]>;
    distributions: Record<
      string,
      { counts: number[]; centres: number[]; mean: number; std: number }
    >;
    palette: { hex: string; rgb: number[]; lab: number[]; proportion: number }[];
    palette_sample: number;
    palette_method: string;
    colourfulness: number;
    channel_correlations: (number | null)[][];
    gray_entropy: number;
    linear_luminance_mean: number;
    alpha: {
      mean: number;
      transparent_ratio: number;
      opaque_ratio: number;
      entropy: number;
    } | null;
    assumption: string;
  };
  diagnostics: Diagnostics;
  fingerprint: { phash: string; dhash: string; definition: string };
  elapsed_ms: number;
  history_id: string | null;
}
export interface Health {
  status: string;
  version: string;
  history_enabled: boolean;
  limits: {
    max_upload_mb: number;
    max_pixels: number;
    max_analysis_pixels: number;
    store_mb: number;
    workers: number;
    job_seconds: number;
  };
  capabilities: {
    decode_formats: string[];
    encode_formats: string[];
    webp: boolean;
    avif: boolean;
    heif: boolean;
  };
  privacy: string;
}
export interface Job<T = Analysis> {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  stage: string;
  result: T | null;
  error: string | null;
}
export type TransformKind =
  | 'grayscale'
  | 'resize'
  | 'crop'
  | 'blur'
  | 'sharpen'
  | 'noise'
  | 'denoise'
  | 'brightness'
  | 'contrast'
  | 'saturation'
  | 'gamma'
  | 'equalize'
  | 'quantize'
  | 'shuffle'
  | 'rotate'
  | 'flip'
  | 'hsv'
  | 'lab';
export interface TransformStep {
  kind: TransformKind;
  value: number;
  width: number;
  height: number;
  x: number;
  y: number;
  seed: number;
  resampling: 'nearest' | 'bilinear' | 'bicubic' | 'lanczos';
}
export interface Experiment {
  image: ImageInfo;
  original_image_id: string;
  difference_image: ImageInfo | null;
  aligned: boolean;
  pixel_equal: boolean;
  histogram_equal: boolean;
  entropy_before: number;
  entropy_after: number;
  mae: number | null;
  mse: number | null;
  psnr: number | null;
  ssim: number | null;
  delta_e76_mean: number | null;
  diagnostics_before: Diagnostics;
  diagnostics_after: Diagnostics;
  spatial_before: Analysis['spatial'];
  spatial_after: Analysis['spatial'];
  notice: string;
  evaluation: string;
  codec?: string;
  source_bytes?: number;
  encoded_bytes?: number;
  size_ratio?: number;
  encode_ms?: number;
  decode_ms?: number;
  lossless_encoding?: boolean;
  source_pixel_equal?: boolean;
}
export interface Comparison {
  images: ImageInfo[];
  matrix: number[][];
  groups: string[][];
  pairs: {
    left: string;
    right: string;
    left_name: string;
    right_name: string;
    byte_duplicate: boolean;
    phash_distance: number;
    dhash_distance: number;
    near_candidate: boolean;
    distances: Record<string, number | string | null>;
  }[];
  definition: string;
}
export interface HistoryRecord {
  id: string;
  created: string;
  filename: string;
  sha256: string;
}
