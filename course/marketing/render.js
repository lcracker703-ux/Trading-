const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch();
  for (const [name, w, h] of [['logo',512,512],['banner',1920,480],['cover',1280,720],['steps',1280,720]]) {
    const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    await p.goto('file://' + path.join(__dirname, name + '.html'));
    await p.screenshot({ path: path.join(__dirname, name + '.png') });
    await p.close();
  }
  await b.close(); console.log('done');
})();
