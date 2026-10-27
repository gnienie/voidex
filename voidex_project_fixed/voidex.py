import os, sys, json, ssl, urllib.request, urllib.parse, threading, queue, re, hashlib
from pathlib import Path
import certifi
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_NAME = 'voidex'
MC_VERSION = '1.21.11'
API = 'https://api.modrinth.com/v2'
USER_AGENT = 'voidex-mod-installer/1.0 (Modrinth-only installer)'
HTTPS_CONTEXT = ssl.create_default_context(cafile=certifi.where())

# Known Modrinth project slugs. The app verifies every downloaded version against
# Minecraft 1.21.11 + Fabric; it never downloads from third-party mod sites.
MODS = [
 ('Architectury API', ['architectury-api']),
 ('BadOptimizations', ['badoptimizations']),
 ('Cloth Config API', ['cloth-config']),
 ('Dynamic FPS', ['dynamic-fps']),
 ('Entity Culling', ['entityculling']),
 ('Exordium', ['exordium']),
 ('Fabric API', ['fabric-api']),
 ('Fabric Language Kotlin', ['fabric-language-kotlin']),
 ('Fast IP Ping', ['fast-ip-ping']),
 ('FastQuit', ['fastquit']),
 ('ImmediatelyFast', ['immediatelyfast']),
 ('Immersive Optimization', ['immersive-optimization']),
 ('Low Fire Reborn', ['low-fire-reborn']),
 ('Mod Menu', ['modmenu']),
 ('More Culling', ['moreculling']),
 ('oωo (owo-lib)', ['owo-lib']),
 ('Placeholder API', ['placeholder-api']),
 ("Reese's Sodium Options", ['reeses-sodium-options']),
 ('SeamlessChunks', ['seamlesschunks', 'seamless-chunks']),
 ('Sodium Extra', ['sodium-extra']),
 ('Sodium', ['sodium']),
 ('YetAnotherConfigLib (YACL)', ['yet-another-config-lib']),
]

def request_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=25, context=HTTPS_CONTEXT) as response:
        return json.loads(response.read().decode('utf-8'))

def get_versions(slug):
    params = urllib.parse.urlencode({'game_versions': json.dumps([MC_VERSION]), 'loaders': json.dumps(['fabric'])})
    return request_json(f'{API}/project/{urllib.parse.quote(slug)}/version?{params}')

def find_project_by_search(title):
    params = urllib.parse.urlencode({'query': title, 'limit': 10, 'facets': json.dumps([[f'versions:{MC_VERSION}'], ['categories:fabric']])})
    data = request_json(f'{API}/search?{params}')
    hits = data.get('hits', [])
    wanted = re.sub(r'[^a-z0-9]', '', title.lower())
    for hit in hits:
        candidate = re.sub(r'[^a-z0-9]', '', hit.get('title', '').lower())
        if candidate == wanted:
            return hit.get('slug')
    return None

def download_file(url, destination):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=60, context=HTTPS_CONTEXT) as response, open(destination, 'wb') as out:
        while True:
            chunk = response.read(1024 * 128)
            if not chunk: break
            out.write(chunk)

def default_mods_dir():
    appdata = os.environ.get('APPDATA')
    if appdata:
        return Path(appdata) / '.tlauncher' / 'legacy' / 'Minecraft' / 'game' / 'mods'
    return Path.home() / 'AppData' / 'Roaming' / '.tlauncher' / 'legacy' / 'Minecraft' / 'game' / 'mods'

