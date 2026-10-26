/// <reference lib="webworker" />
let pixels: Uint8ClampedArray | null = null;
let width = 0;
self.onmessage = (
  event: MessageEvent<{
    type: string;
    buffer?: ArrayBuffer;
    width?: number;
    x?: number;
    y?: number;
  }>,
) => {
  const data = event.data;
  if (data.type === 'init') {
    pixels = new Uint8ClampedArray(data.buffer!);
    width = data.width!;
  } else if (pixels && data.x != null && data.y != null) {
    const offset = (data.y * width + data.x) * 4;
    const rgb = Array.from(pixels.subarray(offset, offset + 4));
    self.postMessage({
      rgb,
      hex:
        '#' +
        rgb
          .slice(0, 3)
          .map((v) => v.toString(16).padStart(2, '0'))
          .join(''),
    });
  }
};
