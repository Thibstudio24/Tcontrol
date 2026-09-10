#!/usr/bin/env python3
"""Tcontrol — application Windows de contrôle parental du temps de jeu.

Interface principale (dashboard utilisateur + panneau admin protégé).
"""
from __future__ import annotations

import queue
import threading
import tkinter.messagebox as messagebox

import customtkinter as ctk

from core.config import Config, APP_NAME, APP_VERSION
from core.state import State
from core.sync import SyncClient, SyncError
from core.monitor import Monitor, get_identity
from core.logic import fmt_duration, normalize_process_name, is_valid_process_name
from core.processes import list_running
from core.crypto import verify_admin, remember_admin
from core.autostart import is_supported as autostart_supported, \
    is_autostart_enabled, set_autostart
from core.tray_helper import TrayIcon

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

ACCENT = "#0e7490"
ACCENT_HOVER = "#155e75"
GOOD = "#22c55e"
WARN = "#f59e0b"
BAD = "#ef4444"
CARD = "#1b1f27"

FONT_TITLE = ("Segoe UI", 22, "bold")
FONT_BIG = ("Segoe UI", 44, "bold")
FONT_H2 = ("Segoe UI", 15, "bold")
FONT_BODY = ("Segoe UI", 13)
FONT_SMALL = ("Segoe UI", 11)


# =====================================================================
# Dialogues
# =====================================================================

class UnlockDialog(ctk.CTkToplevel):
    """Saisie des identifiants admin (les mêmes que sur le site)."""

    def __init__(self, master, on_success):
        super().__init__(master)
        self.on_success = on_success
        self.title(f"{APP_NAME} — Accès admin")
        self.geometry("360x230")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        ctk.CTkLabel(self, text="🔑 Espace administrateur", font=FONT_H2).pack(pady=(18, 4))
        ctk.CTkLabel(self, text="Identifiants du site Tcontrol",
                     font=FONT_SMALL, text_color="gray").pack()
        self.e_user = ctk.CTkEntry(self, placeholder_text="Identifiant", width=240)
        self.e_user.pack(pady=(14, 6))
        self.e_pass = ctk.CTkEntry(self, placeholder_text="Mot de passe", show="•", width=240)
        self.e_pass.pack(pady=6)
        self.e_pass.bind("<Return>", lambda _e: self._submit())
        self.lbl_err = ctk.CTkLabel(self, text="", font=FONT_SMALL, text_color=BAD)
        self.lbl_err.pack()
        ctk.CTkButton(self, text="Déverrouiller", fg_color=ACCENT,
                      hover_color=ACCENT_HOVER, command=self._submit).pack(pady=10)
        self.e_user.focus_set()

    def _submit(self):
        u, p = self.e_user.get().strip(), self.e_pass.get()
        if not u or not p:
            self.lbl_err.configure(text="Remplis les deux champs.")
            return
        self.lbl_err.configure(text="Vérification…", text_color="gray")
        self.update_idletasks()
        ok, msg = self.on_success(u, p)   # App.check_credentials (peut être réseau)
        if ok:
            self.destroy()
        else:
            self.lbl_err.configure(text=msg or "Identifiants incorrects.", text_color=BAD)


class SetupBanner(ctk.CTkFrame):
    """Bandeau affiché tant que l'app n'est pas reliée au site."""

    def __init__(self, master, on_configure):
        super().__init__(master, fg_color="#7a5b13", corner_radius=8)
        ctk.CTkLabel(self, text="⚠ Tcontrol n'est pas encore relié au site. "
                                "Le mode local est actif.",
                     font=FONT_BODY).pack(side="left", padx=12, pady=8)
        ctk.CTkButton(self, text="Configurer (admin)", width=150,
                      command=on_configure).pack(side="right", padx=12, pady=8)


# =====================================================================
# Panneau d'administration
# =====================================================================

