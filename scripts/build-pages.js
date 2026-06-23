const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const docs = path.join(root, 'docs');

function removeDir(target) {
  if (fs.existsSync(target)) {
    fs.rmSync(target, {recursive: true, force: true});
  }
}

function ensureDir(target) {
  fs.mkdirSync(target, {recursive: true});
}

function copyFile(from, to) {
  ensureDir(path.dirname(to));
  fs.copyFileSync(from, to);
}

function copyIndexForPages() {
  const source = path.join(root, 'index.html');
  const target = path.join(docs, 'index.html');
  const html = fs.readFileSync(source, 'utf8').replace(
    'const STATIC_PAGES_BUILD = false;',
    'const STATIC_PAGES_BUILD = true;'
  );
  ensureDir(path.dirname(target));
  fs.writeFileSync(target, html, 'utf8');
}

function copyDirIfExists(from, to) {
  if (!fs.existsSync(from)) return false;
  ensureDir(to);
  for (const entry of fs.readdirSync(from, {withFileTypes: true})) {
    const source = path.join(from, entry.name);
    const target = path.join(to, entry.name);
    if (entry.isDirectory()) {
      copyDirIfExists(source, target);
    } else if (entry.isFile()) {
      copyFile(source, target);
    }
  }
  return true;
}

removeDir(docs);
ensureDir(docs);

copyIndexForPages();
copyDirIfExists(path.join(root, 'data', 'processed'), path.join(docs, 'data', 'processed'));
copyDirIfExists(path.join(root, 'data', 'demo'), path.join(docs, 'data', 'demo'));

fs.writeFileSync(
  path.join(docs, '.nojekyll'),
  '',
  'utf8'
);

console.log('GitHub Pages package created in docs/.');
console.log('Included: index.html, data/processed if present, and data/demo.');
console.log('Excluded: server.js, data/raw, data/output, documentation, exports and dependencies.');
