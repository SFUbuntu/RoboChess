"""Video-only Lichess library panel for RoboChess' Tkinter UI."""
from __future__ import annotations

import posixpath
import tkinter as tk
from tkinter import ttk
from urllib.parse import unquote, urlsplit


LICHESS_VIDEO_URL = "https://lichess.org/video"


class LichessVideo:
    """A lazily loaded video-only WebView with a return-to-study control."""

    def __init__(self, parent, *, language="English", analyze_callback=None,
                 engine_var=None, engine_names=(), engine_callback=None,
                 close_callback=None):
        self.parent = parent
        self.language = language
        self.analyze_callback = analyze_callback
        self.engine_var = engine_var
        self.engine_names = tuple(engine_names)
        self.engine_callback = engine_callback
        self.close_callback = close_callback
        self.web = None
        self.web_error = None

        self.frame = ttk.Frame(parent, padding=6)
        self.toolbar = ttk.Frame(self.frame)
        self.toolbar.pack(fill="x", pady=(0, 5))
        self.title = ttk.Label(self.toolbar, font=("Arial", 11, "bold"))
        self.title.pack(side="left", padx=(0, 8))
        self.engine_selector = None
        if self.engine_var is not None and self.engine_names:
            self.engine_selector = ttk.Combobox(
                self.toolbar, textvariable=self.engine_var,
                values=self.engine_names, state="readonly", width=13,
            )
            self.engine_selector.pack(side="left", padx=3)
            if self.engine_callback:
                self.engine_selector.bind(
                    "<<ComboboxSelected>>",
                    lambda _event: self.engine_callback(self.engine_var.get()),
                )
        self.analyze_button = ttk.Button(
            self.toolbar, command=self._analyze_current_position,
        )
        self.analyze_button.pack(side="left", padx=3)
        self.reload_button = ttk.Button(self.toolbar, command=self.reload)
        self.reload_button.pack(side="right", padx=3)
        self.close_button = ttk.Button(self.toolbar, command=self.close_module)
        self.close_button.pack(side="right", padx=3)

        self.body = ttk.Frame(self.frame)
        self.body.pack(fill="both", expand=True)
        self.safety_note = ttk.Label(self.body, justify="left", wraplength=560)
        self.safety_note.pack(fill="x", padx=10, pady=(3, 6))
        self.status = ttk.Label(self.body, justify="left", wraplength=560)
        self.status.pack(fill="x", padx=16, pady=20)
        self.set_language(language)

    def set_language(self, language):
        self.language = language
        english = str(language).casefold() == "english"
        self.title.configure(text="Lichess Video Library" if english else "Biblioteca de videos de Lichess")
        self.analyze_button.configure(text="Analyze board position" if english else "Analizar posición del tablero")
        self.reload_button.configure(text="Reload" if english else "Recargar")
        self.close_button.configure(text="Close videos · Back to Study" if english else "Cerrar videos · Volver al estudio")
        self.safety_note.configure(text=(
            "Video library only. Lichess sign-in, play, and other pages are blocked in this view."
            if english else
            "Solo biblioteca de videos. El inicio de sesión, las partidas y las demás páginas de Lichess están bloqueadas aquí."
        ))
        self._set_status(self._loading_text() if self.web else self._intro_text())

    def _loading_text(self):
        return "Loading the official Lichess video library…" if self.language == "English" else "Cargando la biblioteca oficial de videos de Lichess…"

    def _intro_text(self):
        return (
            "The official Lichess video library opens here. The chessboard stays available on the left for manual moves and engine analysis."
            if self.language == "English" else
            "La biblioteca oficial de videos de Lichess aparece aquí. El tablero queda disponible a la izquierda para mover manualmente y analizar con el motor."
        )

    def _set_status(self, text):
        try:
            self.status.configure(text=text)
        except tk.TclError:
            pass

    def _show_failure(self, exc):
        self.web_error = str(exc)
        message = (
            "WebView2 could not start. Install the WebView2 Runtime and Python package `tkwry`, then restart RoboChess. External-browser handoff is disabled in this video-only view.\n\n"
            if self.language == "English" else
            "No se pudo iniciar WebView2. Instala el runtime de WebView2 y el paquete Python `tkwry`, y reinicia RoboChess. Este módulo no abre el navegador externo.\n\n"
        )
        self._set_status(message + str(exc))

    @staticmethod
    def _allow_video_navigation(event):
        """Allow only Lichess video routes and the embedded lesson player."""
        try:
            url = urlsplit(event.url)
            host = (url.hostname or "").lower().rstrip(".")
            path = posixpath.normpath(unquote(url.path)).rstrip("/").lower()
            if "\\" in path or url.port not in (None, 443) or url.scheme != "https":
                return False
            if host in {"lichess.org", "www.lichess.org"}:
                return path == "/video" or path.startswith("/video/")
            return host == "www.youtube-nocookie.com" and path.startswith("/embed/")
        except (AttributeError, TypeError, ValueError):
            return False

    @staticmethod
    def _video_only_script():
        """Hide account/game navigation and intercept off-library links."""
        return r"""(()=>{
          const install=()=>{
            if(!document.documentElement)return;
            const style=document.createElement('style');
            style.textContent='#top,.site_header,.site-header,.topnav{display:none!important}';
            (document.head||document.documentElement).appendChild(style);
          };
          if(document.documentElement)install();
          else document.addEventListener('DOMContentLoaded',install,{once:true});
          document.addEventListener('click',event=>{
            const link=event.target&&event.target.closest?event.target.closest('a[href]'):null;
            if(!link)return;
            let url;
            try{url=new URL(link.href,location.href)}catch(_){event.preventDefault();event.stopImmediatePropagation();return}
            if(url.origin!==location.origin||!(url.pathname==='/video'||url.pathname.startsWith('/video/'))){
              event.preventDefault();event.stopImmediatePropagation();
            }
          },true);
        })();"""

    def load(self):
        """Create the isolated browser only when the video module is shown."""
        if self.web is not None:
            self._set_status(self._loading_text())
            try:
                self.web.focus()
            except Exception:
                pass
            return
        try:
            from tkwry import NewWindowResponse, WebView
        except Exception as exc:
            self._show_failure(exc)
            return
        self._set_status(self._loading_text())
        try:
            self.web = WebView(
                self.body,
                url=LICHESS_VIDEO_URL,
                untrusted=True,
                navigation_policy=self._allow_video_navigation,
                on_new_window=lambda _event: NewWindowResponse.Deny,
                initialization_script=self._video_only_script(),
            )
            self.web.pack(fill="both", expand=True)
            self.web.when_failed(self._show_failure)
        except Exception as exc:
            self._show_failure(exc)

    def reload(self):
        if self.web is None:
            self.load()
            return
        self._set_status(self._loading_text())
        try:
            self.web.reload()
        except Exception as exc:
            self._show_failure(exc)

    def _analyze_current_position(self):
        if self.analyze_callback:
            self.analyze_callback(selected_only=True, engine_name=self.engine_var.get())

    def close_module(self):
        if self.close_callback:
            self.close_callback()

    def unload(self):
        """Stop video playback and discard the temporary browser session."""
        if self.web is not None:
            try:
                self.web.destroy()
            except Exception:
                pass
            self.web = None
        self.web_error = None
        self._set_status(self._intro_text())

    def destroy(self):
        self.unload()
        try:
            self.frame.destroy()
        except tk.TclError:
            pass
