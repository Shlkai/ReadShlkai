# Baixa as capas dos mangás (AniList: capa da obra; MangaDex: capa de cada volume) para covers/.
# Roda no GitHub Actions. Lista de séries em covers/series.json.
import json, os, re, time, urllib.request, urllib.parse
UA = {'User-Agent': 'ShikaiCovers/1.0 (leitor pessoal)'}
def get(url, data=None, hdr=None):
    h = dict(UA); h.update(hdr or {})
    for k in range(4):
        try:
            req = urllib.request.Request(url, data=data, headers=h)
            with urllib.request.urlopen(req, timeout=60) as r: return r.read()
        except Exception as e:
            print('  erro', url[:90], e); time.sleep(3 * (k + 1))
    return None
def js(url, data=None, hdr=None):
    b = get(url, data, hdr); return json.loads(b) if b else {}
def slug(k): return re.sub(r'[^a-z0-9]+', '-', k).strip('-')
def save(path, url):
    if os.path.exists(path) and os.path.getsize(path) > 3000: return True
    b = get(url)
    if not b or len(b) < 3000: return False
    open(path, 'wb').write(b); time.sleep(0.3); return True
out, log = {}, []
for s in json.load(open('covers/series.json')):
    k = s['key']; d = 'covers/' + slug(k); os.makedirs(d, exist_ok=True)
    e = {'mode': s.get('mode', 'none'), 'force': bool(s.get('force')), 'vols': {}, 'chVol': []}
    q = 'query($s:String){Media(search:$s,type:MANGA){id title{romaji english} coverImage{extraLarge}}}'
    a = js('https://graphql.anilist.co', json.dumps({'query': q, 'variables': {'s': s['anilist']}}).encode(), {'Content-Type': 'application/json', 'Accept': 'application/json'})
    m = (a.get('data') or {}).get('Media') or {}
    url = (m.get('coverImage') or {}).get('extraLarge')
    if url and save(d + '/obra.jpg', url): e['main'] = d + '/obra.jpg'
    log.append(f"{k}: AniList {m.get('id')} {(m.get('title') or {}).get('romaji')} -> {'ok' if e.get('main') else 'SEM CAPA'}")
    time.sleep(1.5)
    if s.get('mangadex') and e['mode'] != 'none':
        r = js('https://api.mangadex.org/manga?' + urllib.parse.urlencode({'title': s['mangadex'], 'limit': 5, 'order[relevance]': 'desc'}))
        data = r.get('data') or []
        rank = lambda l: {'ja': 0, 'en': 1, 'pt-br': 2}.get(l, 3)
        def covers_of(mid):
            best = {}
            for off in range(0, 400, 100):
                c = js(f'https://api.mangadex.org/cover?manga[]={mid}&limit=100&offset={off}&order[volume]=asc')
                for x in c.get('data') or []:
                    v = (x['attributes'].get('volume') or '').strip()
                    if not v: continue
                    try: v = str(int(float(v))) if float(v) == int(float(v)) else v
                    except: pass
                    if v not in best or rank(x['attributes'].get('locale')) < rank(best[v][1]): best[v] = (x['attributes']['fileName'], x['attributes'].get('locale'))
                if len(c.get('data') or []) < 100: break
                time.sleep(0.5)
            return best
        # entre os 5 primeiros resultados, fica com o que tem mais capas de volume (evita versões coloridas por fãs)
        cand = []
        for x in data[:5]:
            cand.append((x, covers_of(x['id']))); time.sleep(0.5)
        if cand:
            x, best = max(cand, key=lambda c: len(c[1]))
            mid = x['id']; t = x['attributes']['title']
            for v, (f, _) in best.items():
                p = f'{d}/v{v}.jpg'
                if save(p, f'https://uploads.mangadex.org/covers/{mid}/{f}.512.jpg'): e['vols'][v] = p
            if e['mode'] == 'chapters' and not s.get('wiki'):
                ag = js(f'https://api.mangadex.org/manga/{mid}/aggregate')
                cv = []
                for v, o in (ag.get('volumes') or {}).items():
                    if v == 'none': continue
                    for ch in (o.get('chapters') or {}):
                        try: cv.append([float(ch), str(int(float(v)))])
                        except: pass
                e['chVol'] = sorted(cv)
            log.append(f"  MangaDex {mid} {t} -> {len(e['vols'])} volumes, {len(e['chVol'])} capitulos mapeados")
        time.sleep(1)
    if s.get('wiki'):
        # capítulo -> volume pela lista de capítulos da Wikipédia
        w = js('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'parse', 'page': s['wiki'], 'prop': 'wikitext', 'format': 'json', 'formatversion': 2}))
        txt = (w.get('parse') or {}).get('wikitext') or ''
        cv = []
        for blk in re.split(r'\{\{\s*Graphic novel list', txt, flags=re.I)[1:]:
            vm = re.search(r'\|\s*VolumeNumber\s*=\s*(\d+)', blk)
            cl = re.search(r'\|\s*ChapterList\s*=(.*?)(?:\n\s*\|\s*\w+\s*=|\Z)', blk, re.S)
            if not vm or not cl: continue
            for ch in re.findall(r'^\s*\*\s*(?:Page|Chapter|Ch\.?)?\s*(\d{1,3}(?:\.\d)?)', cl.group(1), re.M | re.I):
                cv.append([float(ch), str(int(vm.group(1)))])
        e['chVol'] = sorted(cv)
        log.append(f"  Wikipedia {s['wiki']} -> {len(cv)} capitulos mapeados, volumes {len(set(v for _, v in cv))}")
    out[k] = e
json.dump(out, open('covers/index.json', 'w'), ensure_ascii=False, indent=1)
open('covers/log.txt', 'w').write('\n'.join(log) + '\n'); print('\n'.join(log))
