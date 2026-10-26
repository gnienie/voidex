from __future__ import annotations

import json
import os
import queue
import re
import sys
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from tkinter import filedialog, messagebox

import customtkinter as ctk

try:
    import minecraft_launcher_lib
    import minecraft_launcher_lib.fabric
except ImportError:
    minecraft_launcher_lib = None

APP_NAME = "Voidex"
APP_VERSION = "2.1"
MINECRAFT_MANIFEST = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
MODRINTH_API = "https://api.modrinth.com/v2"
USER_AGENT = f"Voidex/{APP_VERSION} (https://github.com/gnienie/voidex)"
MIN_MINECRAFT = (1, 16, 5)

MODS = [
    {"slug": "fabric-api", "name": "Fabric API", "description": "Common library required by many Fabric mods.", "default": True},
    {"slug": "sodium", "name": "Sodium", "description": "Improves rendering performance and frame pacing.", "default": True},
    {"slug": "lithium", "name": "Lithium", "description": "Optimizes game logic and world ticking.", "default": True},
    {"slug": "ferrite-core", "name": "FerriteCore", "description": "Reduces memory use.", "default": True},
    {"slug": "immediatelyfast", "name": "ImmediatelyFast", "description": "Optimizes immediate-mode rendering.", "default": True},
    {"slug": "entityculling", "name": "Entity Culling", "description": "Skips rendering hidden entities and block entities.", "default": True},
    {"slug": "modernfix", "name": "ModernFix", "description": "A collection of performance and memory fixes.", "default": True},
    {"slug": "dynamic-fps", "name": "Dynamic FPS", "description": "Reduces resource use when the game is inactive.", "default": True},
    {"slug": "moreculling", "name": "More Culling", "description": "Culls objects that do not need to be rendered.", "default": False},
    {"slug": "badoptimizations", "name": "BadOptimizations", "description": "Targets several vanilla client performance issues.", "default": False},
    {"slug": "krypton", "name": "Krypton", "description": "Optimizes parts of the networking stack.", "default": False},
    {"slug": "noisium", "name": "Noisium", "description": "Optimizes world-generation noise calculations.", "default": False},
    {"slug": "fastquit", "name": "FastQuit", "description": "Makes leaving a world less disruptive.", "default": False},
    {"slug": "debugify", "name": "Debugify", "description": "Fixes selected vanilla bugs.", "default": False},
    {"slug": "enhanced-block-entities", "name": "Enhanced Block Entities", "description": "Improves rendering for selected block entities.", "default": False},
    {"slug": "language-reload", "name": "Language Reload", "description": "Improves language switching and reloads.", "default": False},
    {"slug": "memoryleakfix", "name": "Memory Leak Fix", "description": "Fixes memory leaks on compatible game versions.", "default": False},
    {"slug": "exordium", "name": "Exordium", "description": "Reduces GUI rendering work in supported situations.", "default": False},
    {"slug": "sodium-extra", "name": "Sodium Extra", "description": "Adds extra settings for Sodium.", "default": False},
    {"slug": "reeses-sodium-options", "name": "Reese's Sodium Options", "description": "Improves the Sodium settings screen.", "default": False},
    {"slug": "yet-another-config-lib", "name": "YetAnotherConfigLib", "description": "Configuration library used by some optional mods.", "default": False},
    {"slug": "modmenu", "name": "Mod Menu", "description": "Shows installed mods in-game.", "default": False},
]

C = {
    "bg": "#111018", "panel": "#191722", "alt": "#211e2c", "border": "#302b40",
    "purple": "#8b5cf6", "hover": "#7546dc", "text": "#f4f1fb",
    "muted": "#a39bb5", "green": "#55d6a2", "red": "#ff7474",
}


