const $ = (s) => document.querySelector(s);
const views = {home:'#homeView', check:'#checkView', token:'#tokenView', about:'#aboutView'};
function go(name){document.querySelectorAll('.view').forEach(v=>v.classList.add('hidden'));$(views[name]).classList.remove('hidden');$('#mobileNav').classList.remove('open');window.scrollTo({top:0,behavior:'smooth'});if(name==='about')loadTargets()}
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>go(b.dataset.view)));
$('#menuBtn').addEventListener('click',()=>$('#mobileNav').classList.toggle('open'));
$('#dropZone').addEventListener('click',()=>$('#file').click());
$('#file').addEventListener('change',()=>{const f=$('#file').files[0];if(f)$('#dropZone').querySelector('span').textContent=`Выбран файл: ${f.name}`});
$('#tokenBtn').addEventListener('click',async()=>{const r=await fetch('/api/token',{method:'POST'});const d=await r.json();if(d.token)localStorage.setItem('npa_token',d.token);$('#tokenOut').classList.remove('hidden');$('#tokenOut').textContent=`API TOKEN\n${d.token}\n\nENDPOINT\n${d.endpoint}\n\nСкопируйте сейчас: токен показывается один раз.`});
$('#checkBtn').addEventListener('click',async()=>{
  const out=$('#result');out.classList.remove('hidden');out.innerHTML='<div>Проверка…</div>';
  const fd=new FormData();fd.append('platform',$('#platform').value);
  const f=$('#file').files[0];if(f)fd.append('upload',f);else fd.append('code',$('#code').value);
  const token=localStorage.getItem('npa_token')||prompt('Введите API токен сервиса');
  if(!token){out.innerHTML='<div class="bad">Нужен API токен.</div>';return}localStorage.setItem('npa_token',token);
  const r=await fetch('/api/check',{method:'POST',headers:{Authorization:`Bearer ${token}`},body:fd});
  const d=await r.json();if(!r.ok){out.innerHTML=`<div class="bad">${d.detail||'Ошибка'}</div>`;return}
  const result=d.result;let html='';
  if(result.mode==='upload'){
    const remaining=result.remaining_issues||[];
    html+=remaining.length?`<div class="bad"><b>Остались проблемы:</b>${remaining.map(x=>`<div class="issue"><b>${x.severity}</b> · ${x.file}${x.line?':'+x.line:''}<br>${x.message}<br><small>${x.suggestion}</small></div>`).join('')}</div>`:'<div class="ok"><b>После автоматических проверок критичных проблем не обнаружено.</b></div>';
    html+=`<p>Изменённых файлов: ${result.changed_files}</p><a href="${d.download_url}"><button class="primary">Скачать проект клиенту</button></a>`;
  }else{
    html+=result.issues?.length?`<div class="bad">${result.issues.map(x=>`<div class="issue"><b>${x.severity}</b> · ${x.file}${x.line?':'+x.line:''}<br>${x.message}<br><small>${x.suggestion}</small></div>`).join('')}</div>`:'<div class="ok">Статическая проверка не нашла ошибок.</div>';
    html+=`<p>Исправленный текст:</p><pre class="codebox" id="corrected"></pre><button id="copyCorrected">Скопировать код</button>`;
  }
  out.innerHTML=html;if(result.mode==='code'){$('#corrected').textContent=result.corrected_code;$('#copyCorrected').onclick=()=>navigator.clipboard.writeText(result.corrected_code)}
});
async function loadTargets(){const r=await fetch('/api/targets');const d=await r.json();$('#targets').innerHTML='<div class="target-grid">'+Object.entries(d).map(([k,v])=>`<div class="target-box"><b>${k}</b><br>${v.map(x=>`• ${x}`).join('<br>')}</div>`).join('')+'</div>'}
go('home');
