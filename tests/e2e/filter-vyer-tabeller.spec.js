const { test, expect } = require('@playwright/test');

async function waitForAppReady(page) {
  await page.goto('/');
  await expect(page.locator('#statusText')).not.toHaveText(/Startar/i);
  await expect(page.locator('#localFilters')).toHaveClass(/active/);
  await expect(page.locator('#gradeFilter option')).not.toHaveCount(0);
}

test('laddar sidan med filter och overview-tabell', async ({ page }) => {
  await waitForAppReady(page);

  await expect(page.locator('h1')).toContainText('Betygsstatistik');
  await expect(page.locator('#overviewTableSummary')).toContainText('Urval:');
  await expect(page.locator('#localMeritRows tr')).not.toHaveCount(0);
});

test('uppdaterar tabellsammanfattning när filter ändras', async ({ page }) => {
  await waitForAppReady(page);

  await page.locator('#gradeFilter').selectOption(['6']);
  await expect(page.locator('#overviewTableSummary')).toContainText('Årskurs: 6');

  const enabledSchoolValues = await page.locator('#schoolFilter option:not([disabled])').evaluateAll(options =>
    options.slice(0, 1).map(option => option.value),
  );
  expect(enabledSchoolValues.length).toBeGreaterThan(0);

  await page.locator('#schoolFilter').selectOption(enabledSchoolValues);
  await expect(page.locator('#overviewTableSummary')).toContainText('Skolor: 1 skolenheter');

  await page.locator('[data-tab="subjects"]').click();
  await expect(page.locator('#tab-subjects')).toHaveClass(/active/);
  await expect(page.locator('#subjectTableSummary')).toContainText('Årskurs: 6');
  await expect(page.locator('#subjectRows tr')).not.toHaveCount(0);
});

test('visar NP-läge när bara årskurs 3 är vald', async ({ page }) => {
  await waitForAppReady(page);

  const gradeValues = await page.locator('#gradeFilter option').evaluateAll(options =>
    options.map(option => option.value),
  );
  test.skip(!gradeValues.includes('3'), 'Det finns ingen åk 3 i aktuell testdata.');

  await page.locator('#gradeFilter').selectOption(['3']);

  await expect(page.locator('[data-tab="overview"]')).toBeHidden();
  await expect(page.locator('[data-tab="np"]')).toBeVisible();
  await page.locator('[data-tab="np"]').click();
  await expect(page.locator('#tab-np')).toHaveClass(/active/);
  await expect(page.locator('#npFilterSummary')).toContainText('Årskurs: 3');
});
