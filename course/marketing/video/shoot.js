const { chromium } = require('playwright'); const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});
for(const s of ['s1','s2','s3','s4','s5']){await p.goto('file://'+path.join(__dirname,s+'.html'));await p.screenshot({path:path.join(__dirname,s+'.png')});}
await b.close();console.log('shot');})();
