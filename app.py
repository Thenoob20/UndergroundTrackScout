from __future__ import annotations
import threading, tkinter as tk, webbrowser, traceback, io
from tkinter import ttk, messagebox
from datetime import datetime
from collections import Counter, defaultdict

from config import APP_NAME, APP_VERSION, DEFAULT_GENRES, DISCOVERY_MODES, FILTER_STRICTNESS
from db import (
    add_favorite, ignore_artist, ignored_artists, add_feedback, mark_seen,
    seen_counts, label_stats, rising_artist_stats, taste_profile,
    add_track_feedback, export_feedback_csv, feedback_summary,
    get_feedback_settings, save_feedback_settings
)
from exporter import export_csv
from scorer import score_candidates, is_non_track
from sources.manual_seed import demo_candidates
from sources.reddit import search_reddit
from sources.soundcloud import search_soundcloud, search_soundcloud_deep, expanded_soundcloud_queries
from sources.bandcamp import search_bandcamp
from sources.spotify_check import apply_spotify_checks, spotify_configured
try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None
import requests

class UndergroundScoutApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1540x860")
        self.minsize(1200, 680)
        self.configure(bg="#111111")
        self.results = []
        self.errors = []
        self.hover_preview = None
        self._style(); self._ui()

    def _style(self):
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except tk.TclError: pass
        style.configure("TFrame", background="#111111")
        style.configure("TLabel", background="#111111", foreground="#f1f1f1", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#111111", foreground="#ffffff", font=("Segoe UI", 18, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        style.configure("TCheckbutton", background="#111111", foreground="#f1f1f1")
        style.configure("Treeview", background="#181818", foreground="#f1f1f1", fieldbackground="#181818", rowheight=28)
        style.map("Treeview", background=[("selected", "#3a3a3a")])
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _ui(self):
        top = ttk.Frame(self, padding=14); top.pack(fill="x")
        ttk.Label(top, text="Underground Track Scout", style="Header.TLabel").grid(row=0, column=0, sticky="w", columnspan=12)
        ttk.Label(top, text="Find early underground music signals before the mainstream algorithm catches them.").grid(row=1, column=0, sticky="w", columnspan=12, pady=(2, 12))

        ttk.Label(top, text="Genre / keyword").grid(row=2, column=0, sticky="w")
        self.query_var = tk.StringVar(value=DEFAULT_GENRES[0])
        ttk.Combobox(top, textvariable=self.query_var, values=DEFAULT_GENRES, width=24).grid(row=3, column=0, sticky="we", padx=(0, 10))

        ttk.Label(top, text="Source").grid(row=2, column=1, sticky="w")
        self.source_var = tk.StringVar(value="SoundCloud Deep")
        ttk.Combobox(top, textvariable=self.source_var, values=["SoundCloud", "SoundCloud Deep", "SoundCloud Deep + Spotify"], width=24, state="readonly").grid(row=3, column=1, sticky="we", padx=(0, 10))

        ttk.Label(top, text="Discovery Mode").grid(row=2, column=2, sticky="w")
        self.discovery_mode_var = tk.StringVar(value="Deep Dig")
        ttk.Combobox(top, textvariable=self.discovery_mode_var, values=list(DISCOVERY_MODES.keys()), width=24, state="readonly").grid(row=3, column=2, sticky="w", padx=(0, 10))

        ttk.Label(top, text="Filter Strictness").grid(row=2, column=3, sticky="w")
        self.strictness_var = tk.StringVar(value="Balanced")
        ttk.Combobox(top, textvariable=self.strictness_var, values=FILTER_STRICTNESS, width=16, state="readonly").grid(row=3, column=3, sticky="w", padx=(0, 10))

        ttk.Label(top, text="Show Top").grid(row=2, column=4, sticky="w")
        self.limit_var = tk.IntVar(value=30)
        ttk.Spinbox(top, from_=10, to=200, textvariable=self.limit_var, width=10).grid(row=3, column=4, sticky="w", padx=(0, 10))

        self.scan_button = ttk.Button(top, text="Scan", command=self.scan); self.scan_button.grid(row=3, column=5, padx=5)
        self.demo_button = ttk.Button(top, text="Demo Test", command=self.load_demo); self.demo_button.grid(row=3, column=6, padx=5)
        self.export_button = ttk.Button(top, text="Export CSV", command=self.export_results); self.export_button.grid(row=3, column=7, padx=5)
        self.open_top_button = ttk.Button(top, text="Open Top 5", command=self.open_top); self.open_top_button.grid(row=3, column=8, padx=5)

        self.hide_sets_var = tk.BooleanVar(value=True)
        self.hide_seen_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Hide DJ sets / mixes", variable=self.hide_sets_var).grid(row=4, column=0, sticky="w", pady=(10, 0))
        ttk.Checkbutton(top, text="Hide seen-before tracks", variable=self.hide_seen_var).grid(row=4, column=1, sticky="w", pady=(10, 0))
        self.deep_pool_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Deep pool scan", variable=self.deep_pool_var).grid(row=4, column=2, sticky="w", pady=(10, 0))

        self.status_var = tk.StringVar(value="Ready. Feedback form is built in. Click 📝 Beta Feedback to open it.")
        ttk.Label(top, textvariable=self.status_var).grid(row=5, column=0, sticky="w", columnspan=12, pady=(8, 0))
        self.spotify_status_var = tk.StringVar(value=("Spotify: enabled" if spotify_configured() else "Spotify: not configured"))
        ttk.Label(top, textvariable=self.spotify_status_var).grid(row=6, column=0, sticky="w", columnspan=12, pady=(4, 0))
        top.columnconfigure(2, weight=1)

        body = ttk.Frame(self, padding=(14, 0, 14, 10)); body.pack(fill="both", expand=True)
        self.notebook = ttk.Notebook(body); self.notebook.pack(fill="both", expand=True)
        results_frame = ttk.Frame(self.notebook); log_frame = ttk.Frame(self.notebook); labels_frame = ttk.Frame(self.notebook); artists_frame = ttk.Frame(self.notebook); taste_frame = ttk.Frame(self.notebook); feedback_frame = ttk.Frame(self.notebook); settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="Results")
        self.notebook.add(log_frame, text="Source Errors / Log")
        self.notebook.add(labels_frame, text="Label Watch")
        self.notebook.add(artists_frame, text="Rising Artists")
        self.notebook.add(taste_frame, text="Taste Profile")
        self.notebook.add(feedback_frame, text="Feedback Summary")
        self.notebook.add(settings_frame, text="Feedback")

        columns = ("score", "confidence", "taste", "type", "seen", "spotify", "gem", "label", "artist", "title", "genre", "platform", "plays", "likes", "reposts", "date", "reason", "url", "artist_url")
        self.tree = ttk.Treeview(results_frame, columns=columns, show="headings")
        headings = {"score":"Score", "confidence":"Confidence", "taste":"Taste", "type":"Track Type", "seen":"Seen", "spotify":"Spotify", "gem":"Gem", "label":"Label", "artist":"Artist", "title":"Track", "genre":"Genre", "platform":"Platform", "plays":"Plays", "likes":"Likes", "reposts":"Reposts", "date":"Upload Date", "reason":"Why Picked", "url":"Link", "artist_url":"Artist Page"}
        widths = {"score":75, "confidence":90, "taste":70, "type":105, "seen":55, "spotify":130, "gem":60, "label":135, "artist":170, "title":275, "genre":115, "platform":110, "plays":75, "likes":65, "reposts":80, "date":105, "reason":430, "url":260, "artist_url":220}
        for c in columns:
            self.tree.heading(c, text=headings[c]); self.tree.column(c, width=widths[c], minwidth=50, anchor="w")
        self.tree.tag_configure("hot", background="#12351f", foreground="#ffffff")
        self.tree.tag_configure("mid", background="#3a3212", foreground="#ffffff")
        self.tree.tag_configure("low", background="#3a1717", foreground="#ffffff")
        self.tree.tag_configure("gem", background="#163042", foreground="#ffffff")
        self.tree.tag_configure("rising", background="#2f1f45", foreground="#ffffff")
        yscroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(results_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew"); yscroll.grid(row=0, column=1, sticky="ns"); xscroll.grid(row=1, column=0, sticky="ew")
        results_frame.rowconfigure(0, weight=1); results_frame.columnconfigure(0, weight=1)

        self.log_box = tk.Text(log_frame, bg="#151515", fg="#f1f1f1", insertbackground="#ffffff", wrap="word", height=10)
        self.log_box.pack(fill="both", expand=True)

        self.label_tree = self._simple_tree(labels_frame, ("label", "count", "avg", "gems"), {"label":"Label", "count":"Saved", "avg":"Avg Score", "gems":"Gems"})
        self.artist_tree = self._simple_tree(artists_frame, ("artist", "count", "avg", "gems"), {"artist":"Artist", "count":"Saved", "avg":"Avg Score", "gems":"Gems"})
        self.taste_box = tk.Text(taste_frame, bg="#151515", fg="#f1f1f1", insertbackground="#ffffff", wrap="word")
        self.taste_box.pack(fill="both", expand=True)
        self.feedback_box = tk.Text(feedback_frame, bg="#151515", fg="#f1f1f1", insertbackground="#ffffff", wrap="word")
        self.feedback_box.pack(fill="both", expand=True)
        self._feedback_settings_ui(settings_frame)

        bottom = ttk.Frame(self, padding=(14, 0, 14, 14)); bottom.pack(fill="x")
        ttk.Button(bottom, text="Open Selected Track", command=self.open_selected).pack(side="left")
        ttk.Button(bottom, text="Open Artist Page", command=self.open_artist).pack(side="left", padx=8)
        ttk.Button(bottom, text="👍 Like", command=lambda: self.feedback_selected("like")).pack(side="left", padx=8)
        ttk.Button(bottom, text="👎 Dislike", command=lambda: self.feedback_selected("dislike")).pack(side="left", padx=8)
        ttk.Button(bottom, text="⭐ Favorite", command=self.favorite_selected).pack(side="left", padx=8)
        ttk.Button(bottom, text="📝 Beta Feedback", command=self.submit_feedback_selected).pack(side="left", padx=8)
        ttk.Button(bottom, text="Export Feedback", command=self.export_feedback).pack(side="left", padx=8)
        ttk.Button(bottom, text="Ignore Artist", command=self.ignore_selected_artist).pack(side="left", padx=8)
        ttk.Button(bottom, text="Refresh Dashboards", command=self.refresh_dashboards).pack(side="left", padx=8)
        ttk.Button(bottom, text="Clear", command=self.clear_results).pack(side="left", padx=8)
        self.tree.bind("<Motion>", self._on_tree_hover)
        self.tree.bind("<Leave>", self._hide_hover_preview)
        self.refresh_dashboards()

    def _feedback_settings_ui(self, parent):
        wrap = ttk.Frame(parent, padding=24)
        wrap.pack(fill="both", expand=True)

        ttk.Label(wrap, text="Feedback", style="Header.TLabel").pack(anchor="w", pady=(0, 12))

        msg = (
            "Help improve Underground Track Scout.\n\n"
            "Click the button below to open the beta feedback form. Use it to share bugs, bad results, "
            "feature requests, and tracks the app helped you discover."
        )
        ttk.Label(wrap, text=msg, wraplength=760, justify="left").pack(anchor="w", pady=(0, 18))

        ttk.Button(wrap, text="📝 Open Beta Feedback Form", command=self.open_beta_feedback_form).pack(anchor="w", pady=(0, 14))

        ttk.Label(
            wrap,
            text="Feedback form linked ✓",
            foreground="#4ade80"
        ).pack(anchor="w", pady=(0, 18))

        bullets = (
            "Your feedback helps improve:\n"
            "✓ Discovery quality\n"
            "✓ Hidden gem detection\n"
            "✓ Artist and label tracking\n"
            "✓ Future DJ features like BPM, key detection, and crate export"
        )
        ttk.Label(wrap, text=bullets, wraplength=760, justify="left").pack(anchor="w")

    def open_beta_feedback_form(self):
        settings = get_feedback_settings()
        form_url = settings.get("google_form_url", "").strip()
        if not form_url:
            from config import DEFAULT_GOOGLE_FORM_URL
            form_url = DEFAULT_GOOGLE_FORM_URL
        if form_url:
            webbrowser.open(form_url)
            self.status_var.set("Opened beta feedback form.")
        else:
            messagebox.showinfo("Feedback", "Beta feedback form is coming soon.")

    def save_feedback_settings_ui(self):
        # Kept for backward compatibility with older settings files.
        self.status_var.set("Feedback form is already linked.")

    def open_feedback_form_from_settings(self):
        self.open_beta_feedback_form()

    def _simple_tree(self, parent, columns, headings):
        tree = ttk.Treeview(parent, columns=columns, show="headings")
        for c in columns:
            tree.heading(c, text=headings[c]); tree.column(c, width=180, anchor="w")
        tree.pack(fill="both", expand=True, padx=4, pady=4)
        return tree
    def _on_tree_hover(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            self._hide_hover_preview()
            return
        try:
            item = self.results[int(row_id)]
        except Exception:
            self._hide_hover_preview()
            return
        self._show_hover_preview(item, event.x_root + 18, event.y_root + 18)

    def _show_hover_preview(self, item, x, y):
        if self.hover_preview is not None:
            try:
                if getattr(self.hover_preview, "_url", None) == item.url:
                    self.hover_preview.geometry(f"+{x}+{y}")
                    return
                self.hover_preview.destroy()
            except Exception:
                pass
        win = tk.Toplevel(self)
        win.wm_overrideredirect(True)
        win.configure(bg="#101010", padx=10, pady=10)
        win._url = item.url
        win._img_ref = None
        frame = tk.Frame(win, bg="#101010"); frame.pack(fill="both", expand=True)
        art_url = getattr(item, "artwork_url", "") or ""
        if art_url and Image is not None and ImageTk is not None:
            try:
                big_art = art_url.replace("large.jpg", "t300x300.jpg").replace("-large", "-t300x300")
                resp = requests.get(big_art, timeout=5)
                resp.raise_for_status()
                img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                img.thumbnail((140, 140))
                photo = ImageTk.PhotoImage(img)
                lbl = tk.Label(frame, image=photo, bg="#101010")
                lbl.image = photo
                win._img_ref = photo
                lbl.grid(row=0, column=0, rowspan=7, sticky="nw", padx=(0,10))
            except Exception:
                pass
        text = f"{item.artist}\n{item.title}\n\nScore: {item.discovery_score} | Confidence: {item.source_confidence}\nType: {item.track_type} | Genre: {item.genre}\nPlays: {item.plays or '—'}  Likes: {item.likes or '—'}  Reposts: {item.reposts or '—'}\nDate: {(item.upload_date or '')[:10] or '—'}\nLabel: {item.label or item.label_signal or '—'}\n\n{item.reason[:220]}"
        tk.Label(frame, text=text, justify="left", bg="#101010", fg="#f1f1f1", font=("Segoe UI", 9), wraplength=440).grid(row=0, column=1, sticky="w")
        win.geometry(f"+{x}+{y}")
        self.hover_preview = win

    def _hide_hover_preview(self, event=None):
        if self.hover_preview is not None:
            try:
                self.hover_preview.destroy()
            except Exception:
                pass
            self.hover_preview = None


    def set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        for b in [self.scan_button, self.demo_button, self.export_button, self.open_top_button]: b.configure(state=state)

    def scan(self):
        query = self.query_var.get().strip(); source = self.source_var.get(); limit = int(self.limit_var.get() or 15)
        if not query: return messagebox.showwarning("Missing search", "Enter a genre or keyword first.")
        mode = self.discovery_mode_var.get()
        strictness = self.strictness_var.get()
        self.set_busy(True); self.status_var.set(f"Scanning {source} / {mode} for '{query}'...")
        threading.Thread(target=self._scan_worker, args=(query, source, limit, mode, strictness), daemon=True).start()

    def _scan_worker(self, query, source, limit, mode, strictness):
        tracks, errors = [], []
        try:
            if source in ("SoundCloud Deep + Spotify", "SoundCloud Deep"):
                # Collect a larger candidate pool, then score/filter and display the top N.
                res = search_soundcloud_deep(query, limit, mode=mode); tracks.extend(res.tracks); errors.extend(res.errors)
                errors.append("SoundCloud query variations used: " + ", ".join(expanded_soundcloud_queries(query, mode=mode)[:18]))
            else:
                # Regular SoundCloud is a lighter scan.
                res = search_soundcloud(query, limit * (3 if self.deep_pool_var.get() else 1)); tracks.extend(res.tracks); errors.extend(res.errors)

            ignored = ignored_artists()
            tracks = [t for t in tracks if t.artist.lower() not in ignored]
            before_sets = len(tracks)
            if self.hide_sets_var.get():
                if strictness == "Loose":
                    # Loose mode keeps more borderline edits/remixes, only removes obvious long-form content.
                    obvious = ("podcast", "radio", "episode", "full set", "1 hour", "hour mix", "boiler room", "live set")
                    tracks = [t for t in tracks if not any(w in ((t.title or "") + " " + (t.artist or "")).lower() for w in obvious)]
                else:
                    tracks = [t for t in tracks if not is_non_track(t)]
                removed = before_sets - len(tracks)
                if removed:
                    errors.append(f"Hidden DJ sets/mixes/podcasts ({strictness}): {removed}")

            counts = seen_counts([t.url for t in tracks if t.url])
            for t in tracks:
                t.seen_count = counts.get(t.url, 0)
            if self.hide_seen_var.get():
                before_seen = len(tracks)
                tracks = [t for t in tracks if t.seen_count == 0]
                removed_seen = before_seen - len(tracks)
                if removed_seen:
                    errors.append(f"Hidden seen-before tracks: {removed_seen}")

            prelim = score_candidates(tracks, [query])
            if source in ("SoundCloud Deep + Spotify", "All Sources"):
                prelim, spotify_errors = apply_spotify_checks(prelim, max_checks=min(20, limit))
                errors.extend(spotify_errors)
            scored = score_candidates(prelim, [query])
            scored = sorted(scored, key=lambda t: (t.discovery_score, t.source_confidence, t.likes or 0, t.reposts or 0), reverse=True)
            total_scored = len(scored)
            scored = scored[:limit]
            if total_scored > len(scored):
                errors.append(f"Collected/scored {total_scored} candidates; showing top {len(scored)}.")
            self._flag_rising(scored)
            mark_seen(scored)
            gems = sum(1 for t in scored if t.hidden_gem)
            rising = sum(1 for t in scored if t.rising_artist)
            msg = f"Found {len(scored)} tracks for '{query}' using {mode} mode. {gems} hidden gem(s). {rising} rising artist flag(s). {len(errors)} source warning(s)."
            self.after(0, lambda: self.display_results(scored, errors, msg))
        except Exception:
            tb = traceback.format_exc()
            self.after(0, lambda: self.display_results([], ["Scan crashed:\n" + tb], "Scan failed. See Source Errors / Log."))
        finally:
            self.after(0, lambda: self.set_busy(False))

    def _flag_rising(self, tracks):
        by_artist = defaultdict(list)
        for t in tracks:
            by_artist[t.artist].append(t)
        for artist, rows in by_artist.items():
            avg = sum(t.discovery_score for t in rows) / max(1, len(rows))
            if len(rows) >= 2 and avg >= 70:
                for t in rows:
                    t.rising_artist = True
                    t.reason += " | 🔥 rising artist candidate"

    def load_demo(self):
        q = self.query_var.get().strip() or "tech house"
        scored = score_candidates(demo_candidates(q), [q])
        self._flag_rising(scored)
        self.display_results(scored, [], "Loaded demo results. v0.8 feedback and hover previews are ready.")

    def display_results(self, results, errors, status):
        self.results = results; self.errors = errors
        self.tree.delete(*self.tree.get_children())
        for idx, item in enumerate(results):
            date_text = item.upload_date[:10] if item.upload_date else ""
            gem = "🔥" if item.hidden_gem else ""
            score_text = f"🔥 {item.discovery_score}" if item.discovery_score >= 80 else (f"🟡 {item.discovery_score}" if item.discovery_score >= 55 else f"🔴 {item.discovery_score}")
            tag = "rising" if item.rising_artist else ("gem" if item.hidden_gem else ("hot" if item.discovery_score >= 80 else "mid" if item.discovery_score >= 55 else "low"))
            spotify_text = ""
            if getattr(item, "spotify_found", False):
                pop = getattr(item, "spotify_artist_popularity", None); followers = getattr(item, "spotify_artist_followers", None)
                spotify_text = f"pop {pop if pop is not None else '?'}"
                if followers is not None: spotify_text += f" / {followers:,}"
            elif getattr(item, "spotify_note", ""):
                spotify_text = "not found" if "not found" in item.spotify_note.lower() else "skipped"
            self.tree.insert("", "end", iid=str(idx), values=(score_text, item.source_confidence, item.taste_score, item.track_type, item.seen_count, spotify_text, gem, item.label or item.label_signal, item.artist, item.title, item.genre, item.platform, item.plays or "", item.likes or "", item.reposts or "", date_text, item.reason, item.url, item.artist_url), tags=(tag,))
        self.log_box.delete("1.0", "end")
        if errors:
            self.log_box.insert("end", "Source errors / warnings:\n\n" + "\n".join(f"- {e}" for e in errors))
        else:
            self.log_box.insert("end", "No source errors.\n")
        self.status_var.set(status)
        self.refresh_dashboards()

    def refresh_dashboards(self):
        self.label_tree.delete(*self.label_tree.get_children())
        for row in label_stats():
            self.label_tree.insert("", "end", values=row)
        self.artist_tree.delete(*self.artist_tree.get_children())
        current = Counter(t.artist for t in self.results if getattr(t, "rising_artist", False))
        for artist, count, avg, gems in rising_artist_stats():
            flag = "🔥 current scan" if artist in current else ""
            self.artist_tree.insert("", "end", values=(artist + (" " + flag if flag else ""), count, avg, gems))
        self.taste_box.delete("1.0", "end")
        p = taste_profile()
        self.taste_box.insert("end", f"Taste training summary\n\nFavorites: {p['favorites']}\nLikes: {p['likes']}\nDislikes: {p['dislikes']}\n\nTop genres:\n")
        for k, v in sorted(p["genres"].items(), key=lambda x: x[1], reverse=True)[:15]:
            self.taste_box.insert("end", f"- {k}: {v}\n")
        self.taste_box.insert("end", "\nTrack type preference:\n")
        for k, v in sorted(p["types"].items(), key=lambda x: x[1], reverse=True)[:15]:
            self.taste_box.insert("end", f"- {k}: {v}\n")
        self.feedback_box.delete("1.0", "end")
        fs = feedback_summary()
        self.feedback_box.insert("end", f"Feedback summary\n\nTotal feedback rows: {fs['total']}\n\nRatings:\n")
        for rating, count in fs["ratings"]:
            self.feedback_box.insert("end", f"- {rating}: {count}\n")
        self.feedback_box.insert("end", "\nTesters:\n")
        for tester, count in fs["testers"]:
            self.feedback_box.insert("end", f"- {tester}: {count}\n")

    def export_results(self):
        if not self.results: return messagebox.showinfo("No tracks", "No track results to export.")
        path = export_csv(self.results, f"underground_tracks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        messagebox.showinfo("Export complete", f"Saved CSV to:\n{path.resolve()}")
        self.status_var.set(f"Exported {len(self.results)} tracks to {path}")

    def _selected_item(self):
        selected = self.tree.selection()
        if not selected: return None
        try: return self.results[int(selected[0])]
        except Exception: return None

    def open_selected(self):
        item = self._selected_item()
        if not item: return messagebox.showinfo("No selection", "Select a row first.")
        webbrowser.open(item.url)

    def open_artist(self):
        item = self._selected_item()
        if not item: return messagebox.showinfo("No selection", "Select a row first.")
        webbrowser.open(item.artist_url or item.url)

    def feedback_selected(self, feedback):
        item = self._selected_item()
        if not item: return messagebox.showinfo("No selection", "Select a row first.")
        add_feedback(item, feedback)
        self.status_var.set(f"Saved {feedback}: {item.artist} - {item.title}")
        self.refresh_dashboards()

    def submit_feedback_selected(self):
        # Simple beta flow: always open the Google Form. If a track is selected,
        # show quick copy/paste info after opening the form.
        item = self._selected_item()
        settings = get_feedback_settings()
        form_url = settings.get("google_form_url", "").strip()
        if not form_url:
            from config import DEFAULT_GOOGLE_FORM_URL
            form_url = DEFAULT_GOOGLE_FORM_URL

        if form_url:
            webbrowser.open(form_url)
            self.status_var.set("Opened beta feedback form.")
            if item:
                messagebox.showinfo(
                    "Feedback Form Opened",
                    "The Google feedback form opened in your browser.\n\n"
                    "Track info to copy/paste if needed:\n\n"
                    f"Artist: {item.artist}\n"
                    f"Track: {item.title}\n"
                    f"Genre: {item.genre}\n"
                    f"Score: {item.discovery_score}\n"
                    f"Link: {item.url}"
                )
            return

        messagebox.showinfo("Feedback", "Beta feedback form is coming soon.")
        self.status_var.set("Beta feedback form is coming soon.")

    def export_feedback(self):
        path = export_feedback_csv()
        messagebox.showinfo("Feedback exported", f"Saved feedback CSV to:\n{path.resolve()}")
        self.status_var.set(f"Exported feedback to {path}")

    def favorite_selected(self):
        item = self._selected_item()
        if not item: return messagebox.showinfo("No selection", "Select a row first.")
        added = add_favorite(item)
        self.status_var.set(("Saved favorite: " if added else "Already in favorites: ") + f"{item.artist} - {item.title}")
        self.refresh_dashboards()

    def ignore_selected_artist(self):
        item = self._selected_item()
        if not item: return messagebox.showinfo("No selection", "Select a row first.")
        ignore_artist(item.artist)
        self.results = [t for t in self.results if t.artist != item.artist]
        self.display_results(self.results, self.errors, f"Ignored artist: {item.artist}")

    def open_top(self):
        if not self.results: return messagebox.showinfo("No results", "Run a scan first.")
        for item in self.results[:5]:
            if item.url: webbrowser.open(item.url)

    def clear_results(self):
        self.results = []; self.errors = []
        self.tree.delete(*self.tree.get_children()); self.log_box.delete("1.0", "end")
        self.status_var.set("Cleared results.")

if __name__ == "__main__":
    app = UndergroundScoutApp(); app.mainloop()
