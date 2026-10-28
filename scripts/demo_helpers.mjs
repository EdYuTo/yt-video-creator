// Helpers handed to a demo beat: h = helpers(page). All motion is rAF-driven so the CDP screencast sees it.
//   await h.ready                 (the cursor init script is installed; demo_rec awaits it before goto)
//   h.pause(ms)  h.scrollTo(sel, ms=1200)  h.type(sel, text, cps=12)  h.click(sel)  h.hide([sel, ...])

const CURSOR_SIZE = 28;

// Runs in every page of the context (and is idempotent so click() can call it on an already-loaded page).
function cursorInit(size) {
  const make = () => {
    if (window.__demoCursor || !document.documentElement) return;
    const d = document.createElement('div');
    d.id = '__demo-cursor';
    d.style.cssText = `position:fixed;left:0;top:0;width:${size}px;height:${size}px;margin:${-size / 2}px 0 0 ${-size / 2}px;` +
      'border-radius:50%;background:#fff;border:3px solid #1a1a1a;box-sizing:border-box;box-shadow:0 2px 8px rgba(0,0,0,.45);' +
      'pointer-events:none;z-index:2147483647;opacity:0;transition:opacity .2s;transform:translate(216px,600px)';
    document.documentElement.appendChild(d);
    window.__demoCursor = { el: d, x: 216, y: 600 };
  };
  make();
  document.addEventListener('DOMContentLoaded', make);
}

export function helpers(page) {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const ready = page.addInitScript(cursorInit, CURSOR_SIZE);
  return {
    ready,
    pause: sleep,

    // container: optional selector of an inner scroll pane (SPAs); default is the document's scrolling element.
    // Each step uses scrollTo({behavior:'instant'}) so `scroll-behavior: smooth` in the site's CSS cannot hijack it.
    async scrollTo(selector, ms = 1200, container = null) {
      await page.evaluate(([sel, dur, cont]) => new Promise((resolve, reject) => {
        const el = document.querySelector(sel);
        if (!el) return reject(new Error(`scrollTo: no element ${sel}`));
        const root = cont ? document.querySelector(cont) : document.scrollingElement;
        if (!root) return reject(new Error(`scrollTo: no container ${cont}`));
        const from = root.scrollTop;
        const top0 = cont ? root.getBoundingClientRect().top + root.clientTop : 0;
        const to = Math.max(0, Math.min(root.scrollHeight - root.clientHeight, el.getBoundingClientRect().top - top0 + from - 24));
        const t0 = performance.now();
        const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
        const step = (now) => {
          const t = Math.min(1, (now - t0) / dur);
          root.scrollTo({ top: from + (to - from) * ease(t), behavior: 'instant' });
          t < 1 ? requestAnimationFrame(step) : resolve();
        };
        requestAnimationFrame(step);
      }), [selector, ms, container]);
    },

    async type(selector, text, cps = 12) {
      const loc = page.locator(selector).first();
      // Automation never types credentials: logins are done by hand in the persistent profile.
      const secret = await loc.evaluate((el) => el.matches('input[type=password]') ||
        /(current|new)-password/.test(el.getAttribute('autocomplete') ?? ''));
      if (secret) throw new Error(`type: refusing to type into a password field (${selector}); log in by hand with demo_rec.mjs login`);
      await loc.focus();
      await page.keyboard.type(text, { delay: 1000 / cps });
    },

    async click(selector) {
      const loc = page.locator(selector).first();
      await loc.scrollIntoViewIfNeeded();
      const box = await loc.boundingBox();
      if (!box) throw new Error(`click: ${selector} has no box`);
      const x = box.x + box.width / 2, y = box.y + box.height / 2;
      await page.evaluate(([cx, cy, size, ms, init]) => new Promise((resolve) => {
        if (!window.__demoCursor) (new Function(`(${init})(${size})`))();
        const c = window.__demoCursor;
        c.el.style.opacity = '1';
        const x0 = c.x, y0 = c.y, t0 = performance.now();
        const step = (now) => {
          const t = Math.min(1, (now - t0) / ms);
          const e = 1 - Math.pow(1 - t, 3);
          c.x = x0 + (cx - x0) * e; c.y = y0 + (cy - y0) * e;
          c.el.style.transform = `translate(${c.x}px,${c.y}px)`;
          t < 1 ? requestAnimationFrame(step) : resolve();
        };
        requestAnimationFrame(step);
      }), [x, y, CURSOR_SIZE, 400, cursorInit.toString()]);
      await loc.click();
    },

    // Banners and cookie bars only; never use this on personal details.
    async hide(selectors) {
      await page.addStyleTag({ content: `${selectors.join(',')}{display:none !important}` });
    },
  };
}
