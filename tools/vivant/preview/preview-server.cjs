/* Serveur de démonstration statique, sans API, secrets ou paiement. */
'use strict';
const http=require('node:http');
const fs=require('node:fs');
const path=require('node:path');
const root=process.env.ORIGIN_PREVIEW_ROOT||__dirname;
const base=(process.env.ORIGIN_PREVIEW_BASE||'').replace(/\/$/,'');
const files=new Set(['index.html','arbre-vivant.html','ORIGIN_DEMO.html','origin-vivant.js','origin-profiles.js','origin-storage.js','origin-integration.js','origin-vivant.css','logo-origin-officiel.png','preview-fixtures.js','preview.css','manifest.json']);
const types={'.html':'text/html; charset=utf-8','.js':'application/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.png':'image/png','.json':'application/json; charset=utf-8'};
const server=http.createServer((request,response)=>{
  response.setHeader('Cache-Control','no-store');
  response.setHeader('X-Content-Type-Options','nosniff');
  response.setHeader('Referrer-Policy','no-referrer');
  if(!['GET','HEAD'].includes(request.method)){response.writeHead(405,{'Allow':'GET, HEAD'});response.end('Aperçu statique : aucune API disponible.');return}
  let url;
  try{url=new URL(request.url,'http://preview.invalid');url.pathname=decodeURIComponent(url.pathname)}catch{response.writeHead(400);response.end();return}
  if(url.pathname===base+'/health'){
    response.setHeader('Content-Type','application/json');response.end(JSON.stringify({status:'ok',mode:'fictional-demo',payments:false,accounts:false}));return;
  }
  if(url.pathname===base&&base){response.writeHead(302,{'Location':base+'/'});response.end();return}
  if(!url.pathname.startsWith(base+'/')){response.writeHead(404);response.end();return}
  const name=url.pathname.slice(base.length+1)||'index.html';
  if(!files.has(name)){response.writeHead(404);response.end('Ressource absente de la démonstration.');return}
  fs.readFile(path.join(root,name),(error,content)=>{
    if(error){response.writeHead(404);response.end();return}
    response.setHeader('Content-Type',types[path.extname(name)]||'application/octet-stream');
    response.end(request.method==='HEAD'?undefined:content);
  });
});
server.listen(Number(process.env.ORIGIN_PREVIEW_PORT??3000),process.env.ORIGIN_PREVIEW_HOST||'0.0.0.0',()=>{
  const port=server.address().port;
  console.log(JSON.stringify({event:'origin_preview_ready',port}));
  console.log('ORIGIN fictional preview ready on port '+port);
});
process.on('SIGTERM',()=>server.close());
