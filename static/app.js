(function () {
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const root = document.documentElement;
  const MSG = {
    ok: ['Официант скоро подойдёт 🙌', 'Даяшы жақында келеді 🙌'],
    table: ['Укажите номер столика', 'Үстел нөмірін көрсетіңіз'],
    wait: ['Вы уже вызвали официанта, подождите минуту', 'Даяшы шақырылды, бір минут күтіңіз'],
    limit: ['Слишком много вызовов, попробуйте позже', 'Тым көп шақыру, кейінірек қайталаңыз'],
    err: ['Ошибка сети, попробуйте ещё раз', 'Желі қатесі, қайталап көріңіз']
  };
  const L = () => (root.lang === 'kk' ? 1 : 0);
  function setLang(l) { root.lang = l; localStorage.setItem('lang', l); $('#lang').textContent = l === 'ru' ? 'ҚАЗ' : 'РУС'; }
  const lb = $('#lang'); if (!lb) return;
  setLang(root.lang || 'ru'); lb.onclick = () => setLang(root.lang === 'ru' ? 'kk' : 'ru');

  let cat = 'all';
  function filter() {
    const q = $('#q').value.trim().toLowerCase();
    $$('.sec').forEach(s => {
      let n = 0;
      s.querySelectorAll('.card').forEach(c => { const ok = !q || c.dataset.s.includes(q); c.hidden = !ok; if (ok) n++; });
      s.hidden = !(cat === 'all' || s.dataset.c === cat) || !n;
    });
    $('#empty').hidden = !$$('.sec').every(s => s.hidden);
  }
  $('#q').oninput = filter;
  $$('#tabs button').forEach(b => b.onclick = () => {
    $$('#tabs button').forEach(x => x.classList.remove('on')); b.classList.add('on'); cat = b.dataset.c; filter();
  });

  function toast(text, err) {
    const t = $('#toast'); t.textContent = text; t.className = 'toast' + (err ? ' err' : ''); t.hidden = false;
    setTimeout(() => t.hidden = true, 3500);
  }
  const m = $('#modal');
  $('#fab').onclick = () => m.hidden = false;
  $('#close').onclick = () => m.hidden = true;
  m.onclick = e => { if (e.target === m) m.hidden = true; };
  $$('.chip').forEach(c => c.onclick = () => { const t = $('#comment'); t.value = (t.value ? t.value + ', ' : '') + c.dataset.v; });
  $('#send').onclick = async () => {
    const btn = $('#send'); btn.disabled = true;
    try {
      const r = await fetch(m.dataset.url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('meta[name=csrf-token]').content },
        body: JSON.stringify({ table: $('#table').value.trim(), comment: $('#comment').value.trim() })
      });
      const d = await r.json().catch(() => ({}));
      if (r.ok) { m.hidden = true; $('#comment').value = ''; toast(MSG.ok[L()]); }
      else toast((MSG[d.error] || MSG.err)[L()], true);
    } catch (e) { toast(MSG.err[L()], true); }
    btn.disabled = false;
  };
})();
