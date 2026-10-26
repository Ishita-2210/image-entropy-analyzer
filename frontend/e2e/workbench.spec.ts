import { test, expect } from '@playwright/test';

test('interactive API reference works with external requests blocked', async ({ page }) => {
  await page.route('**/*', (route) =>
    new URL(route.request().url()).origin === 'http://127.0.0.1:5173'
      ? route.continue()
      : route.abort(),
  );
  await page.goto('/api/v1/docs');
  await expect(page.locator('.swagger-ui .info .title')).toContainText('Image Entropy Analyzer');
  await expect(
    page.locator('.opblock-summary-path').filter({ hasText: '/api/v1/analysis' }).first(),
  ).toBeVisible();
});

test('demo → numerical analysis → spatial exploration → real compression → transformation', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.stack ?? error.message));
  await page.goto('/');
  await expect(page.getByText('Local engine connected')).toBeVisible();
  await page.getByRole('button', { name: 'Explore a synthetic landscape' }).click();
  await expect(page.getByText('Shannon entropy', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Image analysis', exact: true }).click();
  await expect(page.getByText('Entropy family', { exact: true })).toBeVisible();
  await expect(page.getByRole('img', { name: 'landscape-seed-42.png', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Spatial & frequency', exact: true }).click();
  await expect(
    page.getByRole('img', { name: 'Local entropy heatmap aligned with image coordinates' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Compression lab', exact: true }).click();
  await page.getByRole('button', { name: 'Encode & measure' }).click();
  await expect(page.getByText('Experiment notebook', { exact: true })).toBeVisible();
  await expect(page.getByText('Reconstruction', { exact: true })).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download', exact: true }).click();
  expect((await download).suggestedFilename()).toBe('image.jpg');
  await page.getByRole('button', { name: 'Transform playground', exact: true }).click();
  await page.getByRole('button', { name: 'Add step', exact: true }).click();
  await page.getByRole('button', { name: 'Apply pipeline', exact: true }).click();
  await expect(page.getByText('Yes · measured bin by bin')).toBeVisible();
  await page.getByRole('button', { name: 'Colour & information', exact: true }).click();
  await expect(page.getByText('A perceptual palette')).toBeVisible();
  await page.getByRole('button', { name: 'Image diagnostics', exact: true }).click();
  await expect(page.getByText('Gradient magnitude distribution', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Transform playground', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Shuffle pixels', exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test('upload → batch results → comparisons → exports → opt-in history deletion', async ({
  page,
  request,
}) => {
  const a = await request.post('http://127.0.0.1:8000/api/v1/demo?kind=gradient', { data: {} });
  const info = (await a.json()) as { id: string };
  const source = await request.get(`http://127.0.0.1:8000/api/v1/images/${info.id}/download`);
  await page.goto('/');
  await page.getByLabel('Upload images').setInputFiles([
    { name: 'gradient-a.png', mimeType: 'image/png', buffer: await source.body() },
    { name: 'gradient-b.png', mimeType: 'image/png', buffer: await source.body() },
  ]);
  await expect(page.getByText('Shannon entropy', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Batch workspace', exact: true }).click();
  await page.getByRole('button', { name: 'Analyse 2 selected' }).click();
  await expect(page.getByRole('button', { name: 'Run analysis', exact: true })).toBeEnabled();
  const download = page.waitForEvent('download');
  await page.getByRole('link', { name: 'CSV', exact: true }).click();
  expect((await download).suggestedFilename()).toBe('analysis.csv');
  await page.getByRole('button', { name: 'Similarity & duplicates', exact: true }).click();
  await page.getByRole('button', { name: 'Compare collection' }).click();
  await expect(page.getByText('SHA-256 byte duplicate', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Settings', exact: true }).click();
  await page.getByLabel('Save subsequent analyses to local history').check();
  await page.getByRole('button', { name: 'Run analysis', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Run analysis', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Analysis history', exact: true }).click();
  await expect(page.getByRole('button', { name: 'gradient-a.png', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Delete record gradient-a.png' }).click();
  await expect(page.getByRole('button', { name: 'gradient-a.png', exact: true })).toHaveCount(0);
});

test('invalid upload displays an actionable error and mobile navigation works', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByLabel('Upload images').setInputFiles({
    name: 'fake.png',
    mimeType: 'image/png',
    buffer: Buffer.from('not an image'),
  });
  await expect(page.getByRole('alert')).toContainText('Invalid, unsafe or unsupported image data.');
  await page.getByRole('button', { name: 'Dismiss error' }).click();
  await page.getByRole('button', { name: 'Toggle navigation' }).click();
  await page.getByRole('button', { name: 'Settings', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Settings.' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
});
