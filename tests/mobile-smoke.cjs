const {chromium}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch();fs.mkdirSync('mobile-screenshots',{recursive:true});
 for(const viewport of [{width:360,height:780},{width:390,height:844},{width:768,height:1024},{width:844,height:390}]){
  // Landscape handsets need the same touch layout even when wider than 768px.
  const page=await browser.newPage({viewport,hasTouch:true,isMobile:true});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded'});
  await page.locator('#directoryList .directory-list-item').first().waitFor({state:'attached',timeout:60000});
  const mobile=viewport.width<=900;
  if(mobile){
   assert(await page.locator('#mobileFilterToggle').isVisible());assert(!(await page.locator('#search').isVisible()));
   await page.locator('#mobileFilterToggle').click();await page.locator('#search').waitFor({state:'visible'});
   assert.equal(await page.locator('#search').evaluate(el=>getComputedStyle(el).fontSize),'16px');
   await page.locator('#search').fill('Wien');assert((await page.locator('#directoryList .directory-list-item').count())>0);
   await page.locator('#clearDirectory').click();
   if(await page.locator('#listCount').evaluate(el=>!el.closest('details').open))await page.locator('#listCount').click();
   await page.locator('#directoryList .directory-list-item').first().click();
   await page.locator('#mobileDetail').waitFor({state:'visible'});
   const rect=await page.locator('#mobileDetail').boundingBox();assert(rect.x>=0&&rect.x+rect.width<=viewport.width+1);assert(rect.y>=0&&rect.y+rect.height<=viewport.height+1);
   await page.screenshot({path:`mobile-screenshots/${viewport.width}x${viewport.height}-details.png`});
   await page.locator('#closeMobileDetail').click();assert(!(await page.locator('#mobileDetail').isVisible()));
   await page.locator('#mobileFilterToggle').click();await page.locator('#search').waitFor({state:'visible'});
   await page.screenshot({path:`mobile-screenshots/${viewport.width}x${viewport.height}-filters.png`});
  }
  assert(!(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)),'Horizontal overflow');
  assert.deepEqual(errors,[]);console.log('Viewport OK:',viewport.width,viewport.height);await page.close();
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
