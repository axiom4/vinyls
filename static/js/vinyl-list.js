// Infinite scroll + ricerca mentre si digita sull'elenco vinili.
(() => {
    const grid = document.getElementById('vinyl-grid');
    const sentinel = document.getElementById('scroll-sentinel');
    if (!grid || !sentinel) return;
    const empty = document.getElementById('empty-msg');
    const title = document.getElementById('list-title');
    const spinner = [...sentinel.childNodes];
    // testi tradotti: arrivano dal template (data-*)
    const T = {empty: empty.dataset.empty, error: empty.dataset.error, retry: sentinel.dataset.retry};
    let gen = 0;          // incrementa a ogni nuova ricerca: scarta risposte vecchie
    let ctrl = new AbortController();
    let loading = false;

    // DOMParser: documento inerte, gli script non vengono eseguiti
    const parse = html => new DOMParser().parseFromString(html, 'text/html').body.childNodes;

    const fetchPage = (params) => {
        params.set('partial', '1');
        return fetch('?' + params, {headers: {'X-Requested-With': 'fetch'}, signal: ctrl.signal});
    };

    const showSpinner = () => sentinel.replaceChildren(...spinner.map(n => n.cloneNode(true)));

    function setNext(next) {
        sentinel.dataset.next = next || '';
        sentinel.hidden = !next;
        observer.unobserve(sentinel);  // unobserve+observe forza una nuova verifica se il sentinella è ancora visibile
        if (next) { showSpinner(); observer.observe(sentinel); }
    }

    async function loadMore() {
        if (loading || !sentinel.dataset.next) return;
        loading = true;
        const my = gen;
        const params = new URLSearchParams(location.search);
        params.set('page', sentinel.dataset.next);
        try {
            const r = await fetchPage(params);
            if (!r.ok) throw new Error(r.status);
            const html = await r.text();
            if (my !== gen) return;
            grid.append(...parse(html));
            setNext(r.headers.get('X-Next-Page'));
        } catch (e) {
            if (e.name === 'AbortError' || my !== gen) return;
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-outline-secondary';
            btn.textContent = T.retry;
            btn.onclick = () => { showSpinner(); loadMore(); };
            sentinel.replaceChildren(btn);
        } finally { if (my === gen) loading = false; }
    }

    const observer = new IntersectionObserver(es => { if (es[0].isIntersecting) loadMore(); }, {rootMargin: '600px 0px'});
    if (sentinel.dataset.next) observer.observe(sentinel);

    async function search(q) {
        gen++; loading = false;
        const my = gen;
        if (ctrl) ctrl.abort();
        ctrl = new AbortController();
        const params = new URLSearchParams(location.search);
        if (q) params.set('q', q); else params.delete('q');
        params.delete('page'); params.delete('partial');
        history.replaceState(null, '', params.toString() ? '?' + params : location.pathname);
        document.querySelectorAll('.js-q').forEach(i => { i.value = q; });
        try {
            const r = await fetchPage(params);
            if (!r.ok) throw new Error(r.status);
            const html = await r.text();
            if (my !== gen) return;
            grid.replaceChildren(...parse(html));
            empty.textContent = T.empty;
            empty.hidden = grid.children.length > 0;
            title.textContent = q ? ' (' + q + ')' : '';
            setNext(r.headers.get('X-Next-Page'));
        } catch (e) {
            if (e.name === 'AbortError' || my !== gen) return;
            grid.replaceChildren();
            empty.textContent = T.error;
            empty.hidden = false;
            setNext('');
        }
    }

    let timer;
    document.querySelectorAll('input[data-live-search]').forEach(input => {
        input.form.addEventListener('submit', e => { e.preventDefault(); clearTimeout(timer); search(input.value.trim()); });
        input.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(() => search(input.value.trim()), 250);
        });
    });
})();