class VoidexApp:
    def __init__(self, root):
        self.root = root
        root.title('voidex — Modrinth Mod Installer')
        root.geometry('760x570')
        root.minsize(680, 500)
        root.configure(bg='#0b0616')
        self.q = queue.Queue()
        self.busy = False
        self.path_var = tk.StringVar(value=str(default_mods_dir()))
        self._style()
        self._build()
        self.root.after(100, self._poll)

    def _style(self):
        s = ttk.Style()
        try: s.theme_use('clam')
        except tk.TclError: pass
        s.configure('TFrame', background='#0b0616')
        s.configure('TLabel', background='#0b0616', foreground='#eee7ff', font=('Segoe UI', 10))
        s.configure('Title.TLabel', font=('Segoe UI', 23, 'bold'), foreground='#d87cff')
        s.configure('Sub.TLabel', font=('Segoe UI', 10), foreground='#aaa0c4')
        s.configure('TButton', font=('Segoe UI', 10, 'bold'), padding=9, background='#7224d8', foreground='white')
        s.map('TButton', background=[('active', '#9b3cff'), ('disabled', '#3b3150')])
        s.configure('Horizontal.TProgressbar', troughcolor='#1a1129', background='#c13dff')

    def _build(self):
        outer = ttk.Frame(self.root, padding=22); outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='voidex', style='Title.TLabel').pack(anchor='w')
        ttk.Label(outer, text='FABRIC  •  MINECRAFT 1.21.11  •  MODRINTH ONLY', style='Sub.TLabel').pack(anchor='w', pady=(0, 18))
        ttk.Label(outer, text='Mods folder').pack(anchor='w')
        row = ttk.Frame(outer); row.pack(fill='x', pady=(6, 16))
        self.path_entry = ttk.Entry(row, textvariable=self.path_var); self.path_entry.pack(side='left', fill='x', expand=True, ipady=6)
        self.browse_btn = ttk.Button(row, text='Browse…', command=self._browse); self.browse_btn.pack(side='left', padx=(8, 0))
        self.info = ttk.Label(outer, text=f'{len(MODS)} mods will be checked. Incompatible or unavailable versions will be skipped.', wraplength=690)
        self.info.pack(anchor='w', pady=(0, 12))
        self.progress = ttk.Progressbar(outer, mode='determinate', maximum=len(MODS)); self.progress.pack(fill='x', pady=(0, 10))
        self.log = tk.Text(outer, height=14, bg='#10091d', fg='#e8dcff', insertbackground='white', relief='flat', font=('Consolas', 9), padx=10, pady=8, wrap='word')
        self.log.pack(fill='both', expand=True)
        bottom = ttk.Frame(outer); bottom.pack(fill='x', pady=(14, 0))
        self.install_btn = ttk.Button(bottom, text='DOWNLOAD AND INSTALL MODS', command=self._start); self.install_btn.pack(side='left')
        ttk.Button(bottom, text='Open folder', command=self._open_folder).pack(side='left', padx=8)
        ttk.Label(bottom, text='voidex • Modrinth API', style='Sub.TLabel').pack(side='right')
        self._log('Ready. Mods are downloaded exclusively from the official Modrinth API/CDN.')

    def _log(self, msg):
        self.log.insert('end', msg + '\n'); self.log.see('end')

    def _browse(self):
        p = filedialog.askdirectory(title='Select the mods folder')
        if p: self.path_var.set(p)

    def _open_folder(self):
        p = Path(self.path_var.get()).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        try: os.startfile(str(p))
        except Exception as e: messagebox.showerror('voidex', f'Could not open folder:\n{e}')

    def _start(self):
        if self.busy: return
        p = Path(self.path_var.get().strip()).expanduser()
        if not str(p):
            messagebox.showerror('voidex', 'Please select a mods folder.'); return
        try: p.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror('voidex', f'Cannot access the folder:\n{e}'); return
        self.busy = True; self.install_btn.configure(state='disabled'); self.browse_btn.configure(state='disabled')
        self.progress.configure(value=0); self.log.delete('1.0', 'end')
        threading.Thread(target=self._worker, args=(p,), daemon=True).start()

    def _worker(self, folder):
        installed = 0; skipped = 0; errors = 0
        for i, (title, slugs) in enumerate(MODS, 1):
            self.q.put(('log', f'[{i}/{len(MODS)}] Checking: {title}'))
            try:
                versions = []
                for slug in slugs:
                    try:
                        versions = get_versions(slug)
                        if versions: break
                    except Exception:
                        continue
                if not versions:
                    slug = find_project_by_search(title)
                    if slug: versions = get_versions(slug)
                compatible = [v for v in versions if MC_VERSION in v.get('game_versions', []) and 'fabric' in v.get('loaders', [])]
                if not compatible:
                    skipped += 1
                    self.q.put(('log', f'  SKIPPED: No Fabric version for Minecraft {MC_VERSION} was found on Modrinth.'))
                else:
                    compatible.sort(key=lambda v: (v.get('date_published', ''), v.get('version_number', '')), reverse=True)
                    version = compatible[0]
                    files = [f for f in version.get('files', []) if f.get('primary') and f.get('filename', '').lower().endswith('.jar')]
                    if not files: files = [f for f in version.get('files', []) if f.get('filename', '').lower().endswith('.jar')]
                    if not files:
                        skipped += 1; self.q.put(('log', '  SKIPPED: This version has no JAR file.'))
                    else:
                        f = files[0]; dest = folder / Path(f['filename']).name
                        if dest.exists():
                            self.q.put(('log', f'  File already exists; updating: {dest.name}'))
                        download_file(f['url'], dest)
                        expected = f.get('hashes', {}).get('sha1')
                        if expected:
                            h = hashlib.sha1(dest.read_bytes()).hexdigest()
                            if h.lower() != expected.lower():
                                dest.unlink(missing_ok=True); raise ValueError('SHA-1 checksum mismatch; the file was deleted')
                        installed += 1
                        self.q.put(('log', f'  INSTALLED: {dest.name}'))
            except Exception as e:
                errors += 1; self.q.put(('log', f'  ERROR: {e}'))
            self.q.put(('progress', i))
        self.q.put(('done', (installed, skipped, errors, str(folder))))

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait(); kind = item[0]
                if kind == 'log': self._log(item[1])
                elif kind == 'progress': self.progress.configure(value=item[1])
                elif kind == 'done':
                    installed, skipped, errors, folder = item[1]
                    self.busy = False; self.install_btn.configure(state='normal'); self.browse_btn.configure(state='normal')
                    self._log(''); self._log(f'Finished. Installed/updated: {installed}; skipped: {skipped}; errors: {errors}.')
                    self._log('If the mods do not load in-game, make sure you are launching Fabric for Minecraft 1.21.11.')
                    messagebox.showinfo('voidex — Complete', f'Installed/updated: {installed}\nSkipped (no compatible version): {skipped}\nErrors: {errors}\n\nFolder: {folder}')
        except queue.Empty: pass
        self.root.after(100, self._poll)

def main():
    root = tk.Tk()
    try:
        from PIL import Image, ImageTk
        icon_path = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'voidex_logo.png'
        if icon_path.exists():
            im = Image.open(icon_path).convert('RGBA'); im.thumbnail((64, 64))
            root.iconphoto(True, ImageTk.PhotoImage(im))
    except Exception: pass
    VoidexApp(root)
    root.mainloop()

if __name__ == '__main__': main()
