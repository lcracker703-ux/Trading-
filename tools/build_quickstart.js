// course/quickstart.html -> course/dist/Quick-Start.pdf
const { chromium } = require('playwright'); const fs=require('fs'); const path=require('path');
(async()=>{const root=path.resolve(__dirname,'..'); const brand=process.argv[2]||"Bot's Trading";
const html=fs.readFileSync(path.join(root,'course/quickstart.html'),'utf8').replaceAll('{{BRAND}}',brand);
const b=await chromium.launch(); const p=await b.newPage(); await p.setContent(html,{waitUntil:'load'});
await p.pdf({path:path.join(root,'course/dist/Quick-Start.pdf'),format:'A4',printBackground:true,preferCSSPageSize:true});
await b.close(); console.log('Quick-Start.pdf written');})();
