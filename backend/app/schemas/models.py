from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Region(StrictModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class AnalysisOptions(StrictModel):
    mode: Literal["exact", "preview"] = "exact"
    preview_size: int = Field(default=512, ge=64, le=1024)
    alpha: float = Field(default=2, ge=0, le=100)
    levels: int = Field(default=16, ge=2, le=256)
    window: int = Field(default=9, ge=3, le=63)
    stride: int = Field(default=4, ge=1, le=64)
    local_method: Literal["sliding", "block"] = "sliding"
    scales: list[Annotated[int, Field(ge=3, le=63)]] = Field(
        default=[3, 9, 21], min_length=1, max_length=5
    )
    palette_size: int = Field(default=6, ge=2, le=12)
    region: Region | None = None
    save_history: bool = False

    @model_validator(mode="after")
    def odd_windows(self):
        if self.window % 2 == 0 or any(s % 2 == 0 for s in self.scales):
            raise ValueError("Sliding windows and scales must be odd.")
        return self


class AnalyzeRequest(StrictModel):
    image_id: str
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)


class BatchRequest(StrictModel):
    image_ids: list[str] = Field(min_length=1, max_length=24)
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)


class CompareRequest(StrictModel):
    image_ids: list[str] = Field(min_length=2, max_length=24)
    distribution: Literal["gray", "red", "green", "blue", "rgb"] = "gray"
    metric: Literal["js_distance", "hellinger", "total_variation", "wasserstein"] = "js_distance"
    levels: int = Field(default=16, ge=2, le=32)
    near_threshold: int = Field(default=8, ge=0, le=64)


class TransformStep(StrictModel):
    kind: Literal[
        "grayscale",
        "resize",
        "crop",
        "blur",
        "sharpen",
        "noise",
        "denoise",
        "brightness",
        "contrast",
        "saturation",
        "gamma",
        "equalize",
        "quantize",
        "shuffle",
        "rotate",
        "flip",
        "hsv",
        "lab",
    ]
    value: float = Field(default=1, ge=0, le=4096)
    width: int = Field(default=512, ge=1, le=4096)
    height: int = Field(default=512, ge=1, le=4096)
    x: int = Field(default=0, ge=0)
    y: int = Field(default=0, ge=0)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    resampling: Literal["nearest", "bilinear", "bicubic", "lanczos"] = "lanczos"


class TransformRequest(StrictModel):
    image_id: str
    steps: list[TransformStep] = Field(min_length=1, max_length=16)


class CompressionRequest(StrictModel):
    image_id: str
    codec: Literal["PNG", "JPEG", "WEBP"] = "JPEG"
    quality: int = Field(default=80, ge=1, le=100)
    lossless: bool = False
    compress_level: int = Field(default=6, ge=0, le=9)


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ImageInfo(BaseModel):
    id: str
    filename: str
    width: int
    height: int
    mode: str
    format: str
    frames: int
    frame: int
    bytes: int
    sha256: str
    native_bits: int
    has_alpha: bool
    warnings: list[str]


class EntropyMetrics(BaseModel):
    shannon: float
    hartley: float
    renyi: float
    alpha: float
    collision: float
    min_entropy: float
    maximum: float
    normalized: float
    effective_states: float
    unique_symbols: int
    entropy_deficit: float
    unit: str


class AnalysisResult(BaseModel):
    version: str
    image: ImageInfo
    configuration: AnalysisOptions
    measurement: dict
    entropy: EntropyMetrics
    histogram: dict
    quantization: list[dict]
    rgb: dict
    spatial: dict
    local: dict
    multiscale: list[dict]
    frequency: dict
    colour: dict
    diagnostics: dict
    fingerprint: dict
    elapsed_ms: float
    history_id: str | None = None


class JobStatus(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    progress: float
    stage: str
    result: dict | list | None = None
    error: str | None = None