class AdminPanel(ctk.CTkToplevel):
    def __init__(self, app: "TcontrolApp"):
        super().__init__(app)
        self.app = app
        # Mode "première installation" : pas encore d'admin possible
        # (serveur non configuré) → onglet Configuration uniquement.
        self.setup_only = not app.is_admin
        self.title(f"{APP_NAME} — Administration")
        self.geometry("820x600")
        self.minsize(760, 540)
        self.transient(app)

        if self.setup_only:
            ctk.CTkLabel(
                self,
                text="🛠 Première configuration : renseigne l'URL de l'API et la clé "
                     "(visibles sur ton site, page Paramètres) puis synchronise.",
                font=FONT_SMALL, text_color=WARN, wraplength=740,
                justify="left").pack(padx=14, pady=(12, 0), anchor="w")

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=10)
        tabs.add("Configuration")
        self._build_config_tab(tabs.tab("Configuration"))
        if not self.setup_only:
            tabs.add("Jeux bloqués")
            tabs.add("Aujourd'hui")
            self._build_games_tab(tabs.tab("Jeux bloqués"))
            self._build_today_tab(tabs.tab("Aujourd'hui"))
            tabs.set("Jeux bloqués")
            self._refresh_blocked_list()
            self._refresh_running()

    # ---------------------------------------------------------- onglet jeux
    def _build_games_tab(self, tab):
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(1, weight=1)

        ctk.CTkLabel(tab, text="🖥 Processus actifs sur ce PC", font=FONT_H2)\
            .grid(row=0, column=0, padx=8, pady=(6, 2), sticky="w")
        ctk.CTkLabel(tab, text="🚫 Jeux bloqués (liste commune)", font=FONT_H2)\
            .grid(row=0, column=1, padx=8, pady=(6, 2), sticky="w")

        self.frame_running = ctk.CTkScrollableFrame(tab, fg_color=CARD)
        self.frame_running.grid(row=1, column=0, padx=8, pady=6, sticky="nsew")
        self.frame_blocked = ctk.CTkScrollableFrame(tab, fg_color=CARD)
        self.frame_blocked.grid(row=1, column=1, padx=8, pady=6, sticky="nsew")

        btns = ctk.CTkFrame(tab, fg_color="transparent")
        btns.grid(row=2, column=0, columnspan=2, pady=6)
        ctk.CTkButton(btns, text="🔄 Actualiser les processus",
                      command=self._refresh_running).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="➕ Ajouter manuellement…",
                      command=self._add_manual).pack(side="left", padx=6)

        self.lbl_games_status = ctk.CTkLabel(tab, text="", font=FONT_SMALL,
                                             text_color="gray")
        self.lbl_games_status.grid(row=3, column=0, columnspan=2, pady=(0, 6))

    def _refresh_running(self):
        for w in self.frame_running.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.frame_running, text="Chargement…",
                     font=FONT_SMALL).pack(pady=8)

        def work():
            procs = list_running()
            self.after(0, lambda: self._fill_running(procs))
        threading.Thread(target=work, daemon=True).start()

    def _fill_running(self, procs):
        for w in self.frame_running.winfo_children():
            w.destroy()
        blocked = set(self.app.state.processes)
        for p in procs:
            row = ctk.CTkFrame(self.frame_running, fg_color="transparent")
            row.pack(fill="x", pady=1, padx=4)
            already = p["name"] in blocked
            ctk.CTkLabel(row, text=f"{p['name']}  ×{p['count']}",
                         font=FONT_BODY).pack(side="left", padx=6)
            if already:
                ctk.CTkLabel(row, text="bloqué", font=FONT_SMALL,
                             text_color=BAD).pack(side="right", padx=6)
            else:
                ctk.CTkButton(row, text="Bloquer", width=70, height=24,
                              fg_color=ACCENT, hover_color=ACCENT_HOVER,
                              command=lambda n=p["name"]: self._add_blocked(n))\
                    .pack(side="right", padx=6)

    def _refresh_blocked_list(self):
        for w in self.frame_blocked.winfo_children():
            w.destroy()
        procs = self.app.state.processes
        if not procs:
            ctk.CTkLabel(self.frame_blocked, text="Aucun jeu bloqué pour l'instant.",
                         font=FONT_SMALL, text_color="gray").pack(pady=8)
            return
        for name in sorted(procs):
            row = ctk.CTkFrame(self.frame_blocked, fg_color="transparent")
            row.pack(fill="x", pady=1, padx=4)
            ctk.CTkLabel(row, text=name, font=FONT_BODY).pack(side="left", padx=6)
            ctk.CTkButton(row, text="✖ Autoriser", width=90, height=24,
                          fg_color="#7f1d1d", hover_color="#991b1b",
                          command=lambda n=name: self._remove_blocked(n))\
                .pack(side="right", padx=6)

    def _add_manual(self):
        dlg = ctk.CTkInputDialog(text="Nom du processus (ex : fortnite.exe) :",
                                 title="Ajouter un jeu")
        name = dlg.get_input()
        if name:
            name = normalize_process_name(name)
            if is_valid_process_name(name):
                self._add_blocked(name)
            else:
                messagebox.showerror(APP_NAME, "Nom de processus invalide.", parent=self)

    def _add_blocked(self, name):
        self.lbl_games_status.configure(text=f"Ajout de {name}…")
        def work():
            err = self.app.admin_api("add", name)
            self.after(0, lambda: self._after_mutation(err, f"{name} bloqué."))
        threading.Thread(target=work, daemon=True).start()

    def _remove_blocked(self, name):
        self.lbl_games_status.configure(text=f"Suppression de {name}…")
        def work():
            err = self.app.admin_api("remove", name)
            self.after(0, lambda: self._after_mutation(err, f"{name} autorisé."))
        threading.Thread(target=work, daemon=True).start()

    def _after_mutation(self, err, ok_msg):
        if err:
            self.lbl_games_status.configure(text=f"⚠ {err}", text_color=WARN)
        else:
            self.lbl_games_status.configure(text=ok_msg, text_color=GOOD)
        self._refresh_blocked_list()
        self._refresh_running()

    # ---------------------------------------------------------- onglet aujourd'hui
    def _build_today_tab(self, tab):
        tab.rowconfigure(1, weight=1)
        tab.columnconfigure(0, weight=1)
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=4)
        ctk.CTkLabel(top, text="Activité du jour (données du site)",
                     font=FONT_H2).pack(side="left", padx=8)
        ctk.CTkButton(top, text="🔄 Rafraîchir", width=110,
                      command=self._refresh_today).pack(side="right", padx=8)
        self.frame_today = ctk.CTkScrollableFrame(tab, fg_color=CARD)
        self.frame_today.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
        self._refresh_today()

    def _refresh_today(self):
        for w in self.frame_today.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.frame_today, text="Chargement…", font=FONT_SMALL).pack(pady=8)

        def work():
            rows, err = self.app.admin_api_state()
            def fill():
                for w in self.frame_today.winfo_children():
                    w.destroy()
                if err:
                    ctk.CTkLabel(self.frame_today, text=f"⚠ {err}",
                                 font=FONT_BODY, text_color=WARN).pack(pady=10)
                    return
                if not rows:
                    ctk.CTkLabel(self.frame_today, text="Personne aujourd'hui.",
                                 font=FONT_SMALL, text_color="gray").pack(pady=10)
                    return
                for r in rows:
                    card = ctk.CTkFrame(self.frame_today, fg_color="#232936")
                    card.pack(fill="x", pady=3, padx=4)
                    name = r.get("alias") or r.get("username", "?")
                    line = f"{name} — {fmt_duration(r.get('used', 0))} " \
                           f"({'bloqué' if r.get('blocked') else 'en cours'})"
                    ctk.CTkLabel(card, text=line, font=FONT_BODY,
                                 text_color=(BAD if r.get('blocked') else GOOD))\
                        .pack(side="left", padx=10, pady=6)
                    ctk.CTkLabel(card, text=f"machines : {r.get('machines', '')}",
                                 font=FONT_SMALL, text_color="gray")\
                        .pack(side="right", padx=10)
            self.after(0, fill)
        threading.Thread(target=work, daemon=True).start()

    # ---------------------------------------------------------- onglet config
    def _build_config_tab(self, tab):
        tab.columnconfigure(1, weight=1)
        cfg = self.app.cfg

        ctk.CTkLabel(tab, text="Connexion au site", font=FONT_H2)\
            .grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4))

        ctk.CTkLabel(tab, text="URL de l'API :", font=FONT_BODY)\
            .grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.e_url = ctk.CTkEntry(tab, width=380,
                                  placeholder_text="https://tcontrol.thibstudio.rf.gd/api")
        self.e_url.grid(row=1, column=1, sticky="w", padx=8, pady=4)
        self.e_url.insert(0, cfg.server_url)

        ctk.CTkLabel(tab, text="Clé API :", font=FONT_BODY)\
            .grid(row=2, column=0, sticky="w", padx=8, pady=4)
        self.e_key = ctk.CTkEntry(tab, width=380, show="•",
                                  placeholder_text="clé affichée dans l'admin du site")
        self.e_key.grid(row=2, column=1, sticky="w", padx=8, pady=4)
        self.e_key.insert(0, cfg.api_key)

        ctk.CTkButton(tab, text="💾 Enregistrer et synchroniser",
                      fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      command=self._save_config)\
            .grid(row=3, column=1, sticky="w", padx=8, pady=8)

        st = self.app.state
        ctk.CTkLabel(tab, text="Paramètres actifs (modifiables sur le site)",
                     font=FONT_H2).grid(row=4, column=0, columnspan=2,
                                        sticky="w", padx=8, pady=(16, 4))
        self.lbl_limit = ctk.CTkLabel(
            tab, text=f"• Limite quotidienne : {fmt_duration(st.limit)}",
            font=FONT_BODY)
        self.lbl_limit.grid(row=5, column=0, columnspan=2, sticky="w", padx=16, pady=2)
        self.lbl_reset = ctk.CTkLabel(
            tab, text=f"• Heure de reset : {st.reset_hour:02d}h00", font=FONT_BODY)
        self.lbl_reset.grid(row=6, column=0, columnspan=2, sticky="w", padx=16, pady=2)

        ctk.CTkLabel(tab, text="Système", font=FONT_H2)\
            .grid(row=7, column=0, columnspan=2, sticky="w", padx=8, pady=(16, 4))
        self.sw_autostart = ctk.CTkSwitch(
            tab, text="Démarrer automatiquement avec Windows",
            font=FONT_BODY, command=self._toggle_autostart)
        if autostart_supported() and is_autostart_enabled():
            self.sw_autostart.select()
        if not autostart_supported():
            self.sw_autostart.configure(state="disabled")
        self.sw_autostart.grid(row=8, column=0, columnspan=2, sticky="w",
                               padx=16, pady=6)

        ctk.CTkButton(tab, text="⏻ Quitter Tcontrol", fg_color="#7f1d1d",
                      hover_color="#991b1b", command=self._quit_app)\
            .grid(row=9, column=1, sticky="e", padx=8, pady=(20, 8))

        self.lbl_cfg_status = ctk.CTkLabel(tab, text="", font=FONT_SMALL,
                                           text_color="gray")
        self.lbl_cfg_status.grid(row=10, column=0, columnspan=2, sticky="w",
                                 padx=8, pady=4)

    def _save_config(self):
        cfg = self.app.cfg
        cfg.server_url = self.e_url.get().strip()
        cfg.api_key = self.e_key.get().strip()
        cfg.save()
        self.lbl_cfg_status.configure(text="Enregistré. Synchronisation…",
                                      text_color=GOOD)
        self.app.monitor.force_sync()
        if self.setup_only:
            self.after(3000, self._check_first_sync)

    def _check_first_sync(self):
        if self.app.state.last_sync_ok:
            messagebox.showinfo(
                APP_NAME,
                "✅ Connexion au site réussie !\n\n"
                "Le panneau va se fermer : reconnecte-toi avec le bouton 🔑 "
                "et tes identifiants du site pour gérer les jeux bloqués.",
                parent=self)
            self.destroy()
        else:
            self.lbl_cfg_status.configure(
                text="Toujours hors ligne… vérifie l'URL (…/api) et la clé API, "
                     "puis Enregistrer à nouveau.", text_color=WARN)

    def _toggle_autostart(self):
        ok = set_autostart(bool(self.sw_autostart.get()))
        if not ok:
            messagebox.showwarning(APP_NAME, "Impossible de modifier le "
                                   "démarrage automatique.", parent=self)

    def _quit_app(self):
        if messagebox.askyesno(APP_NAME, "Vraiment quitter Tcontrol ?\n"
                               "La surveillance s'arrêtera.", parent=self):
            self.destroy()
            self.app.quit_app()


