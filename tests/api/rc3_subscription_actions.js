const fs = require('fs');
const vm = require('vm');

if (process.argv.length !== 7) {
  throw new Error('usage: node rc3_subscription_actions.js TEMPLATE CONFIG PBM COPY DOWNLOAD');
}
const [, , templatePath, configPath, pbmPath, copyPath, downloadPath] = process.argv;
const html = fs.readFileSync(templatePath, 'utf8');
const config = fs.readFileSync(configPath, 'utf8');
const scripts = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(match => match[1]);
if (scripts.length !== 2) throw new Error(`expected two inline scripts, got ${scripts.length}`);

let selected = null;
let copied = null;
let downloadedBlob = null;
class Element {
  constructor(name) {
    this.nodeName = name.toUpperCase();
    this.children = [];
    this.childNodes = this.children;
    this.style = {};
    this.dataset = {};
    this.value = '';
    this._innerHTML = '';
  }
  appendChild(child) { this.children.push(child); this.childNodes = this.children; child.parentNode = this; return child; }
  removeChild(child) { this.children = this.children.filter(item => item !== child); this.childNodes = this.children; return child; }
  get firstChild() { return this.children[0] || null; }
  set innerHTML(value) {
    this._innerHTML = value;
    const table = {offsetWidth: 256, offsetHeight: 256, style: {}};
    this.children = value ? [table] : [];
    this.childNodes = this.children;
  }
  get innerHTML() { return this._innerHTML; }
  setAttribute(name, value) { this[name] = value; }
  select() { selected = this; }
  click() { this.clicked = true; }
}
const body = new Element('body');
const qrCodeContainer = new Element('div');
const qrPopup = new Element('div');
const document = {
  documentElement: {tagName: 'html'},
  body,
  createElement: name => new Element(name),
  getElementById: id => id === 'qrPopup' ? qrPopup : (id === 'qrCodeContainer' ? qrCodeContainer : new Element('div')),
  querySelectorAll: () => [],
  addEventListener: () => {},
  execCommand: command => { if (command === 'copy' && selected) copied = selected.value; return true; },
};
global.document = document;
global.navigator = {userAgent: ''};
global.localStorage = {getItem: () => null, setItem: () => {}};
global.qrCodeContainer = qrCodeContainer;
global.qrPopup = qrPopup;
global.setTimeout = () => 0;
global.URL = {
  createObjectURL: blob => { downloadedBlob = blob; return 'blob:rc3'; },
  revokeObjectURL: () => {},
};

for (const script of scripts) vm.runInThisContext(script, {filename: templatePath});
const textarea = {value: config};
const item = {dataset: {name: 'rc3.conf'}, querySelector: selector => {
  if (selector !== '.native-config-input') throw new Error(`unexpected selector ${selector}`);
  return textarea;
}};
const button = {textContent: '', closest: selector => {
  if (selector !== '.native-config-item') throw new Error(`unexpected closest ${selector}`);
  return item;
}};

copyNativeConfig(button);
showNativeConfigQr(button);
downloadNativeConfig(button);
if (copied !== config) throw new Error('copy payload differs from textarea value');
if (!downloadedBlob) throw new Error('download did not create a Blob');

const rows = [...qrCodeContainer.innerHTML.matchAll(/<tr>([\s\S]*?)<\/tr>/g)].map(match => match[1]);
if (!rows.length) throw new Error('QR renderer produced no matrix rows');
const matrix = rows.map(row => [...row.matchAll(/background-color:(#[0-9a-fA-F]{6})/g)].map(match => match[1].toLowerCase() === '#000000' ? 1 : 0));
if (matrix.some(row => row.length !== matrix.length)) throw new Error('QR matrix is not square');
const quiet = 4;
const scale = 8;
const width = (matrix.length + quiet * 2) * scale;
const lines = ['P1', `${width} ${width}`];
const white = Array(width).fill(0);
for (let i = 0; i < quiet * scale; i++) lines.push(white.join(' '));
for (const row of matrix) {
  const scaled = [...Array(quiet * scale).fill(0), ...row.flatMap(value => Array(scale).fill(value)), ...Array(quiet * scale).fill(0)];
  for (let i = 0; i < scale; i++) lines.push(scaled.join(' '));
}
for (let i = 0; i < quiet * scale; i++) lines.push(white.join(' '));
fs.writeFileSync(pbmPath, lines.join('\n') + '\n', {mode: 0o600});
fs.writeFileSync(copyPath, copied, {mode: 0o600});
downloadedBlob.arrayBuffer().then(buffer => fs.writeFileSync(downloadPath, Buffer.from(buffer), {mode: 0o600}));
