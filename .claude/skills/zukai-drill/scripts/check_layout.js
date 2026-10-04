// zukai-drill のページをスマホ幅（390px）で開き、表示崩れを機械的に調べる。
// 使い方: node .claude/skills/zukai-drill/scripts/check_layout.js zukai/<file>.html [screenshot-dir]
// 調べること: ページの横スクロール、SVG 内の文字が枠（幅200超の rect）からはみ出していないか、
//             SVG 内の文字の実表示サイズ（11px 未満は警告）。
const path = require('path');
const { execSync } = require('child_process');
const pw = require(path.join(execSync('npm root -g').toString().trim(), 'playwright'));

(async () => {
  const file = process.argv[2];
  const outDir = process.argv[3];
  if (!file) { console.error('usage: check_layout.js <html> [screenshot-dir]'); process.exit(2); }
  const browser = await pw.chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 800 }, deviceScaleFactor: 2 });
  await page.goto('file://' + path.resolve(file));
  await page.evaluate(() => document.querySelectorAll('details').forEach(d => (d.open = true)));
  const r = await page.evaluate(() => {
    const W = document.documentElement.clientWidth;
    const problems = [];
    if (document.documentElement.scrollWidth > W) problems.push(`page scrolls sideways: ${document.documentElement.scrollWidth}px > ${W}px`);
    let minPx = Infinity;
    document.querySelectorAll('svg').forEach((svg, i) => {
      const vb = svg.viewBox.baseVal;
      if (!vb || !vb.width) { problems.push(`svg#${i} has no viewBox`); return; }
      const scale = svg.getBoundingClientRect().width / vb.width;
      const boxes = [...svg.querySelectorAll('rect')].map(r => r.getBBox()).filter(b => b.width > 200);
      svg.querySelectorAll('text').forEach(t => {
        const b = t.getBBox();
        minPx = Math.min(minPx, parseFloat(getComputedStyle(t).fontSize) * scale);
        if (b.x < vb.x || b.x + b.width > vb.x + vb.width) problems.push(`svg#${i} text outside viewBox: "${t.textContent}"`);
        const box = boxes.find(r => b.y >= r.y - 2 && b.y <= r.y + r.height);
        if (box && b.x + b.width > box.x + box.width - 4) problems.push(`svg#${i} text overflows its box: "${t.textContent}"`);
      });
    });
    if (minPx < 11) problems.push(`smallest SVG text renders at ${minPx.toFixed(1)}px (< 11px)`);
    return { minPx: Number.isFinite(minPx) ? +minPx.toFixed(1) : null, problems };
  });
  if (outDir) {
    const svgs = page.locator('svg');
    for (let i = 0; i < await svgs.count(); i++) await svgs.nth(i).screenshot({ path: path.join(outDir, `svg${i}.png`) });
  }
  await browser.close();
  console.log(JSON.stringify(r, null, 2));
  process.exit(r.problems.length ? 1 : 0);
})();
