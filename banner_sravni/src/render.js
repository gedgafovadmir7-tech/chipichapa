// Рендерит исходники в PNG: node render.js
const { chromium } = require('playwright');
const path = require('path');

const jobs = [
  { file: 'desktop.html', out: 'desktop_1440x315.png', w: 1440, h: 315, scale: 1 },
  { file: 'mobile.html', out: 'mobile_124x101.png', w: 124, h: 101, scale: 1, transparent: true },
  { file: 'mobile.html', out: 'mobile_124x101@2x.png', w: 124, h: 101, scale: 2, transparent: true },
  { file: 'preview.html', out: 'preview_desktop.png', w: 1440, h: 520, scale: 1, sel: '#desk' },
  { file: 'preview.html', out: 'preview_mobile.png', w: 1440, h: 520, scale: 2, sel: '#mob' },
];

(async () => {
  const browser = await chromium.launch();
  for (const j of jobs) {
    const page = await browser.newPage({ viewport: { width: j.w, height: j.h }, deviceScaleFactor: j.scale });
    await page.goto('file://' + path.join(__dirname, j.file));
    await page.evaluate(() => document.fonts.ready);
    const target = j.sel ? await page.$(j.sel) : await page.$('svg');
    await target.screenshot({ path: path.join(__dirname, '..', 'final', j.out), omitBackground: !!j.transparent });
    await page.close();
  }
  await browser.close();
})();
