const key="0f44c665d01a4aa297623b805b457c14",host="www.elyio.co";
const maps=["pages","museums","artworks"];
const documents=await Promise.all(maps.map(name=>fetch(`https://${host}/sitemaps/${name}.xml`).then(r=>{if(!r.ok)throw new Error(`${name} sitemap ${r.status}`);return r.text()})));
const urls=[...new Set(documents.flatMap(xml=>[...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m=>m[1].replaceAll("&amp;","&"))))];
const changed=process.argv.slice(2);const urlList=changed.length?changed:urls;
if(!urlList.length)throw new Error("No changed public URLs supplied or discovered");
for(let i=0;i<urlList.length;i+=10000){const response=await fetch("https://api.indexnow.org/indexnow",{method:"POST",headers:{"content-type":"application/json; charset=utf-8"},body:JSON.stringify({host,key,keyLocation:`https://${host}/${key}.txt`,urlList:urlList.slice(i,i+10000)})});if(!response.ok&&response.status!==202)throw new Error(`IndexNow ${response.status}: ${await response.text()}`)}
console.log(`Submitted ${urlList.length} materially added/changed URLs to IndexNow.`);
