/* FractalOS landing page: a few small interactions, no dependencies.
   The page works without this file; all four tour transcripts simply stay open. */
(function () {
    'use strict';

    // The page has two homes: a checkout (landing.html beside index.html) and the
    // published site (landing.html renamed to the root page, with the OS under os/).
    var localLayout = location.protocol === 'file:' || /\/landing\.html$/.test(location.pathname);
    document.querySelectorAll('[data-boot]').forEach(function (link) {
        link.setAttribute('href', localLayout ? './index.html' : './os/index.html');
    });

    var tabs = Array.prototype.slice.call(document.querySelectorAll('.tour-tab'));
    var panels = Array.prototype.slice.call(document.querySelectorAll('.tour-panel'));

    function activate(tab, focus) {
        var panelId = tab.getAttribute('aria-controls');
        tabs.forEach(function (item) {
            var selected = item === tab;
            item.setAttribute('aria-selected', String(selected));
            item.tabIndex = selected ? 0 : -1;
        });
        panels.forEach(function (panel) {
            panel.hidden = panel.id !== panelId;
        });
        if (focus) tab.focus();
    }

    if (tabs.length && panels.length) {
        panels.slice(1).forEach(function (panel) { panel.hidden = true; });

        tabs.forEach(function (tab, index) {
            tab.addEventListener('click', function () { activate(tab, false); });
            tab.addEventListener('keydown', function (event) {
                var next = null;
                if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
                else if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
                else if (event.key === 'Home') next = 0;
                else if (event.key === 'End') next = tabs.length - 1;
                if (next === null) return;
                event.preventDefault();
                activate(tabs[next], true);
            });
        });
    }

    document.querySelectorAll('[data-copy]').forEach(function (button) {
        button.addEventListener('click', function () {
            var text = button.getAttribute('data-copy') || '';
            var label = button.textContent;
            var done = function () {
                button.textContent = 'Copied';
                window.setTimeout(function () { button.textContent = label; }, 1600);
            };
            var fallback = function () {
                var area = document.createElement('textarea');
                area.value = text;
                area.setAttribute('readonly', '');
                area.style.position = 'fixed';
                area.style.top = '-1000px';
                document.body.appendChild(area);
                area.select();
                try { document.execCommand('copy'); done(); } catch (error) { /* leave the label alone */ }
                document.body.removeChild(area);
            };
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).then(done, fallback);
            } else {
                fallback();
            }
        });
    });

    var contents = Array.prototype.slice.call(document.querySelectorAll('.contents a'));
    var sections = contents.map(function (link) {
        var id = link.getAttribute('href');
        return id && id.charAt(0) === '#' ? document.querySelector(id) : null;
    }).filter(Boolean);

    if (sections.length && 'IntersectionObserver' in window) {
        var setActive = function (id) {
            contents.forEach(function (link) {
                link.classList.toggle('active', link.getAttribute('href') === '#' + id);
            });
        };
        var observer = new IntersectionObserver(function (entries) {
            var visible = entries.filter(function (entry) { return entry.isIntersecting; })
                .sort(function (a, b) { return b.intersectionRatio - a.intersectionRatio; })[0];
            if (visible) setActive(visible.target.id);
        }, { rootMargin: '-18% 0px -68% 0px', threshold: [0, .1, .25] });
        sections.forEach(function (section) { observer.observe(section); });
        setActive((location.hash || '#top').slice(1));
    }
})();
