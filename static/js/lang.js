// Ricorda la lingua scelta nel localStorage e la ripristina se il cookie di Django manca o è diverso.
(() => {
    const KEY = 'language';
    const form = document.querySelector('.lang-switch');
    if (!form) return;
    const save = v => { try { localStorage.setItem(KEY, v); } catch (e) {} };

    form.addEventListener('change', e => { if (e.target.name === 'language') save(e.target.value); });
    form.addEventListener('click', e => {
        const b = e.target.closest('button[name="language"]');
        if (b) save(b.value);
    });

    let saved = null;
    try { saved = localStorage.getItem(KEY); } catch (e) {}
    const known = [...form.querySelectorAll('select[name="language"] option')].some(o => o.value === saved);
    // sessionStorage evita cicli se il ripristino non cambia la lingua della pagina
    if (!saved || !known || saved === document.documentElement.lang || sessionStorage.getItem('lang-restore') === saved) return;
    sessionStorage.setItem('lang-restore', saved);
    const data = new FormData(form);
    data.set('language', saved);
    fetch(form.action, {method: 'POST', body: data}).then(() => location.reload());
})();

document.addEventListener('change', e => {
    if (e.target.matches('[data-autosubmit]')) e.target.form.submit();
});
