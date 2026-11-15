// Render course/guide.html -> course/dist/Build-Your-Own-Trading-Alert-Bot.pdf
//   node tools/build_pdf.js "Tom's Trading"
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const root = path.resolve(__dirname, '..');
  const brand = process.argv[2] || "Trading Bot";
  const html = fs.readFileSync(path.join(root, 'course/guide.html'), 'utf8').replaceAll('{{BRAND}}', brand);
  const out = path.join(root, 'course/dist');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: 'load' });
  await page.pdf({
    path: path.join(out, 'Build-Your-Own-Trading-Alert-Bot.pdf'),
    format: 'A4', printBackground: true, displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate: `<div style="font-size:8px;color:#888;width:100%;text-align:center">${brand} · Build Your Own Trading Alert Bot · <span class="pageNumber"></span>/<span class="totalPages"></span></div>`,
    margin: { top: '18mm', bottom: '20mm', left: '17mm', right: '17mm' },
  });
  await browser.close();
  console.log('PDF written');
})();