def app_data_dir() -> Path:
    folder = Path(os.environ.get("APPDATA", Path.home())) / "Voidex"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def default_game_dir() -> Path:
    appdata = Path(os.environ.get("APPDATA", Path.home()))
    candidates = [
        appdata / ".tlauncher" / "legacy" / "Minecraft" / "game",
        appdata / ".minecraft",
        Path.home() / ".minecraft",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return appdata / ".minecraft"


def version_numbers(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", version)) or (0,)


def supported_release(version: str) -> bool:
    nums = version_numbers(version)
    nums += (0,) * max(0, 3 - len(nums))
    return nums >= MIN_MINECRAFT


def read_url(url: str, timeout: int = 30) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as response:
        return response.read()


def read_json(url: str, timeout: int = 30):
    return json.loads(read_url(url, timeout).decode("utf-8"))


def get_mod_versions(slug: str, minecraft_version: str) -> list[dict]:
    params = urlencode({
        "game_versions": json.dumps([minecraft_version]),
        "loaders": json.dumps(["fabric"]),
    })
    return read_json(f"{MODRINTH_API}/project/{slug}/version?{params}", timeout=22)


def get_primary_file(version: dict) -> dict | None:
    files = version.get("files") or []
    if not files:
        return None
    return next((item for item in files if item.get("primary")), files[0])


class VoidexApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Voidex — Minecraft Optimizer")
        self.geometry("1160x790")
        self.minsize(990, 690)
        self.configure(fg_color=C["bg"])
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.events: queue.Queue = queue.Queue()
        self.cache: dict[tuple[str, str], dict | None] = {}
        self.compat: dict[str, bool | None] = {m["slug"]: None for m in MODS}
        self.checkboxes: dict[str, ctk.CTkCheckBox] = {}
        self.status_labels: dict[str, ctk.CTkLabel] = {}
        self.generation = 0
        self.busy = False
        self.game_dir = default_game_dir()
        self.settings_path = app_data_dir() / "settings.json"
        self.log_path = app_data_dir() / "voidex.log"
        self._load_settings()
        self._build_ui()
        self._load_assets()
        self.after(100, self._poll)
        self.after(150, lambda: threading.Thread(target=self._fetch_versions, daemon=True).start())

    def _load_settings(self):
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            self.game_dir = Path(data.get("game_dir") or self.game_dir)
            self.saved_version = str(data.get("version", ""))
            self.saved_mods = set(data.get("selected_mods", []))
            if "selected_mods" not in data:
                self.saved_mods = {m["slug"] for m in MODS if m["default"]}
        except (OSError, ValueError, TypeError):
            self.saved_version = ""
            self.saved_mods = {m["slug"] for m in MODS if m["default"]}

    def _save_settings(self):
        try:
            data = {
                "game_dir": str(self._current_folder()),
                "version": self.version_menu.get() if hasattr(self, "version_menu") else "",
                "selected_mods": [slug for slug, box in self.checkboxes.items() if box.get()],
            }
            self.settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except (OSError, AttributeError):
            pass

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        side = ctk.CTkFrame(self, width=258, corner_radius=0, fg_color=C["panel"])
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        side.grid_columnconfigure(0, weight=1)

        brand = ctk.CTkFrame(side, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=22, pady=(25, 22))
        brand.grid_columnconfigure(1, weight=1)
        self.logo_slot = ctk.CTkFrame(brand, width=52, height=52, fg_color=C["alt"], corner_radius=15)
        self.logo_slot.grid(row=0, column=0, padx=(0, 12))
        self.logo_slot.grid_propagate(False)
        self.logo_fallback = ctk.CTkLabel(self.logo_slot, text="V",
            font=ctk.CTkFont(size=28, weight="bold"), text_color=C["purple"])
        self.logo_fallback.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(brand, text="VOIDEX", font=ctk.CTkFont(size=23, weight="bold"),
                     text_color=C["text"]).grid(row=0, column=1, sticky="sw")
        ctk.CTkLabel(brand, text=f"VERSION {APP_VERSION}", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=C["muted"]).grid(row=1, column=1, sticky="nw", pady=(2, 0))
        ctk.CTkFrame(side, height=1, fg_color=C["border"]).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))

        ctk.CTkLabel(side, text="YOUR SETUP", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=C["muted"]).grid(row=2, column=0, sticky="w", padx=22, pady=(0, 10))
        self.side_version = ctk.CTkLabel(side, text="Loading Minecraft versions…",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=C["text"], anchor="w")
        self.side_version.grid(row=3, column=0, sticky="ew", padx=22)
        self.side_status = ctk.CTkLabel(side, text="Connecting to Mojang", font=ctk.CTkFont(size=11),
            text_color=C["muted"], anchor="w", wraplength=210)
        self.side_status.grid(row=4, column=0, sticky="ew", padx=22, pady=(5, 22))

        ctk.CTkButton(side, text="Install Fabric", height=43, corner_radius=11,
            fg_color=C["alt"], hover_color=C["border"], text_color=C["text"],
            command=self.install_fabric).grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.install_button = ctk.CTkButton(side, text="Install selected mods", height=46, corner_radius=11,
            fg_color=C["purple"], hover_color=C["hover"], text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"), command=self.install_mods)
        self.install_button.grid(row=6, column=0, sticky="ew", padx=20)
        ctk.CTkLabel(side, text="Only compatible Fabric files are\noffered for installation.",
            justify="left", font=ctk.CTkFont(size=11), text_color=C["muted"]).grid(
            row=7, column=0, sticky="sw", padx=22, pady=(18, 14))

        footer = ctk.CTkFrame(side, fg_color="transparent")
        footer.grid(row=8, column=0, sticky="sew", padx=20, pady=18)
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(footer, text="Open mods folder", height=35, corner_radius=9,
            fg_color="transparent", border_width=1, border_color=C["border"],
            hover_color=C["alt"], command=self.open_mods_folder).grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkButton(footer, text="GitHub source", height=35, corner_radius=9,
            fg_color="transparent", border_width=1, border_color=C["border"],
            hover_color=C["alt"], command=lambda: webbrowser.open("https://github.com/gnienie/voidex")
        ).grid(row=1, column=0, sticky="ew")

        content = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        content.grid(row=0, column=1, sticky="nsew", padx=24, pady=(23, 18))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Make Minecraft feel lighter.", font=ctk.CTkFont(size=28, weight="bold"),
            text_color=C["text"], anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(header, text="Choose a version, check compatibility, and install what you need.",
            font=ctk.CTkFont(size=12), text_color=C["muted"], anchor="w"
        ).grid(row=1, column=0, sticky="ew", pady=(5, 0))

        setup = ctk.CTkFrame(content, fg_color=C["panel"], corner_radius=14, border_width=1, border_color=C["border"])
        setup.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        setup.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(setup, text="Minecraft version", font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["text"]).grid(row=0, column=0, padx=(17, 14), pady=(17, 7), sticky="w")
        self.version_menu = ctk.CTkComboBox(setup, values=["Loading…"], state="readonly", height=36, width=185,
            command=self._version_changed, corner_radius=9, fg_color=C["alt"], border_color=C["border"],
            button_color=C["purple"], button_hover_color=C["hover"])
        self.version_menu.grid(row=0, column=1, padx=(0, 10), pady=(17, 7), sticky="w")
        self.check_button = ctk.CTkButton(setup, text="Check compatibility", height=36, corner_radius=9,
            fg_color=C["alt"], hover_color=C["border"], command=self.check_compatibility)
        self.check_button.grid(row=0, column=2, padx=(0, 17), pady=(17, 7), sticky="e")

        ctk.CTkLabel(setup, text="Game folder", font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["text"]).grid(row=1, column=0, padx=(17, 14), pady=(7, 17), sticky="w")
        self.folder_entry = ctk.CTkEntry(setup, height=36, corner_radius=9, border_color=C["border"],
            fg_color=C["alt"], text_color=C["text"])
        self.folder_entry.grid(row=1, column=1, padx=(0, 10), pady=(7, 17), sticky="ew")
        self.folder_entry.insert(0, str(self.game_dir))
        self.folder_button = ctk.CTkButton(setup, text="Browse", width=82, height=36, corner_radius=9,
            fg_color=C["alt"], hover_color=C["border"], command=self.choose_folder)
        self.folder_button.grid(row=1, column=2, padx=(0, 17), pady=(7, 17), sticky="e")

        mods_head = ctk.CTkFrame(content, fg_color="transparent")
        mods_head.grid(row=2, column=0, sticky="ew", pady=(2, 9))
        mods_head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(mods_head, text="Optimization mods", font=ctk.CTkFont(size=18, weight="bold"),
            text_color=C["text"], anchor="w").grid(row=0, column=0, sticky="w")
        self.mods_count = ctk.CTkLabel(mods_head, text="Checking compatibility…",
            font=ctk.CTkFont(size=11), text_color=C["muted"])
        self.mods_count.grid(row=0, column=1, sticky="e")

        self.mods_scroll = ctk.CTkScrollableFrame(content, fg_color=C["panel"], corner_radius=14,
            border_width=1, border_color=C["border"], scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["muted"])
        self.mods_scroll.grid(row=3, column=0, sticky="nsew", pady=(0, 14))
        self.mods_scroll.grid_columnconfigure(0, weight=1)
        self.mods_scroll.grid_columnconfigure(1, weight=1)
        for idx, mod in enumerate(MODS):
            self._add_mod_card(mod, idx)

        bottom = ctk.CTkFrame(content, fg_color=C["panel"], corner_radius=13, border_width=1, border_color=C["border"])
        bottom.grid(row=4, column=0, sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(bottom, text="Ready when you are.", font=ctk.CTkFont(size=11),
            text_color=C["muted"], anchor="w")
        self.status_label.grid(row=0, column=0, padx=14, pady=(10, 2), sticky="ew")
        self.progress = ctk.CTkProgressBar(bottom, height=4, progress_color=C["purple"], fg_color=C["alt"])
        self.progress.grid(row=1, column=0, padx=14, pady=(4, 10), sticky="ew")
        self.progress.set(0)

    def _add_mod_card(self, mod: dict, index: int):
        row, col = divmod(index, 2)
        card = ctk.CTkFrame(self.mods_scroll, fg_color=C["alt"], corner_radius=11,
            border_width=1, border_color=C["border"])
        card.grid(row=row, column=col, sticky="nsew", padx=7, pady=6)
        card.grid_columnconfigure(0, weight=1)
        selected = mod["slug"] in self.saved_mods
        check = ctk.CTkCheckBox(card, text=mod["name"], height=27, checkbox_width=18, checkbox_height=18,
            corner_radius=5, border_color=C["muted"], fg_color=C["purple"], hover_color=C["hover"],
            text_color=C["text"], font=ctk.CTkFont(size=12, weight="bold"))
        check.grid(row=0, column=0, sticky="w", padx=(12, 5), pady=(10, 2))
        if selected:
            check.select()
        self.checkboxes[mod["slug"]] = check
        label = ctk.CTkLabel(card, text="Not checked", font=ctk.CTkFont(size=10),
            text_color=C["muted"], anchor="e")
        label.grid(row=0, column=1, sticky="e", padx=(0, 10), pady=(10, 2))
        self.status_labels[mod["slug"]] = label
        ctk.CTkLabel(card, text=mod["description"], font=ctk.CTkFont(size=10), text_color=C["muted"],
            anchor="w", justify="left", wraplength=230).grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10))

    def _load_assets(self):
        try:
            from PIL import Image
            asset = self._resource_path("assets/voidex_avatar.png")
            if asset.is_file():
                from customtkinter import CTkImage
                picture = Image.open(asset).convert("RGBA")
                self.brand_image = CTkImage(light_image=picture, dark_image=picture, size=(48, 48))
                self.logo_fallback.destroy()
                ctk.CTkLabel(self.logo_slot, image=self.brand_image, text="").place(
                    relx=0.5, rely=0.5, anchor="center")
            icon = self._resource_path("assets/voidex.ico")
            if icon.is_file() and os.name == "nt":
                self.iconbitmap(str(icon))
        except Exception:
            pass

    @staticmethod
    def _resource_path(relative: str) -> Path:
        return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / relative

    def _fetch_versions(self):
        self.events.put(("status", "Fetching the official Minecraft version list…"))
        try:
            manifest = read_json(MINECRAFT_MANIFEST, timeout=25)
            releases = [x["id"] for x in manifest.get("versions", [])
                        if x.get("type") == "release" and supported_release(x.get("id", ""))]
            if not releases:
                raise RuntimeError("No compatible releases were returned by Mojang.")
            self.events.put(("versions", releases))
        except Exception as exc:
            self.events.put(("versions_error", str(exc)))

    def _version_changed(self, value: str):
        if not value or value.startswith("Loading") or value == "Unavailable":
            return
        self.side_version.configure(text=f"Minecraft {value}")
        self._save_settings()
        self.check_compatibility()

    def choose_folder(self):
        chosen = filedialog.askdirectory(title="Select your Minecraft game folder", initialdir=str(self._current_folder()))
        if chosen:
            self.game_dir = Path(chosen)
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, str(self.game_dir))
            self._save_settings()

    def _current_folder(self) -> Path:
        if hasattr(self, "folder_entry"):
            value = self.folder_entry.get().strip().strip('"')
            if value:
                self.game_dir = Path(value).expanduser()
        return self.game_dir

    def check_compatibility(self):
        version = self.version_menu.get().strip()
        if not version or version.startswith("Loading") or version == "Unavailable":
            return
        self.generation += 1
        generation = self.generation
        for slug, label in self.status_labels.items():
            self.compat[slug] = None
            label.configure(text="Checking…", text_color=C["muted"])
        self.mods_count.configure(text=f"Checking {len(MODS)} mods…")
        self.side_status.configure(text="Checking Modrinth compatibility")
        self.status_label.configure(text=f"Checking Fabric files for Minecraft {version}…")
        self.progress.set(0)
        threading.Thread(target=self._scan_worker, args=(version, generation), daemon=True).start()

    def _scan_worker(self, version: str, generation: int):
        with ThreadPoolExecutor(max_workers=6) as pool:
            tasks = {pool.submit(self._find_mod, mod["slug"], version): mod for mod in MODS}
            done = 0
            for future in as_completed(tasks):
                mod = tasks[future]
                try:
                    info = future.result()
                    ok = info is not None
                    self.events.put(("compat", generation, mod["slug"], ok,
                                     "Compatible" if ok else "Unavailable"))
                except Exception as exc:
                    self.events.put(("compat", generation, mod["slug"], False, "Check failed"))
                    self.events.put(("log", f"Could not check {mod['name']}: {exc}"))
                done += 1
                self.events.put(("scan_progress", generation, done / len(MODS)))
        self.events.put(("scan_done", generation, version, done))

    def _find_mod(self, slug: str, version: str) -> dict | None:
        key = (slug, version)
        if key in self.cache:
            return self.cache[key]
        versions = get_mod_versions(slug, version)
        result = next((item for item in versions
                       if get_primary_file(item) and
                       str(get_primary_file(item).get("filename", "")).lower().endswith(".jar")), None)
        self.cache[key] = result
        return result

    def _confirm_folder(self, folder: Path) -> bool:
        if not folder.exists():
            if not messagebox.askyesno("Create game folder?", f"This folder does not exist:\n\n{folder}\n\nCreate it?"):
                return False
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                messagebox.showerror("Folder error", str(exc))
                return False
        if not folder.is_dir():
            messagebox.showerror("Folder error", "The selected game path is not a folder.")
            return False
        return True

    def install_fabric(self):
        if self.busy:
            return
        if minecraft_launcher_lib is None:
            messagebox.showerror("Dependency missing", "minecraft-launcher-lib is unavailable in this build.")
            return
        version = self.version_menu.get().strip()
        if not version or version.startswith("Loading") or version == "Unavailable":
            messagebox.showwarning("Voidex", "Wait for the Minecraft version list to load.")
            return
        folder = self._current_folder()
        if not self._confirm_folder(folder):
            return
        self._set_busy(True)
        self.status_label.configure(text=f"Installing Fabric for Minecraft {version}…")
        threading.Thread(target=self._fabric_worker, args=(version, folder), daemon=True).start()

    def _fabric_worker(self, version: str, folder: Path):
        try:
            folder.mkdir(parents=True, exist_ok=True)
            minecraft_launcher_lib.fabric.install_fabric(version, str(folder))
            self.events.put(("log", f"Fabric installed for Minecraft {version}."))
            self.events.put(("operation_done", True, f"Fabric is installed for Minecraft {version}."))
        except Exception as exc:
            self.events.put(("log", f"Fabric installation failed: {exc}"))
            self.events.put(("operation_done", False, f"Could not install Fabric: {exc}"))

    def install_mods(self):
        if self.busy:
            return
        version = self.version_menu.get().strip()
        if not version or version.startswith("Loading") or version == "Unavailable":
            messagebox.showwarning("Voidex", "Select a Minecraft version first.")
            return
        chosen = [m for m in MODS if self.checkboxes[m["slug"]].get()]
        if not chosen:
            messagebox.showwarning("Voidex", "Select at least one mod.")
            return
        if any(self.compat[m["slug"]] is None for m in chosen):
            messagebox.showwarning("Compatibility is not checked", "Run Check compatibility before installing.")
            return
        incompatible = [m["name"] for m in chosen if self.compat[m["slug"]] is False]
        chosen = [m for m in chosen if self.compat[m["slug"]] is True]
        if incompatible:
            self._log("Skipped unavailable mods: " + ", ".join(incompatible))
        if not chosen:
            messagebox.showwarning("Voidex", "None of the selected mods has a compatible file for this version.")
            return
        folder = self._current_folder()
        if not self._confirm_folder(folder):
            return
        self._save_settings()
        self._set_busy(True)
        self.progress.set(0)
        self.status_label.configure(text=f"Preparing {len(chosen)} mods for Minecraft {version}…")
        threading.Thread(target=self._install_worker, args=(version, folder, chosen), daemon=True).start()

    def _install_worker(self, version: str, folder: Path, chosen: list[dict]):
        mods_folder = folder / "mods"
        mods_folder.mkdir(parents=True, exist_ok=True)
        manifest_path = folder / ".voidex-installed.json"
        try:
            managed = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(managed, dict):
                managed = {}
        except (OSError, ValueError):
            managed = {}

        installed = skipped = errors = 0
        for index, mod in enumerate(chosen, start=1):
            slug = mod["slug"]
            try:
                info = self._find_mod(slug, version)
                if not info:
                    skipped += 1
                    self.events.put(("log", f"Skipped {mod['name']}: no compatible file was found."))
                    continue
                file_info = get_primary_file(info)
                filename = Path(str(file_info.get("filename", ""))).name
                url = str(file_info.get("url", ""))
                host = (urlparse(url).hostname or "").lower()
                if not filename.lower().endswith(".jar") or not url.startswith("https://") or not (
                    host == "cdn.modrinth.com" or host.endswith(".modrinth.com")
                ):
                    raise RuntimeError("Unexpected JAR name or download host from Modrinth.")

                old_filename = managed.get(slug)
                if old_filename:
                    old_path = mods_folder / Path(str(old_filename)).name
                    if old_path.exists():
                        old_path.unlink()

                destination = mods_folder / filename
                other_managed = {Path(str(name)).name for key, name in managed.items() if key != slug}
                if destination.exists():
                    if filename in other_managed:
                        raise RuntimeError(f"File-name collision with another managed mod: {filename}")
                    skipped += 1
                    self.events.put(("log", f"Skipped {mod['name']}: {filename} already exists and is not managed by Voidex."))
                    continue

                data = read_url(url, timeout=45)
                if len(data) < 100 or len(data) > 200 * 1024 * 1024:
                    raise RuntimeError("Downloaded file size is outside the expected range.")
                temporary = destination.with_suffix(destination.suffix + ".part")
                temporary.write_bytes(data)
                temporary.replace(destination)
                managed[slug] = filename
                installed += 1
                self.events.put(("log", f"Installed {mod['name']} — {filename}"))
            except Exception as exc:
                errors += 1
                self.events.put(("log", f"Could not install {mod['name']}: {exc}"))
            self.events.put(("install_progress", index / len(chosen)))

        try:
            manifest_path.write_text(json.dumps(managed, indent=2), encoding="utf-8")
        except OSError as exc:
            self.events.put(("log", f"Could not write the Voidex install manifest: {exc}"))
        summary = f"Finished: {installed} installed, {skipped} skipped, {errors} failed."
        self.events.put(("log", summary))
        self.events.put(("operation_done", errors == 0, summary))

    def _set_busy(self, busy: bool):
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.install_button.configure(state=state)
        self.check_button.configure(state=state)
        self.folder_button.configure(state=state)
        self.version_menu.configure(state="disabled" if busy else "readonly")
        self.progress.stop()
        if not busy:
            self.progress.set(0)

    def _poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "status":
                    self.status_label.configure(text=event[1])
                elif kind == "versions":
                    versions = event[1]
                    self.version_menu.configure(values=versions)
                    selected = self.saved_version if self.saved_version in versions else versions[0]
                    self.version_menu.set(selected)
                    self.side_version.configure(text=f"Minecraft {selected}")
                    self.side_status.configure(text=f"{len(versions)} official releases available")
                    self.status_label.configure(text=f"Loaded {len(versions)} official releases, from 1.16.5 to latest.")
                    self._save_settings()
                    self.check_compatibility()
                elif kind == "versions_error":
                    self.version_menu.configure(values=["Unavailable"])
                    self.version_menu.set("Unavailable")
                    self.side_status.configure(text="Could not reach Mojang")
                    self.status_label.configure(text=f"Could not load Minecraft versions: {event[1]}")
                    self._log(event[1])
                elif kind == "compat":
                    _, generation, slug, ok, label = event
                    if generation == self.generation:
                        self.compat[slug] = ok
                        self.status_labels[slug].configure(
                            text=label, text_color=C["green"] if ok else C["red"])
                elif kind == "scan_progress":
                    if event[1] == self.generation:
                        self.progress.set(event[2])
                elif kind == "scan_done":
                    _, generation, version, total = event
                    if generation == self.generation:
                        count = sum(1 for value in self.compat.values() if value is True)
                        self.mods_count.configure(text=f"{count} of {total} compatible")
                        self.side_status.configure(text=f"{count} compatible mods for {version}")
                        self.status_label.configure(text=f"Compatibility check complete for Minecraft {version}.")
                        self.progress.set(0)
                elif kind == "install_progress":
                    self.progress.set(event[1])
                elif kind == "log":
                    self._log(event[1])
                elif kind == "operation_done":
                    _, success, message = event
                    self._set_busy(False)
                    self.status_label.configure(text=message)
                    self.side_status.configure(text="Ready")
                    if success:
                        self.progress.set(1)
                else:
                    pass
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _log(self, message: str):
        try:
            with self.log_path.open("a", encoding="utf-8") as stream:
                stream.write(f"[{time.strftime('%H:%M:%S')}] {message}\n")
        except OSError:
            pass

    def open_mods_folder(self):
        path = self._current_folder() / "mods"
        path.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(str(path))
            else:
                import subprocess
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror("Could not open folder", str(exc))


if __name__ == "__main__":
    try:
        from voidex_icon import create_assets
        create_assets()
    except Exception:
        pass
    VoidexApp().mainloop()
