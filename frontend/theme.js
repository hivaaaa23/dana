(function(){
  const root=document.documentElement;
  const savedTheme=localStorage.getItem('gerreh-theme')||'1';
  const savedMode=localStorage.getItem('gerreh-mode')||'light';
  root.dataset.theme=savedTheme;
  root.dataset.mode=savedMode;

  function applyTheme(theme){root.dataset.theme=theme;localStorage.setItem('gerreh-theme',theme);updatePicker()}
  function applyMode(mode){root.dataset.mode=mode;localStorage.setItem('gerreh-mode',mode);updatePicker()}
  function updatePicker(){
    document.querySelectorAll('.tp-theme').forEach(b=>b.classList.toggle('active',b.dataset.theme===root.dataset.theme));
    document.querySelectorAll('.tp-mode button').forEach(b=>b.classList.toggle('active',b.dataset.mode===root.dataset.mode));
  }
  function build(){
    if(document.getElementById('theme-toggle')) return;
    const toggle=document.createElement('button');
    toggle.id='theme-toggle';toggle.type='button';toggle.title='تغییر تم';toggle.innerHTML='◐';
    document.body.appendChild(toggle);
    const panel=document.createElement('section');panel.id='theme-panel';
    panel.innerHTML=`
      <div class="tp-title"><span>شخصی‌سازی ظاهر</span><button class="tp-close" type="button">×</button></div>
      <div class="tp-themes">
        <button class="tp-theme" data-theme="1" aria-label="تم اول"><span style="background:#28264B"></span><span style="background:#B4003B"></span><span style="background:#959ECC"></span></button>
        <button class="tp-theme" data-theme="2" aria-label="تم دوم"><span style="background:#042440"></span><span style="background:#4E499E"></span><span style="background:#D26B9D"></span></button>
        <button class="tp-theme" data-theme="3" aria-label="تم سوم"><span style="background:#2C6975"></span><span style="background:#68B2A0"></span><span style="background:#CDE0C9"></span></button>
      </div>
      <div class="tp-mode"><button type="button" data-mode="light">☀ روشن</button><button type="button" data-mode="dark">☾ تاریک</button></div>`;
    document.body.appendChild(panel);
    toggle.addEventListener('click',()=>panel.classList.toggle('open'));
    panel.querySelector('.tp-close').addEventListener('click',()=>panel.classList.remove('open'));
    panel.querySelectorAll('.tp-theme').forEach(b=>b.addEventListener('click',()=>applyTheme(b.dataset.theme)));
    panel.querySelectorAll('.tp-mode button').forEach(b=>b.addEventListener('click',()=>applyMode(b.dataset.mode)));
    updatePicker();
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',build); else build();
})();
