#!/usr/bin/env node
// Build a phone-width, syntax-highlighted code page to screen-record with demo_rec.mjs.
//
//   node build_viewer.mjs <source file> <out.html> [--lang swift] [--title Name] [--project <P>] [--no-wrap]
//
// --lang   highlight.js language (default: from the file extension, else auto-detected)
// --title  tab label (default: the file name)
// --project  where highlight.js is installed (default: the current directory); it is only needed at build
//          time: the highlighted HTML is written into the page, so it works offline from file://.
//          Install it in the video project with `npm i -D highlight.js`.
// --no-wrap  keep long lines on one line (horizontal scroll) instead of folding them.
//
// Every line is <div class="ln" id="L<n>">; the page exposes window.mark(from, to), window.unmark(),
// window.scrollToLine(n, smooth) for demo beats (page.evaluate(() => window.mark(12, 14))).
import { createRequire } from 'node:module';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, dirname, extname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));

export function parseArgs(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--no-wrap') o.wrap = false;
    else if (['--lang', '--title', '--project'].includes(a)) {
      if (argv[i + 1] === undefined) throw new Error(`${a} needs a value`);
      o[a.slice(2)] = argv[++i];
    } else if (a.startsWith('--')) throw new Error(`unknown option ${a}`);
    else o._.push(a);
  }
  return o;
}

export function loadHljs(project = process.cwd()) {
  const req = createRequire(join(resolve(project), 'package.json'));
  try {
    return req('highlight.js');
  } catch {
    throw new Error(`highlight.js not found from ${resolve(project)}: run \`npm i -D highlight.js\` there or pass --project <P>`);
  }
}

// Split highlighted HTML per line, closing and reopening spans that cross a line break.
export function splitLines(h) {
  const out = [];
  const open = [];
  let cur = '';
  for (const part of h.split(/(<[^>]+>|\n)/)) {
    if (part === '\n') {
      out.push(cur + '</span>'.repeat(open.length));
      cur = open.join('');
    } else if (part.startsWith('</')) {
      open.pop();
      cur += part;
    } else if (part.startsWith('<')) {
      open.push(part);
      cur += part;
    } else {
      cur += part;
    }
  }
  out.push(cur);
  return out;
}

const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export function highlight(hljs, src, lang, file = '') {
  if (lang) {
    if (!hljs.getLanguage(lang)) throw new Error(`highlight.js has no language ${JSON.stringify(lang)}`);
    return { html: hljs.highlight(src, { language: lang, ignoreIllegals: true }).value, lang };
  }
  const ext = extname(file).slice(1).toLowerCase();
  if (ext && hljs.getLanguage(ext)) return { html: hljs.highlight(src, { language: ext, ignoreIllegals: true }).value, lang: ext };
  const r = hljs.highlightAuto(src);
  return { html: r.value, lang: r.language ?? 'plaintext' };
}

export function buildViewer({ src, title, lang, file, hljs, wrap = true, template = readFileSync(join(HERE, 'viewer.template.html'), 'utf8') }) {
  const text = src.replace(/\r\n?/g, '\n').replace(/\n$/, '');
  const { html, lang: used } = highlight(hljs, text, lang, file);
  const lines = splitLines(html).map((l, i) =>
    `<div class="ln" id="L${i + 1}"><span class="no">${i + 1}</span><span class="tx">${l}</span></div>`);
  const page = template
    .replaceAll('{{TITLE}}', esc(title))
    .replaceAll('{{NUMW}}', String(Math.max(2, String(lines.length).length)))
    .replaceAll('{{BODYCLASS}}', wrap ? 'wrap' : '')
    .replace('{{LINES}}', () => lines.join('\n'));
  return { page, lines: lines.length, lang: used };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const o = parseArgs(process.argv.slice(2));
    const [file, out] = o._;
    if (!file || !out || o._.length > 2) throw new Error('usage: node build_viewer.mjs <source file> <out.html> [--lang swift] [--title Name] [--project <P>] [--no-wrap]');
    if (!existsSync(file)) throw new Error(`no such file: ${file}`);
    const { page, lines, lang } = buildViewer({
      src: readFileSync(file, 'utf8'), title: o.title ?? basename(file), lang: o.lang, file, hljs: loadHljs(o.project), wrap: o.wrap !== false,
    });
    writeFileSync(out, page);
    console.log(`${out}: ${lines} lines (${lang})`);
  } catch (e) {
    console.error(e.message);
    process.exit(1);
  }
}
