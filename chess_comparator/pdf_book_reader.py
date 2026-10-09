"""Embedded PDF chess-book reader with page rendering and move-line controls."""
from __future__ import annotations

import base64
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class PDFBookReader(ttk.Frame):
    def __init__(self, parent, *, language_getter, engine_var, engine_names,
                 engine_callback, analyze_callback, apply_line_callback,
                 edit_position_callback, diagram_callback, save_pgn_callback, close_callback):
        super().__init__(parent, padding=6)
        self.language_getter = language_getter
        self.engine_var = engine_var
        self.engine_names = tuple(engine_names)
        self.engine_callback = engine_callback
        self.analyze_callback = analyze_callback
        self.apply_line_callback = apply_line_callback
        self.edit_position_callback = edit_position_callback
        self.diagram_callback = diagram_callback
        self.save_pgn_callback = save_pgn_callback
        self.close_callback = close_callback
        self.doc = None
        self.fitz = None
        self.path = None
        self.page_index = 0
        self.photo = None
        self.render_after = None
        self.zoom = 1.0
        self.page_render_scale = 1.0
        self.selecting_diagram = False
        self.selection_start = None
        self.selection_item = None
        self.status_var = tk.StringVar(value='')
        self.page_var = tk.StringVar(value='1')
        self.page_count_var = tk.StringVar(value='')
        self.file_var = tk.StringVar(value='')
        self.zoom_var = tk.StringVar(value='100%')
        self.notation_kind = tk.StringVar(value='Descriptive')
        self.notation_label = tk.StringVar(value='')
        self._build()
        self.set_language()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill='x')
        self.open_button = ttk.Button(top, command=self.open_dialog)
        self.open_button.pack(side='left')
        self.file_label = ttk.Label(top, textvariable=self.file_var, width=30)
        self.file_label.pack(side='left', padx=7, fill='x', expand=True)
        self.close_button = ttk.Button(top, command=self.close_callback)
        self.close_button.pack(side='right')

        nav = ttk.Frame(self)
        nav.pack(fill='x', pady=(5, 2))
        self.prev_button = ttk.Button(nav, width=4, command=lambda: self.show_page(self.page_index - 1))
        self.prev_button.pack(side='left')
        self.page_entry = ttk.Entry(nav, textvariable=self.page_var, width=5, justify='center')
        self.page_entry.pack(side='left', padx=3)
        self.page_entry.bind('<Return>', self.goto_page)
        self.page_entry.bind('<FocusOut>', self.goto_page)
        self.page_count_label = ttk.Label(nav, textvariable=self.page_count_var)
        self.page_count_label.pack(side='left', padx=(0, 8))
        self.next_button = ttk.Button(nav, width=4, command=lambda: self.show_page(self.page_index + 1))
        self.next_button.pack(side='left')
        self.zoom_label = ttk.Label(nav)
        self.zoom_label.pack(side='left', padx=(12, 3))
        self.zoom_box = ttk.Combobox(nav, textvariable=self.zoom_var,
                                     values=('75%', '100%', '125%', '150%'),
                                     state='readonly', width=7)
        self.zoom_box.pack(side='left')
        self.zoom_box.bind('<<ComboboxSelected>>', self.change_zoom)

        engine = ttk.Frame(self)
        engine.pack(fill='x', pady=(3, 5))
        self.engine_label = ttk.Label(engine)
        self.engine_label.pack(side='left')
        self.engine_selector = ttk.Combobox(engine, textvariable=self.engine_var,
                                             values=self.engine_names, state='readonly', width=16)
        self.engine_selector.pack(side='left', padx=4)
        self.engine_selector.bind('<<ComboboxSelected>>', self._engine_changed)
        self.analyze_button = ttk.Button(engine, command=self._analyze)
        self.analyze_button.pack(side='left', padx=4)

        self.book_tabs = ttk.Notebook(self)
        self.book_tabs.pack(fill='both', expand=True)
        self.page_tab = ttk.Frame(self.book_tabs)
        self.ocr_tab = ttk.Frame(self.book_tabs)
        self.moves_tab = ttk.Frame(self.book_tabs, padding=5)
        self.book_tabs.add(self.page_tab)
        self.book_tabs.add(self.ocr_tab)
        self.book_tabs.add(self.moves_tab)
        self._build_page_tab()
        self._build_ocr_tab()
        self._build_moves_tab()
        ttk.Label(self, textvariable=self.status_var, wraplength=480).pack(fill='x', pady=(4, 0))

    def _build_page_tab(self):
        self.page_tab.rowconfigure(1, weight=1)
        self.page_tab.columnconfigure(0, weight=1)
        tools = ttk.Frame(self.page_tab, padding=(3, 3))
        tools.grid(row=0, column=0, columnspan=2, sticky='ew')
        self.select_diagram_button = ttk.Button(tools, command=self.begin_diagram_selection)
        self.select_diagram_button.pack(side='left')
        self.diagram_help = ttk.Label(tools, wraplength=340)
        self.diagram_help.pack(side='left', padx=6)
        self.page_canvas = tk.Canvas(self.page_tab, background='#d4d7dc', highlightthickness=0)
        self.page_vscroll = ttk.Scrollbar(self.page_tab, orient='vertical', command=self.page_canvas.yview)
        self.page_hscroll = ttk.Scrollbar(self.page_tab, orient='horizontal', command=self.page_canvas.xview)
        self.page_canvas.configure(yscrollcommand=self.page_vscroll.set,
                                   xscrollcommand=self.page_hscroll.set)
        self.page_canvas.grid(row=1, column=0, sticky='nsew')
        self.page_vscroll.grid(row=1, column=1, sticky='ns')
        self.page_hscroll.grid(row=2, column=0, sticky='ew')
        self.page_canvas.bind('<Configure>', self._schedule_render)
        self.page_canvas.bind('<ButtonPress-1>', self._selection_start)
        self.page_canvas.bind('<B1-Motion>', self._selection_drag)
        self.page_canvas.bind('<ButtonRelease-1>', self._selection_finish)

    def _build_ocr_tab(self):
        self.ocr_tab.rowconfigure(0, weight=1)
        self.ocr_tab.columnconfigure(0, weight=1)
        self.ocr_text = tk.Text(self.ocr_tab, wrap='word', state='disabled',
                                font=('Segoe UI', 10), undo=False)
        scroll = ttk.Scrollbar(self.ocr_tab, orient='vertical', command=self.ocr_text.yview)
        self.ocr_text.configure(yscrollcommand=scroll.set)
        self.ocr_text.grid(row=0, column=0, sticky='nsew')
        scroll.grid(row=0, column=1, sticky='ns')

    def _build_moves_tab(self):
        self.moves_tab.columnconfigure(0, weight=1)
        self.notation_label_widget = ttk.Label(self.moves_tab)
        self.notation_label_widget.grid(row=0, column=0, sticky='w')
        self.notation_box = ttk.Combobox(self.moves_tab, textvariable=self.notation_label,
                                         state='readonly', width=29)
        self.notation_box.grid(row=1, column=0, sticky='w', pady=(2, 5))
        self.notation_box.bind('<<ComboboxSelected>>', self._notation_changed)
        self.line_hint = ttk.Label(self.moves_tab, wraplength=470)
        self.line_hint.grid(row=2, column=0, sticky='w', pady=(0, 3))
        self.move_input = tk.Text(self.moves_tab, height=5, wrap='word', font=('Consolas', 10))
        self.move_input.grid(row=3, column=0, sticky='nsew')
        self.moves_tab.rowconfigure(3, weight=1)
        buttonrow = ttk.Frame(self.moves_tab)
        buttonrow.grid(row=4, column=0, sticky='ew', pady=5)
        self.position_button = ttk.Button(buttonrow, command=self.edit_position_callback)
        self.position_button.pack(side='left', padx=(0, 4))
        self.apply_button = ttk.Button(buttonrow, command=self.apply_line)
        self.apply_button.pack(side='left', padx=4)
        self.save_button = ttk.Button(buttonrow, command=self.save_pgn_callback)
        self.save_button.pack(side='left', padx=4)
        self.output_label = ttk.Label(self.moves_tab)
        self.output_label.grid(row=5, column=0, sticky='w', pady=(3, 1))
        self.san_output = tk.Text(self.moves_tab, height=4, wrap='word',
                                  state='disabled', font=('Consolas', 10))
        self.san_output.grid(row=6, column=0, sticky='ew')

    def set_language(self):
        english = self.language_getter() == 'English'
        t = (lambda es, en: en if english else es)
        self.open_button.configure(text=t('Abrir libro PDF…', 'Open PDF book…'))
        self.close_button.configure(text=t('Volver al estudio', 'Back to Study'))
        self.prev_button.configure(text=t('◀ Anterior', '◀ Previous'))
        self.next_button.configure(text=t('Siguiente ▶', 'Next ▶'))
        self.zoom_label.configure(text=t('Zoom:', 'Zoom:'))
        self.engine_label.configure(text=t('Motor:', 'Engine:'))
        self.analyze_button.configure(text=t('Analizar tablero', 'Analyze board'))
        self.select_diagram_button.configure(text=t('Marcar diagrama con el ratón', 'Select diagram with mouse'))
        self.diagram_help.configure(text=t('Marca el tablero en la página; luego revisa y coloca las piezas.',
                                           'Select the board on the page, then verify and place its pieces.'))
        self.prev_button.configure(width=10)
        self.next_button.configure(width=10)
        self.book_tabs.tab(self.page_tab, text=t('Página', 'Page'))
        self.book_tabs.tab(self.ocr_tab, text=t('Texto OCR', 'OCR text'))
        self.book_tabs.tab(self.moves_tab, text=t('Seguir jugadas', 'Follow moves'))
        self.notation_label_widget.configure(text=t('Notación de la línea:', 'Line notation:'))
        self.line_hint.configure(text=t(
            'Pega solo una secuencia. Para líneas descriptivas, configura primero en el tablero la posición del diagrama.',
            'Paste a move sequence only. For descriptive notation, first set up the diagram position on the board.'
        ))
        self.position_button.configure(text=t('Editar posición del diagrama', 'Set up diagram position'))
        self.apply_button.configure(text=t('Convertir y seguir línea', 'Convert and play line'))
        self.save_button.configure(text=t('Guardar línea PGN', 'Save line as PGN'))
        self.output_label.configure(text=t('Línea convertida a notación algebraica:', 'Converted algebraic line:'))
        self.notation_box.configure(values=(t('Descriptiva (española)', 'Descriptive (Spanish)'),
                                            t('Algebraica SAN', 'Algebraic SAN')))
        self._set_notation_label()
        if self.doc is None:
            self.status_var.set(t('Abre un libro PDF para comenzar.', 'Open a PDF book to begin.'))
        else:
            self._update_page_labels()

    def _set_notation_label(self):
        english = self.language_getter() == 'English'
        self.notation_label.set(
            ('Descriptive (Spanish)' if english else 'Descriptiva (española)')
            if self.notation_kind.get() == 'Descriptive'
            else ('Algebraic SAN' if english else 'Algebraica SAN')
        )

    def _notation_changed(self, _event=None):
        english = self.language_getter() == 'English'
        label = self.notation_label.get()
        self.notation_kind.set('Descriptive' if ('Descriptive' in label or 'Descriptiva' in label)
                               else 'SAN')

    def refresh_engines(self, engine_names):
        self.engine_names = tuple(engine_names)
        self.engine_selector.configure(values=self.engine_names)

    def _engine_changed(self, _event=None):
        self.engine_callback(self.engine_var.get())

    def _analyze(self):
        self.analyze_callback(self.engine_var.get())

    def open_dialog(self):
        english = self.language_getter() == 'English'
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title='Select a PDF book' if english else 'Selecciona un libro PDF',
            filetypes=[('PDF', '*.pdf'), ('All files' if english else 'Todos los archivos', '*.*')],
        )
        if path:
            self.open_pdf(path)

    def open_pdf(self, path):
        try:
            import fitz
        except ImportError:
            english = self.language_getter() == 'English'
            messagebox.showerror(
                'PDF reader' if english else 'Lector PDF',
                ('PyMuPDF is missing. Install it once with:\n'
                 'From the project folder: py -m pip install -r chess_comparator/requirements-pdf.txt\n'
                 'From chess_comparator: py -m pip install -r requirements-pdf.txt') if english else
                ('Falta PyMuPDF. Instálalo una vez con:\n'
                 'Desde la carpeta principal: py -m pip install -r chess_comparator/requirements-pdf.txt\n'
                 'Desde chess_comparator: py -m pip install -r requirements-pdf.txt'),
                parent=self.winfo_toplevel(),
            )
            return False
        try:
            candidate = fitz.open(path)
            if candidate.page_count < 1:
                candidate.close()
                raise ValueError('El PDF no contiene páginas / The PDF has no pages.')
        except Exception as exc:
            title='PDF' if self.language_getter() == 'English' else 'Libro PDF'
            message=('Could not open the book:\n' if self.language_getter() == 'English'
                     else 'No se pudo abrir el libro:\n')
            messagebox.showerror(title, message+str(exc),
                                 parent=self.winfo_toplevel())
            return False
        self.close_document()
        self.doc = candidate
        self.fitz = fitz
        self.path = os.path.abspath(path)
        self.page_index = 0
        self.file_var.set(os.path.basename(path))
        self.show_page(0)
        return True

    def close_document(self):
        if self.doc is not None:
            try:
                self.doc.close()
            except Exception:
                pass
        self.doc = None
        self.path = None
        self.fitz = None
        self.photo = None
        self.file_var.set('')
        self.page_count_var.set('')
        self.page_canvas.delete('all')
        self.page_canvas.configure(scrollregion=(0, 0, 1, 1))
        self._set_text(self.ocr_text, '')
        self._set_text(self.san_output, '')
        self.status_var.set('')

    def show_page(self, page_index):
        if self.doc is None:
            return
        self.page_index = max(0, min(self.doc.page_count - 1, int(page_index)))
        self.selecting_diagram = False
        self.selection_start = None
        self.page_var.set(str(self.page_index + 1))
        self._update_page_labels()
        page = self.doc.load_page(self.page_index)
        self._set_text(self.ocr_text, page.get_text('text', sort=True).strip())
        self._render_page()

    def _update_page_labels(self):
        if self.doc is None:
            return
        self.page_count_var.set(f"/ {self.doc.page_count}")
        english = self.language_getter() == 'English'
        self.status_var.set(
            f"Page {self.page_index + 1} of {self.doc.page_count}" if english
            else f"Página {self.page_index + 1} de {self.doc.page_count}"
        )

    def goto_page(self, _event=None):
        if self.doc is None:
            return
        try:
            page = int(self.page_var.get()) - 1
        except ValueError:
            self.page_var.set(str(self.page_index + 1))
            return
        self.show_page(page)

    def change_zoom(self, _event=None):
        try:
            self.zoom = max(0.5, min(2.0, int(self.zoom_var.get().rstrip('%')) / 100))
        except (ValueError, AttributeError):
            self.zoom = 1.0
        self._schedule_render()

    def _schedule_render(self, _event=None):
        if self.doc is None:
            return
        if self.render_after is not None:
            try:
                self.after_cancel(self.render_after)
            except tk.TclError:
                pass
        self.render_after = self.after(120, self._render_page)

    def _render_page(self):
        self.render_after = None
        if self.doc is None or self.fitz is None:
            return
        try:
            page = self.doc.load_page(self.page_index)
            width = max(180, self.page_canvas.winfo_width() - 24)
            scale = min(3.0, max(0.35, width / page.rect.width * self.zoom))
            self.page_render_scale = scale
            pix = page.get_pixmap(matrix=self.fitz.Matrix(scale, scale), alpha=False)
            self.photo = tk.PhotoImage(data=base64.b64encode(pix.tobytes('png')).decode('ascii'))
            self.page_canvas.delete('all')
            self.page_canvas.create_image(8, 8, image=self.photo, anchor='nw')
            self.page_canvas.configure(scrollregion=(0, 0, pix.width + 16, pix.height + 16))
            self.page_canvas.xview_moveto(0)
            self.page_canvas.yview_moveto(0)
        except Exception as exc:
            self.status_var.set(f'PDF: {exc}')

    def begin_diagram_selection(self):
        if self.doc is None:
            self.status_var.set('Abre un PDF primero.' if self.language_getter() != 'English'
                                else 'Open a PDF first.')
            return
        self.selecting_diagram = True
        self.selection_start = None
        self.page_canvas.configure(cursor='crosshair')
        self.status_var.set('Arrastra un rectángulo alrededor del tablero.' if self.language_getter() != 'English'
                            else 'Drag a rectangle around the chessboard.')

    def _selection_start(self, event):
        if not self.selecting_diagram or self.doc is None:
            return
        x, y = self.page_canvas.canvasx(event.x), self.page_canvas.canvasy(event.y)
        self.selection_start = (x, y)
        if self.selection_item is not None:
            self.page_canvas.delete(self.selection_item)
        self.selection_item = self.page_canvas.create_rectangle(
            x, y, x, y, outline='#e33b25', width=3, dash=(5, 3))

    def _selection_drag(self, event):
        if not self.selecting_diagram or self.selection_start is None:
            return
        x, y = self.page_canvas.canvasx(event.x), self.page_canvas.canvasy(event.y)
        self.page_canvas.coords(self.selection_item, *self.selection_start, x, y)

    def _selection_finish(self, event):
        if not self.selecting_diagram or self.selection_start is None or self.doc is None:
            return
        x1, y1 = self.selection_start
        x2, y2 = self.page_canvas.canvasx(event.x), self.page_canvas.canvasy(event.y)
        self.selecting_diagram = False
        self.selection_start = None
        self.page_canvas.configure(cursor='')
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        # The rendered page is drawn at (8, 8) on the canvas.
        left, right = max(0, left - 8), max(0, right - 8)
        top, bottom = max(0, top - 8), max(0, bottom - 8)
        if right - left < 24 or bottom - top < 24:
            size = min(self.photo.width(), self.photo.height()) * 0.72
            cx, cy = (left + right) / 2, (top + bottom) / 2
            left, right = cx - size / 2, cx + size / 2
            top, bottom = cy - size / 2, cy + size / 2
        left, right = max(0, left), min(self.photo.width(), right)
        top, bottom = max(0, top), min(self.photo.height(), bottom)
        if right - left < 50 or bottom - top < 50:
            self.status_var.set('La selección es muy pequeña; vuelve a marcar el tablero.'
                                if self.language_getter() != 'English'
                                else 'Selection is too small; select the board again.')
            return
        scale = max(0.01, self.page_render_scale)
        rect = self.fitz.Rect(left / scale, top / scale, right / scale, bottom / scale)
        try:
            page = self.doc.load_page(self.page_index)
            rect = rect & page.rect
            if rect.is_empty:
                raise ValueError('Selecciona una zona dentro de la página.')
            crop = page.get_pixmap(matrix=self.fitz.Matrix(scale, scale), clip=rect, alpha=False)
            self.page_canvas.configure(cursor='')
            self.status_var.set('Diagrama marcado. Abriendo la vista de referencia…' if self.language_getter() != 'English'
                                else 'Diagram selected. Opening reference preview…')
            self.diagram_callback(crop.tobytes('png'))
        except Exception as exc:
            self.status_var.set(f'No se pudo recortar el diagrama: {exc}')

    @staticmethod
    def _set_text(widget, value):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        if value:
            widget.insert('1.0', value)
        widget.configure(state='disabled')

    def apply_line(self):
        text = self.move_input.get('1.0', 'end').strip()
        if not text:
            self.status_var.set('Paste a move sequence first.' if self.language_getter() == 'English'
                                else 'Pega una secuencia de jugadas.')
            return
        try:
            converted = self.apply_line_callback(text, self.notation_kind.get())
        except Exception as exc:
            title='Moves' if self.language_getter() == 'English' else 'Jugadas'
            messagebox.showerror(title, str(exc), parent=self.winfo_toplevel())
            return
        if converted:
            self._set_text(self.san_output, converted)
            self.book_tabs.select(self.moves_tab)
            self.status_var.set('Línea convertida y cargada en el tablero.' if self.language_getter() != 'English'
                                else 'Line converted and loaded on the board.')

    def show_error(self, message):
        self.status_var.set(message)

    def destroy(self):
        self.close_document()
        super().destroy()
