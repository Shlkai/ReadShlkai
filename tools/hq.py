# Capa de cada HQ (1ª página do arquivo no Drive público) -> covers/hq/<id>.jpg + covers/hq/index.json
# Roda no GitHub Actions. Lista a pasta HQs pela página pública do Drive (sem chave).
import json, os, re, subprocess, sys, time, html, urllib.request, tempfile, shutil
ROOT = '11wvXlT24OPcZqQ_Oz3KlAtHecXCxUlgq'
UA = {'User-Agent': 'Mozilla/5.0 ShikaiCovers'}
OUT = 'covers/hq'; os.makedirs(OUT, exist_ok=True)
IDX = OUT + '/index.json'
idx = json.load(open(IDX)) if os.path.exists(IDX) else {'files': {}, 'fail': {}}
LIMIT = float(os.environ.get('MINUTES', '300')) * 60; T0 = time.time()
def get(url, rng=None, k=4):
    for i in range(k):
        try:
            h = dict(UA)
            if rng: h['Range'] = rng
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=120) as r: return r.read()
        except Exception as e: print('  erro', url[:80], e); time.sleep(3 * (i + 1))
    return None
def ls(fid):
    b = get(f'https://drive.google.com/embeddedfolderview?id={fid}#list')
    if not b: return None
    t = b.decode('utf-8', 'replace'); out = []
    for m in re.finditer(r'<div class="flip-entry" id="entry-([\w-]+)".*?<a href="([^"]+)".*?<div class="flip-entry-title">(.*?)</div>', t, re.S):
        out.append({'id': m.group(1), 'folder': '/folders/' in m.group(2), 'name': html.unescape(m.group(3))})
    return out
def crawl(fid, path, acc):
    items = ls(fid)
    if items is None: print('  NAO LISTOU', path); return
    for x in items:
        if x['folder']: crawl(x['id'], path + [x['name']], acc); time.sleep(0.3)
        elif re.search(r'\.(pdf|cbz|cbr|zip|rar)$', x['name'], re.I): acc.append({**x, 'path': '/'.join(path)})
DL = 'https://drive.usercontent.google.com/download?id={}&export=download&confirm=t'
IMG = re.compile(r'\.(jpe?g|png|webp|gif|bmp)$', re.I)
def nat(s): return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]
def shrink(src, dst):
    r = subprocess.run(['convert', src + '[0]', '-resize', '300x450>', '-strip', '-quality', '78', dst], capture_output=True)
    return r.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 2000
def cover(f):
    tmp = tempfile.mkdtemp(); a = tmp + '/a'; dst = f"{OUT}/{f['id']}.jpg"
    try:
        pdf = f['name'].lower().endswith('.pdf')
        for rng in (['bytes=0-8000000', None] if not pdf else ['bytes=0-6000000', None]):
            b = get(DL.format(f['id']), rng)
            if not b: continue
            open(a, 'wb').write(b)
            if pdf:
                if b[:5] != b'%PDF-': return 'nao e pdf (%r)' % b[:20]
                subprocess.run(['pdftoppm', '-f', '1', '-l', '1', '-jpeg', '-scale-to', '900', a, tmp + '/p'], capture_output=True)
                pg = [x for x in os.listdir(tmp) if x.startswith('p')]
                if pg and shrink(tmp + '/' + pg[0], dst): return None
            else:
                r = subprocess.run(['bsdtar', '-tf', a], capture_output=True)
                names = sorted([n for n in r.stdout.decode('utf-8', 'replace').split('\n') if IMG.search(n) and '__MACOSX' not in n], key=nat)
                if names:
                    subprocess.run(['bsdtar', '-xf', a, '-C', tmp, names[0]], capture_output=True)
                    p = os.path.join(tmp, names[0])
                    if os.path.exists(p) and os.path.getsize(p) > 2000 and shrink(p, dst): return None
            if rng is None: break
            if len(b) < 8000000 and rng: break  # arquivo inteiro já veio
        return 'sem imagem'
    finally: shutil.rmtree(tmp, ignore_errors=True)
files = []
crawl(ROOT, [], files)
print(len(files), 'arquivos de HQ')
json.dump(files, open(OUT + '/inventario.json', 'w'), ensure_ascii=False, indent=0)
import threading
from concurrent.futures import ThreadPoolExecutor
lock = threading.Lock(); done = [0]
def work(f):
    if time.time() - T0 > LIMIT: return
    err = cover(f)
    with lock:
        if err is None: idx['files'][f['id']] = f"{OUT}/{f['id']}.jpg"; idx['fail'].pop(f['id'], None); done[0] += 1
        else:
            fl = idx['fail'].setdefault(f['id'], {'n': 0}); fl['n'] += 1; fl['err'] = err; fl['name'] = f['path'] + '/' + f['name']; print('  falhou', f['name'], err)
        if done[0] % 100 == 0: json.dump(idx, open(IDX, 'w'), ensure_ascii=False, indent=0); print('  ...', len(idx['files']), flush=True)
todo = [f for f in files if f['id'] not in idx['files'] and idx['fail'].get(f['id'], {}).get('n', 0) < 2]
print(len(todo), 'a fazer')
with ThreadPoolExecutor(8) as ex: list(ex.map(work, todo))
json.dump(idx, open(IDX, 'w'), ensure_ascii=False, indent=0)
print('capas', len(idx['files']), 'de', len(files), '| falhas', len(idx['fail']))
