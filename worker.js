const REPO = '101195hn-hue/lemmy-news-monitor';
const FILE = 'keywords.json';
function reply(data,status=200){return new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff'}})}
async function equalSecret(a,b){if(typeof a!=='string'||typeof b!=='string'||!a||!b)return false;const enc=new TextEncoder();const [x,y]=await Promise.all([crypto.subtle.digest('SHA-256',enc.encode(a)),crypto.subtle.digest('SHA-256',enc.encode(b))]);const aa=new Uint8Array(x),bb=new Uint8Array(y);let diff=0;for(let i=0;i<aa.length;i++)diff|=aa[i]^bb[i];return diff===0}
export default {async fetch(request,env){
 const url=new URL(request.url);
 if(url.pathname!=='/api/admin/keywords')return env.ASSETS.fetch(request);
 if(request.method!=='PUT')return reply({error:'지원하지 않는 요청입니다.'},405);
 const password=request.headers.get('x-admin-password')||'';
 if(!await equalSecret(password,env.ADMIN_PASSWORD))return reply({error:'관리자 비밀번호가 올바르지 않습니다.'},401);
 if(!env.GITHUB_TOKEN)return reply({error:'서버에 GITHUB_TOKEN이 설정되지 않았습니다.'},500);
 let body;try{body=await request.json()}catch{return reply({error:'JSON 형식이 아닙니다.'},400)}
 if(!body||typeof body!=='object'||Array.isArray(body)||Object.keys(body).length!==4)return reply({error:'카테고리 구성이 올바르지 않습니다.'},400);
 const categories=['경쟁사·유사업체','로봇 산업','교육·영어 로봇','시장·사업 동향'];
 for(const c of categories){if(!Array.isArray(body[c])||body[c].length>80||body[c].some(k=>typeof k!=='string'||!k.trim()||k.length>80)||new Set(body[c]).size!==body[c].length)return reply({error:c+' 키워드를 확인해 주세요.'},400)}
 const headers={'Authorization':`Bearer ${env.GITHUB_TOKEN}`,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'LEMMY-News-Monitor','Content-Type':'application/json'};
 const endpoint=`https://api.github.com/repos/${REPO}/contents/${FILE}`;
 try{
  const current=await fetch(endpoint,{headers});if(!current.ok)return reply({error:'GitHub 기존 설정 조회 실패 ('+current.status+')'},502);
  const metadata=await current.json();
  const raw=new TextEncoder().encode(JSON.stringify(body,null,2)+'\n');let binary='';for(const byte of raw)binary+=String.fromCharCode(byte);
  const updated=await fetch(endpoint,{method:'PUT',headers,body:JSON.stringify({message:'Update monitored keywords from admin panel',content:btoa(binary),sha:metadata.sha,branch:'main'})});
  if(!updated.ok){const msg=await updated.text();return reply({error:'GitHub 저장 실패 ('+updated.status+'): '+msg.slice(0,180)},updated.status===409?409:502)}
  return reply({ok:true,message:'GitHub keywords.json에 저장했습니다. 다음 자동 수집부터 적용됩니다.'});
 }catch(e){return reply({error:'저장 요청 실패: '+String(e).slice(0,180)},502)}
 }};