# =====================================================================
# Application principale
# =====================================================================

class TcontrolApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} — Contrôle du temps de jeu")
        self.geometry("940x620")
        self.minsize(860, 560)

        # --- état & services
        self.cfg = Config.load()
        self.state = State.load()
        self.sync = SyncClient(self.cfg)
        self.events: "queue.Queue" = queue.Queue()
        self.monitor = Monitor(self.cfg, self.state, self.sync, self.events)
        self.user, self.machine = get_identity()
        self.admin_user = None
        self.admin_pass = None
        self.admin_panel = None

        self.tray = TrayIcon(on_open=self.show_window, on_quit=self.tray_quit)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._poll_events()
        self._refresh_clock()
        self.monitor.start()

        if not self.admin_user:  # propose le démarrage auto dès la 1ʳᵉ config
            pass

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(2, weight=1)

        # ---- bandeau config
        self.banner = None
        if not self.cfg.configured:
            self.banner = SetupBanner(self, self.open_admin)
            self.banner.grid(row=0, column=0, columnspan=2, sticky="ew",
                             padx=12, pady=(12, 0))

        # ---- header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(14, 6))
        ctk.CTkLabel(header, text="⏱ Tcontrol", font=FONT_TITLE).pack(side="left")
        self.lbl_status = ctk.CTkLabel(header, text="● démarrage…",
                                       font=FONT_BODY, text_color="gray")
        self.lbl_status.pack(side="left", padx=18)
        ctk.CTkButton(header, text="🔑 Admin", width=90, fg_color=ACCENT,
                      hover_color=ACCENT_HOVER, command=self.open_admin)\
            .pack(side="right")
        self.lbl_user = ctk.CTkLabel(header, text=f"{self.user}@{self.machine}",
                                     font=FONT_SMALL, text_color="gray")
        self.lbl_user.pack(side="right", padx=10)

        # ---- carte temps
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        card.grid(row=2, column=0, sticky="nsew", padx=(16, 8), pady=8)

        ctk.CTkLabel(card, text="Temps restant aujourd'hui",
                     font=FONT_H2).pack(pady=(22, 4))
        self.lbl_remaining = ctk.CTkLabel(card, text="--:--", font=FONT_BIG,
                                          text_color=GOOD)
        self.lbl_remaining.pack()
        self.progress = ctk.CTkProgressBar(card, width=380)
        self.progress.pack(pady=14)
        self.progress.set(1)
        self.lbl_used = ctk.CTkLabel(card, text="", font=FONT_BODY,
                                     text_color="gray")
        self.lbl_used.pack()
        self.lbl_game = ctk.CTkLabel(card, text="", font=FONT_BODY,
                                     text_color=WARN)
        self.lbl_game.pack(pady=(8, 0))
        self.lbl_blocked = ctk.CTkLabel(card, text="", font=FONT_H2,
                                        text_color=BAD)
        self.lbl_blocked.pack(pady=(6, 12))

        # ---- carte jeux surveillés
        side = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        side.grid(row=2, column=1, sticky="nsew", padx=(8, 16), pady=8)
        ctk.CTkLabel(side, text="🎮 Jeux surveillés", font=FONT_H2)\
            .pack(anchor="w", padx=14, pady=(14, 4))
        self.frame_watch = ctk.CTkScrollableFrame(side, fg_color="transparent")
        self.frame_watch.pack(fill="both", expand=True, padx=8, pady=4)
        self.lbl_reset_info = ctk.CTkLabel(side, text="", font=FONT_SMALL,
                                           text_color="gray")
        self.lbl_reset_info.pack(anchor="w", padx=14, pady=(4, 2))
        self.lbl_sync_info = ctk.CTkLabel(side, text="", font=FONT_SMALL,
                                          text_color="gray")
        self.lbl_sync_info.pack(anchor="w", padx=14, pady=(0, 12))

        self._refresh_watchlist()

    # ------------------------------------------------------------------ rafraîchissement
    def _refresh_clock(self):
        st = self.state
        remaining = st.remaining()
        used = st.local_used()
        limit = st.limit or 0

        h, rem = divmod(int(remaining), 3600)
        m, s = divmod(rem, 60)
        self.lbl_remaining.configure(text=f"{h:02d}:{m:02d}:{s:02d}")

        color = GOOD if remaining > 600 else (WARN if remaining > 300 else BAD)
        self.lbl_remaining.configure(text_color=color)
        self.progress.configure(progress_color=color)
        self.progress.set(used / limit if limit else 0)

        self.lbl_used.configure(
            text=f"Utilisé : {fmt_duration(used)}  •  Limite : {fmt_duration(limit)}")
        self.lbl_game.configure(
            text=f"▶ en cours : {st.current_game}" if st.current_game else "")

        blocked = st.is_blocked()
        self.lbl_blocked.configure(
            text="🚫 Temps écoulé — jeux bloqués" if blocked else "")

        self.lbl_reset_info.configure(
            text=f"Reset quotidien à {st.reset_hour:02d}h00 • Journée : {st.day or '—'}")
        if st.last_sync:
            self.lbl_sync_info.configure(text=f"Dernière synchro : {st.last_sync}"
                                              + ("" if st.last_sync_ok else " (hors ligne)"))
        self.after(1000, self._refresh_clock)

    def _refresh_watchlist(self):
        for w in self.frame_watch.winfo_children():
            w.destroy()
        procs = self.state.processes
        if not procs:
            ctk.CTkLabel(self.frame_watch,
                         text="Aucun jeu surveillé.\nL'admin peut en ajouter\nvia le bouton 🔑.",
                         font=FONT_SMALL, text_color="gray",
                         justify="left").pack(anchor="w", pady=6, padx=6)
        for name in sorted(procs):
            running = name == self.state.current_game
            ctk.CTkLabel(self.frame_watch,
                         text=("🔴 " if running else "⚫ ") + name,
                         font=FONT_BODY).pack(anchor="w", padx=8, pady=2)
        self.after(3000, self._refresh_watchlist)

    def _poll_events(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                self._handle_event(kind, data)
        except queue.Empty:
            pass
        self.after(400, self._poll_events)

    def _handle_event(self, kind, data):
        if kind == "status":
            if data["online"] is True:
                self.lbl_status.configure(text="● en ligne", text_color=GOOD)
            elif data["online"] is False:
                self.lbl_status.configure(text="● hors ligne (cache local)",
                                          text_color=WARN)
            elif data.get("error"):
                self.lbl_status.configure(text="● erreur interne", text_color=BAD)
        elif kind == "day_reset":
            self._refresh_watchlist_once()
        elif kind == "synced":
            if self.banner is not None and self.cfg.configured:
                self.banner.destroy()
                self.banner = None

    def _refresh_watchlist_once(self):
        # force un rafraîchissement immédiat de la liste (la boucle le fait sinon)
        for w in self.frame_watch.winfo_children():
            w.destroy()
        procs = self.state.processes
        for name in sorted(procs):
            ctk.CTkLabel(self.frame_watch, text="⚫ " + name,
                         font=FONT_BODY).pack(anchor="w", padx=8, pady=2)

    # ------------------------------------------------------------------ admin
    @property
    def is_admin(self) -> bool:
        return bool(self.admin_user)

    def check_credentials(self, user: str, password: str) -> tuple[bool, str]:
        """Appelé par UnlockDialog. En ligne : vérifie sur le site ;
        hors ligne : vérifie contre les admins mémorisés."""
        if self.cfg.configured:
            if self.sync.auth(user, password):
                self._grant_admin(user, password)
                return True, ""
            if self.state.cached_admins:
                # pas de compte serveur mais cache dispo → on tente le cache
                if verify_admin(user, password, self.state.cached_admins):
                    self._grant_admin(user, password)
                    return True, "(hors ligne — vérifié localement) "
            return False, "Identifiants incorrects ou serveur injoignable."
        if verify_admin(user, password, self.state.cached_admins):
            self._grant_admin(user, password)
            return True, ""
        return False, "Hors ligne et aucun admin mémorisé sur ce PC."

    def _grant_admin(self, user, password):
        self.admin_user, self.admin_pass = user, password
        self.state.cached_admins = remember_admin(user, password,
                                                  self.state.cached_admins)
        self.state.save()
        self.after(100, self._open_admin_panel)

    def open_admin(self):
        if self.is_admin:
            self._open_admin_panel()
            return
        if not self.cfg.configured and not self.state.cached_admins:
            # Toute première installation : on ne peut vérifier d'identifiants
            # nulle part → panneau en mode "configuration seule".
            self._open_admin_panel()
            return
        UnlockDialog(self, self.check_credentials)

    def _open_admin_panel(self):
        if self.admin_panel is not None and self.admin_panel.winfo_exists():
            self.admin_panel.focus()
            return
        self.admin_panel = AdminPanel(self)

    def admin_api(self, action: str, name: str):
        """Ajoute/retire un processus via le site. Retourne None ou un message d'erreur."""
        if not self.is_admin:
            return "Non authentifié."
        try:
            if action == "add":
                resp = self.sync.admin_add_process(self.admin_user, self.admin_pass, name)
            else:
                resp = self.sync.admin_remove_process(self.admin_user, self.admin_pass, name)
            procs = resp.get("processes")
            if isinstance(procs, list):
                self.state.processes = [str(p).strip().lower() for p in procs]
                self.state.save()
            return None
        except SyncError as e:
            return str(e)

    def admin_api_state(self):
        """Retourne (rows, error). rows = usage du jour depuis le site."""
        if not self.is_admin:
            return [], "Non authentifié."
        try:
            resp = self.sync.admin_state(self.admin_user, self.admin_pass)
            return resp.get("usage", []), None
        except SyncError as e:
            return [], str(e)

    # ------------------------------------------------------------------ fermeture
    def on_close(self):
        if self.is_admin:
            if messagebox.askyesno(APP_NAME, "Quitter Tcontrol ?\n"
                                   "(la surveillance s'arrêtera)", parent=self):
                self.quit_app()
            return
        # utilisateur normal : on se cache dans la zone de notification
        self.hide_to_tray()

    def hide_to_tray(self):
        if self.tray.available:
            self.withdraw()
            self.tray.show()
        else:
            self.iconify()  # repli : simple réduction

    def show_window(self):
        self.after(0, self._do_show)

    def _do_show(self):
        self.tray.hide()
        self.deiconify()
        self.lift()
        self.focus_force()

    def tray_quit(self):
        self.after(0, self._tray_quit)

    def _tray_quit(self):
        self._do_show()
        if self.is_admin:
            if messagebox.askyesno(APP_NAME, "Quitter Tcontrol ?", parent=self):
                self.quit_app()
        else:
            self.open_admin()  # débloquer puis Quitter via le panneau

    def quit_app(self):
        self.monitor.stop()
        self.tray.hide()
        self.state.save()
        self.destroy()


def main():
    app = TcontrolApp()
    app.mainloop()


if __name__ == "__main__":
    main()
