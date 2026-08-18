const { test, expect } = require('@playwright/test');
const path = require('path');

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

test('tolkar språkfälten enligt datafilsbeskrivningen för 2026', async ({ page }) => {
  await waitForAppReady(page);

  await expect.poll(() => page.evaluate(() => resolveAmnesnamn('M1_betyg'))).toBe('Moderna språk (skolans val)');
  await expect.poll(() => page.evaluate(() => resolveAmnesnamn('M2_betyg'))).toBe('Moderna språk (språkval)');
  await expect.poll(() => page.evaluate(() => resolveAmnesnamn('ML_betyg'))).toBe('Modersmål');
  await page.evaluate(() => { state.filters.grades = ['9']; });
  await expect.poll(() => page.evaluate(() => tableNoteForSelectedGrades())).toBe('');
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

test('visar anonymiserad progression och filtrerar skola och SVA', async ({ page }) => {
  test.setTimeout(20_000);
  await page.route('**/betygsprogression_ak6_ak9.json', route =>
    route.fulfill({
      path: path.join(__dirname, '..', 'fixtures', 'betygsprogression_ak6_ak9.json'),
      contentType: 'application/json',
    }),
  );
  await waitForAppReady(page);

  await page.locator('[data-tab="progression"]').click();

  await expect(page.locator('#tab-progression')).toHaveClass(/active/);
  await expect(page.locator('#progressionCards')).toContainText('Matchade elever');
  await expect(page.locator('#progressionRows tr')).toHaveCount(2);

  const interpretation = page.locator('#progressionInterpretation');
  await expect(interpretation).toContainText('36 av 40 elever');
  await expect(interpretation).toContainText('jämförbara ämnesbetyg');
  await expect(interpretation).toContainText('50 % höjts');
  await expect(interpretation).toContainText('35 % varit oförändrade');
  await expect(interpretation).toContainText('15 % sänkts');
  await expect(interpretation).toContainText('ungefär 2 av 10 jämförbara ämnesbetyg');
  await expect(interpretation).toContainText('0,4 betygssteg högre');
  await expect(interpretation).not.toContainText('2 av 10 elever');

  const correlation = page.locator('#progressionCorrelation');
  await expect(correlation).toContainText('måttligt positivt samband');
  await expect(correlation).toContainText('relativt höga betyg');
  await expect(correlation).toContainText('visar inte om betygen har höjts eller sänkts');
  await expect(correlation).toContainText('vilken effekt skolan haft');

  await expect(page.locator('#progressionCards')).toContainText('Genomsnittlig betygsförändring');
  await expect(page.locator('#progressionCards')).toContainText('Jämförbara ämnesbetyg som höjts');
  await expect(page.locator('#progressionCards')).toContainText('Jämförbara ämnesbetyg som är oförändrade');
  await expect(page.locator('#progressionCards')).toContainText('Jämförbara ämnesbetyg som sänkts');
  await expect(page.locator('#progressionCards')).not.toContainText('Meritvärde åk 9');
  await expect(page.locator('#progressionSecondary')).toContainText('Kompletterande slutmått');
  await expect(page.locator('#progressionSecondary')).toContainText('Meritvärde i årskurs 9: 231');
  await expect(page.locator('#progressionSecondary')).toContainText('jämförs inte med årskurs 6');
  await expect(page.locator('#progressionSubjectIntro')).toContainText(
    'giltigt betyg i ämnet både i årskurs 6 och årskurs 9',
  );
  await expect(page.locator('#progressionSubjectTable thead')).toContainText('Jämförbara elever');
  await expect(page.locator('#progressionSubjectTable thead')).toContainText('Förändring i steg');
  await expect(page.locator('#progressionSubjectTable thead')).toContainText('Samband mellan resultaten');
  await expect(page.locator('#progressionSubjectTable thead')).toContainText('Kort tolkning');

  const mathematicsRow = page.locator('#progressionRows tr', { hasText: 'Matematik' });
  await expect(mathematicsRow).toContainText('0,6 steg högre');
  await expect(mathematicsRow).toContainText('måttligt');
  await expect(mathematicsRow).toContainText('visar inte varför');

  const roundedZeroInterpretation = await page.evaluate(() => subjectInterpretation({
    genomsnittlig_forandring: 0.04,
    korrelation: 0.5,
  }));
  expect(roundedZeroInterpretation).toContain('Betygen är i genomsnitt oförändrade');
  expect(roundedZeroInterpretation).not.toContain('0 steg högre');
  const roundedZeroOverview = await page.evaluate(() => changeInterpretation(0.04));
  expect(roundedZeroOverview).toContain('i genomsnitt oförändrade');
  expect(roundedZeroOverview).not.toContain('0 betygssteg högre');
  const roundedNegativeInterpretation = await page.evaluate(() => subjectInterpretation({
    genomsnittlig_forandring: -0.05,
    korrelation: 0.5,
  }));
  expect(roundedNegativeInterpretation).toContain('0,1 steg lägre');
  const roundedNegativeOverview = await page.evaluate(() => changeInterpretation(-0.05));
  expect(roundedNegativeOverview).toContain('0,1 betygssteg lägre');

  await page.locator('#progressionSubjectSort').selectOption('correlation');
  await expect(page.locator('#progressionRows tr').first()).toContainText('Engelska');
  await expect.poll(() => page.evaluate(() => Chart.getChart('progressionChangeChart').data.labels[0])).toBe('Engelska');
  await expect.poll(() => page.evaluate(() => Chart.getChart('progressionGradeChart').data.labels[0])).toBe('Engelska');

  await page.locator('#progressionSubjectSort').selectOption('increase');
  await expect(page.locator('#progressionRows tr').first()).toContainText('Matematik');
  await expect.poll(() => page.evaluate(() => Chart.getChart('progressionChangeChart').data.labels[0])).toBe('Matematik');
  await expect.poll(() => page.evaluate(() => Chart.getChart('progressionGradeChart').data.labels[0])).toBe('Matematik');

  await page.locator('#progressionSchoolFilter').selectOption('59983229');
  await page.locator('#progressionGroupFilter').selectOption('SVA');

  await expect(page.locator('#progressionStatus')).toContainText(
    'Resultatet visas inte eftersom gruppen är för liten.',
  );
  await expect(page.locator('#progressionRows')).toBeEmpty();
});

test('saknat progressionsunderlag påverkar inte ordinarie översikt', async ({ page }) => {
  test.setTimeout(20_000);
  await page.route('**/betygsprogression_ak6_ak9.json', route =>
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        schema_version: 1,
        status: 'saknar_underlag',
        source: 'test_fixture',
        ak6_lasar: '2022-2023',
        ak9_lasar: '2025-2026',
        sekretessgrans: 10,
        segment: [],
      }),
    }),
  );
  await waitForAppReady(page);

  await expect(page.locator('#localMeritRows tr')).not.toHaveCount(0);
  await page.locator('[data-tab="progression"]').click();
  await expect(page.locator('#progressionStatus')).toContainText('Historiska betyg för åk 6 saknas');
  await expect(page.locator('#progressionResults')).toHaveCount(1);
  await expect(page.locator('#progressionResults')).toBeHidden();
});
