"""Dual engine chess analysis, using Nibbler's piece images by Rooklift."""
import os, sys, traceback

def _resource_root():
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', None)
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        if meipass and os.path.isdir(os.path.join(meipass, 'assets')):
            return meipass
        if os.path.isdir(os.path.join(exe_dir, 'assets')):
            return exe_dir
        return meipass or exe_dir
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    candidates = (script_dir, os.path.join(script_dir, 'chess_comparator'),
                 parent_dir, os.path.join(parent_dir, 'chess_comparator'))
    for candidate in candidates:
        if (os.path.isfile(os.path.join(candidate, 'profile_store.py'))
                and os.path.isdir(os.path.join(candidate, 'assets'))):
            return candidate
    return script_dir

def _pause_if_console():
    if sys.stdout and sys.stdout.isatty():
        try:
            input('\nPulsa ENTER para cerrar / Press ENTER to close...')
        except Exception:
            pass

def _fatal(title, message):
    print(title)
    print(message)
    try:
        import tkinter as _tk
        from tkinter import messagebox as _mb
        root = _tk.Tk(); root.withdraw()
        _mb.showerror(title, message)
        root.destroy()
    except Exception:
        _pause_if_console()
    sys.exit(1)

try:
    import threading, queue, platform, math, tempfile, random, time, tkinter as tk, urllib.request, urllib.parse, urllib.error, io, webbrowser, csv, json, base64
    from pathlib import Path
    from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
except Exception:
    _fatal('RoboChess no pudo arrancar / failed to start',
           'Falta tkinter (Tcl/Tk).\n\nInstala Python 3 desde python.org y marca "tcl/tk and IDLE".\nLuego abre INICIAR.bat, no hagas doble clic en app.py.\n\n' + traceback.format_exc())

ROOT = _resource_root()
sys.path.insert(0, os.path.join(ROOT, 'vendor'))
sys.path.insert(0, ROOT)
try:
    import chess, chess.engine, chess.pgn
    import profile_store
    import board_settings
    import training_resources
    import quad_tournament
    import lichess_puzzles
    import puzzle_rush
    import personalities
    from lichess_video import LichessVideo
    from pdf_book_reader import PDFBookReader
    from descriptive_notation import parse_line as parse_chess_book_line
    from locale_ui import LABELS, SPANISH, choose
except Exception:
    _fatal('RoboChess no pudo importar módulos', traceback.format_exc())

class App:
    BUILTIN_ENGINE_NAMES=('Stockfish','Crafty','RoboChess')
    ENGINE_COLORS={'Stockfish':'#22a35b','Crafty':'#e77730','RoboChess':'#9b59b6'}
    BOARD_PALETTES={
        'Verde clásico / Classic green':('#eeeed2','#769656'),
        'Azul / Blue':('#e7eff5','#4f7898'),
        'Nogal / Walnut':('#f0d9b5','#9b6542'),
        'Gris / Gray':('#eeeeee','#777777'),
        'Morado / Purple':('#eee6f5','#8064a2'),
        'Rosa / Pink':('#f7e6ec','#c77b98'),
    }
    TIME_CONTROLS={
        'No clock / Sin reloj (5 s/move)':{'base':None,'increment':0,'delay':0,'increment_until':None},
        'Bullet 1+0':{'base':60,'increment':0,'delay':0,'increment_until':None},
        'Bullet 2+1':{'base':120,'increment':1,'delay':0,'increment_until':None},
        'Blitz 3+0':{'base':180,'increment':0,'delay':0,'increment_until':None},
        'Blitz 3+2':{'base':180,'increment':2,'delay':0,'increment_until':None},
        'Blitz 5+0':{'base':300,'increment':0,'delay':0,'increment_until':None},
        'Blitz 5+3':{'base':300,'increment':3,'delay':0,'increment_until':None},
        'Rapid/Rápidas 15+0':{'base':900,'increment':0,'delay':0,'increment_until':None},
        'Rapid/Rápidas 15+10':{'base':900,'increment':10,'delay':0,'increment_until':None},
        'Rapid/Rápidas 25+0 (sudden death)':{'base':1500,'increment':0,'delay':0,'increment_until':None},
        'Rapid/Rápidas 30+0':{'base':1800,'increment':0,'delay':0,'increment_until':None},
        'Classical/Clásica 90+5 delay':{'base':5400,'increment':0,'delay':5,'increment_until':None},
        'Classical/Clásica 90+30; no inc after/desde move/jugada 40':{'base':5400,'increment':30,'delay':0,'increment_until':39},
    }
    @property
    def ENGINE_NAMES(self):
        return self.BUILTIN_ENGINE_NAMES+tuple(self.custom_engines)
    @staticmethod
    def _engine_store_file():
        if platform.system()=='Windows':
            base=os.environ.get('APPDATA') or os.path.expanduser('~')
        else:
            base=os.environ.get('XDG_CONFIG_HOME') or os.path.join(os.path.expanduser('~'),'.config')
        return os.path.join(base,'RoboChess','uci_engines.json')
    def _read_custom_engines(self):
        try:
            with open(self._engine_store_file(),encoding='utf-8') as f:data=json.load(f)
            records=data.get('engines',{}) if isinstance(data,dict) else {}
            return {str(name):{'path':os.path.abspath(str(record['path'])),
                               'reported_name':str(record.get('reported_name','UCI engine'))}
                    for name,record in records.items()
                    if isinstance(record,dict) and record.get('path')
                    and str(name).casefold() not in {n.casefold() for n in self.BUILTIN_ENGINE_NAMES}}
        except (OSError,ValueError,TypeError):
            return {}
    def _save_custom_engines(self):
        target=self._engine_store_file();folder=os.path.dirname(target)
        os.makedirs(folder,exist_ok=True)
        temporary=target+'.tmp'
        with open(temporary,'w',encoding='utf-8') as f:
            json.dump({'engines':self.custom_engines},f,ensure_ascii=False,indent=2)
        os.replace(temporary,target)
    def _refresh_engine_choices(self,select_name=None):
        names=self.ENGINE_NAMES
        for widget in (getattr(self,'engine_selector',None),getattr(self,'engine_view_selector',None)):
            if widget is not None:widget.configure(values=names)
        video_selector=getattr(getattr(self,'lichess_video',None),'engine_selector',None)
        if video_selector is not None:video_selector.configure(values=names)
        pdf_reader=getattr(self,'pdf_reader',None)
        if pdf_reader is not None:pdf_reader.refresh_engines(names)
        if select_name:
            self.play_engine.set(select_name);self.engine_view.set(select_name)
            if select_name not in self.BUILTIN_ENGINE_NAMES and hasattr(self,'show_engine_arrows'):
                self.show_engine_arrows.setdefault(select_name,tk.BooleanVar(value=True))
        if hasattr(self,'panels') and select_name and select_name not in self.panels:
            self.panels[select_name]=tk.Text(self.engine_panel_holder,height=8,width=55,wrap='word',state='disabled')
        if hasattr(self,'engines_menu'):
            self._rebuild_engine_menu()
        if select_name:
            self.show_engine_panel()
            self._update_video_analysis_title()
    def _rebuild_engine_menu(self):
        menu=self.engines_menu;menu.delete(0,'end')
        for name in self.ENGINE_NAMES:
            menu.add_command(label=self.T(f'Usar {name} en partida/análisis','Select {name} for play/analysis').format(name=name),
                             command=lambda n=name:self.select_engine(n))
            menu.add_command(label=self.T(f'Elegir archivo de {name}…','Choose {name} executable…').format(name=name),
                             command=lambda n=name:self.choose(n))
        menu.add_separator()
        menu.add_command(label=self.T('Agregar motor UCI…','Add UCI Engine…'),command=self.add_uci_engine)
        menu.add_separator()
        menu.add_command(label=self.T('Enfrentar dos motores…','Match two engines…'),command=self.engine_match_dialog,accelerator='Ctrl+M')
    def select_engine(self,name):
        if name not in self.ENGINE_NAMES:return
        self.play_engine.set(name);self.engine_view.set(name)
        self.show_engine_panel()
        self._update_video_analysis_title()
        self.status.set(self.T(f'{name} seleccionado. Pulsa Analizar o inicia una partida.',f'{name} selected. Press Analyze or start a game.'))
    def __init__(self, window):
        self.w=window; window.title('RoboChess · Nibbler chess study'); window.geometry('1540x960'); window.minsize(1180,760)
        self.board=chess.Board(); self.events=queue.Queue(); self.epoch=0; self.engines={}; self.selected=None; self.results={}
        self.custom_engines=self._read_custom_engines()
        self.paths={'Stockfish':'','Crafty':os.path.join(ROOT,'crafty-linux' if platform.system()=='Linux' else 'crafty.exe'),
                    'RoboChess':next((p for p in (os.path.join(ROOT,'robbochess','RoboChess-x64.exe'),os.path.join(ROOT,'robbochess','RoboChess.exe')) if os.path.isfile(p)),'')}
        self.paths.update({name:record['path'] for name,record in self.custom_engines.items()})
        self.images={}; self.square=70;self.flipped=False;self.playing=False;self.play_busy=False;self._fitting_board=False
        self.play_events=queue.Queue();self.human_color=chess.WHITE;self.game_engine_name='Stockfish'
        self.personality=None;self.personality_launch=False;self.personality_images={}
        self.coach_events=queue.Queue();self.coach_generation=0;self.feedback_pending=False
        self.coach_enabled=tk.BooleanVar(value=False);self.coach_images={}
        self.profile_data=profile_store.load();self.profile=profile_store.find(self.profile_data,self.profile_data.get('active'))
        self.language=tk.StringVar(value='English');self.final_result=None;self.draw_events=queue.Queue();self.draw_offer_pending=False
        self.piece_style=tk.StringVar(value='Nibbler');self.last_2d_style='Nibbler';self.last_3d_style='Staunton 3D';self.board_view=tk.StringVar(value='2D')
        self.board_colors=board_settings.load()
        self.light_square=self.board_colors['light'];self.dark_square=self.board_colors['dark']
        initial_palette=next((name for name,colors in self.BOARD_PALETTES.items() if colors==(self.light_square,self.dark_square)),'Personalizar / Custom')
        self.board_palette=tk.StringVar(value=initial_palette)
        self.book_path=training_resources.BOOK
        self.book_paths={str(p.relative_to(training_resources.BOOKS)):p for p in training_resources.book_files()}
        self.book_choice=tk.StringVar(value=next((k for k,v in self.book_paths.items() if v==self.book_path),'GMopenings.bin'))
        self.training_sets=training_resources.training_sets();self.training_choice=tk.StringVar(value='All Lucas Chess exercises')
        self.external_training=None;self.puzzle_moves=[];self.puzzle_index=0;self.puzzle_color=None
        self.puzzle_mistakes=0;self.puzzle_failed=False;self.puzzle_banner='';self.puzzle_undo_token=0
        self.puzzle_category=tk.StringVar(value=next(iter(lichess_puzzles.PUZZLE_CATEGORIES)))
        self.puzzle_theme_choice=tk.StringVar(value=lichess_puzzles.PUZZLE_CATEGORIES[self.puzzle_category.get()][0][0])
        self.rush_categories=puzzle_rush.available_categories(self.training_sets)
        self.rush_category=tk.StringVar(value='all')
        self.rush_stats=puzzle_rush.load_stats();self.rush_session=None;self.rush_window=None
        self.rush_text=tk.StringVar(value='');self.rush_seen=set()
        self.lichess_puzzle_file=tk.StringVar(value='');self.lichess_puzzle_events=queue.Queue();self.lichess_puzzle_token=0;self.puzzle_meta=None
        self.gaviota_path=training_resources.GAVIOTA;self.puzzle_active=False;self.challenge_best=None;self.challenge_events=queue.Queue()
        self.play_engine=tk.StringVar(value='Stockfish');self.play_color=tk.StringVar(value='White')
        self.target_elo=tk.StringVar(value='1500');self.move_seconds=tk.StringVar(value='5')
        self.time_control=tk.StringVar(value='No clock / Sin reloj (5 s/move)')
        self.clock_label=tk.StringVar(value='Reloj: —')
        self.clock_remaining={chess.WHITE:0.0,chess.BLACK:0.0};self.clock_mode=self.TIME_CONTROLS[self.time_control.get()]
        self.clock_running=None;self.clock_started=None;self.clock_after=None
        self.quad=None;self.quad_window=None;self.quad_summary=None;self.quad_round_button=None;self.quad_launch=False
        self.engine_match_events=queue.Queue();self.engine_match_token=0;self.engine_match_stop=None;self.engine_match_thread=None
        self.engine_match_window=None;self.engine_match_games=[];self.engine_match_running=False
        self.dgt_events=queue.Queue();self.dgt_link=None;self.dgt_port=''
        self.editor_mode=False;self.editor_piece=None;self.editor_saved_board=None;self.editor_choice=tk.StringVar(value='K')
        self.pdf_diagram_pending=False;self.pdf_diagram_photo=None;self.pdf_diagram_window=None
        self.lichess_events=queue.Queue();self.lichess_games=[];self.database_games=[];self.lichess_username=tk.StringVar();self.database_label=tk.StringVar(value='Sin base PGN cargada / No PGN database loaded')
        self.live_events=queue.Queue();self.live_token=0;self.live_round_id=None;self.live_source_kind='round';self.live_stop_event=None
        self.live_games=[];self.live_follow_key=None;self.live_follow_plies=-1;self.live_follow_result='*';self.live_dialog=None;self.live_tree=None
        self.live_url=tk.StringVar(value='');self.live_status=tk.StringVar(value='');self.live_auto_analyze=tk.BooleanVar(value=False)
        self.review_game=None;self.review_ply=0;self.review_label=tk.StringVar(value='—')
        self.engine_view=tk.StringVar(value='Stockfish');self.side_to_move=tk.StringVar(value='White')
        self.show_stockfish=tk.BooleanVar(value=True);self.show_crafty=tk.BooleanVar(value=True);self.show_robochess=tk.BooleanVar(value=True)
        # Custom UCI engines (including Sargon) get their own arrow toggle.
        self.show_engine_arrows={name:tk.BooleanVar(value=True) for name in self.ENGINE_NAMES[3:]}
        self.make_menu()
        self.bind_keyboard_shortcuts()
        top=ttk.Frame(window,padding=(8,4));top.pack(fill='x')
        self.study_button=ttk.Button(top,text=self.T('Estudio','Study'),command=self.show_study_view);self.study_button.pack(side='left',padx=3)
        self.resources_button=ttk.Button(top,text=self.T('Recursos','Resources'),command=self.show_tools_view);self.resources_button.pack(side='left',padx=3)
        self.seconds=tk.StringVar(value='3')
        self.seconds_label=ttk.Label(top,text=self.T('Segundos por motor:','Seconds / engine:'));self.seconds_label.pack(side='left',padx=(15,3))
        ttk.Spinbox(top,from_=1,to=120,width=5,textvariable=self.seconds).pack(side='left')
        ttk.Label(top,textvariable=self.clock_label,font=('Arial',11,'bold')).pack(side='right',padx=8)
        self._hidden=ttk.Frame(window)
        self.engine_selector=ttk.Combobox(self._hidden,textvariable=self.play_engine,values=self.ENGINE_NAMES,state='readonly',width=11)
        self.engine_selector.bind('<<ComboboxSelected>>',self.preview_opponent)
        self.move_seconds_control=ttk.Spinbox(self._hidden,from_=1,to=60,textvariable=self.move_seconds,width=4)
        self.clock_selector=ttk.Combobox(self._hidden,textvariable=self.time_control,values=tuple(self.TIME_CONTROLS),state='readonly',width=50)
        self.clock_selector.bind('<<ComboboxSelected>>',self.time_control_changed)
        self.fen=tk.StringVar(value=self.board.fen())
        self.editor_palette=ttk.LabelFrame(window,text='Paleta · selecciona pieza y pulsa casilla / Piece palette · choose a piece, then click a square',padding=4)
        self.make_editor_palette()
        self.play_actions=ttk.Frame(window,padding=(8,2))
        ttk.Button(self.play_actions,text='Retirar jugada / Takeback',command=self.takeback).pack(side='left',padx=4)
        ttk.Button(self.play_actions,text='Ofrecer tablas / Offer draw',command=self.offer_draw).pack(side='left',padx=4)
        ttk.Button(self.play_actions,text='Rendirse / Resign',command=self.resign).pack(side='left',padx=4)
        ttk.Button(self.play_actions,text='Terminar / End game',command=self.end_game).pack(side='left',padx=8)
        self.status=tk.StringVar(value='Select engine executables, then Analyze. Click two squares to play a move.')
        root_pane=ttk.Panedwindow(window,orient='vertical');self.root_pane=root_pane;root_pane.pack(fill='both',expand=True,padx=8,pady=6)
        body=ttk.Panedwindow(root_pane,orient='horizontal');root_pane.add(body,weight=6)
        board_frame=ttk.Frame(body,padding=(2,4));self.board_frame=board_frame;body.add(board_frame,weight=0)
        self.evalbar=tk.Canvas(board_frame,width=36,height=560,highlightthickness=0,bg='#d9d9d9');self.evalbar.pack(side='left',anchor='n',padx=(0,6))
        self.canvas=tk.Canvas(board_frame,width=560,height=560,highlightthickness=0);self.canvas.pack(side='left',anchor='n')
        board_frame.bind('<Configure>',self._fit_board)
        side=ttk.Frame(body,padding=(8,2));body.add(side,weight=1)
        self.study_view=ttk.Frame(side);self.study_view.pack(fill='both',expand=True)
        self.video_view=ttk.Panedwindow(side,orient='vertical')
        self.lichess_video=LichessVideo(
            self.video_view,language=self.language.get(),
            analyze_callback=self.analyze,engine_var=self.engine_view,
            engine_names=self.ENGINE_NAMES,engine_callback=self.select_engine,
            close_callback=self.show_study_view,
        )
        self.video_view.add(self.lichess_video.frame,weight=4)
        self.video_analysis_frame=ttk.LabelFrame(self.video_view,text='',padding=4)
        self.video_analysis=tk.Text(self.video_analysis_frame,height=7,wrap='word',state='disabled',font=('Consolas',10))
        self.video_analysis.pack(fill='both',expand=True)
        self.video_view.add(self.video_analysis_frame,weight=1)
        self._update_video_analysis_title()
        self.video_view.pack_forget()
        self.pdf_view=ttk.Panedwindow(side,orient='vertical')
        self.pdf_reader=PDFBookReader(
            self.pdf_view,language_getter=lambda:self.language.get(),
            engine_var=self.engine_view,engine_names=self.ENGINE_NAMES,
            engine_callback=self.select_engine,
            analyze_callback=lambda name:self.analyze(selected_only=True,engine_name=name),
            apply_line_callback=self.apply_pdf_line,
            edit_position_callback=self.start_position_editor,
            diagram_callback=self.preview_pdf_diagram,
            save_pgn_callback=self.save_pdf_line_pgn,
            close_callback=self.show_study_view,
        )
        self.pdf_view.add(self.pdf_reader,weight=4)
        self.pdf_analysis_frame=ttk.LabelFrame(self.pdf_view,text='',padding=4)
        self.pdf_analysis=tk.Text(self.pdf_analysis_frame,height=7,wrap='word',state='disabled',font=('Consolas',10))
        self.pdf_analysis.pack(fill='both',expand=True)
        self.pdf_view.add(self.pdf_analysis_frame,weight=1)
        self.pdf_view.pack_forget()
        self._update_video_analysis_title()
        ttk.Label(self.study_view,textvariable=self.status,wraplength=560).pack(fill='x',pady=(0,5))
        self.move_frame=ttk.LabelFrame(self.study_view,text='Jugadas · notación algebraica / Moves · algebraic notation',padding=4);self.move_frame.pack(fill='both',expand=True,pady=(0,5))
        self.move_text=tk.Text(self.move_frame,height=5,wrap='word',state='disabled',font=('Consolas',10));self.move_text.pack(fill='both',expand=True)
        review_bar=ttk.Frame(self.move_frame);review_bar.pack(fill='x',pady=(3,0))
        for text,delta in [('|◀',-99999),('◀',-1),('▶',1),('▶|',99999)]:ttk.Button(review_bar,text=text,width=4,command=lambda d=delta:self.review_step(d)).pack(side='left',padx=2)
        ttk.Label(review_bar,textvariable=self.review_label).pack(side='left',padx=5)
        self.opening_frame=ttk.LabelFrame(self.study_view,text='Libro de aperturas / Opening book',padding=4);self.opening_frame.pack(fill='both',expand=True,pady=5)
        cols=('move','weight','share');self.opening_tree=ttk.Treeview(self.opening_frame,columns=cols,show='headings',height=5)
        for key,title,width in [('move','Jugada / Move',150),('weight','Frecuencia / Weight',150),('share','Porcentaje / Share',110)]:self.opening_tree.heading(key,text=title);self.opening_tree.column(key,width=width,anchor='center')
        self.opening_tree.pack(fill='both',expand=True)
        ttk.Button(self.opening_frame,text='Actualizar libro / Refresh book',command=self.show_book).pack(anchor='e',pady=(3,0))
        engine_frame=ttk.LabelFrame(self.study_view,text='Análisis del motor / Engine analysis',padding=4);engine_frame.pack(fill='both',expand=True,pady=(5,0))
        engine_header=ttk.Frame(engine_frame);engine_header.pack(fill='x')
        ttk.Label(engine_header,text='Motor / Engine:').pack(side='left')
        self.engine_view_selector=ttk.Combobox(engine_header,textvariable=self.engine_view,values=self.ENGINE_NAMES,state='readonly',width=14)
        self.engine_view_selector.pack(side='left',padx=4);self.engine_view_selector.bind('<<ComboboxSelected>>',self.show_engine_panel)
        self.engine_panel_holder=ttk.Frame(engine_frame);self.engine_panel_holder.pack(fill='both',expand=True)
        self.panels={}
        for name in self.ENGINE_NAMES:
            box=tk.Text(self.engine_panel_holder,height=8,width=55,wrap='word',state='disabled');self.panels[name]=box
        self.panels[self.engine_view.get()].pack(fill='both',expand=True)
        self.tactics=tk.Text(engine_frame,height=4,wrap='word',state='disabled');self.tactics.pack(fill='x',pady=(3,0))
        bottom=ttk.Panedwindow(root_pane,orient='horizontal');root_pane.add(bottom,weight=1)
        db_frame=ttk.LabelFrame(bottom,text='Base de partidas PGN / PGN game database',padding=5);bottom.add(db_frame,weight=1)
        dbbar=ttk.Frame(db_frame);dbbar.pack(fill='x')
        ttk.Button(dbbar,text='Abrir base PGN / Open PGN database',command=self.open_pgn_database).pack(side='left')
        ttk.Label(dbbar,textvariable=self.database_label).pack(side='left',padx=8)
        dbcols=('number','white','black','result','event','date');self.database_tree=ttk.Treeview(db_frame,columns=dbcols,show='headings',height=4)
        for key,title,width in [('number','#',40),('white','Blancas / White',130),('black','Negras / Black',130),('result','Resultado / Result',80),('event','Evento / Event',180),('date','Fecha / Date',90)]:self.database_tree.heading(key,text=title);self.database_tree.column(key,width=width,anchor='w')
        self.database_tree.pack(fill='both',expand=True);self.database_tree.bind('<Double-1>',self.open_database_game)
        lich_frame=ttk.LabelFrame(bottom,text='Partidas de Lichess / Lichess games',padding=5);bottom.add(lich_frame,weight=1)
        lichbar=ttk.Frame(lich_frame);lichbar.pack(fill='x')
        ttk.Label(lichbar,text='Usuario público / Public username:').pack(side='left')
        ttk.Entry(lichbar,textvariable=self.lichess_username,width=18).pack(side='left',padx=4)
        ttk.Button(lichbar,text='Cargar partidas / Fetch games',command=self.fetch_lichess_games).pack(side='left')
        ttk.Button(lichbar,text='Partidas en vivo / Live games',command=self.open_live_broadcast_dialog).pack(side='left',padx=(4,0))
        lichcols=('date','white','black','result','opening','speed');self.lichess_tree=ttk.Treeview(lich_frame,columns=lichcols,show='headings',height=4)
        for key,title,width in [('date','Fecha / Date',95),('white','Blancas / White',120),('black','Negras / Black',120),('result','Resultado / Result',80),('opening','Apertura / Opening',200),('speed','Ritmo / Speed',85)]:self.lichess_tree.heading(key,text=title);self.lichess_tree.column(key,width=width,anchor='w')
        self.lichess_tree.pack(fill='both',expand=True);self.lichess_tree.bind('<Double-1>',self.open_lichess_game)
        ttk.Label(lich_frame,text='Doble clic para cargar y revisar la partida completa / Double-click a game to review it').pack(anchor='w')
        tabs=ttk.Notebook(side);self.tabs=tabs
        # Keep the existing tutor and resource panels available from a compact drawer tab bar.
        tabs.pack_forget()
        self.tutor_tab=ttk.Frame(tabs,padding=7);resources_tab=ttk.Frame(tabs,padding=8);self.resources_tab=resources_tab
        tabs.add(self.tutor_tab,text='Tutor y personajes');tabs.add(resources_tab,text='Recursos y ejercicios')
        # The tutor/resources tabs are opened from the View menu to keep the study layout uncluttered.
        header=ttk.Frame(self.tutor_tab);header.pack(fill='x')
        self.coach_images['Einstein']=self.portrait('coach_einstein.png',104)
        self.coach_images['Crafty_happy']=self.portrait('coach_dino_happy.png',105)
        self.coach_images['Crafty_worried']=self.portrait('coach_dino_worried.png',105)
        self.coach_images['Stockfish_happy']=self.portrait('coach_fish_happy.png',105)
        self.coach_images['Stockfish_worried']=self.portrait('coach_fish_worried.png',105)
        self.coach_images['Crafty']=self.portrait('coach_dino.png',105)
        self.coach_images['Stockfish']=self.portrait('coach_fish.png',105)
        self.coach_images['RoboChess']=self.portrait('coach_robochess.png',112)
        ttk.Label(header,image=self.coach_images['Einstein']).pack(side='left',padx=(0,10))
        ttk.Label(header,text='Tutor de ajedrez\nPistas basadas en el motor',font=('Arial',12,'bold')).pack(side='left')
        self.opponent_frame=ttk.LabelFrame(self.tutor_tab,text='Tu rival',padding=6);self.opponent_frame.pack(fill='x',pady=(10,4))
        self.opponent_image=ttk.Label(self.opponent_frame,image=self.coach_images['Stockfish']);self.opponent_image.pack(side='left',padx=(0,9))
        self.mood=tk.StringVar(value='Stockfish: 😐 pensando')
        ttk.Label(self.opponent_frame,textvariable=self.mood,wraplength=270,font=('Arial',10,'bold')).pack(side='left',fill='x',expand=True)
        row=ttk.Frame(self.tutor_tab);row.pack(fill='x',pady=7)
        ttk.Checkbutton(row,text='Activar tutor automático',variable=self.coach_enabled,command=self.coach_toggle).pack(side='left')
        ttk.Button(row,text='Pista',command=lambda:self.request_coach('hint')).pack(side='left',padx=4)
        ttk.Button(row,text='Explicar',command=lambda:self.request_coach('explain')).pack(side='left')
        self.coach_text=tk.Text(self.tutor_tab,height=15,width=54,wrap='word',state='disabled');self.coach_text.pack(fill='both',expand=True)
        self.put(self.coach_text,'Activa el tutor para recibir comentarios después de tus jugadas. Pulsa Pista antes de mover o Explicar para estudiar la posición.')
        lich_puzzles=ttk.LabelFrame(resources_tab,text='Puzzles de Lichess / Lichess puzzles',padding=6);lich_puzzles.pack(fill='x',pady=(0,8))
        theme_row=ttk.Frame(lich_puzzles);theme_row.pack(fill='x')
        ttk.Label(theme_row,text='Categoría / Category:').pack(side='left')
        self.puzzle_category_box=ttk.Combobox(theme_row,textvariable=self.puzzle_category,values=tuple(lichess_puzzles.PUZZLE_CATEGORIES),state='readonly',width=25)
        self.puzzle_category_box.pack(side='left',padx=4);self.puzzle_category_box.bind('<<ComboboxSelected>>',self.puzzle_category_changed)
        ttk.Label(theme_row,text='Tema / Theme:').pack(side='left',padx=(6,2))
        self.puzzle_theme_box=ttk.Combobox(theme_row,textvariable=self.puzzle_theme_choice,values=tuple(label for label,tag in lichess_puzzles.PUZZLE_CATEGORIES[self.puzzle_category.get()]),state='readonly',width=34)
        self.puzzle_theme_box.pack(side='left',padx=4)
        file_row=ttk.Frame(lich_puzzles);file_row.pack(fill='x',pady=(4,0))
        ttk.Button(file_row,text='Elegir archivo CSV Lichess / Choose puzzle CSV',command=self.choose_lichess_puzzle_file).pack(side='left')
        ttk.Label(file_row,textvariable=self.lichess_puzzle_file).pack(side='left',padx=5)
        ttk.Button(file_row,text='Descargar / Download',command=lambda:webbrowser.open('https://database.lichess.org/#puzzles')).pack(side='right',padx=3)
        ttk.Button(file_row,text='Siguiente puzzle / Next Lichess puzzle',command=self.next_lichess_puzzle).pack(side='right',padx=3)
        self.lichess_puzzle_status=tk.StringVar(value='La colección oficial se descarga aparte; puedes elegir .csv, .csv.zst o .csv.gz.')
        ttk.Label(lich_puzzles,textvariable=self.lichess_puzzle_status,wraplength=820).pack(anchor='w',pady=(4,0))
        ttk.Label(resources_tab,text='Piezas / Pieces').pack(anchor='w')
        viewrow=ttk.Frame(resources_tab);viewrow.pack(anchor='w',fill='x',pady=4)
        ttk.Label(viewrow,text='Vista 2D / 3D · Board view:').pack(side='left')
        self.view_selector=ttk.Combobox(viewrow,textvariable=self.board_view,values=('2D','3D'),state='readonly',width=7)
        self.view_selector.pack(side='left',padx=(6,12));self.view_selector.bind('<<ComboboxSelected>>',self.set_board_view)
        styles=self._piece_style_names()
        self.style_selector=ttk.Combobox(resources_tab,textvariable=self.piece_style,values=styles,state='readonly',width=30)
        self.style_selector.pack(anchor='w',pady=4);self.style_selector.bind('<<ComboboxSelected>>',self.change_pieces)
        ttk.Label(resources_tab,text='Colores del tablero / Board colors').pack(anchor='w',pady=(5,1))
        colorrow=ttk.Frame(resources_tab);colorrow.pack(anchor='w',fill='x',pady=(0,3))
        palettes=ttk.Combobox(colorrow,textvariable=self.board_palette,values=(*self.BOARD_PALETTES,'Personalizar / Custom'),state='readonly',width=30)
        palettes.pack(side='left',padx=(0,8));palettes.bind('<<ComboboxSelected>>',self.select_board_palette)
        ttk.Label(colorrow,text='Clara / Light').pack(side='left')
        self.light_color_button=tk.Button(colorrow,text='   ',width=3,relief='solid',bd=1,bg=self.light_square,command=lambda:self.choose_board_color('light'))
        self.light_color_button.pack(side='left',padx=(3,8))
        ttk.Label(colorrow,text='Oscura / Dark').pack(side='left')
        self.dark_color_button=tk.Button(colorrow,text='   ',width=3,relief='solid',bd=1,bg=self.dark_square,command=lambda:self.choose_board_color('dark'))
        self.dark_color_button.pack(side='left',padx=3)
        ttk.Label(resources_tab,text='Libro de aperturas Lucas Chess / Lucas Chess opening books').pack(anchor='w',pady=(8,2))
        books=ttk.Combobox(resources_tab,textvariable=self.book_choice,values=tuple(self.book_paths),state='readonly',width=55)
        books.pack(anchor='w');books.bind('<<ComboboxSelected>>',self.book_selected)
        ttk.Button(resources_tab,text='Consultar libro / Show book moves',command=self.show_book).pack(anchor='w',pady=3)
        ttk.Button(resources_tab,text='Elegir libro Polyglot externo / Choose external book',command=self.choose_book).pack(anchor='w')
        ttk.Button(resources_tab,text='Consultar final Gaviota / Probe endgame',command=self.show_ending).pack(anchor='w',pady=(12,3))
        ttk.Button(resources_tab,text='Elegir carpeta Gaviota / Choose folder',command=self.choose_gaviota).pack(anchor='w')
        ttk.Label(resources_tab,text='Colección de ejercicios / Training collection').pack(anchor='w',pady=(12,2))
        trainings=ttk.Combobox(resources_tab,textvariable=self.training_choice,values=tuple(self.training_sets),state='readonly',width=55)
        trainings.pack(anchor='w');trainings.bind('<<ComboboxSelected>>',self.training_selected)
        ttk.Button(resources_tab,text='Siguiente ejercicio / Next exercise',command=self.new_puzzle).pack(anchor='w',pady=3)
        ttk.Button(resources_tab,text='Abrir otra colección .fns / Open another .fns collection',command=self.choose_training).pack(anchor='w')
        ttk.Button(resources_tab,text='Encontrar la mejor jugada / Find best move',command=self.best_move_challenge).pack(anchor='w')
        self.resource_text=tk.Text(resources_tab,height=13,width=52,wrap='word',state='disabled');self.resource_text.pack(fill='both',expand=True,pady=8)
        self.put(self.resource_text,'Lucas Chess R2: tres estilos de piezas, libro de grandes maestros, finales de hasta tres piezas y ejercicios de mate en uno.')
        self.canvas.bind('<Button-1>',self.click)
        self.w.protocol('WM_DELETE_WINDOW',self.close)
        self.draw();self.set_language();self.w.after(100,self.poll)
        if self.profile:self.status.set(self.T(f"Perfil: {self.profile['name']}. Menú Perfil o Entrenamiento para continuar.",f"Profile: {self.profile['name']}. Use Profile or Training menus."))
    def T(self,spanish,english):return choose(self.language.get(),spanish,english)
    def make_menu(self):
        old=getattr(self,'menu_bar',None)
        bar=tk.Menu(self.w);self.menu_bar=bar;self.w.configure(menu=bar)
        filemenu=tk.Menu(bar,tearoff=0);bar.add_cascade(label=self.T('Archivo','File'),menu=filemenu)
        filemenu.add_command(label=self.T('Abrir partida PGN…','Open PGN game…'),command=self.load_pgn,accelerator='Ctrl+O')
        filemenu.add_command(label=self.T('Abrir libro de ajedrez PDF…','Open chess book PDF…'),command=self.open_pdf_book,accelerator='Ctrl+Shift+B')
        filemenu.add_command(label=self.T('Importar base de partidas PGN…','Import PGN game database…'),command=self.open_pgn_database)
        filemenu.add_command(label=self.T('Guardar partida…','Save game…'),command=self.save_game)
        filemenu.add_command(label=self.T('Guardar análisis en PGN…','Save analysis as PGN…'),command=self.save_pgn,accelerator='Ctrl+S')
        filemenu.add_command(label=self.T('Guardar análisis en TXT…','Save analysis as TXT…'),command=self.save_txt)
        filemenu.add_separator();filemenu.add_command(label=self.T('Perfil y progreso…','Profile and progress…'),command=self.profile_dialog)
        filemenu.add_command(label=self.T('Configuración…','Settings…'),command=self.settings_dialog)
        filemenu.add_separator();filemenu.add_command(label=self.T('Salir','Exit'),command=self.close,accelerator='Ctrl+Q')
        edit=tk.Menu(bar,tearoff=0);bar.add_cascade(label=self.T('Editar','Edit'),menu=edit)
        edit.add_command(label=self.T('Editar posición…','Edit position…'),command=self.start_position_editor)
        edit.add_command(label=self.T('Pegar o fijar FEN…','Paste or set FEN…'),command=self.fen_dialog)
        edit.add_command(label=self.T('Deshacer jugada','Undo move'),command=self.undo,accelerator='Ctrl+Z')
        edit.add_command(label=self.T('Reiniciar tablero','Reset board'),command=self.reset,accelerator='Ctrl+R')
        game=tk.Menu(bar,tearoff=0);bar.add_cascade(label=self.T('Partida','Game'),menu=game)
        game.add_command(label=self.T('Configurar partida…','Game setup…'),command=self.game_setup_dialog)
        game.add_command(label=self.T('Personalidades…','Personalities…'),command=self.personalities_dialog)
        game.add_command(label=self.T('Nueva partida','New game'),command=self.start_game)
        game.add_command(label=self.T('Terminar partida','End game'),command=self.end_game)
        game.add_separator()
        game.add_command(label=self.T('Retirar jugada','Takeback'),command=self.takeback)
        game.add_command(label=self.T('Ofrecer tablas','Offer draw'),command=self.offer_draw)
        game.add_command(label=self.T('Rendirse','Resign'),command=self.resign)
        view=tk.Menu(bar,tearoff=0);bar.add_cascade(label=self.T('Vista','View'),menu=view)
        view.add_command(label=self.T('Girar tablero','Flip board'),command=self.flip_board,accelerator='Ctrl+F')
        view.add_command(label=self.T('Estudio','Study'),command=self.show_study_view)
        view.add_command(label=self.T('Recursos','Resources'),command=self.show_tools_view)
        view.add_command(label=self.T('Biblioteca de videos de Lichess…','Lichess Video Library…'),command=self.show_lichess_video,accelerator='Ctrl+Shift+L')
        view.add_command(label=self.T('Leer libro PDF…','Read PDF chess book…'),command=self.open_pdf_book,accelerator='Ctrl+Shift+B')
        view.add_command(label=self.T('Analizar posición','Analyze position'),command=self.analyze,accelerator='Ctrl+A')
        view.add_separator()
        view.add_checkbutton(label=self.T('Flechas de Stockfish','Stockfish arrows'),variable=self.show_stockfish,command=self.draw)
        view.add_checkbutton(label=self.T('Flecha de Crafty','Crafty arrow'),variable=self.show_crafty,command=self.draw)
        view.add_checkbutton(label=self.T('Flecha de RoboChess','RoboChess arrow'),variable=self.show_robochess,command=self.draw)
        for name in self.ENGINE_NAMES[3:]:
            arrow_var=self.show_engine_arrows.setdefault(name,tk.BooleanVar(value=True))
            view.add_checkbutton(label=self.T(f'Flecha de {name}',f'{name} arrow'),variable=arrow_var,command=self.draw)
        langmenu=tk.Menu(view,tearoff=0)
        langmenu.add_radiobutton(label='English',variable=self.language,value='English',command=self.set_language)
        langmenu.add_radiobutton(label='Español',variable=self.language,value='Español',command=self.set_language)
        view.add_cascade(label=self.T('Idioma','Language'),menu=langmenu)
        engines=tk.Menu(bar,tearoff=0);bar.add_cascade(label=self.T('Motores','Engines'),menu=engines);self.engines_menu=engines
        self._rebuild_engine_menu()
        tournament=tk.Menu(bar,tearoff=0);bar.add_cascade(label=self.T('Torneo','Tournament'),menu=tournament)
        tournament.add_command(label=self.T('Nuevo torneo de entrenamiento…','New training tournament…'),command=self.quad_dialog)
        tournament.add_command(label=self.T('Panel del torneo','Tournament panel'),command=self.quad_dialog)
        tournament.add_command(label=self.T('Revisar partidas del torneo…','Review tournament games…'),command=self.show_tournament_review)
        training=tk.Menu(bar,tearoff=0);bar.add_cascade(label=self.T('Entrenamiento','Training'),menu=training)
        training.add_command(label=self.T('Puzzles y ejercicios Lucas Chess…','Lucas Chess puzzles and exercises…'),command=self.training_dialog,accelerator='Ctrl+Shift+T')
        training.add_command(label=self.T('Puzzle Rush…','Puzzle Rush…'),command=self.puzzle_rush_dialog,accelerator='Ctrl+Shift+R')
        training.add_command(label=self.T('Siguiente ejercicio Lucas Chess','Next Lucas Chess exercise'),command=self.new_puzzle)
        training.add_command(label=self.T('Encontrar la mejor jugada','Find the best move'),command=self.best_move_challenge)
        profilemenu=tk.Menu(bar,tearoff=0);bar.add_cascade(label=self.T('Perfil','Profile'),menu=profilemenu)
        profilemenu.add_command(label=self.T('Ver o editar perfiles…','View or edit profiles…'),command=self.profile_dialog,accelerator='Ctrl+Shift+P')
        profilemenu.add_command(label=self.T('Crear perfil nuevo…','Create new profile…'),command=lambda:self.profile_dialog(create=True))
        settings=tk.Menu(bar,tearoff=0);bar.add_cascade(label=self.T('Configuración','Settings'),menu=settings)
        settings.add_command(label=self.T('Piezas, tablero y perspectiva…','Pieces, board and view…'),command=self.settings_dialog)
        settings.add_command(label=self.T('Configurar partida…','Game setup…'),command=self.game_setup_dialog)
        helpmenu=tk.Menu(bar,tearoff=0);bar.add_cascade(label=self.T('Ayuda','Help'),menu=helpmenu)
        helpmenu.add_command(label=self.T('Atajos de teclado…','Keyboard Shortcuts…'),command=self.keyboard_shortcuts_dialog)
        boardmenu=tk.Menu(bar,tearoff=0);bar.add_cascade(label=self.T('Tablero DGT','DGT Board'),menu=boardmenu)
        boardmenu.add_command(label=self.T('Conectar tablero DGT…','Connect DGT board…'),command=self.connect_dgt)
        boardmenu.add_command(label=self.T('Desconectar tablero DGT','Disconnect DGT board'),command=self.disconnect_dgt)
        if old:
            try:old.destroy()
            except tk.TclError:pass
    def bind_keyboard_shortcuts(self):
        bindings=(
            ('<Control-o>',self.load_pgn),('<Control-s>',self.save_pgn),
            ('<Control-Shift-p>',self.profile_dialog),('<Control-Shift-t>',self.training_dialog),
            ('<Control-Shift-r>',self.puzzle_rush_dialog),
            ('<Control-Shift-l>',self.show_lichess_video),
            ('<Control-Shift-b>',self.open_pdf_book),
            ('<Control-z>',self.undo),('<Control-r>',self.reset),('<Control-f>',self.flip_board),
            ('<Control-a>',self.analyze),('<Control-m>',self.engine_match_dialog),('<Control-q>',self.close),
        )
        for sequence,action in bindings:
            self.w.bind_all(sequence,lambda event,callback=action:(callback(),'break')[1])
    def keyboard_shortcuts_dialog(self):
        title=self.T('Atajos de teclado','Keyboard Shortcuts')
        rows=(
            ('Abrir partida PGN','Open PGN game','Ctrl+O'),
            ('Guardar análisis PGN','Save analysis PGN','Ctrl+S'),
            ('Perfiles','Profiles','Ctrl+Shift+P'),
            ('Puzzles y ejercicios','Puzzles and exercises','Ctrl+Shift+T'),
            ('Puzzle Rush','Puzzle Rush','Ctrl+Shift+R'),
            ('Biblioteca de videos de Lichess','Lichess Video Library','Ctrl+Shift+L'),
            ('Abrir libro de ajedrez PDF','Open chess book PDF','Ctrl+Shift+B'),
            ('Deshacer jugada','Undo move','Ctrl+Z'),('Reiniciar tablero','Reset board','Ctrl+R'),
            ('Girar tablero','Flip board','Ctrl+F'),('Analizar posición','Analyze position','Ctrl+A'),
            ('Engine Match','Engine Match','Ctrl+M'),('Salir','Exit','Ctrl+Q'),
        )
        lines=[f'{self.T(es,en):<31} {key}' for es,en,key in rows]
        messagebox.showinfo(title,'\n'.join(lines),parent=self.w)
    def _fit_board(self,event=None):
        if self._fitting_board or not hasattr(self,'board_frame'):return
        raw_h=self.board_frame.winfo_height();raw_w=self.board_frame.winfo_width()
        if raw_h<200 or raw_w<200:return
        avail_h=max(280,raw_h-8)
        avail_w=max(280,raw_w-48)
        square=max(32,min(78,(min(avail_h,avail_w)//8)))
        if square==self.square:return
        self._fitting_board=True
        try:
            self.square=square;self.images.clear()
            size=square*8
            self.canvas.configure(width=size,height=size)
            self.evalbar.configure(height=size)
            self.draw()
        finally:
            self._fitting_board=False
    def _sync_play_chrome(self):
        if self.playing:
            if not self.play_actions.winfo_ismapped():
                self.play_actions.pack(fill='x',before=self.root_pane)
        else:
            self.play_actions.pack_forget()
    def game_setup_dialog(self):
        win=tk.Toplevel(self.w);win.title(self.T('Configurar partida','Game setup'));win.transient(self.w);win.resizable(False,False)
        frame=ttk.Frame(win,padding=14);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text=self.T('Estas opciones estaban en las barras duplicadas. Ahora viven aquí y en Partida / Game.','These controls left the stacked toolbars. They now live here and under Game.')).pack(anchor='w',pady=(0,8))
        row=ttk.Frame(frame);row.pack(fill='x',pady=3)
        ttk.Label(row,text=self.T('Jugar contra','Play against'),width=22).pack(side='left')
        box=ttk.Combobox(row,textvariable=self.play_engine,values=self.ENGINE_NAMES,state='readonly',width=16)
        box.pack(side='left');box.bind('<<ComboboxSelected>>',self.preview_opponent)
        row=ttk.Frame(frame);row.pack(fill='x',pady=3)
        ttk.Label(row,text=self.T('Tu color','Your color'),width=22).pack(side='left')
        ttk.Combobox(row,textvariable=self.play_color,values=('White','Black'),state='readonly',width=16).pack(side='left')
        row=ttk.Frame(frame);row.pack(fill='x',pady=3)
        ttk.Label(row,text=self.T('Nivel Elo del motor (1–3800)','Engine Elo level (1–3800)'),width=22).pack(side='left')
        ttk.Spinbox(row,from_=1,to=3800,textvariable=self.target_elo,width=8).pack(side='left')
        row=ttk.Frame(frame);row.pack(fill='x',pady=3)
        ttk.Label(row,text=self.T('Ritmo / Time control', 'Time control'),width=22).pack(side='left')
        ttk.Combobox(row,textvariable=self.time_control,values=tuple(self.TIME_CONTROLS),state='readonly',width=52).pack(side='left')
        row=ttk.Frame(frame);row.pack(fill='x',pady=3)
        ttk.Label(row,text=self.T('Segundos/jugada (sin reloj)','Seconds/move (no clock)'),width=22).pack(side='left')
        ttk.Spinbox(row,from_=1,to=60,textvariable=self.move_seconds,width=8).pack(side='left')
        btns=ttk.Frame(frame);btns.pack(fill='x',pady=(12,0))
        ttk.Button(btns,text=self.T('Nueva partida','New game'),command=lambda:(win.destroy(),self.start_game())).pack(side='left')
        ttk.Button(btns,text=self.T('Cerrar','Close'),command=win.destroy).pack(side='right')
    def fen_dialog(self):
        win=tk.Toplevel(self.w);win.title('FEN');win.transient(self.w)
        frame=ttk.Frame(win,padding=12);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='FEN').pack(anchor='w')
        entry=ttk.Entry(frame,textvariable=self.fen,width=88);entry.pack(fill='x',pady=4)
        row=ttk.Frame(frame);row.pack(fill='x')
        ttk.Label(row,text=self.T('Juega / To move:','To move:')).pack(side='left')
        ttk.Combobox(row,textvariable=self.side_to_move,values=('White','Black'),state='readonly',width=8).pack(side='left',padx=6)
        ttk.Button(row,text='Set FEN',command=lambda:(self.set_fen(),win.destroy())).pack(side='left',padx=8)
        ttk.Button(row,text=self.T('Cancelar','Cancel'),command=win.destroy).pack(side='right')
    PIECE_3D=('Staunton 3D','Cool Arcade')
    def _piece_style_names(self):
        required={f'{color}{piece}.png' for color in ('','_') for piece in ('K','Q','R','B','N','P')}
        style_root=os.path.join(ROOT,'assets','lucas_styles')
        png_styles=[]
        if os.path.isdir(style_root):
            for name in os.listdir(style_root):
                folder=os.path.join(style_root,name)
                try:files=set(os.listdir(folder))
                except OSError:continue
                if os.path.isdir(folder) and required.issubset(files):png_styles.append(name)
        try:discovered=list(training_resources.piece_sets())
        except Exception:discovered=[]
        # The board renderer loads PNG sprites. Keep only usable styles and also
        # include PNG-only sets such as Cool Arcade, which have SVG index files
        # only for compatibility with older resource scanners.
        styles=[name for name in discovered if name in png_styles]
        styles.extend(name for name in png_styles if name not in styles)
        if self.board_view.get()=='3D':
            return [name for name in self.PIECE_3D if name in styles]
        styles=[name for name in styles if name not in self.PIECE_3D]
        if 'Nibbler' not in styles:styles=['Nibbler',*styles]
        else:styles=['Nibbler']+[name for name in styles if name!='Nibbler']
        return styles
    def settings_dialog(self):
        win=tk.Toplevel(self.w);win.title(self.T('Configuración del tablero','Board settings'));win.transient(self.w)
        frame=ttk.Frame(win,padding=14);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text=self.T('Piezas, colores y perspectiva 2D/3D','Pieces, colors and 2D/3D view'),font=('Arial',12,'bold')).pack(anchor='w')
        row=ttk.Frame(frame);row.pack(fill='x',pady=8)
        ttk.Label(row,text=self.T('Perspectiva','View'),width=18).pack(side='left')
        view=ttk.Combobox(row,textvariable=self.board_view,values=('2D','3D'),state='readonly',width=8)
        view.pack(side='left');view.bind('<<ComboboxSelected>>',self.set_board_view)
        row=ttk.Frame(frame);row.pack(fill='x',pady=4)
        ttk.Label(row,text=self.T('Estilo de piezas','Piece style'),width=18).pack(side='left')
        styles=self._piece_style_names()
        self.settings_style_selector=ttk.Combobox(row,textvariable=self.piece_style,values=styles,state='readonly',width=28)
        self.settings_style_selector.pack(side='left');self.settings_style_selector.bind('<<ComboboxSelected>>',self.change_pieces)
        ttk.Label(frame,text=self.T('En 3D puedes elegir Staunton 3D o Cool Arcade. En 2D puedes elegir Nibbler o cualquier otro set.','3D can use Staunton 3D or Cool Arcade. 2D can use Nibbler or any other set.')).pack(anchor='w',pady=(0,8))
        ttk.Label(frame,text=self.T('Colores del tablero','Board colors')).pack(anchor='w')
        colorrow=ttk.Frame(frame);colorrow.pack(anchor='w',fill='x',pady=4)
        palettes=ttk.Combobox(colorrow,textvariable=self.board_palette,values=(*self.BOARD_PALETTES,'Personalizar / Custom'),state='readonly',width=30)
        palettes.pack(side='left',padx=(0,8));palettes.bind('<<ComboboxSelected>>',self.select_board_palette)
        ttk.Label(colorrow,text=self.T('Clara','Light')).pack(side='left')
        self.light_color_button=tk.Button(colorrow,text='   ',width=3,relief='solid',bd=1,bg=self.light_square,command=lambda:self.choose_board_color('light'))
        self.light_color_button.pack(side='left',padx=(3,8))
        ttk.Label(colorrow,text=self.T('Oscura','Dark')).pack(side='left')
        self.dark_color_button=tk.Button(colorrow,text='   ',width=3,relief='solid',bd=1,bg=self.dark_square,command=lambda:self.choose_board_color('dark'))
        self.dark_color_button.pack(side='left',padx=3)
        ttk.Button(frame,text=self.T('Cerrar','Close'),command=win.destroy).pack(anchor='e',pady=10)
    def training_dialog(self):
        win=tk.Toplevel(self.w);win.title(self.T('Entrenamiento y puzzles','Training and puzzles'));win.geometry('720x560');win.transient(self.w)
        frame=ttk.Frame(win,padding=12);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text=self.T('Ejercicios de Lucas Chess (carpeta assets/lucas_resources)','Lucas Chess exercises (assets/lucas_resources folder)'),font=('Arial',12,'bold')).pack(anchor='w')
        groups={'Todos / All':list(self.training_sets)}
        for key in self.training_sets:
            top=key.replace('\\','/').split('/')[0]
            groups.setdefault(top,[]).append(key)
        group_var=tk.StringVar(value='Todos / All')
        row=ttk.Frame(frame);row.pack(fill='x',pady=6)
        ttk.Label(row,text=self.T('Categoría','Category'),width=16).pack(side='left')
        group_box=ttk.Combobox(row,textvariable=group_var,values=tuple(groups),state='readonly',width=28)
        group_box.pack(side='left')
        row=ttk.Frame(frame);row.pack(fill='x',pady=4)
        ttk.Label(row,text=self.T('Colección','Collection'),width=16).pack(side='left')
        self.training_box=ttk.Combobox(row,textvariable=self.training_choice,values=tuple(self.training_sets),state='readonly',width=52)
        self.training_box.pack(side='left',fill='x',expand=True)
        def apply_group(event=None):
            keys=groups.get(group_var.get(),list(self.training_sets))
            self.training_box.configure(values=keys)
            if keys and self.training_choice.get() not in keys:
                self.training_choice.set(keys[0])
        group_box.bind('<<ComboboxSelected>>',apply_group)
        btns=ttk.Frame(frame);btns.pack(fill='x',pady=8)
        ttk.Button(btns,text=self.T('Siguiente ejercicio','Next exercise'),command=self.new_puzzle).pack(side='left')
        ttk.Button(btns,text=self.T('Mejor jugada','Find best move'),command=self.best_move_challenge).pack(side='left',padx=6)
        ttk.Button(btns,text=self.T('Abrir archivo .fns','Open .fns file'),command=self.choose_training).pack(side='left')
        ttk.Separator(frame).pack(fill='x',pady=10)
        ttk.Label(frame,text=self.T('Puzzles de Lichess (archivo CSV aparte)','Lichess puzzles (separate CSV file)'),font=('Arial',11,'bold')).pack(anchor='w')
        theme_row=ttk.Frame(frame);theme_row.pack(fill='x',pady=4)
        ttk.Label(theme_row,text=self.T('Categoría','Category')).pack(side='left')
        self.puzzle_category_box=ttk.Combobox(theme_row,textvariable=self.puzzle_category,values=tuple(lichess_puzzles.PUZZLE_CATEGORIES),state='readonly',width=24)
        self.puzzle_category_box.pack(side='left',padx=4);self.puzzle_category_box.bind('<<ComboboxSelected>>',self.puzzle_category_changed)
        self.puzzle_theme_box=ttk.Combobox(theme_row,textvariable=self.puzzle_theme_choice,values=tuple(label for label,tag in lichess_puzzles.PUZZLE_CATEGORIES[self.puzzle_category.get()]),state='readonly',width=32)
        self.puzzle_theme_box.pack(side='left',padx=4)
        file_row=ttk.Frame(frame);file_row.pack(fill='x',pady=4)
        ttk.Button(file_row,text=self.T('Elegir CSV Lichess','Choose Lichess CSV'),command=self.choose_lichess_puzzle_file).pack(side='left')
        ttk.Button(file_row,text=self.T('Siguiente puzzle Lichess','Next Lichess puzzle'),command=self.next_lichess_puzzle).pack(side='left',padx=6)
        ttk.Label(file_row,textvariable=self.lichess_puzzle_file).pack(side='left',padx=6)
        if not hasattr(self,'lichess_puzzle_status'):
            self.lichess_puzzle_status=tk.StringVar(value='')
        ttk.Label(frame,textvariable=self.lichess_puzzle_status,wraplength=680).pack(anchor='w',pady=4)
        hint=tk.Text(frame,height=10,wrap='word');hint.pack(fill='both',expand=True,pady=8)
        n=sum(len(v) for k,v in self.training_sets.items() if k!='All Lucas Chess exercises')
        hint.insert('1.0',self.T(
            f'Se detectaron {len(self.training_sets)-1} colecciones locales.\nElige Tactics o Trainings, pulsa Siguiente ejercicio y resuelve en el tablero.\nLos puzzles de Lichess necesitan el CSV descargado de database.lichess.org.',
            f'{len(self.training_sets)-1} local collections were found.\nPick Tactics or Trainings, press Next exercise and solve on the board.\nLichess puzzles need the CSV from database.lichess.org.'))
        hint.configure(state='disabled')
    def puzzle_rush_dialog(self):
        win=tk.Toplevel(self.w);win.title(self.T('Puzzle Rush','Puzzle Rush'));win.geometry('720x420');win.transient(self.w)
        frame=ttk.Frame(win,padding=12);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text=self.T('Puzzle Rush · 5 minutos','Puzzle Rush · 5 minutes'),font=('Arial',16,'bold')).pack(anchor='w')
        ttk.Label(frame,text=self.T('Resuelve tantos puzzles como puedas. Cada ejercicio permite tres intentos; una pista resta Elo.','Solve as many puzzles as you can. Each puzzle allows three tries; using a hint lowers your rating.'),wraplength=680).pack(anchor='w',pady=(4,8))
        category_row=ttk.Frame(frame);category_row.pack(fill='x',pady=3)
        ttk.Label(category_row,text=self.T('Tema','Theme'),width=16).pack(side='left')
        category_labels={key:self.T(*puzzle_rush.CATEGORIES[key]) for key in self.rush_categories}
        current_label=category_labels.get(self.rush_category.get(),category_labels.get('all',''))
        category_var=tk.StringVar(value=current_label)
        category_box=ttk.Combobox(category_row,textvariable=category_var,values=tuple(category_labels.values()),state='readonly',width=45)
        category_box.pack(side='left',fill='x',expand=True)
        count_labels={category_labels[k]:len(v) for k,v in self.rush_categories.items()}
        count_var=tk.StringVar(value=self.T(f"{count_labels.get(current_label,0)} colecciones",f"{count_labels.get(current_label,0)} collections"))
        ttk.Label(category_row,textvariable=count_var).pack(side='left',padx=8)
        def update_rush_count(event=None):
            count=count_labels.get(category_var.get(),0)
            count_var.set(self.T(f'{count} colecciones',f'{count} collections'))
        category_box.bind('<<ComboboxSelected>>',update_rush_count)
        ttk.Label(frame,text=self.T(f"Elo Puzzle Rush: {self.rush_stats['rating']}   ·   Récord: {self.rush_stats['best_score']} puzzles",
                                    f"Puzzle Rush rating: {self.rush_stats['rating']}   ·   Record: {self.rush_stats['best_score']} puzzles"),font=('Arial',11,'bold')).pack(anchor='w',pady=4)
        def start_rush():
            label=category_var.get()
            selected=next((key for key,value in category_labels.items() if value==label),'all')
            self.rush_category.set(selected)
            self.start_puzzle_rush(selected)
            if self.rush_session:win.destroy()
        ttk.Button(frame,text=self.T('Iniciar Puzzle Rush','Start Puzzle Rush'),command=start_rush).pack(anchor='w',pady=(3,9))
    def start_puzzle_rush(self,category='all'):
        paths=self.rush_categories.get(category) or self.rush_categories.get('all',[])
        if not paths:
            messagebox.showinfo(self.T('Puzzle Rush','Puzzle Rush'),self.T('No hay puzzles instalados en este tema.','No installed puzzles are available for this theme.'),parent=self.w);return
        self.stop();self.playing=False;self.play_busy=False;self.selected=None;self.results={};self.final_result=None
        self.stop_clock(settle=False);self.review_game=None;self.abort_quad_match()
        self.rush_seen=set()
        self.rush_session={'category':category,'paths':paths,'started':time.monotonic(),'ends':time.monotonic()+300,
                           'solved':0,'attempts_left':3,'wrong':0,'hints':0,'hint_used':False,'rating':self.rush_stats['rating'],
                           'finished':False,'last_attempt':0,'waiting_engine':False,'engine_failures':0}
        self.puzzle_active='rush';self.puzzle_meta=None;self.puzzle_banner=''
        if not self._next_rush_puzzle():
            self.finish_puzzle_rush('empty');return
        if self.rush_window is not None:
            try:self.rush_window.destroy()
            except tk.TclError:pass
        win=tk.Toplevel(self.w);self.rush_window=win;win.title(self.T('Puzzle Rush','Puzzle Rush'));win.geometry('460x190');win.transient(self.w)
        ttk.Label(win,textvariable=self.rush_text,font=('Arial',12,'bold'),justify='left').pack(fill='x',padx=12,pady=10)
        row=ttk.Frame(win);row.pack(fill='x',padx=10,pady=5)
        ttk.Button(row,text=self.T('Pista (−10 Elo)','Hint (−10 rating)'),command=self.puzzle_rush_hint).pack(side='left',padx=3)
        ttk.Button(row,text=self.T('Terminar y volver','Finish and return'),command=lambda:self.finish_puzzle_rush('quit')).pack(side='right',padx=3)
        win.protocol('WM_DELETE_WINDOW',lambda:self.finish_puzzle_rush('quit'))
        self.show_study_view()
        self.status.set(self.T('Puzzle Rush: resuelve el problema. Juegan las '+('blancas.' if self.board.turn else 'negras.'),
                               'Puzzle Rush: solve the position. '+('White' if self.board.turn else 'Black')+' to move.'))
        self.update_puzzle_rush_display()
    def _next_rush_puzzle(self):
        session=self.rush_session
        if not session:return False
        choices=list(session['paths']);random.shuffle(choices)
        for _ in range(60):
            try:board,solution,credit,path=training_resources.random_exercise(choices)
            except Exception:continue
            moves=training_resources.solution_moves(board,solution)
            key=(board.fen(),tuple(move.uci() for move in moves))
            if not moves or key in self.rush_seen:continue
            self.rush_seen.add(key)
            self.board=board;self.puzzle_moves=moves;self.puzzle_index=0;self.puzzle_color=board.turn
            self.flipped=board.turn==chess.BLACK;self.selected=None;session['attempts_left']=3;session['hint_used']=False
            session['last_attempt']=0;session['credit']=credit;session['source']=path.name;session['expected']=moves[0]
            self.side_to_move.set('White' if board.turn else 'Black');self.draw()
            return True
        engine_name=self.first_configured_engine();engine_path=self.paths.get(engine_name) if engine_name else None
        if engine_path:
            for _ in range(8):
                try:board,solution,credit,path=training_resources.random_exercise(choices)
                except Exception:continue
                if training_resources.solution_moves(board,solution):continue
                key=(board.fen(),())
                if key in self.rush_seen:continue
                self.rush_seen.add(key);self.board=board;self.puzzle_moves=[];self.puzzle_index=0
                self.puzzle_color=board.turn;self.flipped=board.turn==chess.BLACK;self.selected=None
                session['attempts_left']=3;session['hint_used']=False;session['waiting_engine']=True
                session['source']=path.name;session['credit']=credit
                self.side_to_move.set('White' if board.turn else 'Black');self.draw()
                self.status.set(self.T('Preparando una jugada de referencia con el motor…','Preparing a reference move with the engine…'))
                self.update_puzzle_rush_display()
                token=self.epoch
                threading.Thread(target=self.challenge_worker,args=(token,engine_name,engine_path,board.copy()),daemon=True).start()
                return True
        return False
    def update_puzzle_rush_display(self):
        session=self.rush_session
        if not session or session.get('finished'):return
        seconds=max(0,int(session['ends']-time.monotonic()+0.999))
        category_label=self.T(*puzzle_rush.CATEGORIES.get(session['category'],puzzle_rush.CATEGORIES['all']))
        turn=self.T('Blancas','White') if self.board.turn==chess.WHITE else self.T('Negras','Black')
        self.rush_text.set(self.T(f"⏱ {seconds//60}:{seconds%60:02d}   ·   Puzzles: {session['solved']}   ·   Elo: {session['rating']}\nTema: {category_label}   ·   Juegan: {turn}   ·   Intentos: {session['attempts_left']}/3",
                                  f"⏱ {seconds//60}:{seconds%60:02d}   ·   Puzzles: {session['solved']}   ·   Rating: {session['rating']}\nTheme: {category_label}   ·   To move: {turn}   ·   Tries: {session['attempts_left']}/3"))
        if seconds<=0:self.finish_puzzle_rush('time')
    def _save_puzzle_rush_stats(self):
        try:puzzle_rush.save_stats(self.rush_stats)
        except OSError as err:self.status.set(self.T('No se pudo guardar el progreso de Puzzle Rush: ','Could not save Puzzle Rush progress: ')+str(err))
    def puzzle_rush_hint(self):
        session=self.rush_session
        if not session or session.get('finished'):return
        if session.get('waiting_engine'):
            self.status.set(self.T('El motor está preparando la jugada.','The engine is preparing the move.'));return
        if not self.puzzle_moves:return
        session['rating']=max(100,session['rating']-10);session['hints']+=1;session['hint_used']=True
        self.rush_stats['rating']=session['rating'];self._save_puzzle_rush_stats()
        move=self.puzzle_moves[self.puzzle_index]
        self.selected=move.from_square;self.draw()
        square=chess.square_name(move.from_square)
        self.status.set(self.T(f'Pista: considera mover la pieza de {square}. Se restaron 10 puntos de Elo.',
                               f'Hint: consider moving the piece on {square}. 10 rating points were deducted.'))
        self.update_puzzle_rush_display()
    def finish_puzzle_rush(self,reason='quit'):
        session=self.rush_session
        if not session or session.get('finished'):return
        session['finished']=True;session['rating']=max(100,session['rating'])
        self.puzzle_active=False;self.selected=None;self.rush_stats['rating']=session['rating'];self.rush_stats['runs']+=1
        new_record=session['solved']>self.rush_stats['best_score']
        if new_record:self.rush_stats['best_score']=session['solved']
        self._save_puzzle_rush_stats()
        if self.rush_window is not None:
            try:self.rush_window.destroy()
            except tk.TclError:pass
            self.rush_window=None
        self.draw();self.show_study_view()
        if reason=='lost':title=self.T('Lo siento, inténtalo otra vez','Sorry, try again')
        elif reason=='time':title=self.T('¡Tiempo!','Time!')
        elif reason=='empty':title=self.T('Puzzle Rush','Puzzle Rush')
        elif reason=='engine':title=self.T('El motor no pudo preparar más posiciones.','The engine could not prepare more positions.')
        else:title=self.T('Puzzle Rush terminado','Puzzle Rush finished')
        record_line=self.T('¡Felicitaciones, hiciste un récord nuevo!','Congratulations, you set a new record!') if new_record else self.T(f"Récord personal: {self.rush_stats['best_score']} puzzles.",f"Personal record: {self.rush_stats['best_score']} puzzles.")
        summary=self.T(f"{title}\nPuzzles resueltos: {session['solved']}\nElo Puzzle Rush: {session['rating']}\nPistas usadas: {session['hints']}\n{record_line}",
                       f"{title}\nPuzzles solved: {session['solved']}\nPuzzle Rush rating: {session['rating']}\nHints used: {session['hints']}\n{record_line}")
        self.rush_session=None
        if reason!='quit' or new_record:messagebox.showinfo(self.T('Resultado de Puzzle Rush','Puzzle Rush result'),summary,parent=self.w)
    @staticmethod
    def _uci_command(path):
        lower=path.lower()
        if lower.endswith('.py'):return [sys.executable,path]
        if platform.system()=='Windows' and lower.endswith(('.bat','.cmd')):return ['cmd.exe','/c',path]
        return path
    def add_uci_engine(self):
        suggested=''
        path=filedialog.askopenfilename(title=self.T('Selecciona el ejecutable UCI','Select the UCI executable'),
                                        filetypes=[('Chess engine','*.exe *.bat *.cmd *.py'),('All files','*.*')])
        if not path:return
        suggested=os.path.splitext(os.path.basename(path))[0]
        name=simpledialog.askstring(self.T('Agregar motor UCI','Add UCI Engine'),
                                    self.T('Nombre que aparecerá en los menús de RoboChess:','Name to show in RoboChess menus:'),
                                    initialvalue=suggested,parent=self.w)
        if name is None:return
        name=' '.join(name.strip().split())
        if not name:
            messagebox.showerror(self.T('Nombre requerido','Name required'),self.T('Escribe un nombre para el motor.','Enter a name for the engine.'));return
        if name.casefold() in {n.casefold() for n in self.BUILTIN_ENGINE_NAMES}:
            messagebox.showerror(self.T('Nombre reservado','Reserved name'),self.T('Ese nombre ya pertenece a un motor integrado. Elige otro.','That name is already used by a built-in engine. Choose another.'));return
        existing=next((n for n in self.custom_engines if n.casefold()==name.casefold()),None)
        if existing and not messagebox.askyesno(self.T('Reemplazar motor','Replace engine'),
                self.T(f'{existing} ya está registrado. ¿Reemplazar su ejecutable?',f'{existing} is already registered. Replace its executable?')):return
        previous_record=self.custom_engines.get(existing) if existing else None
        previous_path=self.paths.get(existing) if existing else None
        engine=None
        try:
            engine=chess.engine.SimpleEngine.popen_uci(self._uci_command(path),timeout=12)
            reported=engine.id.get('name','UCI engine')
            engine.quit();engine=None
        except Exception as err:
            if engine:
                try:engine.quit()
                except Exception:pass
            messagebox.showerror(self.T('No se pudo iniciar el motor UCI','Could not start UCI engine'),
                                 self.T(f'RoboChess no recibió una respuesta UCI válida de este archivo:\n{err}',f'RoboChess did not receive a valid UCI response from this file:\n{err}'))
            return
        if existing:del self.custom_engines[existing]
        self.custom_engines[name]={'path':os.path.abspath(path),'reported_name':reported}
        self.paths[name]=os.path.abspath(path)
        try:self._save_custom_engines()
        except OSError as err:
            self.custom_engines.pop(name,None);self.paths.pop(name,None)
            if existing and previous_record:
                self.custom_engines[existing]=previous_record;self.paths[existing]=previous_path
            messagebox.showerror(self.T('No se pudo guardar el motor','Could not save engine'),str(err));return
        self._refresh_engine_choices(name)
        self.status.set(self.T(f'{name} agregado ({reported}) y disponible en los selectores.',f'{name} added ({reported}) and available in engine selectors.'))
    def show_study_view(self):
        self.lichess_video.unload()
        self.tabs.pack_forget();self.video_view.pack_forget();self.pdf_view.pack_forget();self.study_view.pack(fill='both',expand=True)
    def show_tools_view(self):
        self.lichess_video.unload()
        self.study_view.pack_forget();self.video_view.pack_forget();self.pdf_view.pack_forget();self.tabs.pack(fill='both',expand=True)
    def show_lichess_video(self):
        self.study_view.pack_forget();self.tabs.pack_forget();self.pdf_view.pack_forget()
        self.video_view.pack(fill='both',expand=True)
        self.lichess_video.set_language(self.language.get())
        self.lichess_video.load()
    def show_pdf_view(self):
        self.lichess_video.unload()
        self.study_view.pack_forget();self.tabs.pack_forget();self.video_view.pack_forget()
        self.pdf_view.pack(fill='both',expand=True)
        self.pdf_reader.set_language()
    def open_pdf_book(self):
        self.show_pdf_view()
        self.pdf_reader.open_dialog()
    def preview_pdf_diagram(self,png_data):
        if getattr(self,'pdf_diagram_window',None) is not None:
            try:self.pdf_diagram_window.destroy()
            except tk.TclError:pass
        import diagram_recognize
        recognized=diagram_recognize.recognize_diagram(png_data)
        win=tk.Toplevel(self.w);self.pdf_diagram_window=win
        win.title(self.T('Diagrama seleccionado','Selected diagram'))
        win.transient(self.w)
        frame=ttk.Frame(win,padding=10);frame.pack(fill='both',expand=True)
        try:
            photo=tk.PhotoImage(data=base64.b64encode(png_data).decode('ascii'))
            factor=max(1,math.ceil(max(photo.width(),photo.height())/420))
            if factor>1:photo=photo.subsample(factor,factor)
            self.pdf_diagram_photo=photo
            ttk.Label(frame,image=photo).pack(pady=(0,8))
        except Exception as err:
            ttk.Label(frame,text=f'PNG: {err}').pack()
        ttk.Label(frame,wraplength=460,justify='left',text=self.T(
            'El diagrama marcado se interpreta y se carga en el tablero de análisis. Elige quién mueve y pulsa Analizar. Si una pieza no coincide, corrígela en el editor.',
            'The marked diagram is interpreted and loaded on the analysis board. Choose who moves, then Analyze. If a piece does not match, correct it in the editor.'
        )).pack(fill='x')
        turn=tk.StringVar(value='White')
        row=ttk.Frame(frame);row.pack(fill='x',pady=6)
        ttk.Label(row,text=self.T('Juegan','To move')).pack(side='left')
        ttk.Radiobutton(row,text=self.T('Blancas','White'),variable=turn,value='White').pack(side='left',padx=6)
        ttk.Radiobutton(row,text=self.T('Negras','Black'),variable=turn,value='Black').pack(side='left')
        fen_var=tk.StringVar(value=recognized or '')
        ttk.Entry(frame,textvariable=fen_var).pack(fill='x',pady=4)
        buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=(4,0))
        self._pdf_diagram_turn=turn
        self._pdf_diagram_fen=fen_var
        self._pdf_diagram_png=png_data
        ttk.Button(buttons,text=self.T('Cargar y analizar','Load and analyze'),command=lambda:self.load_marked_diagram(True)).pack(side='left')
        ttk.Button(buttons,text=self.T('Solo cargar','Load only'),command=lambda:self.load_marked_diagram(False)).pack(side='left',padx=6)
        ttk.Button(buttons,text=self.T('Editar posición','Edit position'),command=self.start_pdf_diagram_editor).pack(side='left')
        ttk.Button(buttons,text=self.T('Cancelar','Cancel'),command=win.destroy).pack(side='right')
        win.lift()
        if recognized:
            try:
                self._load_diagram_board(chess.Board(f'{recognized} w - - 0 1'))
                self.status.set(self.T('Posición del diagrama cargada. Elige quién mueve y pulsa Cargar y analizar.','Diagram position loaded. Choose who moves, then Load and analyze.'))
            except ValueError:
                self.status.set(self.T('Se leyó el diagrama, pero hay que revisarlo.','The diagram was read, but it needs a check.'))
        else:
            self.status.set(self.T('No se leyeron piezas. Marca solo el tablero, de borde a borde.','No pieces were read. Mark only the board, edge to edge.'))
    def load_marked_diagram(self,start_analysis):
        self.status.set(self.T('Cargando diagrama en el tablero…','Loading diagram onto the board…'))
        try:
            placement=(self._pdf_diagram_fen.get().strip() if getattr(self,'_pdf_diagram_fen',None) else '')
            turn=self._pdf_diagram_turn.get() if getattr(self,'_pdf_diagram_turn',None) else 'White'
            if not placement:
                self.status.set(self.T('El recuadro de la posición está vacío. Marca solo el tablero y vuelve a pulsar Cargar.','The position box is empty. Mark only the board, then press Load again.'))
                return
            board=chess.Board(f'{placement} {"w" if turn=="White" else "b"} - - 0 1')
            self._load_diagram_board(board)
            if getattr(self,'pdf_diagram_window',None) is not None:
                self.pdf_diagram_window.destroy()
            if start_analysis:
                self.w.after(150,lambda:self.analyze(selected_only=True,engine_name=self.engine_view.get()))
        except Exception as err:
            self.status.set(self.T('No se pudo cargar el diagrama: ','Could not load the diagram: ')+str(err))
            messagebox.showerror(self.T('Diagrama','Diagram'),str(err),parent=self.w)
    def _load_diagram_board(self,board):
        self.stop();self.playing=False;self.play_busy=False;self.puzzle_active=False
        self.stop_clock(settle=False);self.clock_selector.configure(state='readonly')
        self.abort_quad_match();self.review_game=None;self.final_result=None;self.results={}
        self.board=board;self.selected=None;self.editor_mode=False
        self.side_to_move.set('White' if board.turn else 'Black')
        self.fen.set(board.fen());self.refresh_move_list();self.draw()
        self.show_pdf_view()
        self.status.set(self.T('Posición del diagrama cargada en el tablero.','Diagram position loaded on the board.'))
    def start_pdf_diagram_editor(self):
        self.pdf_diagram_pending=True
        self.start_position_editor()
        self.status.set(self.T('Coloca las piezas del diagrama. Elige quién juega y pulsa Aplicar; el motor seleccionado analizará la posición.',
                               'Place the diagram pieces, choose whose turn it is, then Apply; the selected engine will analyze the position.'))
    def apply_pdf_line(self,text,notation):
        if self.playing or self.engine_match_running or (self.quad and self.quad.get('active')):
            raise ValueError(self.T('Termina la partida o el torneo antes de cargar una línea del libro.',
                                    'Finish the game or tournament before loading a book line.'))
        start=self.board.copy(stack=True)
        moves,converted=parse_chess_book_line(start,text,notation,self.language.get())
        if not moves:raise ValueError(self.T('No se encontraron jugadas legales.','No legal moves were found.'))
        trial=start.copy(stack=True)
        for move in moves:trial.push(move)
        self.stop();self.playing=False;self.play_busy=False;self.puzzle_active=False
        self.stop_clock(settle=False);self.clock_selector.configure(state='readonly')
        self.abort_quad_match();self.review_game=None;self.final_result=None;self.results={}
        self.board=trial;self.selected=None;self.side_to_move.set('White' if self.board.turn else 'Black')
        self.fen.set(self.board.fen());self.refresh_move_list();self.draw()
        self.status.set(self.T('Línea del libro cargada y convertida a notación algebraica.',
                               'Book line loaded and converted to algebraic notation.'))
        return converted
    def save_pdf_line_pgn(self):
        if not self.board.move_stack:
            messagebox.showinfo(self.T('Libro PDF','PDF book'),self.T('Carga una línea en el tablero antes de guardarla.',
                                                                       'Load a move line on the board before saving it.'))
            return
        path=filedialog.asksaveasfilename(defaultextension='.pgn',filetypes=[('PGN','*.pgn')],
                                          title=self.T('Guardar línea del libro como PGN','Save book line as PGN'))
        if not path:return
        game=chess.pgn.Game.from_board(self.board)
        game.headers['Event']='PDF chess book study'
        if self.pdf_reader.path:game.headers['Source']=os.path.basename(self.pdf_reader.path)
        try:
            with open(path,'w',encoding='utf-8') as stream:print(game,file=stream,end='\n\n')
            self.status.set(self.T('Línea guardada: ','Line saved: ')+path)
        except OSError as err:messagebox.showerror('PGN',str(err))
    def make_editor_palette(self):
        ttk.Label(self.editor_palette,text='Blancas / White:').pack(side='left',padx=3)
        labels={'K':'♔ Rey','Q':'♕ Dama','R':'♖ Torre','B':'♗ Alfil','N':'♘ Caballo','P':'♙ Peón',
                'k':'♚ Rey','q':'♛ Dama','r':'♜ Torre','b':'♝ Alfil','n':'♞ Caballo','p':'♟ Peón'}
        self.editor_radio_buttons=[]
        for color,order,title in [('white','KQRBNP','Blancas / White:'),('black','kqrbnp','Negras / Black:')]:
            if color=='black':ttk.Label(self.editor_palette,text=title).pack(side='left',padx=(8,2))
            for symbol in order:
                button=ttk.Radiobutton(self.editor_palette,text=labels[symbol],value=symbol,variable=self.editor_choice,
                    command=lambda:self.choose_editor_piece(self.editor_choice.get()))
                button.pack(side='left',padx=1);self.editor_radio_buttons.append(button)
        ttk.Button(self.editor_palette,text='Vaciar / Erase',command=lambda:self.choose_editor_piece(None)).pack(side='left',padx=(6,2))
        ttk.Button(self.editor_palette,text='Limpiar / Clear',command=self.clear_editor_board).pack(side='left',padx=2)
        ttk.Button(self.editor_palette,text='Aplicar / Apply',command=self.apply_position_editor).pack(side='left',padx=2)
        ttk.Button(self.editor_palette,text='Cancelar / Cancel',command=self.cancel_position_editor).pack(side='left',padx=2)
        ttk.Label(self.editor_palette,text='Juega / To move:').pack(side='left',padx=(8,2))
        self.editor_turn_box=ttk.Combobox(self.editor_palette,textvariable=self.side_to_move,
                                           values=('White','Black'),state='readonly',width=7)
        self.editor_turn_box.pack(side='left',padx=2)
        self.editor_turn_box.bind('<<ComboboxSelected>>',self.editor_turn_changed)
    def choose_editor_piece(self,symbol):
        self.editor_piece=None if symbol is None else chess.Piece.from_symbol(symbol)
        self.status.set(self.T('Pulsa una casilla para colocar la pieza elegida.','Click a square to place the selected piece.'))
    def editor_turn_changed(self,_event=None):
        if self.editor_mode:
            self.board.turn=self.side_to_move.get()=='White'
            self.draw()
    def start_position_editor(self):
        if not self.editor_mode:self.editor_saved_board=self.board.copy(stack=True)
        self.stop();self.playing=False;self.play_busy=False;self.puzzle_active=False;self.results={};self.review_game=None
        self.board=chess.Board(None);self.editor_mode=True;self.editor_piece=chess.Piece.from_symbol(self.editor_choice.get())
        self.board.turn=self.side_to_move.get()=='White';self.selected=None
        self.editor_palette.pack(fill='x',padx=8,pady=(2,4),before=self.root_pane)
        self.status.set(self.T('Editor activo: coloca las piezas; debe haber un rey blanco y uno negro.','Editor active: place pieces; the board needs one White king and one Black king.'))
        self.draw()
    def clear_editor_board(self):
        if self.editor_mode:self.board=chess.Board(None);self.board.turn=self.side_to_move.get()=='White';self.draw()
    def cancel_position_editor(self):
        if not self.editor_mode:return
        if self.editor_saved_board is not None:self.board=self.editor_saved_board
        self.editor_mode=False;self.editor_saved_board=None;self.editor_palette.pack_forget();self.draw()
        if self.pdf_diagram_pending:
            self.pdf_diagram_pending=False
            if self.pdf_diagram_window is not None:
                try:self.pdf_diagram_window.destroy()
                except tk.TclError:pass
    def apply_position_editor(self):
        if not self.editor_mode:return
        if len(self.board.pieces(chess.KING,chess.WHITE))!=1 or len(self.board.pieces(chess.KING,chess.BLACK))!=1:
            messagebox.showerror('Posición / Position',self.T('La posición necesita exactamente un rey blanco y un rey negro.','The position must have exactly one White king and one Black king.'));return
        self.board.turn=self.side_to_move.get()=='White';self.board.clear_stack();self.editor_mode=False;self.editor_saved_board=None
        self.editor_palette.pack_forget();self.results={};self.final_result=None;self.fen.set(self.board.fen())
        diagram_analysis=self.pdf_diagram_pending
        self.pdf_diagram_pending=False
        self.status.set(self.T('Posición lista. Puedes analizarla o guardarla como FEN/PGN.','Position ready. You can analyze it or save it as FEN/PGN.'));self.draw()
        if diagram_analysis:
            if self.pdf_diagram_window is not None:
                try:self.pdf_diagram_window.destroy()
                except tk.TclError:pass
            self.analyze(selected_only=True,engine_name=self.engine_view.get())
    def show_engine_panel(self,event=None):
        for name,box in self.panels.items():box.pack_forget()
        self.panels[self.engine_view.get()].pack(fill='both',expand=True)
    def _update_video_analysis_title(self):
        frame=getattr(self,'video_analysis_frame',None)
        name=self.engine_view.get()
        title=self.T('Análisis del motor — {name}','Engine analysis — {name}').format(name=name)
        if frame is not None:frame.configure(text=title)
        pdf_frame=getattr(self,'pdf_analysis_frame',None)
        if pdf_frame is not None:pdf_frame.configure(text=title)
    def selected_engine_analysis_output(self):
        pdf_view=getattr(self,'pdf_view',None)
        if pdf_view is not None and pdf_view.winfo_ismapped():return self.pdf_analysis
        return self.video_analysis
    def refresh_move_list(self):
        if not hasattr(self,'move_text'):return
        board=self.board.root();rows=[]
        for move in self.board.move_stack:
            number=board.fullmove_number;white=board.turn;san=board.san(move);board.push(move)
            if white:rows.append(f'{number}. {san}')
            elif rows:rows[-1]+='  '+san
            else:rows.append(f'{number}… {san}')
        text='   '.join(rows) if rows else '—'
        self.put(self.move_text,text)
        if self.review_game:
            total=sum(1 for _ in self.review_game.mainline_moves())
            self.review_label.set(f'{self.review_ply} / {total} ply')
        else:self.review_label.set('PGN review / Revisión PGN')
    def review_step(self,delta):
        if not self.review_game:return
        moves=list(self.review_game.mainline_moves());self.review_ply=max(0,min(len(moves),self.review_ply+delta))
        board=self.review_game.board();sound=None
        for index,move in enumerate(moves[:self.review_ply]):
            if delta>0 and index==self.review_ply-1:sound=self.sound_for_move(board,move)
            board.push(move)
        if sound:self.play_sound(sound)
        self.stop();self.playing=False;self.play_busy=False;self.results={};self.board=board;self.side_to_move.set('White' if board.turn else 'Black');self.draw()
    def refresh_opening_tree(self):
        if not hasattr(self,'opening_tree'):return
        for iid in self.opening_tree.get_children():self.opening_tree.delete(iid)
        try:moves=training_resources.book_moves(self.board,self.book_path)
        except (OSError,ValueError,IndexError):moves=[]
        for san,weight,percentage in moves[:12]:self.opening_tree.insert('', 'end',values=(san,weight,f'{percentage}%'))
    def open_pgn_database(self):
        path=filedialog.askopenfilename(title='Select a PGN database',filetypes=[('PGN files','*.pgn'),('All files','*.*')])
        if not path:return
        try:
            games=[]
            with open(path,encoding='utf-8-sig',errors='replace') as source:
                while game:=chess.pgn.read_game(source):games.append(game)
            self.database_games=games
            for iid in self.database_tree.get_children():self.database_tree.delete(iid)
            for index,game in enumerate(games):
                h=game.headers;self.database_tree.insert('','end',iid=str(index),values=(index+1,h.get('White','?'),h.get('Black','?'),h.get('Result','*'),h.get('Event',''),h.get('Date','')))
            self.database_label.set(f'{os.path.basename(path)} · {len(games)} partidas / games')
            if not games:messagebox.showinfo('PGN','No games found in this PGN file.')
        except (OSError,ValueError) as err:messagebox.showerror('PGN',str(err))
    def open_database_game(self,event=None):
        selection=self.database_tree.selection()
        if not selection:return
        self.load_review_game(self.database_games[int(selection[0])])
    def fetch_lichess_games(self):
        username=self.lichess_username.get().strip()
        if not username:messagebox.showinfo('Lichess','Enter a public Lichess username.');return
        self.status.set(self.T('Descargando partidas públicas de Lichess…','Fetching public games from Lichess…'))
        threading.Thread(target=self.lichess_worker,args=(username,),daemon=True).start()
    def lichess_worker(self,username):
        try:
            endpoint='https://lichess.org/api/games/user/'+urllib.parse.quote(username,safe='')
            endpoint+='?'+urllib.parse.urlencode({'max':100,'opening':'true','clocks':'false','evals':'false'})
            request=urllib.request.Request(endpoint,headers={'Accept':'application/x-chess-pgn','User-Agent':'RoboChess/23 (desktop chess study)'})
            with urllib.request.urlopen(request,timeout=35) as response:data=response.read().decode('utf-8-sig',errors='replace')
            games=[];stream=io.StringIO(data)
            while game:=chess.pgn.read_game(stream):games.append(game)
            self.lichess_events.put((games,None,username))
        except Exception as err:self.lichess_events.put(([],str(err),username))
    def open_lichess_game(self,event=None):
        selection=self.lichess_tree.selection()
        if selection:self.load_review_game(self.lichess_games[int(selection[0])])
    def load_review_game(self,game):
        if game is None:return
        self.stop();self.playing=False;self.play_busy=False;self.puzzle_active=False;self.results={};self.final_result=game.headers.get('Result')
        self.stop_clock(settle=False);self.clock_selector.configure(state='readonly');self.abort_quad_match()
        self.review_game=game;self.review_ply=sum(1 for _ in game.mainline_moves())
        self.board=game.end().board();self.side_to_move.set('White' if self.board.turn else 'Black');self.draw()
        self.status.set(f"{game.headers.get('White','White')} – {game.headers.get('Black','Black')} · {game.headers.get('Result','*')} · {game.headers.get('Opening','')}")
    def poll_lichess(self):
        try:
            while True:
                games,error,username=self.lichess_events.get_nowait()
                if error:
                    self.status.set(self.T('No se pudieron cargar partidas: ','Could not fetch games: ')+error);continue
                self.lichess_games=games
                for iid in self.lichess_tree.get_children():self.lichess_tree.delete(iid)
                for index,game in enumerate(games):
                    h=game.headers;self.lichess_tree.insert('','end',iid=str(index),values=(h.get('UTCDate',h.get('Date','')),h.get('White','?'),h.get('Black','?'),h.get('Result','*'),h.get('Opening',h.get('ECO','')),h.get('TimeControl','')))
                self.status.set(self.T(f'{len(games)} partidas cargadas de {username}. Doble clic para abrir.',f'Loaded {len(games)} games from {username}. Double-click to open.'))
        except queue.Empty:pass
    def open_live_broadcast_dialog(self):
        if self.live_dialog is not None and self.live_dialog.winfo_exists():
            self.live_dialog.deiconify();self.live_dialog.lift();return
        dialog=tk.Toplevel(self.w);self.live_dialog=dialog
        dialog.title(self.T('Partidas en vivo de Lichess','Lichess live games'));dialog.geometry('840x510');dialog.minsize(680,400);dialog.transient(self.w)
        frame=ttk.Frame(dialog,padding=12);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text=self.T('Pega el enlace de una ronda o torneo de Lichess:','Paste a Lichess round or tournament link:')).pack(anchor='w')
        row=ttk.Frame(frame);row.pack(fill='x',pady=(5,8))
        entry=ttk.Entry(row,textvariable=self.live_url);entry.pack(side='left',fill='x',expand=True)
        ttk.Button(row,text=self.T('Conectar','Connect'),command=self.start_live_broadcast).pack(side='left',padx=(6,0))
        ttk.Button(row,text=self.T('Detener','Stop'),command=self.stop_live_broadcast).pack(side='left',padx=(4,0))
        columns=('white','black','moves','result')
        self.live_tree=ttk.Treeview(frame,columns=columns,show='headings',height=13,selectmode='browse')
        for key,title,width in [('white',self.T('Blancas','White'),220),('black',self.T('Negras','Black'),220),('moves',self.T('Jugadas','Moves'),80),('result',self.T('Resultado','Result'),100)]:
            self.live_tree.heading(key,text=title);self.live_tree.column(key,width=width,anchor='w')
        self.live_tree.pack(fill='both',expand=True);self.live_tree.bind('<Double-1>',lambda event:self.follow_live_game())
        controls=ttk.Frame(frame);controls.pack(fill='x',pady=(8,3))
        ttk.Button(controls,text=self.T('Seguir partida seleccionada','Follow selected game'),command=self.follow_live_game).pack(side='left')
        ttk.Button(controls,text=self.T('Analizar con motor seleccionado','Analyze with selected engine'),command=lambda:self.analyze(selected_only=True)).pack(side='left',padx=5)
        ttk.Checkbutton(controls,text=self.T('Analizar automáticamente cada nueva jugada','Auto-analyze each new move'),variable=self.live_auto_analyze).pack(side='left',padx=6)
        ttk.Label(frame,textvariable=self.live_status,wraplength=800).pack(anchor='w',pady=(3,0))
        dialog.protocol('WM_DELETE_WINDOW',self.close_live_broadcast_dialog)
        entry.focus_set()
        if self.live_round_id:self.live_status.set(self.T('Ronda conectada; actualizando las partidas cada 8 segundos.','Round connected; refreshing games every 8 seconds.'))
    @staticmethod
    def parse_live_broadcast_source(raw):
        value=raw.strip()
        if not value:raise ValueError('Paste a Lichess broadcast URL or ID.')
        if value.lower().startswith(('lichess.org/','www.lichess.org/')):value='https://'+value
        if '://' in value:
            parsed=urllib.parse.urlparse(value)
            host=(parsed.hostname or '').lower()
            if host not in ('lichess.org','www.lichess.org'):raise ValueError('Use a public lichess.org broadcast link.')
            parts=[part for part in parsed.path.strip('/').split('/') if part]
            if len(parts)<3 or parts[0].lower()!='broadcast':raise ValueError('Use a broadcast round or tournament link from lichess.org.')
            if len(parts)>=4:
                kind='round';identifier=parts[-1]
            else:
                kind='tour';identifier=parts[-1]
        else:
            kind='round';identifier=value
        if not 4<=len(identifier)<=32 or not all(ch.isalnum() or ch in '-_' for ch in identifier):
            raise ValueError('The broadcast ID does not look valid.')
        return kind,identifier
    def start_live_broadcast(self):
        try:kind,identifier=self.parse_live_broadcast_source(self.live_url.get())
        except ValueError:
            messagebox.showerror(self.T('Lichess en vivo','Lichess live'),self.T('Pega un enlace de retransmisión válido de Lichess o el identificador de una ronda.','Paste a valid Lichess broadcast link or a round ID.'),parent=self.live_dialog);return
        self.stop_live_broadcast()
        self.live_token+=1;token=self.live_token;self.live_source_kind=kind;self.live_round_id=identifier
        self.live_follow_key=None;self.live_follow_plies=-1;self.live_follow_result='*';self.live_games=[]
        if self.live_tree is not None:
            for iid in self.live_tree.get_children():self.live_tree.delete(iid)
        stop_event=threading.Event();self.live_stop_event=stop_event
        self.live_status.set(self.T('Conectando y cargando partidas…','Connecting and loading games…'))
        threading.Thread(target=self.live_broadcast_worker,args=(token,kind,identifier,stop_event),daemon=True).start()
    def live_broadcast_worker(self,token,kind,identifier,stop_event):
        endpoint=(f'https://lichess.org/api/broadcast/{identifier}.pgn' if kind=='tour'
                  else f'https://lichess.org/api/broadcast/round/{identifier}.pgn')
        while not stop_event.is_set():
            try:
                request=urllib.request.Request(endpoint,headers={'Accept':'application/x-chess-pgn','User-Agent':'RoboChess/Live (desktop chess study)'})
                with urllib.request.urlopen(request,timeout=20) as response:
                    text=response.read().decode('utf-8-sig',errors='replace')
                stream=io.StringIO(text);games=[]
                while True:
                    game=chess.pgn.read_game(stream)
                    if game is None:break
                    games.append(game)
                self.live_events.put((token,games,None))
            except urllib.error.HTTPError as err:
                message=f'HTTP {err.code}: {err.reason}'
                self.live_events.put((token,[],message))
                if 400<=err.code<500 and err.code!=429:break
            except Exception as err:self.live_events.put((token,[],str(err)))
            if stop_event.wait(8):break
    @staticmethod
    def live_game_key(game):
        headers=game.headers
        return (headers.get('Site',''),headers.get('Round',''),headers.get('White','?'),headers.get('Black','?'))
    def follow_live_game(self):
        if self.live_tree is None:return
        selection=self.live_tree.selection()
        if not selection:return
        try:game=self.live_games[int(selection[0])]
        except (IndexError,ValueError):return
        self.live_follow_key=self.live_game_key(game);self.live_follow_plies=-1;self.live_follow_result='*'
        self.apply_live_game(game,auto_analyze=True)
    def apply_live_game(self,game,auto_analyze=False):
        plies=sum(1 for _ in game.mainline_moves())
        old_plies=self.live_follow_plies;self.live_follow_plies=plies
        self.live_follow_result=game.headers.get('Result','*')
        self.load_review_game(game)
        headers=game.headers
        message=self.T(f"En vivo · {headers.get('White','?')} – {headers.get('Black','?')} · {plies} jugadas · actualiza cada 8 s",
                       f"Live · {headers.get('White','?')} – {headers.get('Black','?')} · {plies} plies · refreshes every 8 s")
        self.status.set(message)
        if auto_analyze and self.live_auto_analyze.get() and (old_plies<0 or plies>old_plies) and headers.get('Result','*')=='*':
            self.w.after(150,lambda:self.analyze(selected_only=True))
    def poll_live_broadcast(self):
        try:
            while True:
                token,games,error=self.live_events.get_nowait()
                if token!=self.live_token:continue
                if error:
                    self.live_status.set(self.T('No se pudo actualizar la retransmisión: ','Could not refresh broadcast: ')+error);continue
                previous_key=self.live_follow_key;self.live_games=games
                if self.live_tree is not None and self.live_tree.winfo_exists():
                    for iid in self.live_tree.get_children():self.live_tree.delete(iid)
                    followed_index=None
                    for index,game in enumerate(games):
                        h=game.headers;plies=sum(1 for _ in game.mainline_moves())
                        key=self.live_game_key(game)
                        if key==previous_key:followed_index=index
                        self.live_tree.insert('','end',iid=str(index),values=(h.get('White','?'),h.get('Black','?'),plies,h.get('Result','*')))
                    if followed_index is not None:
                        iid=str(followed_index);self.live_tree.selection_set(iid);self.live_tree.see(iid)
                        game=games[followed_index]
                        plies=sum(1 for _ in game.mainline_moves())
                        result=game.headers.get('Result','*')
                        if plies!=self.live_follow_plies or result!=self.live_follow_result:
                            self.apply_live_game(game,auto_analyze=True)
                    label=self.T(f'{len(games)} partidas en la retransmisión. Selecciona una y pulsa Seguir.',
                                 f'{len(games)} games in this broadcast. Select one and press Follow.')
                    if previous_key and followed_index is None:label=self.T('La partida seguida ya no aparece en esta retransmisión.','The followed game is no longer in this broadcast.')
                    self.live_status.set(label)
        except queue.Empty:pass
    def stop_live_broadcast(self):
        if self.live_stop_event:self.live_stop_event.set()
        self.live_stop_event=None;self.live_round_id=None;self.live_token+=1
        if hasattr(self,'live_status'):self.live_status.set(self.T('Retransmisión detenida.','Broadcast stopped.'))
    def close_live_broadcast_dialog(self):
        self.stop_live_broadcast()
        dialog=self.live_dialog;self.live_dialog=None;self.live_tree=None
        if dialog is not None and dialog.winfo_exists():dialog.destroy()
    def first_configured_engine(self):
        return next((name for name in self.ENGINE_NAMES if self.paths.get(name)),None)
    @staticmethod
    def plan_en(profile):
        if profile['evaluated']<5:return 'Initial plan: play at least five moves with an engine. Look for checks, captures, and threats before moving. Study the tutor alternative afterward.'
        candidates=[(v['mistakes']/v['evaluated'],v['mistakes'],phase) for phase,v in profile['phases'].items() if v['evaluated']>=3]
        focus=max(candidates)[2] if candidates and max(candidates)[1] else None
        return {'apertura':'Focus: opening. For three games, develop pieces, contest the center, and castle. Review where the evaluation first changed.',
                'medio juego':'Focus: middlegame. Check forcing moves and loose pieces before every turn. Replay positions with mistakes.',
                'final':'Focus: endgame. Practice king activity, passed pawns, and pawn races. Replay difficult endgames.',
                None:'Play three more games at your level and review the tutor lines. There is no clear priority yet.'}[focus]
    def set_language(self,event=None):
        def visit(widget):
            if isinstance(widget,ttk.Notebook):
                for tab in widget.tabs():
                    original=widget.tab(tab,'text')
                    if not hasattr(self,'_tab_labels'):self._tab_labels={}
                    if tab not in self._tab_labels:self._tab_labels[tab]=original
                    widget.tab(tab,text=LABELS.get(self._tab_labels[tab],self._tab_labels[tab]) if self.language.get()=='English' else SPANISH.get(self._tab_labels[tab],self._tab_labels[tab]))
            try:
                original=widget.cget('text')
                if not hasattr(self,'_ui_labels'):self._ui_labels={}
                if widget not in self._ui_labels:self._ui_labels[widget]=original
                widget.configure(text=LABELS.get(self._ui_labels[widget],self._ui_labels[widget]) if self.language.get()=='English' else SPANISH.get(self._ui_labels[widget],self._ui_labels[widget]))
            except (tk.TclError,AttributeError):pass
            for child in widget.winfo_children():visit(child)
        visit(self.w)
        if hasattr(self,'lichess_video'):self.lichess_video.set_language(self.language.get())
        if hasattr(self,'pdf_reader'):self.pdf_reader.set_language()
        if hasattr(self,'study_button'):self.study_button.configure(text=self.T('Estudio','Study'))
        if hasattr(self,'resources_button'):self.resources_button.configure(text=self.T('Recursos','Resources'))
        if hasattr(self,'seconds_label'):self.seconds_label.configure(text=self.T('Segundos por motor:','Seconds / engine:'))
        self._update_video_analysis_title()
        if hasattr(self,'engines_menu'):self.make_menu()
        if not self.playing and not self.puzzle_active:self.status.set(self.T('Selecciona los motores y pulsa Analizar.','Select engines and press Analyze.'))
        if not self.playing:self.put(self.coach_text,self.T('Activa el tutor para recibir consejos. Pulsa Pista o Explicar.','Enable the tutor for advice. Press Hint or Explain.'))
    def portrait(self,filename,max_size):
        path=os.path.join(ROOT,'assets',filename)
        if not os.path.isfile(path):
            img=tk.PhotoImage(width=max_size,height=max_size)
            return img
        source=tk.PhotoImage(file=path)
        factor=max(1,math.ceil(max(source.width(),source.height())/max_size))
        return source.subsample(factor,factor)
    def change_pieces(self,event=None):
        if self.board_view.get()=='3D':self.last_3d_style=self.piece_style.get()
        else:self.last_2d_style=self.piece_style.get()
        self.images.clear();self.draw()
    def _load_piece_image(self,key):
        style=self.piece_style.get()
        folders=[os.path.join(ROOT,'assets','lucas_styles',style)]
        if style=='Nibbler':folders.insert(0,os.path.join(ROOT,'assets'))
        folders.append(os.path.join(ROOT,'assets'))
        for folder in folders:
            path=os.path.join(folder,key+'.png')
            if not os.path.isfile(path):continue
            try:
                source=tk.PhotoImage(file=path)
                factor=max(1,round(max(source.width(),source.height())/max(1,self.square)))
                return source.subsample(factor,factor) if factor>1 else source
            except (tk.TclError,OSError):
                continue
        return None
    def select_board_palette(self,event=None):
        colors=self.BOARD_PALETTES.get(self.board_palette.get())
        if colors:self.set_board_colors(*colors)
    def choose_board_color(self,square):
        current=self.light_square if square=='light' else self.dark_square
        title=self.T('Elige el color de las casillas claras','Choose the light-square color') if square=='light' else self.T('Elige el color de las casillas oscuras','Choose the dark-square color')
        selection=colorchooser.askcolor(color=current,title=title,parent=self.w)
        chosen=selection[1] if selection else None
        if chosen:
            self.board_palette.set('Personalizar / Custom')
            self.set_board_colors(chosen if square=='light' else self.light_square,
                                  chosen if square=='dark' else self.dark_square)
    def set_board_colors(self,light,dark):
        self.light_square=light;self.dark_square=dark
        for attr,color in (('light_color_button',light),('dark_color_button',dark)):
            button=getattr(self,attr,None)
            if button is not None:
                try:button.configure(bg=color,activebackground=color)
                except tk.TclError:pass
        try:board_settings.save(light,dark)
        except OSError as err:self.status.set(self.T('No se pudieron guardar los colores: ','Could not save board colors: ')+str(err))
        self.draw()
    def set_board_view(self,event=None):
        if self.board_view.get()=='3D':
            if self.piece_style.get() not in self.PIECE_3D:self.last_2d_style=self.piece_style.get()
            self.piece_style.set(self.last_3d_style if self.last_3d_style in self.PIECE_3D else 'Staunton 3D')
        else:
            if self.piece_style.get() in self.PIECE_3D:self.last_3d_style=self.piece_style.get()
            self.piece_style.set(self.last_2d_style)
        names=self._piece_style_names()
        for box in (getattr(self,'style_selector',None),getattr(self,'settings_style_selector',None)):
            if box is not None:
                box.configure(values=names,state='readonly')
        self.images.clear();self.draw()
    def book_selected(self,event=None):
        self.book_path=self.book_paths.get(self.book_choice.get(),training_resources.BOOK);self.show_book()
    def training_selected(self,event=None):self.external_training=None
    def choose_book(self):
        path=filedialog.askopenfilename(title='Polyglot .bin',filetypes=[('Polyglot book','*.bin')])
        if path:self.book_path=path;self.book_choice.set(os.path.basename(path));self.show_book()
    def show_book(self):
        self.refresh_opening_tree()
        try:
            moves=training_resources.book_moves(self.board,self.book_path)
            if moves:
                output='\n'.join(f'{san}: {percentage}% ({weight})' for san,weight,percentage in moves[:12])
                self.put(self.resource_text,self.T('Libro de aperturas:','Opening book:')+'\n'+output)
            else:self.put(self.resource_text,self.T('Esta posición no aparece en el libro.','This position is not in the book.'))
        except (OSError,ValueError,IndexError) as err:self.put(self.resource_text,self.T('No se pudo leer el libro: ','Could not read the book: ')+str(err))
    def choose_gaviota(self):
        path=filedialog.askdirectory(title='Gaviota tablebases')
        if path:self.gaviota_path=path;self.show_ending()
    def show_ending(self):
        try:
            wdl,dtm=training_resources.ending(self.board,self.gaviota_path)
            outcome={1:self.T('ganan quienes mueven','side to move wins'),0:self.T('tablas','draw'),-1:self.T('pierden quienes mueven','side to move loses')}[wdl]
            distance=self.T(f'Mate forzado en {abs(dtm)} medias jugadas.',f'Forced mate in {abs(dtm)} half-moves.') if dtm else self.T('Sin mate forzado.','No forced mate.')
            self.put(self.resource_text,self.T('Gaviota: ','Gaviota: ')+outcome+'. '+distance)
        except (OSError,ValueError,KeyError) as err:
            self.put(self.resource_text,self.T('Final no disponible. Se incluyen tablas de hasta cinco piezas. ','Endgame unavailable. Tables for up to five pieces are included. ')+str(err))
    def new_puzzle(self):
        collections=self.training_sets.get(self.training_choice.get())
        if self.external_training:collections=[self.external_training]
        if not collections:
            self.put(self.resource_text,self.T('Selecciona una colección FNS.','Select an FNS collection.'));return
        try:board,solution,credit,path=training_resources.random_exercise(collections)
        except Exception as err:
            self.put(self.resource_text,self.T('No se pudo cargar un ejercicio: ','Could not load an exercise: ')+str(err));return
        moves=training_resources.solution_moves(board,solution)
        try:source_label=str(path.relative_to(training_resources.LUCAS))
        except ValueError:source_label=path.name
        self.stop();self.playing=False;self.play_busy=False;self.selected=None;self.results={};self.final_result=None
        self.board=board;self.puzzle_active='mate' if moves else 'tactic';self.puzzle_moves=moves;self.puzzle_index=0;self.puzzle_color=board.turn;self.puzzle_meta=None
        self.puzzle_mistakes=0;self.puzzle_failed=False;self.puzzle_banner=''
        self.flipped=board.turn==chess.BLACK
        self.side_to_move.set('White' if board.turn else 'Black')
        self.draw();self.show_tools_view();self.tabs.select(self.tabs.tabs()[-1])
        turn=self.puzzle_turn_text(board.turn)
        message=self.T(f'{turn}. Resuelve el ejercicio. Haz clic en origen y destino.',f'{turn}. Solve the exercise. Click the origin and destination squares.')
        if moves:self.status.set(message);self.put(self.resource_text,message+'\n'+credit+'\n'+source_label)
        else:
            name=self.first_configured_engine();engine_path=self.paths.get(name) if name else None
            if not engine_path:
                self.puzzle_active=False;self.put(self.resource_text,self.T('Este ejercicio necesita un motor. Selecciona Stockfish, Crafty o RoboChess.','This exercise needs an engine. Select Stockfish, Crafty or RoboChess.'));return
            self.challenge_best=None;token=self.epoch
            self.status.set(self.T('El motor está preparando este final…','The engine is preparing this endgame…'))
            self.put(self.resource_text,message+'\n'+credit+'\n'+source_label)
            threading.Thread(target=self.challenge_worker,args=(token,name,engine_path,board.copy()),daemon=True).start()
    def choose_training(self):
        path=filedialog.askopenfilename(title='Lucas Chess FNS training',initialdir=str(training_resources.LUCAS),filetypes=[('FNS positions','*.fns')])
        if path:self.external_training=Path(path);self.new_puzzle()
    def puzzle_category_changed(self,event=None):
        choices=lichess_puzzles.PUZZLE_CATEGORIES.get(self.puzzle_category.get(),[])
        self.puzzle_theme_box.configure(values=tuple(label for label,tag in choices))
        if choices:self.puzzle_theme_choice.set(choices[0][0])
    def choose_lichess_puzzle_file(self):
        path=filedialog.askopenfilename(title='Lichess puzzle database',filetypes=[('Lichess puzzle CSV','*.csv *.csv.zst *.csv.gz'),('All files','*.*')])
        if path:
            self.lichess_puzzle_file.set(path)
            self.lichess_puzzle_status.set(self.T('Archivo seleccionado. Los ejercicios se elegirán al azar entre sus primeras posiciones.','Database selected. Puzzles are sampled from its first rows.'))
    def next_lichess_puzzle(self):
        path=self.lichess_puzzle_file.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showinfo('Lichess puzzles',self.T('Elige primero el archivo de puzzles desde el botón Descargar.','First download the puzzle file and choose it here.'));return
        theme=next((tag for label,tag in lichess_puzzles.PUZZLE_CATEGORIES[self.puzzle_category.get()] if label==self.puzzle_theme_choice.get()),'')
        self.lichess_puzzle_token+=1;token=self.lichess_puzzle_token
        self.lichess_puzzle_status.set(self.T('Buscando un puzzle del tema elegido…','Finding a puzzle for the selected theme…'))
        self.status.set(self.T('Leyendo una muestra del archivo de puzzles…','Sampling the puzzle database…'))
        threading.Thread(target=self.lichess_puzzle_worker,args=(token,path,theme),daemon=True).start()
    def lichess_puzzle_worker(self,token,path,theme):
        try:
            row=lichess_puzzles.pick_puzzle(path,theme);row['_SelectedTheme']=theme
        except Exception as err:self.lichess_puzzle_events.put((token,None,str(err)))
        else:self.lichess_puzzle_events.put((token,row,None))
    def poll_lichess_puzzles(self):
        try:
            while True:
                token,row,error=self.lichess_puzzle_events.get_nowait()
                if token!=self.lichess_puzzle_token:continue
                if error:
                    self.lichess_puzzle_status.set(error);self.status.set(error);continue
                try:
                    board=chess.Board(row['FEN']);moves_uci=row['Moves'].split()
                    if len(board.pieces(chess.KING,chess.WHITE))!=1 or len(board.pieces(chess.KING,chess.BLACK))!=1:raise ValueError('Puzzle FEN is missing a king.')
                    if len(moves_uci)<2:raise ValueError('Puzzle has no solution line.')
                    board.push_uci(moves_uci[0])
                    shown=board.copy(stack=False);solution=[]
                    for uci in moves_uci[1:]:
                        move=chess.Move.from_uci(uci)
                        if move not in board.legal_moves:break
                        solution.append(move);board.push(move)
                    if not solution:raise ValueError('Puzzle solution could not be read.')
                    self.stop();self.playing=False;self.play_busy=False;self.results={};self.final_result=None;self.review_game=None
                    self.board=shown;self.selected=None;self.flipped=shown.turn==chess.BLACK
                    self.puzzle_moves=solution;self.puzzle_index=0;self.puzzle_color=shown.turn;self.puzzle_active='lichess';self.puzzle_meta=row
                    self.puzzle_mistakes=0;self.puzzle_failed=False;self.puzzle_banner=''
                    self.side_to_move.set('White' if shown.turn else 'Black')
                    self.draw();self.show_tools_view();self.tabs.select(self.resources_tab)
                    turn=self.puzzle_turn_text(shown.turn)
                    description=(f"Lichess puzzle {row.get('PuzzleId','')} · Elo {row.get('Rating','?')} · {row.get('NbPlays','?')} plays\n"
                                 f"{turn}\nThemes: {row.get('Themes','')}\nGame: {row.get('GameUrl','')}\nFind the best continuation.")
                    self.lichess_puzzle_status.set(description);self.put(self.resource_text,description)
                    self.status.set(turn)
                except Exception as err:
                    self.lichess_puzzle_status.set(self.T('No se pudo iniciar este puzzle: ','Could not start this puzzle: ')+str(err))
        except queue.Empty:pass
    def best_move_challenge(self):
        name=self.first_configured_engine();path=self.paths.get(name) if name else None
        if not path:
            self.put(self.resource_text,self.T('Selecciona un motor primero.','Select an engine first.'));return
        self.stop();self.playing=False;self.play_busy=False;self.selected=None;self.puzzle_active='best';self.challenge_best=None;self.puzzle_meta=None
        self.puzzle_mistakes=0;self.puzzle_failed=False;self.puzzle_banner=''
        token=self.epoch;board=self.board.copy()
        self.put(self.resource_text,self.T('Preparando el ejercicio…','Preparing the challenge…'))
        threading.Thread(target=self.challenge_worker,args=(token,name,path,board),daemon=True).start()
    def challenge_worker(self,token,name,path,board):
        engine=None;work=None
        try:
            engine,work=self.open_engine(name,path)
            info=engine.analyse(board,chess.engine.Limit(time=2.0))
            best=info.get('pv',[None])[0]
            self.challenge_events.put((token,best,None))
        except Exception as err:self.challenge_events.put((token,None,str(err)))
        finally:
            if engine:
                try:engine.quit()
                except Exception:pass
            if work:
                try:work.cleanup()
                except OSError:pass
    def put(self,box,value):
        box.configure(state='normal');box.delete('1.0','end');box.insert('end',value);box.configure(state='disabled')
    def avatar_path(self,key,photo=''):
        if photo and os.path.isfile(photo):return photo
        name=(key or 'robot')+'.png'
        for folder in (os.path.join(ROOT,'avatars'),os.path.join(os.path.dirname(os.path.abspath(__file__)),'avatars')):
            path=os.path.join(folder,name)
            if os.path.isfile(path):return path
        return ''
    def profile_dialog(self,create=False):
        dialog=tk.Toplevel(self.w);dialog.title(self.T('Perfiles de entrenamiento','Training profiles'));dialog.geometry('700x760')
        dialog.transient(self.w)
        self._avatar_images=[]
        frame=ttk.Frame(dialog,padding=14);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text=self.T('Perfiles locales (se guardan en este equipo)','Local profiles (saved on this computer)'),font=('Arial',13,'bold')).pack(anchor='w')
        profiles=self.profile_data['profiles']
        labels=[f"{p['name']} · Elo {p.get('reported_elo') or '—'} · {p.get('gender','')}" for p in profiles]
        active_index=next((i for i,p in enumerate(profiles) if p['id']==self.profile_data.get('active')),0)
        selected=tk.StringVar(value=labels[active_index] if labels else '')
        list_row=ttk.Frame(frame);list_row.pack(fill='x',pady=6)
        ttk.Label(list_row,text=self.T('Perfil','Profile'),width=14).pack(side='left')
        picker=ttk.Combobox(list_row,values=labels,textvariable=selected,state='readonly',width=46)
        picker.pack(side='left',fill='x',expand=True)
        ttk.Separator(frame).pack(fill='x',pady=8)
        ttk.Label(frame,text=self.T('Nuevo perfil / datos','New profile / details'),font=('Arial',11,'bold')).pack(anchor='w')
        name=tk.StringVar();gender=tk.StringVar(value='masculino');elo=tk.StringVar();knows=tk.BooleanVar(value=False)
        avatar=tk.StringVar(value='robot');photo=tk.StringVar(value='')
        if create is False and self.profile:
            name.set(self.profile.get('name',''));gender.set(self.profile.get('gender','otro'))
            elo.set('' if self.profile.get('reported_elo') is None else str(self.profile.get('reported_elo')))
            knows.set(bool(self.profile.get('knows_chess')));avatar.set(self.profile.get('avatar','robot'))
            photo.set(self.profile.get('photo',''))
        form=ttk.Frame(frame);form.pack(fill='x',pady=4)
        ttk.Label(form,text=self.T('Nombre','Name'),width=16).grid(row=0,column=0,sticky='w',pady=2)
        ttk.Entry(form,textvariable=name,width=32).grid(row=0,column=1,sticky='w',pady=2)
        ttk.Label(form,text=self.T('Género','Gender'),width=16).grid(row=1,column=0,sticky='w',pady=2)
        ttk.Combobox(form,textvariable=gender,values=('masculino','femenino','nino','nina','otro'),state='readonly',width=16).grid(row=1,column=1,sticky='w',pady=2)
        ttk.Label(form,text=self.T('Elo (1–4000)','Elo (1–4000)'),width=16).grid(row=2,column=0,sticky='w',pady=2)
        ttk.Entry(form,textvariable=elo,width=10).grid(row=2,column=1,sticky='w',pady=2)
        ttk.Checkbutton(form,text=self.T('Ya sé jugar al ajedrez','I already know how to play chess'),variable=knows).grid(row=3,column=1,sticky='w',pady=4)
        ttk.Label(frame,text=self.T('Avatar','Avatar')).pack(anchor='w',pady=(8,2))
        avatars=ttk.Frame(frame);avatars.pack(fill='x')
        labels_map={'hombre':'Hombre','mujer':'Mujer','nino':'Niño','nina':'Niña','astronauta':'Astronauta','robot':'Robot','duende':'Duende','unicornio':'Unicornio','abuelo':'Abuelo','abuela':'Abuela'}
        for key in profile_store.AVATARS:
            cell=ttk.Frame(avatars);cell.pack(side='left',padx=3,pady=2)
            path=self.avatar_path(key)
            if path:
                try:
                    img=tk.PhotoImage(file=path)
                    if img.width()>72:img=img.subsample(max(1,img.width()//72),max(1,img.height()//72))
                    self._avatar_images.append(img)
                    tk.Radiobutton(cell,image=img,variable=avatar,value=key,indicatoron=False).pack()
                except tk.TclError:
                    ttk.Radiobutton(cell,text=labels_map[key],variable=avatar,value=key).pack()
            else:
                ttk.Radiobutton(cell,text=labels_map[key],variable=avatar,value=key).pack()
            ttk.Label(cell,text=labels_map[key]).pack()
        photo_row=ttk.Frame(frame);photo_row.pack(fill='x',pady=6)
        ttk.Button(photo_row,text=self.T('Usar foto de archivo…','Use photo file…'),command=lambda:photo.set(filedialog.askopenfilename(filetypes=[('Images','*.png *.gif *.jpg *.jpeg')]) or photo.get())).pack(side='left')
        ttk.Label(photo_row,textvariable=photo).pack(side='left',padx=8)
        def activate(profile):
            if profile is not self.profile:
                self.coach_generation+=1;self.feedback_pending=False
            self.profile=profile
            self.profile_data['active']=profile['id'] if profile else None
            try:profile_store.save(self.profile_data)
            except OSError as err:messagebox.showerror('Perfil',str(err),parent=dialog);return
            dialog.destroy()
            self.status.set(self.T(f"Perfil: {profile['name']}. Abre «Perfil / progreso» para consultar tu plan.",f"Profile: {profile['name']}. Open Profile / progress to see your plan.") if profile else self.T('Modo invitado: el entrenamiento no se guardará.','Guest mode: training progress will not be saved.'))
        def create():
            cleaned=name.get().strip()
            if not cleaned or len(cleaned)>60:
                messagebox.showerror(self.T('Perfil','Profile'),self.T('Escribe un nombre de 1 a 60 caracteres.','Enter a name of 1 to 60 characters.'),parent=dialog);return
            rating=elo.get().strip()
            if rating and (not rating.isdigit() or not 1<=int(rating)<=4000):
                messagebox.showerror(self.T('Perfil','Profile'),self.T('El ELO debe ser un número entre 1 y 4000, o dejarse vacío.','Elo must be 1 to 4000, or left blank.'),parent=dialog);return
            try:profile=profile_store.new_profile(self.profile_data,cleaned,knows.get(),int(rating) if rating else None,gender.get(),avatar.get(),photo.get())
            except OSError as err:messagebox.showerror('Perfil',str(err),parent=dialog);return
            activate(profile)
        def use_selected():
            if not labels or selected.get() not in labels:return
            activate(profiles[labels.index(selected.get())])
        def delete_selected():
            if not labels or selected.get() not in labels:return
            target=profiles[labels.index(selected.get())]
            if not messagebox.askyesno('Perfil',self.T(f'¿Borrar el perfil {target["name"]}?','Delete profile {0}?'.format(target['name'])),parent=dialog):return
            try:
                active_id=profile_store.delete_profile(self.profile_data,target['id'])
            except OSError as err:messagebox.showerror('Perfil',str(err),parent=dialog);return
            self.profile=profile_store.find(self.profile_data,active_id)
            dialog.destroy();self.profile_dialog()
        buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=12)
        ttk.Button(buttons,text=self.T('Crear perfil','Create profile'),command=create).pack(side='left')
        ttk.Button(buttons,text=self.T('Usar perfil','Use profile'),command=use_selected).pack(side='left',padx=6)
        ttk.Button(buttons,text=self.T('Borrar perfil','Delete profile'),command=delete_selected).pack(side='left',padx=6)
        ttk.Button(buttons,text=self.T('Invitado','Guest'),command=lambda:activate(None)).pack(side='left',padx=6)
        ttk.Button(buttons,text=self.T('Cerrar','Close'),command=dialog.destroy).pack(side='right')
        if self.profile:
            p=self.profile;q=p['quality'];ph=p['phases']
            theme_progress=p.get('puzzles_by_theme',{});theme_line=', '.join(f'{theme}: {count}' for theme,count in sorted(theme_progress.items(),key=lambda item:item[1],reverse=True)[:5]) or '—'
            details=(f"{p['name']} · ELO declarado: {p.get('reported_elo') or 'sin indicar'}\n"
                     f"Jugadas: {p['moves']} · Pistas: {p['hints']} · Evaluadas: {p['evaluated']}\n"
                     f"Ejercicios resueltos: {p.get('tactics_solved',0)} · Mejores jugadas: {p.get('best_moves_solved',0)}\n"
                     f"Temas de puzzles Lichess: {theme_line}\n"
                     f"Buenas: {q['buena']} · Imprecisiones: {q['imprecision']} · Errores: {q['error']} · Graves: {q['grave']}\n"
                     + 'Por fase: '+', '.join(f"{phase}: {v['mistakes']}/{v['evaluated']} errores" for phase,v in ph.items())
                     +'\n\n'+profile_store.plan(p))
            if self.language.get()=='English':
                details=(f"{p['name']} · Reported Elo: {p.get('reported_elo') or 'not provided'}\n"
                         f"Moves: {p['moves']} · Hints: {p['hints']} · Evaluated: {p['evaluated']}\n"
                         f"Exercises solved: {p.get('tactics_solved',0)} · Best moves: {p.get('best_moves_solved',0)}\n"
                         f"Lichess puzzle themes: {theme_line}\n"
                         f"Good: {q['buena']} · Inaccuracies: {q['imprecision']} · Mistakes: {q['error']} · Serious: {q['grave']}\n"
                         + 'By phase: '+', '.join(f"{phase}: {v['mistakes']}/{v['evaluated']} mistakes" for phase,v in ph.items())
                         +'\n\n'+self.plan_en(p))
            ttk.Label(frame,text=details,wraplength=450,justify='left').pack(anchor='w',pady=8)
        dialog.protocol('WM_DELETE_WINDOW',dialog.destroy)
    def draw(self):
        c=self.canvas;c.delete('all');s=self.square
        last=self.board.move_stack[-1] if self.board.move_stack else None
        for row in range(8):
            for col in range(8):
                sq=chess.square(7-col,row) if self.flipped else chess.square(col,7-row);x=col*s;y=row*s
                c.create_rectangle(x,y,x+s,y+s,fill=(self.light_square if (row+col)%2==0 else self.dark_square),outline='')
                if last and sq in (last.from_square,last.to_square):
                    c.create_rectangle(x+2,y+2,x+s-2,y+s-2,fill='#f4d56b' if sq==last.to_square else '#e7d997',outline='')
                if sq==self.selected:c.create_rectangle(x+2,y+2,x+s-2,y+s-2,outline='#e47e22',width=4)
                p=self.board.piece_at(sq)
                if p:
                    # Nibbler uses uppercase white piece, underscore-prefixed black piece.
                    key=p.symbol().upper() if p.color else '_'+p.symbol().upper()
                    if key not in self.images:
                        self.images[key]=self._load_piece_image(key)
                    if self.images[key] is not None:
                        c.create_image(x+s//2,y+s//2,image=self.images[key])
                    else:
                        # Keep every piece visible even if an optional sprite
                        # was omitted from a user's installation.
                        fill='#f8f5e8' if p.color else '#202632'
                        ink='#17202a' if p.color else '#f5f5f5'
                        d=s*.68
                        c.create_oval(x+(s-d)/2,y+(s-d)/2,x+(s+d)/2,y+(s+d)/2,
                                      fill=fill,outline=ink,width=2)
                        c.create_text(x+s//2,y+s//2,text=p.symbol().upper(),fill=ink,
                                      font=('Arial',max(14,int(s*.42)),'bold'))
                if col==0:c.create_text(x+9,y+12,text=str(8-row),fill='#354139')
                if row==7:c.create_text(x+s-10,y+s-10,text=chr(97+col),fill='#354139')
        self.draw_arrows()
        self.draw_evalbar()
        if self.puzzle_active or self.puzzle_banner:
            turn=self.puzzle_banner or self.puzzle_turn_text(self.board.turn)
            c.create_rectangle(0,0,8*s,28,fill='#1f4b73',outline='')
            c.create_text(4*s,14,text=f'{turn}   ·   Elo {self.puzzle_rating()}',fill='white',font=('Arial',max(11,int(s*0.2)),'bold'))
        self.fen.set(self.board.fen())
        self.side_to_move.set('White' if self.board.turn else 'Black')
        self.refresh_move_list();self.refresh_opening_tree()
    def puzzle_turn_text(self,turn):
        if turn==chess.WHITE:
            return self.T('Juegan las blancas','White to move')
        return self.T('Juegan las negras','Black to move')
    def puzzle_rating(self):
        if self.profile:
            return int(self.profile.get('puzzle_elo') or self.profile.get('reported_elo') or 1200)
        return int(getattr(self,'guest_puzzle_elo',1200))
    def adjust_puzzle_elo(self,delta):
        rating=max(100,self.puzzle_rating()+delta)
        if self.profile:
            self.profile['puzzle_elo']=rating
            try:profile_store.save(self.profile_data)
            except OSError:pass
        else:
            self.guest_puzzle_elo=rating
        return rating
    def reject_puzzle_move(self,move):
        self.play_sound('illegal.wav')
        self.puzzle_mistakes+=1
        self.board.push(move)
        self.puzzle_banner=self.T('Vuelve a intentarlo','Try again')
        self.status.set(self.puzzle_banner)
        self.put(self.resource_text,self.puzzle_banner)
        self.puzzle_undo_token+=1
        token=self.puzzle_undo_token
        self.w.after(700,lambda:self.undo_rejected_puzzle_move(token))
    def undo_rejected_puzzle_move(self,token):
        if token!=self.puzzle_undo_token or not self.puzzle_active:return
        if self.board.move_stack:self.board.pop()
        if self.puzzle_mistakes>=3 and not self.puzzle_failed:
            self.puzzle_failed=True
            rating=self.adjust_puzzle_elo(-12)
            self.puzzle_banner=self.T(f'Vuelve a intentarlo. Elo {rating} (-12)','Try again. Elo {rating} (-12)')
            self.status.set(self.puzzle_banner)
        self.draw()
    def finish_puzzle(self,solved):
        delta=16 if solved and self.puzzle_mistakes==0 else 8 if solved and not self.puzzle_failed else 4 if solved else -12
        rating=self.adjust_puzzle_elo(delta)
        self.puzzle_active=False
        self.puzzle_banner=self.T(f'¡Pasaste! Elo {rating} ({delta:+d})',f'Passed! Elo {rating} ({delta:+d})') if solved else self.T(f'No pasó. Elo {rating} ({delta:+d})',f'Not solved. Elo {rating} ({delta:+d})')
        self.status.set(self.puzzle_banner)
        if self.profile and solved:
            try:
                if self.puzzle_meta:profile_store.record_lichess_puzzle(self.profile_data,self.profile,self.puzzle_meta.get('_SelectedTheme',''))
                else:profile_store.record_exercise(self.profile_data,self.profile,'tactic')
            except OSError:pass
        self.put(self.resource_text,self.puzzle_banner+'\n'+self.T('Cargando el siguiente ejercicio…','Loading the next exercise…'))
        self.draw()
        messagebox.showinfo(self.T('Puzzle','Puzzle'),self.puzzle_banner,parent=self.w)
        if self.puzzle_meta:self.w.after(400,self.next_lichess_puzzle)
        else:self.w.after(400,self.new_puzzle)
    def score_fraction(self,info):
        score=info.get('score') if info else None
        if not score:return None,None
        white=score.white();mate=white.mate()
        if mate is not None:return (0.98 if mate>0 else 0.02),f'M{mate:+d}'
        cp=white.score()
        if cp is None:return None,None
        return 1/(1+math.exp(-max(-3000,min(3000,cp))/350)),f'{cp/100:+.1f}'
    def draw_evalbar(self):
        c=self.evalbar;c.delete('all');height=592;width=40
        def first(name):
            value=self.results.get(name,[])
            return value[0] if isinstance(value,list) and value else value
        available={name:first(name) for name in self.ENGINE_NAMES if first(name)}
        source=available.get('Stockfish') or available.get('RoboChess') or available.get('Crafty') or next(iter(available.values()),None)
        fraction,label=self.score_fraction(source)
        fraction=.5 if fraction is None else fraction
        split=round(height*(1-fraction))
        if self.flipped:
            split=round(height*fraction)
            c.create_rectangle(0,0,width,split,fill='#f6f5e9',outline='')
            c.create_rectangle(0,split,width,height,fill='#2d2b29',outline='')
        else:
            c.create_rectangle(0,0,width,split,fill='#2d2b29',outline='')
            c.create_rectangle(0,split,width,height,fill='#f6f5e9',outline='')
        c.create_rectangle(0,0,width-1,height-1,outline='#777777')
        if label:c.create_text(width//2,max(15,min(height-15,split+17 if split<height//2 else split-17)),text=label,fill=('#eeeeee' if (split<height//2)==self.flipped else '#222222'),font=('Arial',9,'bold'))
        primary_name=next((name for name in ('Stockfish','RoboChess','Crafty') if name in available),next(iter(available),None))
        for name,info in available.items():
            if name==primary_name:continue
            other,_=self.score_fraction(info)
            if other is not None:
                y=round(height*(other if self.flipped else 1-other));c.create_line(1,y,width-1,y,fill=self.engine_color(name),width=4)
        c.create_text(width//2,10,text=('W' if self.flipped else 'B'),fill=('#222222' if self.flipped else '#ffffff'),font=('Arial',9,'bold'))
        c.create_text(width//2,height-10,text=('B' if self.flipped else 'W'),fill=('#ffffff' if self.flipped else '#222222'),font=('Arial',9,'bold'))
    @staticmethod
    def engine_color(name):
        known=App.ENGINE_COLORS.get(name)
        if known:return known
        palette=('#1d7ea8','#bb5870','#7a8c2e','#9365b4','#d18b2c','#3c9b83')
        return palette[sum((i+1)*ord(ch) for i,ch in enumerate(name))%len(palette)]
    def draw_arrows(self):
        c=self.canvas;s=self.square
        groups=[]
        if self.show_stockfish.get():
            lines=self.results.get('Stockfish',[])
            for index,info in enumerate(lines if isinstance(lines,list) else ([lines] if lines else [])):
                if index>=3:break
                pv=info.get('pv',[])
                if pv:groups.append((pv[0],('S'+str(index+1)),['#22a35b','#3983d6','#b29328'][index],index))
        if self.show_crafty.get():
            info=self.results.get('Crafty');info=info[0] if isinstance(info,list) and info else info
            if info and info.get('pv'):groups.append((info['pv'][0],'C','#e77730',3))
        if self.show_robochess.get():
            info=self.results.get('RoboChess');info=info[0] if isinstance(info,list) and info else info
            if info and info.get('pv'):groups.append((info['pv'][0],'R','#9b59b6',4))
        for offset,name in enumerate(self.ENGINE_NAMES[3:],5):
            arrow_var=self.show_engine_arrows.get(name)
            if arrow_var is not None and not arrow_var.get():continue
            info=self.results.get(name);info=info[0] if isinstance(info,list) and info else info
            if info and info.get('pv'):
                groups.append((info['pv'][0],name[:2].upper(),self.engine_color(name),offset))
        for move,label,color,index in groups:
            x1,y1=self.center(move.from_square)
            x2,y2=self.center(move.to_square)
            dx=x2-x1;dy=y2-y1;distance=math.hypot(dx,dy)
            if distance<1:continue
            # Stop before the center so the destination piece remains visible.
            end_x=x2-dx/distance*17;end_y=y2-dy/distance*17
            offset=(index-1)*4 if index<3 else 7
            nx=-dy/distance*offset;ny=dx/distance*offset
            c.create_line(x1+nx,y1+ny,end_x+nx,end_y+ny,fill='#212121',width=7,arrow=tk.LAST,arrowshape=(14,17,6))
            c.create_line(x1+nx,y1+ny,end_x+nx,end_y+ny,fill=color,width=4,arrow=tk.LAST,arrowshape=(12,15,5))
            mx=x1+dx*.53+nx;my=y1+dy*.53+ny
            c.create_oval(mx-12,my-10,mx+12,my+10,fill=color,outline='#222222',width=1)
            c.create_text(mx,my,text=label,fill='white',font=('Arial',8,'bold'))
    def center(self,square):
        file=chess.square_file(square);rank=chess.square_rank(square)
        return ((7-file if self.flipped else file)+.5)*self.square,((rank if self.flipped else 7-rank)+.5)*self.square
    def play_sound(self,filename):
        path=os.path.join(ROOT,'sounds',filename)
        if not os.path.isfile(path):
            path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'sounds',filename)
        if not os.path.isfile(path):return
        try:
            import winsound
            winsound.PlaySound(path,winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
        except Exception:pass
    def sound_for_move(self,board,move):
        if board.is_castling(move):return 'castle.wav'
        if board.is_capture(move):return 'capture1.wav'
        return 'move6.wav'
    def flip_board(self):
        self.flipped=not self.flipped;self.selected=None;self.draw()
    def promotion_choices(self,from_square,to_square):
        piece=self.board.piece_at(from_square)
        if not piece or piece.piece_type!=chess.PAWN:return []
        rank=chess.square_rank(to_square)
        if piece.color==chess.WHITE and rank!=7:return []
        if piece.color==chess.BLACK and rank!=0:return []
        return [move for promo in (chess.QUEEN,chess.ROOK,chess.BISHOP,chess.KNIGHT)
                if (move:=chess.Move(from_square,to_square,promotion=promo)) in self.board.legal_moves]
    def ask_promotion(self,choices):
        labels={chess.QUEEN:('Dama','Queen'),chess.ROOK:('Torre','Rook'),chess.BISHOP:('Alfil','Bishop'),chess.KNIGHT:('Caballo','Knight')}
        dialog=tk.Toplevel(self.w)
        dialog.title(self.T('Coronación','Promotion'))
        dialog.transient(self.w);dialog.resizable(False,False);dialog.grab_set();dialog.attributes('-topmost',True)
        paused=self.playing and self.clock_running is not None
        if paused:self.stop_clock(settle=True)
        chosen={'move':None}
        frame=ttk.Frame(dialog,padding=14);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text=self.T('Elige la pieza de coronación','Choose the promotion piece'),font=('Arial',12,'bold')).pack(anchor='w',pady=(0,8))
        row=ttk.Frame(frame);row.pack()
        def pick(move):
            chosen['move']=move;dialog.destroy()
        for move in choices:
            es,en=labels[move.promotion]
            ttk.Button(row,text=self.T(es,en),width=12,command=lambda m=move:pick(m)).pack(side='left',padx=4)
        ttk.Button(frame,text=self.T('Cancelar','Cancel'),command=dialog.destroy).pack(anchor='e',pady=(10,0))
        dialog.protocol('WM_DELETE_WINDOW',dialog.destroy)
        dialog.update_idletasks()
        x=self.w.winfo_rootx()+(self.w.winfo_width()-dialog.winfo_width())//2
        y=self.w.winfo_rooty()+80
        dialog.geometry(f'+{max(0,x)}+{max(0,y)}')
        self.w.wait_window(dialog)
        if paused and self.playing and chosen['move']:
            self.start_clock(self.board.turn)
        return chosen['move']
    def click(self,event):
        col,row=event.x//self.square,event.y//self.square
        if col not in range(8) or row not in range(8):return
        if self.editor_mode:
            sq=chess.square(7-col,row) if self.flipped else chess.square(col,7-row)
            self.board.remove_piece_at(sq)
            if self.editor_piece:self.board.set_piece_at(sq,self.editor_piece)
            self.draw();return
        if self.playing and not self.puzzle_active and (self.play_busy or self.board.turn!=self.human_color):return
        sq=chess.square(7-col,row) if self.flipped else chess.square(col,7-row)
        if self.selected is None:self.selected=sq;self.draw();return
        move=chess.Move(self.selected,sq)
        promos=self.promotion_choices(self.selected,sq)
        if promos:
            self.selected=None;self.draw()
            self.status.set(self.T('Coronación: elige dama, torre, alfil o caballo.','Promotion: choose queen, rook, bishop or knight.'))
            move=self.ask_promotion(promos)
            if not move:
                self.status.set(self.T('Coronación cancelada.','Promotion cancelled.'));self.draw();return
        else:
            if move not in self.board.legal_moves:move=chess.Move(self.selected,sq,promotion=chess.QUEEN)
            self.selected=None
        if move in self.board.legal_moves:
            if self.puzzle_active:
                if self.puzzle_active=='rush':
                    session=self.rush_session
                    if not session:return
                    if session.get('waiting_engine'):
                        self.status.set(self.T('Espera a que el motor prepare la posición.','Wait for the engine to prepare the position.'));return
                    expected=self.puzzle_moves[self.puzzle_index] if self.puzzle_index<len(self.puzzle_moves) else None
                    if expected is not None and move.from_square==expected.from_square and move.to_square==expected.to_square:
                        first_try=session['attempts_left']==3
                        self.play_sound(self.sound_for_move(self.board,move))
                        self.board.push(move);self.puzzle_index+=1
                        while self.puzzle_index<len(self.puzzle_moves) and self.board.turn!=self.puzzle_color:
                            reply=self.puzzle_moves[self.puzzle_index]
                            if reply not in self.board.legal_moves:break
                            self.play_sound(self.sound_for_move(self.board,reply))
                            self.board.push(reply);self.puzzle_index+=1
                        if self.puzzle_index>=len(self.puzzle_moves):
                            session['solved']+=1
                            session['rating']+=puzzle_rush.rating_change(first_try,session['hint_used'])
                            self.rush_stats['rating']=session['rating'];self._save_puzzle_rush_stats()
                            self.status.set(self.T('¡Correcto! Sigue el próximo puzzle.','Correct! Here comes the next puzzle.'))
                            if self._next_rush_puzzle():
                                self.draw();self.update_puzzle_rush_display()
                            else:
                                self.finish_puzzle_rush('empty')
                        else:
                            self.status.set(self.T('¡Buena jugada! Continúa la combinación.','Good move! Continue the combination.'))
                            self.draw();self.update_puzzle_rush_display()
                    else:
                        session['attempts_left']-=1;session['wrong']+=1
                        if session['attempts_left']<=0:
                            session['rating']=max(100,session['rating']-15)
                            self.rush_stats['rating']=session['rating'];self._save_puzzle_rush_stats()
                            self.finish_puzzle_rush('lost');return
                        self.status.set(self.T(f"No es esa. Intenta otra vez; quedan {session['attempts_left']} oportunidades.",
                                               f"That is not it. Try again; {session['attempts_left']} tries remain."))
                        self.draw();self.update_puzzle_rush_display()
                    return
                if self.puzzle_active=='best':
                    if self.challenge_best is None:
                        self.status.set(self.T('Espera a que el motor prepare el ejercicio.','Wait while the engine prepares the challenge.'));return
                    if move==self.challenge_best:
                        self.play_sound(self.sound_for_move(self.board,move))
                        self.board.push(move)
                        self.finish_puzzle(True)
                    else:
                        self.reject_puzzle_move(move)
                    self.draw();return
                test=self.board.copy();test.push(move)
                self.selected=None
                expected=self.puzzle_moves[self.puzzle_index] if self.puzzle_index<len(self.puzzle_moves) else None
                same=expected is not None and move.from_square==expected.from_square and move.to_square==expected.to_square
                trial=self.board.copy();trial.push(move)
                if same or (not self.puzzle_moves and trial.is_checkmate()):
                    self.play_sound(self.sound_for_move(self.board,move))
                    self.board.push(move);self.puzzle_index+=1
                    while self.puzzle_index<len(self.puzzle_moves) and self.board.turn!=self.puzzle_color:
                        reply=self.puzzle_moves[self.puzzle_index]
                        self.play_sound(self.sound_for_move(self.board,reply))
                        self.board.push(reply);self.puzzle_index+=1
                    if not self.puzzle_moves or self.puzzle_index>=len(self.puzzle_moves) or self.board.is_game_over():
                        self.finish_puzzle(True)
                    else:
                        self.puzzle_banner=self.puzzle_turn_text(self.board.turn)
                        self.status.set(self.T('¡Buena jugada! Sigue la combinación.','Good move! Continue the combination.'))
                else:
                    self.reject_puzzle_move(move)
                self.draw();return
            before=self.board.copy();was_human=self.playing and self.board.turn==self.human_color;self.review_game=None
            if was_human and not self.complete_clock_move(self.board.turn):return
            self.play_sound(self.sound_for_move(self.board,move))
            self.stop();self.results={};self.board.push(move);self.status.set(f'Played {move.uci()}');self.draw()
            if was_human and self.profile:
                try:profile_store.record_move(self.profile_data,self.profile,self.phase_key(before))
                except OSError as err:self.status.set('No se pudo guardar el perfil: '+str(err))
            if was_human and (self.coach_enabled.get() or self.profile):self.request_coach('feedback',before,move)
            if self.board.is_game_over(claim_draw=True):
                self.final_result=self.board.result(claim_draw=True);self.playing=False
                self.stop_clock(settle=False);self.clock_selector.configure(state='readonly')
                self.record_quad_result(self.final_result)
                self.status.set(self.T('Partida terminada: ','Game over: ')+self.final_result)
                self._sync_play_chrome()
            elif self.playing:
                self.start_clock(self.board.turn);self.w.after(100,self.computer_turn)
        else:
            self.play_sound('illegal.wav')
            self.status.set('Illegal move');self.draw()
    def choose(self,name):
        path=filedialog.askopenfilename(title=self.T(f'Elige el ejecutable de {name}',f'Choose {name} executable'),
                                        filetypes=[('Chess engine','*.exe *.bat *.cmd *.py'),('All files','*.*')])
        if not path:return
        self.paths[name]=os.path.abspath(path)
        if name in self.custom_engines:
            self.custom_engines[name]['path']=self.paths[name]
            try:self._save_custom_engines()
            except OSError as err:messagebox.showerror(self.T('No se pudo guardar el motor','Could not save engine'),str(err));return
        self.status.set(f'{name}: {path}')
    def stop(self):
        self.epoch+=1;self.coach_generation+=1;self.feedback_pending=False;self.draw_offer_pending=False
        for engine in list(self.engines.values()):
            try:engine.close()
            except Exception:pass
        self.engines.clear()
    def abort_quad_match(self):
        if self.quad and self.quad.get('active'):
            self.quad['active']=False;self.update_quad_view()
    def stop_action(self):
        self.stop();self.playing=False;self.play_busy=False;self.puzzle_active=False
        self.stop_clock(settle=True);self.clock_selector.configure(state='readonly')
        self.abort_quad_match()
        self.status.set('Stopped.');self.draw();self._sync_play_chrome()
    def reset(self):
        self.stop();self.playing=False;self.play_busy=False;self.puzzle_active=False;self.results={};self.final_result=None;self.review_game=None;self.board.reset()
        self.stop_clock(settle=False);self.clock_selector.configure(state='readonly');self.abort_quad_match();self.draw()
    def undo(self):
        self.stop();self.playing=False;self.play_busy=False;self.puzzle_active=False;self.results={};self.final_result=None
        self.stop_clock(settle=False);self.clock_selector.configure(state='readonly');self.abort_quad_match()
        if self.board.move_stack:self.board.pop()
        self.draw()
    def set_fen(self):
        try:
            board=chess.Board(self.fen.get())
            if len(board.pieces(chess.KING,chess.WHITE))!=1 or len(board.pieces(chess.KING,chess.BLACK))!=1:
                raise ValueError(self.T('El FEN debe incluir un rey blanco y uno negro.','The FEN must contain one White king and one Black king.'))
            board.turn=self.side_to_move.get()=='White';board.clear_stack()
            self.stop();self.playing=False;self.play_busy=False;self.puzzle_active=False;self.results={};self.final_result=None;self.board=board;self.editor_mode=False;self.editor_saved_board=None
            self.review_game=None
            self.editor_palette.pack_forget();self.stop_clock(settle=False);self.clock_selector.configure(state='readonly');self.abort_quad_match();self.draw()
        except (ValueError,AssertionError) as err:messagebox.showerror('FEN',str(err) or 'Invalid position')
    def load_pgn(self):
        path=filedialog.askopenfilename(filetypes=[('PGN files','*.pgn')])
        if not path:return
        try:
            with open(path,encoding='utf-8-sig') as file:game=chess.pgn.read_game(file)
            if game is None:raise ValueError('No game found')
            self.load_review_game(game)
        except Exception as err:messagebox.showerror('PGN',str(err))
    def analyze(self,selected_only=False,engine_name=None):
        self.stop();self.playing=False;self.play_busy=False;self.puzzle_active=False
        self.stop_clock(settle=True);self.clock_selector.configure(state='readonly');self.abort_quad_match();token=self.epoch
        try:seconds=max(1,min(120,int(self.seconds.get())))
        except ValueError:seconds=3
        board=self.board.copy();self.results={};self.draw()
        chosen_name=engine_name or self.engine_view.get()
        names=(chosen_name,) if selected_only else self.ENGINE_NAMES
        if selected_only and chosen_name not in self.ENGINE_NAMES:
            message=self.T(f'El motor seleccionado «{chosen_name}» no está instalado.','The selected engine "{chosen_name}" is not installed.')
            self.put(self.selected_engine_analysis_output(),message);self.status.set(message);return
        if selected_only and not self.paths.get(chosen_name):
            message=self.T(f'No hay un ejecutable configurado para {chosen_name}.','No executable is configured for {chosen_name}.')
            self.put(self.selected_engine_analysis_output(),message);self.status.set(message);return
        self.status.set(self.T('Analizando con {name}…','Analyzing with {name}…').format(name=names[0]) if selected_only else self.T('Analizando…','Analyzing…'))
        if hasattr(self,'video_analysis'):
            self.put(self.selected_engine_analysis_output(),self.T('Analizando posición actual con {name}…','Analyzing current position with {name}…').format(name=names[0]) if selected_only else self.T('Analizando posición actual…','Analyzing current position…'))
        for name in names:
            self.put(self.panels[name],'Analyzing…' if self.paths[name] else 'Choose an executable to enable this engine.')
            if self.paths[name]:threading.Thread(target=self.worker,args=(name,self.paths[name],board.copy(),seconds,token),daemon=True).start()
    def open_engine(self,name,path):
        work=None
        try:
            if name in ('Stockfish','RoboChess') or name in self.custom_engines:
                command=self._uci_command(path) if name in self.custom_engines else path
                engine=chess.engine.SimpleEngine.popen_uci(command,timeout=15)
            else:
                lower=os.path.basename(path).lower()
                if lower.endswith('.py'):
                    engine=chess.engine.SimpleEngine.popen_uci([sys.executable,path],timeout=20)
                elif 'uci' in lower or lower.endswith('.bat') or lower.endswith('.cmd'):
                    engine=chess.engine.SimpleEngine.popen_uci(path,timeout=20)
                else:
                    work=tempfile.TemporaryDirectory(prefix='crafty-analysis-')
                    engine=chess.engine.SimpleEngine.popen_xboard([path,'xboard'] if lower=='crafty.exe' else path,timeout=20,cwd=work.name,env={**os.environ,'CRAFTY_LOG_PATH':'.'})
            return engine,work
        except Exception:
            if work:work.cleanup()
            raise
    def worker(self,name,path,board,seconds,token):
        engine=None;crafty_work=None
        try:
            engine,crafty_work=self.open_engine(name,path)
            if token!=self.epoch:return
            self.engines[name]=engine
            # An opening book returns a move immediately, without a searched
            # principal variation. For analysis, disable an engine's own book
            # so Sargon reports depth, line, evaluation, and an arrowable move.
            if 'OwnBook' in engine.options:
                engine.configure({'OwnBook':False})
            supports_multipv='MultiPV' in engine.options
            result=(engine.analyse(board,chess.engine.Limit(time=seconds),multipv=3) if supports_multipv else engine.analyse(board,chess.engine.Limit(time=seconds)))
            self.events.put((token,name,board,result,None))
        except Exception as err:self.events.put((token,name,board,None,str(err)))
        finally:
            if engine:
                try:engine.quit()
                except Exception:pass
                if self.engines.get(name) is engine:self.engines.pop(name,None)
            if crafty_work:
                try:crafty_work.cleanup()
                except OSError:pass
    @staticmethod
    def clock_text(seconds):
        seconds=max(0,int(math.ceil(seconds)))
        return f'{seconds//60:02d}:{seconds%60:02d}'
    def time_control_changed(self,event=None):
        mode=self.TIME_CONTROLS.get(self.time_control.get(),next(iter(self.TIME_CONTROLS.values())))
        self.move_seconds_control.configure(state='normal' if mode.get('base') is None else 'disabled')
        self.refresh_clock()
    def clock_snapshot(self):
        values=dict(self.clock_remaining)
        if self.clock_running is not None and self.clock_started is not None:
            elapsed=max(0.0,time.monotonic()-self.clock_started-self.clock_mode.get('delay',0))
            values[self.clock_running]=max(0.0,values[self.clock_running]-elapsed)
        return values
    def refresh_clock(self):
        english=getattr(self,'language',None) is not None and self.language.get()=='English'
        if self.clock_mode.get('base') is None:
            self.clock_label.set('Clock: —' if english else 'Reloj: —');return
        values=self.clock_snapshot()
        white='White' if english else 'Blancas';black='Black' if english else 'Negras'
        self.clock_label.set(f"{white} {self.clock_text(values[chess.WHITE])}   {black} {self.clock_text(values[chess.BLACK])}")
    def stop_clock(self,settle=True):
        if self.clock_running is not None and self.clock_started is not None and settle:
            elapsed=max(0.0,time.monotonic()-self.clock_started-self.clock_mode.get('delay',0))
            color=self.clock_running
            self.clock_remaining[color]=max(0.0,self.clock_remaining[color]-elapsed)
        self.clock_running=None;self.clock_started=None
        if self.clock_after is not None:
            try:self.w.after_cancel(self.clock_after)
            except tk.TclError:pass
            self.clock_after=None
        self.refresh_clock()
    def start_clock(self,color):
        if not self.playing or self.clock_mode.get('base') is None:return
        if self.clock_running==color:return
        self.stop_clock(settle=True)
        self.clock_running=color;self.clock_started=time.monotonic();self.refresh_clock();self.schedule_clock_tick()
    def schedule_clock_tick(self):
        if self.playing and self.clock_running is not None and self.clock_after is None:
            self.clock_after=self.w.after(100,self.clock_tick)
    def clock_tick(self):
        self.clock_after=None
        if not self.playing or self.clock_running is None:return
        values=self.clock_snapshot();self.refresh_clock()
        if values[self.clock_running]<=0:
            loser=self.clock_running
            result='0-1' if loser==chess.WHITE else '1-0'
            self.clock_remaining[loser]=0.0
            self.finish_game(result,self.T('Se acabó el tiempo. La partida termina por tiempo.','Time is up. The game ends on time.'))
            return
        self.schedule_clock_tick()
    def complete_clock_move(self,color):
        if self.clock_mode.get('base') is None:return True
        if self.clock_running==color and self.clock_started is not None:
            elapsed=max(0.0,time.monotonic()-self.clock_started-self.clock_mode.get('delay',0))
            self.clock_remaining[color]=max(0.0,self.clock_remaining[color]-elapsed)
        self.stop_clock(settle=False)
        if self.clock_remaining[color]<=0:
            result='0-1' if color==chess.WHITE else '1-0'
            self.finish_game(result,self.T('Se acabó el tiempo. La partida termina por tiempo.','Time is up. The game ends on time.'))
            return False
        cap=self.clock_mode.get('increment_until')
        if cap is None or self.board.fullmove_number<=cap:
            self.clock_remaining[color]+=self.clock_mode.get('increment',0)
        self.refresh_clock()
        return True
    def engine_clock_limit(self,color):
        values=self.clock_snapshot();delay=self.clock_mode.get('delay',0)
        clocks={chess.WHITE:values[chess.WHITE],chess.BLACK:values[chess.BLACK]}
        if self.clock_running==color:clocks[color]+=delay
        increment=self.clock_mode.get('increment',0)
        cap=self.clock_mode.get('increment_until')
        if cap is not None and self.board.fullmove_number>cap:increment=0
        remaining_moves=(cap-self.board.fullmove_number+1) if cap is not None and self.board.fullmove_number<=cap else None
        return chess.engine.Limit(white_clock=clocks[chess.WHITE],black_clock=clocks[chess.BLACK],
                                  white_inc=increment,black_inc=increment,remaining_moves=remaining_moves,
                                  clock_id=(self.board.fullmove_number,color))
    def quad_dialog(self):
        if self.quad_window is not None:
            try:
                if self.quad_window.winfo_exists():self.quad_window.lift();return
            except tk.TclError:pass
        win=tk.Toplevel(self.w);self.quad_window=win
        win.title(self.T('Torneo de entrenamiento','Training tournament'));win.transient(self.w)
        frame=ttk.Frame(win,padding=12);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text=self.T('Torneo local contra motores (entrenamiento de torneo)','Local engine tournament (tournament practice)'),font=('Arial',11,'bold')).pack(anchor='w')
        ttk.Label(frame,text=self.T(
            'Juegas todas las partidas. Cada rival es un motor limitado a un Elo. Al terminar se calcula tu performance y puedes revisar cada PGN.',
            'You play every game. Each opponent is an engine capped to an Elo. At the end you get a performance rating and can review every PGN.')).pack(anchor='w',pady=(3,8))
        form=ttk.Frame(frame);form.pack(fill='x')
        self.quad_name=tk.StringVar(value=(self.profile or {}).get('name','Jugador'))
        default_elo=(self.profile or {}).get('reported_elo') or 1500
        self.quad_rating=tk.StringVar(value=str(min(2400,max(800,int(default_elo)))))
        self.quad_rounds=tk.StringVar(value='5')
        self.quad_spread=tk.StringVar(value='100')
        self.quad_engine=tk.StringVar(value=self.play_engine.get())
        self.quad_time=tk.StringVar(value=self.time_control.get())
        rows=(
            (self.T('Tu nombre','Your name'),ttk.Entry(form,textvariable=self.quad_name,width=22)),
            (self.T('Tu Elo estimado','Your estimated Elo'),ttk.Spinbox(form,from_=800,to=2800,increment=25,textvariable=self.quad_rating,width=8)),
            (self.T('Rondas','Rounds'),ttk.Combobox(form,textvariable=self.quad_rounds,values=('3','4','5','7','9'),state='readonly',width=8)),
            (self.T('Motor de los rivales','Opponent engine'),ttk.Combobox(form,textvariable=self.quad_engine,values=self.ENGINE_NAMES,state='readonly',width=14)),
            (self.T('Ritmo de las partidas','Time control'),ttk.Combobox(form,textvariable=self.quad_time,values=tuple(self.TIME_CONTROLS),state='readonly',width=48)),
            (self.T('Separación Elo entre rivales','Elo gap between opponents'),ttk.Spinbox(form,from_=25,to=200,increment=25,textvariable=self.quad_spread,width=8)),
        )
        for i,(label,widget) in enumerate(rows):
            ttk.Label(form,text=label).grid(row=i,column=0,sticky='w',pady=2,padx=(0,8))
            widget.grid(row=i,column=1,sticky='w',pady=2)
        btns=ttk.Frame(frame);btns.pack(fill='x',pady=8)
        ttk.Button(btns,text=self.T('Crear torneo','Create tournament'),command=self.create_quad).pack(side='left')
        ttk.Button(btns,text=self.T('Revisar partidas','Review games'),command=self.show_tournament_review).pack(side='left',padx=6)
        self.quad_summary=tk.StringVar(value=self.T('Configura Elo, rondas y ritmo, luego crea el torneo.','Set Elo, rounds and time control, then create the event.'))
        ttk.Label(frame,textvariable=self.quad_summary,justify='left',wraplength=640).pack(anchor='w',pady=6)
        self.quad_table=ttk.Label(frame,text='',justify='left',font=('Consolas',10));self.quad_table.pack(anchor='w',fill='x')
        self.quad_notes=tk.Text(frame,height=7,width=84,wrap='word',state='disabled');self.quad_notes.pack(fill='both',expand=True,pady=(8,0))
        self.quad_round_button=ttk.Button(frame,text=self.T('Jugar siguiente ronda','Play next round'),command=self.start_quad_round,state='disabled')
        self.quad_round_button.pack(anchor='w',pady=(8,0))
        win.protocol('WM_DELETE_WINDOW',self.close_quad_window)
        if self.quad:self.update_quad_view()
    def close_quad_window(self):
        if self.quad_window is not None:
            try:self.quad_window.destroy()
            except tk.TclError:pass
        self.quad_window=None;self.quad_summary=None;self.quad_round_button=None
    def _available_engine(self,preferred):
        if self.paths.get(preferred):return preferred
        for name in self.ENGINE_NAMES:
            if self.paths.get(name):return name
        return preferred
    def create_quad(self):
        try:
            rating=int(self.quad_rating.get());rounds=int(self.quad_rounds.get());spread=int(self.quad_spread.get())
        except (ValueError,AttributeError):
            messagebox.showerror('Torneo','Revisa Elo, rondas y separación.');return
        if not 800<=rating<=2800 or rounds not in (3,4,5,7,9) or not 25<=spread<=200:
            messagebox.showerror('Torneo','Elo 800–2800, rondas 3/4/5/7/9, separación 25–200.');return
        engine_name=self._available_engine(self.quad_engine.get());path=self.paths.get(engine_name)
        if not path:
            messagebox.showerror('Motor',self.T(f'Selecciona primero el ejecutable de {engine_name}.',f'Select the {engine_name} executable first.'));return
        name=self.quad_name.get().strip() or 'Jugador'
        opponent_ratings=quad_tournament.section_ratings(rating,count=rounds,spread=spread)
        players=[{'name':name,'rating':rating,'points':0.0,'human':True,'engine':None}]
        for i,elo in enumerate(opponent_ratings):
            players.append({'name':f'{engine_name} {elo}','rating':int(elo),'points':0.0,'human':False,'engine':engine_name})
        self.time_control.set(self.quad_time.get())
        self.quad={
            'players':players,'rounds':rounds,'round_index':0,'active':False,
            'engine':engine_name,'path':path,'played':[],'games':[],'pgns':[],
            'time_control':self.quad_time.get(),'user_elo':rating
        }
        self.update_quad_view();self.start_quad_round()
    def _quad_performance(self):
        if not self.quad:return None
        played=[g for g in self.quad['played'] if g.get('result') in ('1-0','0-1','1/2-1/2')]
        if not played:return None
        opps=[self.quad['players'][g['opponent']]['rating'] for g in played]
        score=sum(g.get('points',0) for g in played)
        return quad_tournament.performance_rating(opps,score),score,len(played),opps
    def update_quad_view(self):
        if not self.quad:return
        rounds=self.quad.get('rounds',3)
        rows=['Pts    Elo   Jugador / Player']
        for place,(index,player) in enumerate(quad_tournament.standings(self.quad['players'],self.quad['games']),1):
            tag=' ★' if player.get('human') else ''
            rows.append(f"{place:>2}. {player['points']:>4.1f}   {player['rating']:>4}   {player['name']}{tag}")
        perf=self._quad_performance()
        if perf:
            rp,score,n,opps=perf
            expected=quad_tournament.expected_score(self.quad['user_elo'],opps)
            rows.append('')
            rows.append(self.T(
                f'Performance estimada: {rp}  ·  Puntos {score:.1f}/{n}  ·  Esperado {expected:.1f} según tu Elo {self.quad["user_elo"]}',
                f'Estimated performance: {rp}  ·  Score {score:.1f}/{n}  ·  Expected {expected:.1f} from your Elo {self.quad["user_elo"]}'))
        try:self.quad_table.configure(text='\n'.join(rows))
        except (tk.TclError,AttributeError):pass
        notes=quad_tournament.training_notes(self.quad['played'],self.language.get())
        try:
            self.quad_notes.configure(state='normal');self.quad_notes.delete('1.0','end');self.quad_notes.insert('1.0',notes);self.quad_notes.configure(state='disabled')
        except (tk.TclError,AttributeError):pass
        if self.quad_summary is not None:
            index=self.quad['round_index']
            if self.quad['active']:
                opp=self.quad['players'][self.quad['current_opponent']]
                text=self.T(
                    f'Ronda {index+1}/{rounds} en curso contra {opp["name"]} (Elo {opp["rating"]}). Juega en el tablero principal.',
                    f'Round {index+1}/{rounds} in progress vs {opp["name"]} (Elo {opp["rating"]}). Play on the main board.')
            elif index<rounds:
                text=self.T(f'Torneo listo · ronda {index+1}/{rounds}. Ritmo: {self.quad["time_control"]}.',
                            f'Tournament ready · round {index+1}/{rounds}. Tempo: {self.quad["time_control"]}.')
            else:
                text=self.T('Torneo terminado. Revisa las partidas y el plan de mejora.','Tournament finished. Review the games and the study plan.')
            self.quad_summary.set(text)
        if self.quad_round_button is not None:
            done=not self.quad['active'] and self.quad['round_index']>=rounds
            try:
                self.quad_round_button.configure(
                    state='normal' if not self.quad['active'] and self.quad['round_index']<rounds else 'disabled',
                    text=self.T('Ver informe final','Open final report') if done else self.T('Jugar ronda ','Play round ')+str(min(rounds,self.quad['round_index']+1)))
            except tk.TclError:pass
    def start_quad_round(self):
        if not self.quad or self.quad['active'] or self.quad['round_index']>=self.quad.get('rounds',3):
            if self.quad and self.quad['round_index']>=self.quad.get('rounds',3):self.show_tournament_review()
            return
        index=self.quad['round_index'];opponent=self.quad['players'][index+1]
        engine=opponent.get('engine') or self.quad['engine']
        self.game_engine_name=engine;self.play_engine.set(engine)
        self.target_elo.set(str(opponent['rating']))
        self.time_control.set(self.quad['time_control'])
        human_white=index%2==0
        self.play_color.set('White' if human_white else 'Black')
        self.quad['active']=True;self.quad['human_color']=chess.WHITE if human_white else chess.BLACK
        self.quad['current_opponent']=index+1;self.quad['current_round']=index
        self.quad_launch=True
        try:self.start_game()
        finally:self.quad_launch=False
        if self.playing:
            self.close_quad_window()
            try:
                self.w.deiconify();self.w.lift();self.w.focus_force()
            except tk.TclError:pass
        self.update_quad_view()
    def _current_game_pgn(self,result):
        game=chess.pgn.Game.from_board(self.board)
        game.headers['Event']='RoboChess training tournament'
        game.headers['TimeControl']=self.pgn_time_control()
        game.headers['TimeMode']=self.time_control.get()
        if result:game.headers['Result']=result
        human_name=(self.profile or {}).get('name',self.quad['players'][0]['name'] if self.quad else 'Human')
        opponent=self.quad['players'][self.quad.get('current_opponent',1)] if self.quad else {'name':self.game_engine_name,'rating':self.target_elo.get()}
        opponent_name=f"{opponent['name']} (Elo {opponent['rating']})"
        if self.quad:game.headers['Round']=str(self.quad.get('current_round',0)+1)
        if self.human_color==chess.WHITE:
            game.headers['White']=human_name;game.headers['Black']=opponent_name
            game.headers['WhiteElo']=str(self.quad['user_elo'] if self.quad else '')
            game.headers['BlackElo']=str(opponent['rating'])
        else:
            game.headers['White']=opponent_name;game.headers['Black']=human_name
            game.headers['WhiteElo']=str(opponent['rating'])
            game.headers['BlackElo']=str(self.quad['user_elo'] if self.quad else '')
        return game
    def record_quad_result(self,result):
        if not self.quad or not self.quad.get('active'):return
        index=self.quad['current_round'];opponent=self.quad['current_opponent']
        human_white=self.quad['human_color']==chess.WHITE
        white=0 if human_white else opponent;black=opponent if human_white else 0
        quad_tournament.award(self.quad['players'],white,black,result)
        game=self._current_game_pgn(result)
        self.quad['games'].append({'white':white,'black':black,'result':result,'estimated':False,'pgn':str(game)})
        self.quad['pgns'].append(str(game))
        self.quad['played'].append({
            'round':index+1,'opponent':opponent,'result':result,'human_white':human_white,
            'points':quad_tournament.result_points_for_human(result,human_white),
            'plies':len(self.board.move_stack),'pgn':str(game),
            'opp_name':self.quad['players'][opponent]['name'],
            'opp_elo':self.quad['players'][opponent]['rating'],
        })
        self.quad['active']=False;self.quad['round_index']=index+1
        self.update_quad_view()
        if self.quad['round_index']>=self.quad.get('rounds',3):
            self.w.after(200,self.show_tournament_review)
        else:
            self.status.set(self.T(
                f'Ronda {index+1} terminada ({result}). Abre Torneo → Abrir panel para la siguiente.',
                f'Round {index+1} finished ({result}). Open Tournament → Open panel for the next round.'))
    def show_tournament_review(self):
        if not self.quad or not self.quad.get('played'):
            messagebox.showinfo('Torneo',self.T('Todavía no hay partidas de torneo para revisar.','There are no tournament games to review yet.'));return
        win=tk.Toplevel(self.w);win.title(self.T('Informe del torneo','Tournament report'));win.geometry('720x520');win.transient(self.w)
        frame=ttk.Frame(win,padding=10);frame.pack(fill='both',expand=True)
        perf=self._quad_performance()
        header=self.T('Informe de entrenamiento','Training report')
        if perf:
            rp,score,n,opps=perf
            header=self.T(
                f'Performance {rp} Elo  ·  {score:.1f}/{n}  ·  Elo medio rivales {int(sum(opps)/n)}',
                f'Performance {rp} Elo  ·  {score:.1f}/{n}  ·  avg opponent {int(sum(opps)/n)}')
        ttk.Label(frame,text=header,font=('Arial',12,'bold')).pack(anchor='w')
        ttk.Label(frame,text=quad_tournament.training_notes(self.quad['played'],self.language.get()),justify='left',wraplength=680).pack(anchor='w',pady=6)
        cols=('round','color','opp','elo','result','pts')
        tree=ttk.Treeview(frame,columns=cols,show='headings',height=10)
        for key,title,width in [('round','Ronda',60),('color','Color',70),('opp','Rival',220),('elo','Elo',60),('result','Resultado',80),('pts','Pts',50)]:
            tree.heading(key,text=title);tree.column(key,width=width,anchor='center')
        tree.pack(fill='both',expand=True,pady=4)
        for i,game in enumerate(self.quad['played']):
            tree.insert('', 'end', iid=str(i), values=(
                game['round'], self.T('Blancas','White') if game.get('human_white') else self.T('Negras','Black'),
                game.get('opp_name',''), game.get('opp_elo',''), game.get('result',''), game.get('points','')))
        def load_selected(event=None):
            selection=tree.selection()
            if not selection:return
            raw=self.quad['played'][int(selection[0])].get('pgn')
            if not raw:return
            game=chess.pgn.read_game(io.StringIO(raw))
            if game:self.load_review_game(game);win.destroy()
        tree.bind('<Double-1>',load_selected)
        bar=ttk.Frame(frame);bar.pack(fill='x',pady=6)
        ttk.Button(bar,text=self.T('Cargar partida seleccionada','Load selected game'),command=load_selected).pack(side='left')
        def save_all():
            path=filedialog.asksaveasfilename(defaultextension='.pgn',filetypes=[('PGN','*.pgn')])
            if not path:return
            with open(path,'w',encoding='utf-8') as out:out.write('\n\n'.join(self.quad.get('pgns') or []))
            self.status.set(self.T('PGN del torneo guardado: ','Tournament PGN saved: ')+path)
        ttk.Button(bar,text=self.T('Guardar todas las partidas PGN','Save all games as PGN'),command=save_all).pack(side='left',padx=6)
        ttk.Label(frame,text=self.T('Doble clic en una fila para cargarla en el tablero y pulsar Analizar.','Double-click a row to load it on the board, then press Analyze.')).pack(anchor='w')
    def engine_match_dialog(self):
        if self.engine_match_window is not None:
            try:
                if self.engine_match_window.winfo_exists():self.engine_match_window.lift();return
            except tk.TclError:pass
        win=tk.Toplevel(self.w);self.engine_match_window=win
        win.title(self.T('Engine Match · partida entre motores','Engine Match · engine vs engine'))
        win.geometry('820x650');win.minsize(720,560);win.transient(self.w)
        frame=ttk.Frame(win,padding=12);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text=self.T('Prueba de fuerza entre dos motores','Playing-strength test between two engines'),font=('Arial',13,'bold')).pack(anchor='w')
        ttk.Label(frame,text=self.T(
            'Juegan partidas automáticamente, alternan colores y cada pareja empieza desde la misma posición de apertura. El Elo es una estimación relativa; usa un motor de referencia con Elo conocido para estimar un valor absoluto.',
            'Engines play automatically, swap colors, and each pair starts from the same opening position. Elo is a relative estimate; use a reference engine with a known Elo to estimate an absolute value.'),wraplength=780,justify='left').pack(anchor='w',pady=(3,8))
        form=ttk.Frame(frame);form.pack(fill='x')
        self.engine_match_a=tk.StringVar(value='Stockfish');self.engine_match_b=tk.StringVar(value='Crafty')
        self.engine_match_count=tk.StringVar(value='20');self.engine_match_time=tk.StringVar(value='Blitz 3+2')
        self.engine_match_move_seconds=tk.StringVar(value='5');self.engine_match_hash=tk.StringVar(value='128')
        self.engine_match_threads=tk.StringVar(value='1');self.engine_match_reference=tk.StringVar(value='')
        self.engine_match_use_book=tk.BooleanVar(value=bool(self.book_path and os.path.isfile(self.book_path)))
        rows=(
            (self.T('Motor A','Engine A'),ttk.Combobox(form,textvariable=self.engine_match_a,values=self.ENGINE_NAMES,state='readonly',width=18)),
            (self.T('Motor B','Engine B'),ttk.Combobox(form,textvariable=self.engine_match_b,values=self.ENGINE_NAMES,state='readonly',width=18)),
            (self.T('Partidas (número par)','Games (even number)'),ttk.Spinbox(form,from_=2,to=1000,increment=2,textvariable=self.engine_match_count,width=9)),
            (self.T('Control de tiempo','Time control'),ttk.Combobox(form,textvariable=self.engine_match_time,values=tuple(self.TIME_CONTROLS),state='readonly',width=50)),
            (self.T('Segundos por jugada (sin reloj)','Seconds per move (no clock)'),ttk.Spinbox(form,from_=1,to=60,textvariable=self.engine_match_move_seconds,width=9)),
            (self.T('Hash por motor (MB)','Hash per engine (MB)'),ttk.Spinbox(form,from_=1,to=4096,textvariable=self.engine_match_hash,width=9)),
            (self.T('Hilos por motor','Threads per engine'),ttk.Spinbox(form,from_=1,to=max(1,os.cpu_count() or 1),textvariable=self.engine_match_threads,width=9)),
            (self.T('Elo conocido del motor B (opcional)','Known Elo for engine B (optional)'),ttk.Entry(form,textvariable=self.engine_match_reference,width=12)),
        )
        for i,(label,widget) in enumerate(rows):
            ttk.Label(form,text=label).grid(row=i,column=0,sticky='w',pady=2,padx=(0,10));widget.grid(row=i,column=1,sticky='w',pady=2)
        ttk.Checkbutton(form,text=self.T('Usar el libro de aperturas seleccionado; mismas posiciones en cada pareja','Use the selected opening book; paired games use the same positions'),variable=self.engine_match_use_book).grid(row=len(rows),column=1,sticky='w',pady=4)
        load_row=ttk.Frame(frame);load_row.pack(fill='x',pady=(3,6))
        ttk.Button(load_row,text=self.T('Elegir ejecutable de A…','Choose A executable…'),command=lambda:self.choose(self.engine_match_a.get())).pack(side='left')
        ttk.Button(load_row,text=self.T('Elegir ejecutable de B…','Choose B executable…'),command=lambda:self.choose(self.engine_match_b.get())).pack(side='left',padx=6)
        path_text='\n'.join(f'{name}: {self.paths.get(name) or self.T("sin seleccionar","not selected")}' for name in self.ENGINE_NAMES)
        ttk.Label(frame,text=path_text,justify='left',wraplength=780,foreground='#555').pack(anchor='w',pady=(0,5))
        self.engine_match_summary=tk.StringVar(value=self.engine_match_summary_text())
        ttk.Label(frame,textvariable=self.engine_match_summary,wraplength=780,justify='left',font=('Arial',10,'bold')).pack(anchor='w',pady=4)
        self.engine_match_log=tk.Text(frame,height=11,wrap='word',state='disabled',font=('Consolas',9));self.engine_match_log.pack(fill='both',expand=True,pady=4)
        actions=ttk.Frame(frame);actions.pack(fill='x',pady=(4,0))
        self.engine_match_start_button=ttk.Button(actions,text=self.T('Iniciar prueba','Start match'),command=self.start_engine_match);self.engine_match_start_button.pack(side='left')
        self.engine_match_stop_button=ttk.Button(actions,text=self.T('Detener','Stop'),command=self.stop_engine_match,state='disabled');self.engine_match_stop_button.pack(side='left',padx=5)
        ttk.Button(actions,text=self.T('Guardar partidas PGN…','Save games as PGN…'),command=self.save_engine_match_pgn).pack(side='left',padx=5)
        ttk.Button(actions,text=self.T('Guardar resultados CSV…','Save results as CSV…'),command=self.save_engine_match_csv).pack(side='left',padx=5)
        win.protocol('WM_DELETE_WINDOW',self.close_engine_match_dialog)
        if self.engine_match_games:self._engine_match_log(self.T('Resultados anteriores de esta sesión cargados.','Previous results from this session are loaded.'))
    def close_engine_match_dialog(self):
        if self.engine_match_window is not None:
            try:self.engine_match_window.destroy()
            except tk.TclError:pass
        self.engine_match_window=None;self.engine_match_log=None;self.engine_match_start_button=None;self.engine_match_stop_button=None
    def _engine_match_log(self,text):
        box=getattr(self,'engine_match_log',None)
        if box is None:return
        try:
            box.configure(state='normal');box.insert('end',str(text)+'\n');box.see('end');box.configure(state='disabled')
        except tk.TclError:pass
    def engine_match_summary_text(self):
        rows=getattr(self,'engine_match_games',[]);config=getattr(self,'engine_match_config',{})
        if not rows:return self.T('Configura los motores y pulsa Iniciar.','Choose engines and press Start.')
        a=config.get('a','Motor A');b=config.get('b','Motor B');n=len(rows)
        wins=sum(r['result']=='1-0' if r['white_engine']==a else r['result']=='0-1' for r in rows)
        losses=sum(r['result']=='0-1' if r['white_engine']==a else r['result']=='1-0' for r in rows)
        draws=n-wins-losses;score=sum(r['score_a'] for r in rows);pct=100*score/n
        p=(score+.5)/(n+1);delta=400*math.log10(p/(1-p))
        se=400/math.log(10)*math.sqrt(1/((n+1)*p*(1-p)));lo=delta-1.96*se;hi=delta+1.96*se
        text=self.T(f'{a}: {wins} victorias · {draws} tablas · {losses} derrotas · {score:.1f}/{n} puntos ({pct:.1f}%). Diferencia Elo estimada: {delta:+.0f} (intervalo aproximado 95%: {lo:+.0f} a {hi:+.0f}).',
                    f'{a}: {wins} wins · {draws} draws · {losses} losses · {score:.1f}/{n} points ({pct:.1f}%). Estimated Elo difference: {delta:+.0f} (approx. 95% interval: {lo:+.0f} to {hi:+.0f}).')
        reference=config.get('reference')
        if reference is not None:
            estimate=reference+delta
            text+='\n'+self.T(f'Elo estimado de {a}: {estimate:.0f}, usando {b} como referencia de {reference}. No es rating oficial.',f'Estimated Elo for {a}: {estimate:.0f}, using {b} as a {reference} reference. This is not an official rating.')
        else:text+='\n'+self.T('Para estimar un Elo absoluto, indica el Elo conocido del motor B.','To estimate an absolute Elo, enter a known rating for engine B.')
        return text
    @staticmethod
    def _engine_match_score(result,white_engine,a):
        if result=='1/2-1/2':return .5
        if result=='*':return 0.0
        white_won=result=='1-0'
        return 1.0 if white_won==(white_engine==a) else 0.0
    @staticmethod
    def _engine_match_opening(reader,rng):
        board=chess.Board();plies=rng.randint(8,14)
        if reader:
            for _ in range(plies):
                try:move=reader.weighted_choice(board).move
                except (IndexError,ValueError):break
                if move not in board.legal_moves:break
                board.push(move)
        board.clear_stack()
        return board
    @staticmethod
    def _engine_match_configure(engine,hash_mb,threads):
        options=getattr(engine,'options',{}) or {};found={str(key).casefold():key for key in options}
        settings={}
        for key,value in (('Hash',hash_mb),('Threads',threads),('OwnBook',False),('UCI_LimitStrength',False)):
            if key.casefold() in found:settings[found[key.casefold()]]=value
        if settings:engine.configure(settings)
        return set(str(k).casefold() for k in settings)
    def start_engine_match(self):
        if self.engine_match_running:return
        if self.playing:
            messagebox.showinfo('Engine Match',self.T('Termina la partida contra el motor antes de iniciar la prueba.','Finish the game against the engine before starting a match.'));return
        a=self.engine_match_a.get();b=self.engine_match_b.get();path_a=self.paths.get(a);path_b=self.paths.get(b)
        if not path_a or not os.path.isfile(path_a) or not path_b or not os.path.isfile(path_b):
            messagebox.showerror('Engine Match',self.T('Selecciona ejecutables válidos para ambos motores en este panel o en Motores.','Choose valid executables for both engines here or from the Engines menu.'));return
        if os.path.normcase(os.path.abspath(path_a))==os.path.normcase(os.path.abspath(path_b)):
            messagebox.showerror('Engine Match',self.T('Los dos motores apuntan al mismo archivo. Selecciona dos ejecutables distintos.','Both engines point to the same file. Select two different executables.'));return
        try:
            count=int(self.engine_match_count.get());move_seconds=max(1,min(60,int(self.engine_match_move_seconds.get())))
            hash_mb=max(1,min(4096,int(self.engine_match_hash.get())));threads=max(1,min(os.cpu_count() or 1,int(self.engine_match_threads.get())))
            reference=int(self.engine_match_reference.get()) if self.engine_match_reference.get().strip() else None
            if count<2 or count>1000 or count%2:raise ValueError('Game count must be an even number from 2 to 1000.')
            if reference is not None and not 1<=reference<=5000:raise ValueError('Reference Elo must be from 1 to 5000.')
        except ValueError as err:messagebox.showerror('Engine Match',str(err));return
        if self.engine_match_time.get() not in self.TIME_CONTROLS:messagebox.showerror('Engine Match','Select a valid time control.');return
        if self.engine_match_use_book.get() and (not self.book_path or not os.path.isfile(self.book_path)):
            messagebox.showerror('Engine Match',self.T('El libro de aperturas seleccionado no se encuentra. Selecciona otro libro o desactiva la casilla.','The selected opening book was not found. Choose another book or turn off the checkbox.'));return
        if self.engine_match_stop:self.engine_match_stop.set()
        self.stop();self.engine_match_token+=1;token=self.engine_match_token
        cancel=threading.Event();self.engine_match_stop=cancel;self.engine_match_running=True;self.engine_match_games=[]
        self.engine_match_config={'a':a,'b':b,'reference':reference,'count':count,'time_control':self.engine_match_time.get()}
        self.engine_match_summary.set(self.T('Preparando la serie…','Preparing the match…'))
        try:
            self.engine_match_log.configure(state='normal');self.engine_match_log.delete('1.0','end');self.engine_match_log.configure(state='disabled')
        except (tk.TclError,AttributeError):pass
        self._engine_match_log(self.T(f'Prueba iniciada: {a} vs {b}, {count} partidas; colores alternados.','Match started: {a} vs {b}, {count} games; colors alternate.').format(a=a,b=b,count=count))
        self.engine_match_start_button.configure(state='disabled');self.engine_match_stop_button.configure(state='normal')
        args=(token,cancel,a,b,path_a,path_b,count,self.engine_match_time.get(),move_seconds,hash_mb,threads,self.book_path if self.engine_match_use_book.get() else None)
        self.engine_match_thread=threading.Thread(target=self.engine_match_worker,args=args,daemon=True);self.engine_match_thread.start()
    def stop_engine_match(self):
        if self.engine_match_stop:self.engine_match_stop.set()
        self._engine_match_log(self.T('Detención solicitada; se finalizará la jugada actual.','Stop requested; the current engine move will finish first.'))
    def engine_match_worker(self,token,cancel,a,b,path_a,path_b,count,time_name,move_seconds,hash_mb,threads,book_path):
        reader=None;completed=0;rng=random.Random()
        try:
            if book_path:
                try:reader=chess.polyglot.open_reader(book_path)
                except Exception as err:self.engine_match_events.put((token,'status',f'Opening book unavailable; using the initial position: {err}'))
            mode=self.TIME_CONTROLS[time_name]
            pair_board=None;last_pair=-1
            for number in range(count):
                if cancel.is_set():break
                pair=number//2
                if pair!=last_pair:
                    pair_board=self._engine_match_opening(reader,rng) if book_path else chess.Board()
                    last_pair=pair
                board=pair_board.copy(stack=True)
                a_color=chess.WHITE if number%2==0 else chess.BLACK
                white_engine=a if a_color else b;black_engine=b if a_color else a
                engines={};works={};termination='normal'
                try:
                    engines[a],works[a]=self.open_engine(a,path_a)
                    engines[b],works[b]=self.open_engine(b,path_b)
                    opts_a=self._engine_match_configure(engines[a],hash_mb,threads)
                    opts_b=self._engine_match_configure(engines[b],hash_mb,threads)
                    if number==0 and ('hash' not in opts_a or 'hash' not in opts_b):
                        self.engine_match_events.put((token,'status','One or both engines do not expose a Hash option; requested memory could not be applied to both.'))
                    clocks={chess.WHITE:float(mode['base'] or 0),chess.BLACK:float(mode['base'] or 0)}
                    max_plies=400
                    for ply in range(max_plies):
                        if cancel.is_set():break
                        if board.is_game_over(claim_draw=True):break
                        color=board.turn;engine=engines[a] if color==a_color else engines[b]
                        if mode['base'] is None:limit=chess.engine.Limit(time=move_seconds)
                        else:
                            delay=float(mode.get('delay',0));inc=float(mode.get('increment',0));cap=mode.get('increment_until')
                            if cap is not None and board.fullmove_number>cap:inc=0
                            limit=chess.engine.Limit(
                                white_clock=clocks[chess.WHITE]+(delay if color==chess.WHITE else 0),
                                black_clock=clocks[chess.BLACK]+(delay if color==chess.BLACK else 0),
                                white_inc=inc,black_inc=inc)
                        started=time.monotonic();played=engine.play(board,limit)
                        if mode['base'] is not None:
                            elapsed=max(0.0,time.monotonic()-started-float(mode.get('delay',0)))
                            clocks[color]=max(0.0,clocks[color]-elapsed)
                            if clocks[color]<=0:
                                termination='time forfeit';break
                            cap=mode.get('increment_until')
                            if cap is None or board.fullmove_number<=cap:clocks[color]+=float(mode.get('increment',0))
                        move=played.move
                        if move is None or move not in board.legal_moves:
                            termination='engine forfeit';break
                        board.push(move)
                        if ply%8==7:self.engine_match_events.put((token,'status',f'Partida / Game {number+1}/{count}: jugada / move {board.fullmove_number}.'))
                    if cancel.is_set():break
                    if termination in ('time forfeit','engine forfeit'):
                        winner=not board.turn;result='1-0' if winner==chess.WHITE else '0-1'
                    elif board.is_game_over(claim_draw=True):result=board.result(claim_draw=True)
                    else:result='1/2-1/2';termination='move limit'
                    game=chess.pgn.Game.from_board(board)
                    game.headers['Event']='RoboChess Engine Match';game.headers['Round']=str(number+1)
                    game.headers['White']=white_engine;game.headers['Black']=black_engine;game.headers['Result']=result
                    game.headers['TimeMode']=time_name;game.headers['TimeControl']=f"{mode['base'] or move_seconds}+{mode.get('increment',0)}"
                    game.headers['Termination']=termination
                    game.headers['WhiteEngine']=str(engines[white_engine].id.get('name',white_engine))
                    game.headers['BlackEngine']=str(engines[black_engine].id.get('name',black_engine))
                    if book_path:game.headers['OpeningBook']=os.path.basename(os.fspath(book_path))
                    pgn=io.StringIO();print(game,file=pgn,end='\n\n')
                    row={'round':number+1,'white_engine':white_engine,'black_engine':black_engine,'result':result,
                         'score_a':self._engine_match_score(result,white_engine,a),'plies':len(board.move_stack),'termination':termination,'pgn':pgn.getvalue()}
                    completed+=1;self.engine_match_events.put((token,'game',row))
                finally:
                    for name,engine in engines.items():
                        try:engine.quit()
                        except Exception:pass
                    for work in works.values():
                        if work:
                            try:work.cleanup()
                            except OSError:pass
            self.engine_match_events.put((token,'done',{'completed':completed,'cancelled':cancel.is_set()}))
        except Exception as err:self.engine_match_events.put((token,'error',str(err)))
        finally:
            if reader:
                try:reader.close()
                except Exception:pass
    def poll_engine_match(self):
        try:
            while True:
                token,kind,payload=self.engine_match_events.get_nowait()
                if token!=self.engine_match_token:continue
                if kind=='status':self._engine_match_log(payload)
                elif kind=='game':
                    self.engine_match_games.append(payload)
                    self._engine_match_log(self.T(f"Partida {payload['round']}: {payload['white_engine']}–{payload['black_engine']} · {payload['result']} · {payload['plies']} medias jugadas.",f"Game {payload['round']}: {payload['white_engine']}–{payload['black_engine']} · {payload['result']} · {payload['plies']} plies."))
                    self.engine_match_summary.set(self.engine_match_summary_text())
                elif kind=='error':
                    self.engine_match_running=False;self._engine_match_log(self.T('Error del motor: ','Engine error: ')+payload)
                    self.engine_match_summary.set(self.engine_match_summary_text())
                    if self.engine_match_start_button:self.engine_match_start_button.configure(state='normal')
                    if self.engine_match_stop_button:self.engine_match_stop_button.configure(state='disabled')
                elif kind=='done':
                    self.engine_match_running=False
                    text=self.T(f"Prueba detenida: {payload['completed']} partidas completas.",f"Match stopped: {payload['completed']} completed games.") if payload['cancelled'] else self.T(f"Prueba terminada: {payload['completed']} partidas.",f"Match complete: {payload['completed']} games.")
                    self._engine_match_log(text);self.engine_match_summary.set(self.engine_match_summary_text())
                    if self.engine_match_start_button:self.engine_match_start_button.configure(state='normal')
                    if self.engine_match_stop_button:self.engine_match_stop_button.configure(state='disabled')
        except queue.Empty:pass
    def save_engine_match_pgn(self):
        if not self.engine_match_games:messagebox.showinfo('Engine Match',self.T('Todavía no hay partidas para guardar.','There are no games to save yet.'));return
        path=filedialog.asksaveasfilename(defaultextension='.pgn',filetypes=[('PGN','*.pgn')])
        if not path:return
        try:
            with open(path,'w',encoding='utf-8') as out:out.write('\n'.join(row['pgn'] for row in self.engine_match_games))
            self.status.set(self.T('Partidas guardadas: ','Games saved: ')+path)
        except OSError as err:messagebox.showerror('Engine Match',str(err))
    def save_engine_match_csv(self):
        if not self.engine_match_games:messagebox.showinfo('Engine Match',self.T('Todavía no hay resultados para guardar.','There are no results to save yet.'));return
        path=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')])
        if not path:return
        try:
            with open(path,'w',newline='',encoding='utf-8-sig') as out:
                writer=csv.writer(out);writer.writerow(('Round','White engine','Black engine','Result','Score for engine A','Plies','Termination'))
                for row in self.engine_match_games:writer.writerow(tuple(row[key] for key in ('round','white_engine','black_engine','result','score_a','plies','termination')))
                writer.writerow(());writer.writerow(('Summary',self.engine_match_summary_text()))
            self.status.set(self.T('Resultados guardados: ','Results saved: ')+path)
        except OSError as err:messagebox.showerror('Engine Match',str(err))
    def personalities_dialog(self):
        players=personalities.PLAYERS
        dialog=tk.Toplevel(self.w)
        dialog.title(self.T('Personalidades','Personalities'))
        dialog.transient(self.w);dialog.grab_set();dialog.geometry('980x680')
        dialog.configure(bg='#f4f5f7')
        selected={'player':players[2]}
        left=ttk.Frame(dialog);left.pack(side='left',fill='both',expand=True,padx=8,pady=8)
        canvas=tk.Canvas(left,width=390,highlightthickness=0,bg='#f4f5f7')
        scroll=ttk.Scrollbar(left,orient='vertical',command=canvas.yview)
        grid=ttk.Frame(canvas)
        grid.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0,0),window=grid,anchor='nw')
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        right=ttk.Frame(dialog);right.pack(side='right',fill='both',expand=True,padx=12,pady=12)
        portrait=ttk.Label(right);portrait.pack(anchor='w')
        heading=ttk.Frame(right);heading.pack(anchor='w',fill='x',pady=(8,0))
        flag=ttk.Label(heading);flag.pack(side='left',padx=(0,8))
        name_var=tk.StringVar();title_var=tk.StringVar();info_var=tk.StringVar()
        ttk.Label(heading,textvariable=name_var,font=('Segoe UI',16,'bold')).pack(side='left')
        ttk.Label(right,textvariable=title_var,wraplength=460).pack(anchor='w')
        ttk.Label(right,textvariable=info_var,justify='left',wraplength=460).pack(anchor='w',pady=8)
        def load_image(path,max_size):
            if not path:return None
            key=(path,max_size)
            if key in self.personality_images:return self.personality_images[key]
            image=tk.PhotoImage(file=path)
            factor=max(1,math.ceil(max(image.width(),image.height())/max_size))
            image=image.subsample(factor,factor)
            self.personality_images[key]=image
            return image
        cards={}
        def show(player):
            selected['player']=player
            for pid,card in cards.items():
                card.configure(relief='solid' if pid==player['id'] else 'flat',borderwidth=2 if pid==player['id'] else 1)
            photo=load_image(personalities.portrait_path(player),220)
            if photo:portrait.configure(image=photo)
            flag_image=load_image(personalities.flag_path(player),64)
            if flag_image:flag.configure(image=flag_image)
            name_var.set(player['name'])
            title_var.set(personalities.display_text(player,'title',self.language.get()))
            info_var.set(
                f"{personalities.display_text(player,'country',self.language.get())}\n"
                f"{self.T('Elo','Elo')}  {player['elo']}\n\n"
                f"{self.T('Estilo de juego','Playing style')}\n"
                f"{personalities.display_text(player,'style',self.language.get())}\n\n"
                f"{self.T('Con blancas','With White')}\n{player['white']}\n"
                f"{self.T('Con negras','With Black')}\n{player['black']}"
            )
        for index,player in enumerate(players):
            card=tk.Frame(grid,bd=1,relief='flat',bg='white',highlightbackground='#d0d4da',highlightthickness=1)
            card.grid(row=index//3,column=index%3,padx=6,pady=6)
            thumb=load_image(personalities.thumb_path(player),132)
            label=tk.Label(card,image=thumb,bg='white',cursor='hand2') if thumb else tk.Label(card,text=player['id'][:1],width=8,height=4,bg='white')
            label.pack()
            tk.Label(card,text=player['id'],bg='white',font=('Segoe UI',9)).pack()
            label.bind('<Button-1>',lambda e,p=player:show(p))
            card.bind('<Button-1>',lambda e,p=player:show(p))
            cards[player['id']]=card
        show(players[2])
        buttons=ttk.Frame(dialog);buttons.pack(side='bottom',fill='x',padx=12,pady=10)
        def play(color):
            player=selected['player']
            if not self.paths.get(self.play_engine.get()):
                messagebox.showinfo(self.T('Personalidades','Personalities'),self.T('Selecciona primero un motor en Motores.','Select an engine under Engines first.'))
                return
            self.personality=player
            self.personality_book=personalities.book_path(player)
            self.personality_launch=True
            self.play_color.set(color)
            self.target_elo.set(str(player['elo']))
            dialog.destroy()
            self.start_game()
        ttk.Button(buttons,text=self.T('Jugar con blancas','Play as White'),command=lambda:play('White')).pack(side='left',padx=4)
        ttk.Button(buttons,text=self.T('Jugar con negras','Play as Black'),command=lambda:play('Black')).pack(side='left',padx=4)
        ttk.Button(buttons,text=self.T('Cancelar','Cancel'),command=dialog.destroy).pack(side='right',padx=4)
        dialog.wait_window()
    def start_game(self):
        if self.quad and not self.quad_launch:self.quad=None
        if not self.personality_launch:self.personality=None;self.personality_book=None
        self.personality_launch=False
        name=self.play_engine.get();path=self.paths.get(name)
        if not path:
            self.status.set(f'Select a {name} executable first.');return
        try:
            level=int(self.target_elo.get());seconds=int(self.move_seconds.get())
            if not 1<=level<=3800 or not 1<=seconds<=60:raise ValueError
        except ValueError:
            messagebox.showerror('Level','Use level 1–3800 and 1–60 seconds per move.');return
        self.stop();self.stop_clock(settle=False)
        self.clock_mode=self.TIME_CONTROLS.get(self.time_control.get(),next(iter(self.TIME_CONTROLS.values())))
        base=self.clock_mode.get('base')
        self.clock_remaining={chess.WHITE:float(base or 0),chess.BLACK:float(base or 0)}
        self.board.reset();self.results={};self.selected=None;self.final_result=None;self.puzzle_active=False;self.review_game=None
        self.play_sound('newgame.wav')
        self.playing=True;self.play_busy=False;self.game_engine_name=name;self.coach_generation+=1
        self.human_color=chess.WHITE if self.play_color.get()=='White' else chess.BLACK
        self.flipped=self.human_color==chess.BLACK
        self.clock_selector.configure(state='disabled')
        if self.quad and self.quad_launch:
            opponent=self.quad['players'][self.quad['current_opponent']]
            match=f"{opponent['name']} (Elo {opponent['rating']})"
            self.status.set(f"Quad · ronda {self.quad['current_round']+1}/3 · {match}. "+self.T('Te toca mover.','Your move.') if self.human_color==chess.WHITE else f"Quad · ronda {self.quad['current_round']+1}/3 · {match}. "+self.T('El motor piensa…','The engine is thinking…'))
        else:
            who=self.personality['name'] if self.personality else name
            self.status.set(self.T(f'Jugando contra {who}, nivel {level}. Te toca mover.',f'Playing against {who}, level {level}. Your turn.') if self.human_color==chess.WHITE else self.T(f'Jugando contra {who}, nivel {level}. El motor piensa…',f'Playing against {who}, level {level}. Engine thinking…'))
        photo=self.personality_images.get((personalities.portrait_path(self.personality),420)) if self.personality else None
        self.opponent_image.configure(image=photo or self.coach_images[name])
        self.mood.set(f"{self.personality['name']}: Elo {self.personality['elo']}" if self.personality else self.T(f'{name}: 😐 listo para jugar',f'{name}: 😐 ready to play'))
        if self.coach_enabled.get():self.show_tools_view();self.tabs.select(self.tutor_tab)
        self.draw()
        if self.human_color==chess.BLACK:self.w.after(100,self.computer_turn)
        else:self.start_clock(self.board.turn)
        self._sync_play_chrome()
    def save_game(self):
        path=filedialog.asksaveasfilename(defaultextension='.pgn',filetypes=[('PGN','*.pgn')])
        if not path:return
        game=chess.pgn.Game.from_board(self.board)
        game.headers['Event']='Personality game' if self.personality else ('Quad training tournament' if self.quad else 'Game vs chess engine')
        game.headers['TimeControl']=self.pgn_time_control()
        game.headers['TimeMode']=self.time_control.get()
        if self.quad:game.headers['Round']=str(self.quad.get('current_round',0)+1)
        if self.final_result:game.headers['Result']=self.final_result
        name=self.game_engine_name
        human_name=(self.profile or {}).get('name','Human')
        opponent_name=self.personality['name'] if self.personality else name
        if self.quad:
            opponent=self.quad['players'][self.quad.get('current_opponent',1)]
            opponent_name=f"{opponent['name']} (Elo {opponent['rating']}) · {name}"
        if self.human_color==chess.WHITE:
            game.headers['White']=human_name;game.headers['Black']=opponent_name
        else:
            game.headers['White']=opponent_name;game.headers['Black']=human_name
        with open(path,'w',encoding='utf-8') as file:print(game,file=file,end='\n\n')
        self.status.set(self.T('Partida guardada: ','Saved game: ')+path)
    def end_game(self):
        self.stop();self.playing=False;self.play_busy=False;self.selected=None
        self.stop_clock(settle=True);self.clock_selector.configure(state='readonly')
        self.abort_quad_match()
        self.status.set(self.T('Partida terminada. Puedes analizar o iniciar otra.','Game ended. You can analyze or start a new game.'));self.draw()
        self._sync_play_chrome()
    def takeback(self):
        if not self.playing or not self.board.move_stack:
            self.status.set(self.T('Inicia una partida antes de retirar una jugada.','Start a game before taking back a move.'));return
        self.stop_clock(settle=True);self.stop();self.play_busy=False;self.results={};self.selected=None;self.final_result=None
        self.board.pop()
        if self.board.move_stack and self.board.turn!=self.human_color:self.board.pop()
        self.draw()
        if self.board.turn!=self.human_color:
            self.status.set(self.T('Jugada retirada. El motor volverá a mover.','Move taken back. The engine will play again.'))
            self.start_clock(self.board.turn);self.w.after(100,self.computer_turn)
        else:
            self.start_clock(self.board.turn);self.status.set(self.T('Jugada retirada. Te toca mover.','Move taken back. Your turn.'))
    def finish_game(self,result,message):
        self.stop();self.playing=False;self.play_busy=False;self.selected=None;self.final_result=result
        self.stop_clock(settle=True);self.clock_selector.configure(state='readonly')
        self.record_quad_result(result)
        self.status.set(message);self.put(self.coach_text,message);self.show_tools_view();self.tabs.select(self.tutor_tab);self.draw()
        self._sync_play_chrome()
    def pgn_time_control(self):
        mode=self.clock_mode
        if mode.get('base') is None:return '?'
        cap=mode.get('increment_until')
        if mode.get('delay'):return f"{int(mode['base'])}+0"
        if cap is not None:return f"{cap}/{int(mode['base'])}+{int(mode['increment'])}"
        return f"{int(mode['base'])}+{int(mode['increment'])}"
    def resign(self):
        if not self.playing:return
        result='0-1' if self.human_color==chess.WHITE else '1-0'
        self.finish_game(result,self.T('Lo siento. ¡Analicemos la partida juntos! Pulsa Analizar para comparar las jugadas.','I am sorry. Let us analyze the game together! Press Analyze to compare the moves.'))
    def offer_draw(self):
        if not self.playing or self.play_busy or self.draw_offer_pending or self.board.turn!=self.human_color or self.board.is_game_over(claim_draw=True):
            self.status.set(self.T('Espera tu turno para ofrecer tablas.','Wait for your turn to offer a draw.'));return
        self.draw_offer_pending=True;token=self.epoch;board=self.board.copy();name=self.game_engine_name
        self.status.set(self.T(f'{name} está considerando las tablas…',f'{name} is considering your draw offer…'))
        threading.Thread(target=self.draw_worker,args=(token,name,self.paths[name],board),daemon=True).start()
    def draw_worker(self,token,name,path,board):
        engine=None;work=None
        try:
            engine,work=self.open_engine(name,path)
            info=engine.analyse(board,chess.engine.Limit(time=1.0))
            cp=self.pov_cp(info,not self.human_color)
            # A training opponent only accepts when worse, or late in a balanced game.
            accept=cp is not None and (cp<=-150 or (board.fullmove_number>=25 and abs(cp)<=35))
            self.draw_events.put((token,accept,None))
        except Exception as err:self.draw_events.put((token,False,str(err)))
        finally:
            if engine:
                try:engine.quit()
                except Exception:pass
            if work:
                try:work.cleanup()
                except OSError:pass
    def effective_level(self,name,level):
        if name in self.custom_engines:return level,0.0
        if name=='RoboChess':
            # This legacy engine has no Elo UCI option. Map the UI slider to a
            # documented search-depth cap; it is not calibrated Elo.
            return max(5,min(32,5+round(level*27/3800))),0.0
        floor=1320 if name=='Stockfish' else 800
        ceiling=3190 if name=='Stockfish' else 3600
        # Outside each engine's supported rating range the control is a handicap scale.
        random_chance=max(0,min(.95,(floor-level)/floor*.95))
        return min(max(level,floor),ceiling),random_chance
    def computer_turn(self):
        if not self.playing or self.play_busy or self.board.turn==self.human_color:return
        if self.board.is_game_over(claim_draw=True):self.status.set(f'Game over: {self.board.result(claim_draw=True)}');return
        book=getattr(self,'personality_book',None)
        if self.personality and book:
            move=personalities.book_move(book,self.board)
            if move:
                self.play_events.put((self.epoch,move,None))
                self.status.set(self.T(f"{self.personality['name']} juega de su libro.","{name} plays from the opening book.").format(name=self.personality['name']))
                return
        self.start_clock(self.board.turn)
        name=self.game_engine_name;path=self.paths.get(name)
        try:level=int(self.target_elo.get());seconds=int(self.move_seconds.get())
        except ValueError:level,seconds=1500,5
        level=max(1,min(3800,level));seconds=max(1,min(60,seconds))
        token=self.epoch;self.play_busy=True;self.status.set(self.T(f'{name} piensa (nivel {level})…',f'{name} thinking (level {level})…'))
        limit=self.engine_clock_limit(self.board.turn) if self.clock_mode.get('base') is not None else chess.engine.Limit(time=seconds)
        threading.Thread(target=self.play_worker,args=(name,path,self.board.copy(),seconds,level,token,limit),daemon=True).start()
    def play_worker(self,name,path,board,seconds,level,token,limit=None):
        engine=None;work=None
        try:
            effective,chance=self.effective_level(name,level)
            if random.random()<chance:
                move=random.choice(list(board.legal_moves))
            else:
                engine,work=self.open_engine(name,path)
                if token!=self.epoch:return
                self.engines['Game']=engine
                if name=='Stockfish':
                    engine.configure({'UCI_LimitStrength':level<=3190,'UCI_Elo':effective,'Skill Level':20})
                elif name=='RoboChess':
                    engine.configure({'Hash':128})
                    limit=limit or chess.engine.Limit(time=seconds)
                    limit.depth=effective
                elif name in self.custom_engines:
                    options=engine.options;config={}
                    if 'UCI_LimitStrength' in options:config['UCI_LimitStrength']=True
                    if 'UCI_Elo' in options:
                        option=options['UCI_Elo'];config['UCI_Elo']=max(option.min or 1,min(option.max or 3800,level))
                    elif 'Skill Level' in options:
                        option=options['Skill Level'];config['Skill Level']=max(option.min or 0,min(option.max or 20,round(level/3800*20)))
                    if config:engine.configure(config)
                elif isinstance(engine.protocol,chess.engine.XBoardProtocol):
                    engine.protocol.loop.call_soon_threadsafe(engine.protocol.send_line,f'elo {3601 if level>=3600 else effective}')
                    engine.ping()
                move=engine.play(board,limit or chess.engine.Limit(time=seconds)).move
            self.play_events.put((token,move,None))
        except Exception as err:self.play_events.put((token,None,str(err)))
        finally:
            if engine:
                try:engine.quit()
                except Exception:pass
                if self.engines.get('Game') is engine:self.engines.pop('Game',None)
            if work:
                try:work.cleanup()
                except OSError:pass
    def poll_play(self):
        try:
            while True:
                token,move,error=self.play_events.get_nowait()
                if token!=self.epoch or not self.playing:continue
                self.play_busy=False
                if error:
                    self.playing=False;self.stop_clock(settle=True);self.clock_selector.configure(state='readonly')
                    self.abort_quad_match()
                    self.status.set(self.T('Error del motor: ','Engine error: ')+error);continue
                if move not in self.board.legal_moves:
                    self.playing=False;self.stop_clock(settle=True);self.clock_selector.configure(state='readonly')
                    self.abort_quad_match()
                    self.status.set('Engine returned an illegal move.');continue
                if not self.complete_clock_move(self.board.turn):continue
                self.play_sound(self.sound_for_move(self.board,move))
                san=self.board.san(move);self.board.push(move);self.results={};self.draw()
                if self.board.is_game_over(claim_draw=True):
                    self.final_result=self.board.result(claim_draw=True);self.playing=False
                    self.stop_clock(settle=False);self.clock_selector.configure(state='readonly')
                    self.record_quad_result(self.final_result)
                    self.status.set(self.T(f'{self.game_engine_name} jugó {san}. Fin: {self.final_result}',f'{self.game_engine_name} played {san}. Game over: {self.final_result}'))
                else:
                    self.status.set(self.T(f'{self.game_engine_name} jugó {san}. Te toca mover.',f'{self.game_engine_name} played {san}. Your turn.'))
                    self.start_clock(self.board.turn)
                if self.coach_enabled.get() and not self.feedback_pending:self.request_coach('status')
        except queue.Empty:pass
    def preview_opponent(self,event=None):
        if not self.playing:
            name=self.play_engine.get()
            self.opponent_image.configure(image=self.coach_images[name]);self.mood.set(self.T(f'{name}: 😐 listo para jugar',f'{name}: 😐 ready to play'))
    def coach_toggle(self):
        if self.coach_enabled.get():self.request_coach('status')
        else:
            self.coach_generation+=1;self.feedback_pending=False
            self.put(self.coach_text,self.T('Tutor desactivado. Puedes pedir una Pista o Explicar en cualquier momento.','Tutor disabled. You can request a Hint or Explanation at any time.'))
    def request_coach(self,kind,before=None,move=None):
        if kind in ('hint','explain') and self.playing and self.board.turn!=self.human_color:
            self.put(self.coach_text,self.T('Espera a que el motor termine su jugada para pedir una pista.','Wait for the engine to finish its move before requesting a hint.'));return
        if kind=='status' and self.feedback_pending:return
        if kind=='feedback':self.feedback_pending=True
        if kind=='hint' and self.profile:
            self.profile['hints']+=1
            try:profile_store.save(self.profile_data)
            except OSError as err:self.status.set('No se pudo guardar el perfil: '+str(err))
        self.coach_generation+=1;generation=self.coach_generation
        name=self.game_engine_name if self.playing and self.paths.get(self.game_engine_name) else self.first_configured_engine()
        if name is None:
            self.feedback_pending=False;self.put(self.coach_text,self.T('Selecciona primero un motor para obtener consejos.','Select an engine first to get advice.'));return
        path=self.paths.get(name)
        if not path:
            self.feedback_pending=False;self.put(self.coach_text,self.T('Selecciona primero un motor para obtener consejos.','Select an engine first to get advice.'));return
        board=before.copy() if before else self.board.copy()
        self.put(self.coach_text,self.T('Einstein está estudiando la posición…','Einstein is studying the position…'))
        threading.Thread(target=self.coach_worker,args=(generation,kind,name,path,board,move,self.game_engine_name,self.human_color,self.language.get()),daemon=True).start()
    @staticmethod
    def phase_key(board):
        queens=len(board.pieces(chess.QUEEN,chess.WHITE))+len(board.pieces(chess.QUEEN,chess.BLACK))
        pieces=sum(len(board.pieces(pt,color)) for color in (chess.WHITE,chess.BLACK) for pt in (chess.QUEEN,chess.ROOK,chess.BISHOP,chess.KNIGHT))
        if board.fullmove_number<=10 and pieces>=12:return 'apertura'
        if queens==0 or pieces<=6:return 'final'
        return 'medio juego'
    @staticmethod
    def phase_tip(board):
        queens=len(board.pieces(chess.QUEEN,chess.WHITE))+len(board.pieces(chess.QUEEN,chess.BLACK))
        pieces=sum(len(board.pieces(pt,color)) for color in (chess.WHITE,chess.BLACK) for pt in (chess.QUEEN,chess.ROOK,chess.BISHOP,chess.KNIGHT))
        if board.fullmove_number<=10 and pieces>=12:return 'Apertura: desarrolla tus piezas, protege al rey y disputa el centro.'
        if queens==0 or pieces<=6:return 'Final: activa el rey, crea peones pasados y vigila las amenazas de promoción.'
        return 'Medio juego: revisa jaques, capturas y amenazas antes de decidir.'
    @staticmethod
    def phase_tip_en(board):
        phase=App.phase_key(board)
        return {'apertura':'Opening: develop pieces, protect your king, and contest the center.',
                'medio juego':'Middlegame: check forcing moves, captures, and threats before deciding.',
                'final':'Endgame: activate your king, create passed pawns, and watch promotion threats.'}[phase]
    @staticmethod
    def persona_tip_en(board,name):
        phase=App.phase_key(board)
        if name=='RoboChess':
            return {'apertura':'RoboChess: Fischer would develop quickly and fight for the center.',
                    'medio juego':'RoboChess: Karpov would restrict counterplay; Kasparov would seize the initiative.',
                    'final':'RoboChess: Capablanca would activate the king and simplify when ahead.'}[phase]
        if name=='Crafty':
            return {'apertura':'Crafty: Even a dinosaur develops its pieces before attacking!',
                    'medio juego':'Crafty: Before roaring, look for checks and loose pieces.',
                    'final':'Crafty: In the endgame, the king leaves its cave.'}[phase]
        return {'apertura':'Stockfish: Swim toward the center and protect your king!',
                'medio juego':'Stockfish: Before biting, check captures and threats.',
                'final':'Stockfish: In the endgame, every pawn can swim far.'}[phase]
    @staticmethod
    def reason_en(board,move):
        if move not in board.legal_moves:return 'The engine line changed; analyze again.'
        san=board.san(move);piece=board.piece_at(move.from_square)
        if board.gives_check(move):return f'{san} gives check and demands a reply.'
        if board.is_capture(move):return f'{san} captures material; check the recapture.'
        if board.is_castling(move):return f'{san} makes the king safer and connects the rooks.'
        if piece and piece.piece_type in (chess.KNIGHT,chess.BISHOP) and board.fullmove_number<=10:return f'{san} develops a minor piece.'
        if piece and piece.piece_type==chess.PAWN and move.to_square in (chess.D4,chess.E4,chess.D5,chess.E5):return f'{san} fights for the center.'
        return f'{san} is the engine choice in this search; its variation shows a possible continuation.'
    @staticmethod
    def persona_tip(board,name):
        queens=len(board.pieces(chess.QUEEN,chess.WHITE))+len(board.pieces(chess.QUEEN,chess.BLACK))
        if name=='RoboChess':
            if board.fullmove_number<=10:return 'RoboChess: ¡Desarrolla rápido y pelea por el centro, como aconsejaba Fischer!'
            if queens==0:return 'RoboChess: ¡Activa el rey y simplifica cuando tengas ventaja, al estilo de Capablanca!'
            return 'RoboChess: ¡Restringe el contrajuego como Karpov o toma la iniciativa como Kasparov!'
        if board.fullmove_number<=10:
            return ('Crafty: ¡Un dinosaurio también debe desarrollar sus piezas antes de atacar!' if name=='Crafty' else 'Stockfish: ¡Nada hacia el centro y cuida tu rey!')
        if queens==0:
            return ('Crafty: En el final, el rey sale de su cueva.' if name=='Crafty' else 'Stockfish: En el final, cada peón puede llegar muy lejos.')
        return ('Crafty: Antes de rugir, busca jaques y piezas indefensas.' if name=='Crafty' else 'Stockfish: Antes de morder, revisa capturas y amenazas.')
    @staticmethod
    def advantage_reason(board,info):
        values={chess.PAWN:1,chess.KNIGHT:3,chess.BISHOP:3,chess.ROOK:5,chess.QUEEN:9}
        material=sum(values[pt]*(len(board.pieces(pt,chess.WHITE))-len(board.pieces(pt,chess.BLACK))) for pt in values)
        score=info.get('score');white=score.white().score(mate_score=100000) if score else None
        if white is not None and white>80 and material>=2:return f'Las blancas tienen aproximadamente {material} puntos más de material.'
        if white is not None and white< -80 and material<=-2:return f'Las negras tienen aproximadamente {-material} puntos más de material.'
        pv=info.get('pv',[])
        if pv and pv[0] in board.legal_moves:
            move=pv[0];san=board.san(move)
            if board.gives_check(move):return f'La primera variante empieza con {san}, que da jaque.'
            if board.is_capture(move):return f'La primera variante empieza con {san}, una captura.'
            return f'El motor prefiere {san}; estudia esa continuación para entender la ventaja posicional.'
        return 'No hay una causa simple verificable en esta búsqueda; analiza la variante con más tiempo.'
    @staticmethod
    def reason(board,move):
        if move not in board.legal_moves:return 'La variante del motor cambió; vuelve a analizar.'
        san=board.san(move);piece=board.piece_at(move.from_square)
        if board.gives_check(move):return f'{san} crea un jaque que exige respuesta.'
        if board.is_capture(move):return f'{san} captura una pieza o un peón; revisa la recaptura.'
        if board.is_castling(move):return f'{san} pone al rey más seguro y conecta las torres.'
        if piece and piece.piece_type in (chess.KNIGHT,chess.BISHOP) and board.fullmove_number<=10:
            return f'{san} desarrolla una pieza menor hacia una nueva casilla.'
        if piece and piece.piece_type==chess.PAWN and move.to_square in (chess.D4,chess.E4,chess.D5,chess.E5):
            return f'{san} lucha por una casilla central.'
        return f'{san} es la preferencia del motor en esta búsqueda; su variante muestra una posible continuación.'
    @staticmethod
    def pov_cp(info,color):
        score=info.get('score') if info else None
        return score.pov(color).score(mate_score=100000) if score else None
    def coach_worker(self,generation,kind,name,path,board,move,opponent,human_color,language='Español'):
        engine=None;work=None
        try:
            engine,work=self.open_engine(name,path)
            limit=chess.engine.Limit(time=1.2 if kind=='status' else 1.8)
            info=engine.analyse(board,limit)
            pv=info.get('pv',[]);best=pv[0] if pv else None
            tip=self.phase_tip(board)
            quality_key=None;played_uci=None;phase=self.phase_key(board)
            if kind=='feedback' and move:
                played_uci=move.uci()
                after=board.copy();played=board.san(move);after.push(move)
                after_info=engine.analyse(after,chess.engine.Limit(time=1.8))
                initial=self.pov_cp(info,board.turn);ending=self.pov_cp(after_info,board.turn)
                drop=initial-ending if initial is not None and ending is not None else None
                best_san=board.san(best) if best else '?'
                if best==move:quality='Buena jugada: coincide con la primera opción del motor.';quality_key='buena'
                elif drop is None:quality='La evaluación no fue suficiente para clasificar esta jugada.'
                elif drop>=300:quality=f'Error grave estimado: la evaluación empeoró aproximadamente {drop/100:.1f} peones.';quality_key='grave'
                elif drop>=150:quality=f'Error estimado: la evaluación empeoró aproximadamente {drop/100:.1f} peones.';quality_key='error'
                elif drop>=70:quality=f'Imprecisión estimada: la evaluación bajó aproximadamente {drop/100:.1f} peones.';quality_key='imprecision'
                else:quality='La diferencia de evaluación es pequeña en esta búsqueda.';quality_key='buena'
                why=self.reason(board,best) if best else tip
                text=f'Jugada: {played}. {quality}\n\nLa alternativa del motor era {best_san}. {why}\n'
                reply=after_info.get('pv',[])
                if reply and reply[0] in after.legal_moves:
                    answer=reply[0];response=after.san(answer)
                    text+=f'Una respuesta fuerte del rival sería {response}.'
                    if after.gives_check(answer):text+=' Da jaque.'
                    elif after.is_capture(answer):text+=' Captura material.'
                    text+='\n'
                moved=after.piece_at(move.to_square)
                if moved and moved.piece_type!=chess.KING and after.is_attacked_by(not moved.color,move.to_square):
                    text+='Tu pieza queda atacada; comprueba si está defendida o si existe una combinación.\n'
                text+='\nConsejo general: '+tip+'\n'+self.persona_tip(after,opponent)
                if language=='English':
                    q={'buena':'Good move in this search.','imprecision':'Estimated inaccuracy.',
                       'error':'Estimated mistake.','grave':'Estimated serious mistake.'}.get(quality_key,'Not enough evaluation to classify this move.')
                    text=f'Move: {played}. {q}'
                    if drop is not None and quality_key!='buena':text+=f' The evaluation fell by about {drop/100:.1f} pawns.'
                    text+=f'\n\nThe engine alternative was {best_san}. '+(self.reason_en(board,best) if best else self.phase_tip_en(board))
                    if reply and reply[0] in after.legal_moves:
                        text+=f'\nA strong reply is {after.san(reply[0])}.'
                    text+='\n\nGeneral advice: '+self.phase_tip_en(board)+'\n'+self.persona_tip_en(after,opponent)
                position_cp=ending if board.turn==chess.WHITE else (-ending if ending is not None else None)
            else:
                cp=self.pov_cp(info,chess.WHITE)
                position_cp=cp
                if kind=='status':
                    if cp is None:state='Todavía no hay evaluación suficiente.'
                    elif cp>80:state=f'Las blancas tienen ventaja estimada ({cp/100:+.1f}).'
                    elif cp<-80:state=f'Las negras tienen ventaja estimada ({cp/100:+.1f}).'
                    else:state='La posición parece equilibrada en esta búsqueda.'
                    text=f'{state} {self.advantage_reason(board,info)}\n\n{tip}\n{self.persona_tip(board,opponent)}\n\nLa evaluación puede cambiar al buscar más tiempo.'
                    if language=='English':
                        state=('White has an estimated advantage.' if cp>80 else 'Black has an estimated advantage.' if cp< -80 else 'The position appears balanced in this search.') if cp is not None else 'No evaluation is available yet.'
                        lead=('White' if cp and cp>80 else 'Black' if cp and cp< -80 else 'Neither side')
                        text=f'{state} {lead} can study the engine variation to understand the position.\n\n{self.phase_tip_en(board)}\n{self.persona_tip_en(board,opponent)}\n\nThe evaluation may change with a longer search.'
                else:
                    if best:
                        candidate=board.san(best);why=self.reason(board,best)
                        text=f'Pista: considera {candidate}.\n\n{why}'
                        if kind=='explain':
                            copy=board.copy();sequence=[]
                            for pv_move in pv[:6]:
                                if pv_move not in copy.legal_moves:break
                                sequence.append(copy.san(pv_move));copy.push(pv_move)
                            text+='\n\nUna variante posible: '+' '.join(sequence)+'.'
                    else:text='No encontré una variante útil para esta posición.'
                    text+='\n\nConsejo general: '+tip+'\n'+self.persona_tip(board,opponent)
                    if language=='English':
                        if best:
                            text=f'Hint: consider {candidate}.\n\n{self.reason_en(board,best)}'
                            if kind=='explain':text+='\n\nPossible continuation: '+' '.join(sequence)+'.'
                        else:text='No useful variation was found for this position.'
                        text+='\n\nGeneral advice: '+self.phase_tip_en(board)+'\n'+self.persona_tip_en(board,opponent)
            self.coach_events.put((generation,kind,text,position_cp,opponent,human_color,None,(phase,quality_key,played_uci)))
        except Exception as err:self.coach_events.put((generation,kind,'',None,opponent,human_color,str(err),None))
        finally:
            if engine:
                try:engine.quit()
                except Exception:pass
            if work:
                try:work.cleanup()
                except OSError:pass
    def poll_coach(self):
        try:
            while True:
                generation,kind,content,white_cp,opponent,human_color,error,record=self.coach_events.get_nowait()
                if generation!=self.coach_generation:continue
                if kind=='feedback':self.feedback_pending=False
                if error:self.put(self.coach_text,'Tutor: '+error);continue
                if kind=='feedback' and record and record[1] and self.profile:
                    try:profile_store.record_feedback(self.profile_data,self.profile,*record)
                    except OSError as err:self.status.set('No se pudo guardar el progreso: '+str(err))
                self.put(self.coach_text,content)
                if self.playing and white_cp is not None:
                    engine_cp=white_cp if human_color==chess.BLACK else -white_cp
                    if engine_cp>120:face='😀';mood='contento'
                    elif engine_cp< -120:face='😟';mood='preocupado'
                    else:face='😐';mood='concentrado'
                    quips={'Crafty':('¡Mis piezas tienen hambre!','¡Creo que escondí mal la cola!','Mi cola dice que hay que pensar.'),'Stockfish':('¡Hoy nado con ventaja!','¡Necesito un salvavidas!','Aún no muerdo el anzuelo.'),'RoboChess':('¡Sistemas en verde: el rey rival está bajo presión!','¡Mis circuitos piden una retirada estratégica!','¡Calculando… el café sería una mejora de hardware!')}
                    phrases=quips.get(opponent,quips['Stockfish'])
                    joke=phrases[0 if engine_cp>120 else 1 if engine_cp< -120 else 2]
                    expression='happy' if engine_cp>120 else 'worried' if engine_cp< -120 else ''
                    portrait_key=opponent+'_'+expression if expression and opponent+'_'+expression in self.coach_images else opponent
                    self.opponent_image.configure(image=self.coach_images[portrait_key])
                    if self.language.get()=='English':
                        mood={'contento':'happy','preocupado':'worried','concentrado':'focused'}[mood]
                        joke={'Crafty':('My pieces are hungry!','I think I hid my tail poorly!','My tail says I should think.'),'Stockfish':('I swim with an advantage today!','I need a life preserver!','I will not bite the hook yet.'),'RoboChess':('Systems green: the enemy king is under pressure!','My circuits request a strategic retreat!','Calculating… coffee would be a hardware upgrade!')}[opponent][0 if engine_cp>120 else 1 if engine_cp< -120 else 2]
                    self.mood.set(f'{opponent}: {face} {mood}. {joke}')
        except queue.Empty:pass
    def connect_dgt(self):
        try:
            import dgt_link
        except Exception as err:
            messagebox.showerror(self.T('Tablero DGT','DGT board'),self.T('No se pudo cargar el módulo DGT: ','Could not load the DGT module: ')+str(err))
            return
        port=simpledialog.askstring(self.T('Tablero DGT','DGT board'),self.T('Puerto serial, por ejemplo COM3. Déjalo vacío para buscar.','Serial port, for example COM3. Leave blank to scan.'),initialvalue=self.dgt_port,parent=self.w)
        if port is None:return
        ports=[port.strip()] if port and port.strip() else dgt_link.default_ports()
        self.disconnect_dgt()
        self.dgt_link=dgt_link.DgtLink(self.dgt_events)
        self.dgt_port=port.strip() if port else ''
        self.dgt_link.start(ports)
        self.status.set(self.T('Buscando tablero DGT…','Looking for a DGT board…'))
    def disconnect_dgt(self):
        if self.dgt_link:
            self.dgt_link.stop_link();self.dgt_link=None
        self.status.set(self.T('Tablero DGT desconectado.','DGT board disconnected.'))
    def poll_dgt(self):
        try:
            while True:
                kind,payload=self.dgt_events.get_nowait()
                if kind=='connected':
                    self.status.set(self.T(f'Tablero DGT conectado en {payload}.','DGT board connected on {payload}.'))
                elif kind=='disconnected':
                    self.status.set(self.T('El tablero DGT se desconectó.','The DGT board disconnected.'))
                elif kind=='error':
                    self.status.set(self.T('DGT: ','DGT: ')+str(payload))
                elif kind=='board':
                    self.apply_dgt_board(payload)
        except queue.Empty:
            pass
    def apply_dgt_board(self,physical):
        try:
            import chess
            if hasattr(physical,'board_fen'):
                placement=physical.board_fen()
            else:
                # Accept either a placement FEN or a complete FEN from a
                # future DGT backend; asyncdgt.Board itself is not chess.Board.
                placement=str(physical).strip().split()[0]
            probe=chess.Board(None)
            probe.set_board_fen(placement)
        except Exception as err:
            self.status.set(self.T('No se pudo leer la posición DGT: ','Could not read the DGT position: ')+str(err));return
        # Returning every physical piece to its standard square is an explicit
        # board reset, like placing the pieces back after a game in ChessBase.
        # Compare piece placement only because DGT does not report side to move.
        if placement==chess.Board().board_fen() and placement!=self.board.board_fen():
            if self.editor_mode or self.puzzle_active or self.review_game is not None or self.engine_match_running or (self.quad and self.quad.get('active')):
                self.status.set(self.T('Termina el modo actual antes de reiniciar desde el tablero DGT.','Finish the current mode before resetting from the DGT board.'))
                return
            self.reset()
            self.status.set(self.T('Tablero DGT en posición inicial: partida reiniciada.','DGT board returned to the starting position: game reset.'))
            return
        if placement==self.board.board_fen():return
        if self.editor_mode or self.puzzle_active or self.review_game is not None or self.engine_match_running or (self.quad and self.quad.get('active')):
            self.status.set(self.T('Termina el modo actual antes de mover desde el tablero DGT.','Finish the current mode before entering moves from the DGT board.'))
            return
        matched=[]
        for move in self.board.legal_moves:
            trial=self.board.copy();trial.push(move)
            if trial.board_fen()==placement:matched.append(move)
        if len(matched)==1:
            self.selected=None
            self.push_dgt_move(matched[0]);return
        # Intermediate piece lifts, captures, and adjustments are normal DGT
        # updates. Keep the current game intact until one legal position settles.
    def push_dgt_move(self,move):
        if self.playing and (self.play_busy or self.board.turn!=self.human_color):
            self.status.set(self.T('Espera: no es tu turno en el tablero DGT.','Wait: it is not your turn on the DGT board.'));return
        before=self.board.copy();was_human=self.playing and self.board.turn==self.human_color
        if was_human and not self.complete_clock_move(self.board.turn):return
        self.play_sound(self.sound_for_move(self.board,move))
        self.stop();self.results={};self.review_game=None;self.board.push(move)
        self.status.set(self.T(f'Tablero DGT: {move.uci()}','DGT board: {move.uci()}'));self.draw()
        if was_human and self.profile:
            try:profile_store.record_move(self.profile_data,self.profile,self.phase_key(before))
            except OSError as err:self.status.set(str(err))
        if self.board.is_game_over(claim_draw=True):
            self.final_result=self.board.result(claim_draw=True);self.playing=False
            self.stop_clock(settle=False);self.clock_selector.configure(state='readonly')
            self.record_quad_result(self.final_result)
            self.status.set(self.T('Partida terminada: ','Game over: ')+self.final_result)
            self._sync_play_chrome()
        elif was_human:
            if self.coach_enabled.get() or self.profile:self.request_coach('feedback',before,move)
            self.start_clock(self.board.turn)
            self.w.after(100,self.computer_turn)
    def poll(self):
        self.poll_play();self.poll_coach();self.poll_lichess();self.poll_live_broadcast();self.poll_lichess_puzzles();self.poll_engine_match();self.poll_dgt()
        if self.rush_session and not self.rush_session.get('finished'):
            self.update_puzzle_rush_display()
        try:
            while True:
                token,best,error=self.challenge_events.get_nowait()
                if token!=self.epoch:continue
                if self.puzzle_active=='rush' and self.rush_session and self.rush_session.get('waiting_engine'):
                    session=self.rush_session;session['waiting_engine']=False
                    if error or best is None:
                        session['engine_failures']+=1
                        if session['engine_failures']<=2 and self._next_rush_puzzle():
                            self.update_puzzle_rush_display()
                        else:self.finish_puzzle_rush('engine')
                    else:
                        self.challenge_best=best;self.puzzle_moves=[best];self.puzzle_index=0;self.puzzle_color=self.board.turn
                        self.status.set(self.T('Posición lista. Juega la mejor jugada que encontró el motor.',
                                               'Position ready. Play the best move found by the engine.'))
                        self.update_puzzle_rush_display()
                    continue
                if self.puzzle_active not in ('best','tactic'):continue
                if error or best is None:
                    self.puzzle_active=False
                    self.put(self.resource_text,self.T('No se pudo preparar el ejercicio: ','Could not prepare the challenge: ')+(error or 'No legal move'))
                else:
                    self.challenge_best=best
                    if self.puzzle_active=='tactic':
                        self.puzzle_moves=[best];self.puzzle_index=0;self.puzzle_color=self.board.turn
                    message=self.puzzle_turn_text(self.board.turn)+'. '+(self.T('Encuentra la mejor jugada en esta búsqueda. Puedes pedir Pista.','Find the best move in this search. You may request a Hint.') if self.puzzle_active=='best' else self.T('Encuentra la mejor jugada del final.','Find the best move in this endgame.'))
                    self.status.set(message);self.put(self.resource_text,message)
                    self.show_tools_view();self.tabs.select(self.tabs.tabs()[-1])
        except queue.Empty:pass
        try:
            while True:
                token,accept,error=self.draw_events.get_nowait()
                if token!=self.epoch or not self.playing:continue
                self.draw_offer_pending=False
                if error:
                    self.status.set(self.T('No se pudo consultar al motor: ','Could not consult the engine: ')+error)
                elif accept:
                    self.finish_game('1/2-1/2',self.T(f'{self.game_engine_name}: Acepto las tablas. ¡Buena partida! Analicémosla.',f'{self.game_engine_name}: I accept the draw. Good game! Let us analyze it.'))
                else:
                    message=self.T(f'{self.game_engine_name}: No quiero tablas, ¡juguemos un poco más!',f'{self.game_engine_name}: I do not want a draw. Let us play a little longer!')
                    self.status.set(message);self.put(self.coach_text,message);self.show_tools_view();self.tabs.select(self.tutor_tab)
        except queue.Empty:pass
        try:
            while True:
                token,name,board,result,error=self.events.get_nowait()
                if token!=self.epoch:continue
                if error:
                    self.put(self.panels[name],f'Engine error: {error}')
                    if name==self.engine_view.get():self.put(self.selected_engine_analysis_output(),f'Engine error: {error}')
                    continue
                lines=result if isinstance(result,list) else [result]
                output=[]
                for index,info in enumerate(lines,1):
                    pv=info.get('pv',[])
                    if not pv:continue
                    score=info.get('score'); pov=score.pov(board.turn) if score else None
                    mate=pov.mate() if pov else None
                    val=(f'Mate in {mate}' if mate is not None else f'{pov.score()/100:+.2f}' if pov and pov.score() is not None else '?')
                    copy=board.copy(); san=[]
                    for move in pv[:14]:
                        if move not in copy.legal_moves:break
                        san.append(copy.san(move));copy.push(move)
                    if san:output.append(f'#{index}  {val}  depth {info.get("depth","?")}\n'+ ' '.join(san))
                if not output:
                    message=self.T('El motor respondió, pero no entregó una variante de jugadas. Comprueba que sea un motor UCI compatible.',
                                   'The engine responded but returned no principal variation. Check that it is a compatible UCI engine.')
                    self.put(self.panels[name],message);self.results.pop(name,None);self.draw()
                    if name==self.engine_view.get():self.put(self.selected_engine_analysis_output(),message)
                    continue
                rendered='\n\n'.join(output)
                self.put(self.panels[name],rendered)
                if name==self.engine_view.get():self.put(self.selected_engine_analysis_output(),rendered)
                self.results[name]=(lines if name=='Stockfish' or isinstance(result,list) else lines[0]);self.explain(board);self.draw()
                self.status.set(self.T('Análisis terminado','Analysis complete'))
        except queue.Empty:pass
        self.w.after(100,self.poll)
    def explain(self,board):
        notes=[]
        for name,info in self.results.items():
            info=info[0] if isinstance(info,list) and info else info
            pv=info.get('pv',[])
            if not pv:continue
            score=info.get('score');mate=score.pov(board.turn).mate() if score else None
            if mate is not None:notes.append(self.T(f'{name}: mate en {mate} según la variante del motor.',f'{name}: forced mate in {mate} (engine principal line).'))
            move=pv[0];b=board.copy();san=b.san(move);b.push(move)
            if b.is_check():notes.append(self.T(f'{name}: {san} da jaque.',f'{name}: {san} gives check.'))
            if board.is_capture(move):notes.append(self.T(f'{name}: {san} captura una pieza.',f'{name}: {san} captures a piece.'))
            moved=b.piece_at(move.to_square)
            if moved:
                targets=[(sq,p) for sq,p in b.piece_map().items() if p.color!=moved.color and p.piece_type in (chess.KNIGHT,chess.BISHOP,chess.ROOK,chess.QUEEN,chess.KING) and b.is_attacked_by(moved.color,sq) and sq in b.attacks(move.to_square)]
                if len(targets)>=2:notes.append(self.T(f'{name}: {san} ataca varias piezas valiosas (posible doble ataque).',f'{name}: {san} attacks multiple valuable pieces (fork candidate).'))
                pinned=[sq for sq,p in b.piece_map().items() if p.color!=moved.color and b.is_pinned(p.color,sq) and not board.is_pinned(p.color,sq)]
                if pinned:notes.append(self.T(f'{name}: {san} crea una clavada (comprueba su valor táctico).',f'{name}: {san} creates a pin (verify its tactical value).'))
                if b.is_attacked_by(not moved.color,move.to_square) and moved.piece_type in (chess.BISHOP,chess.KNIGHT,chess.ROOK,chess.QUEEN):notes.append(self.T(f'{name}: {san} deja la pieza atacada (posible sacrificio; revisa respuestas).',f'{name}: {san} leaves the moved piece attacked (possible sacrifice; inspect replies).'))
            if len(pv)>1:
                reply=pv[1];b.push(reply)
                if b.is_check():notes.append(self.T(f'{name}: sigue un jaque forzado.',f'{name}: forcing check follows the reply.'))
        available=[]
        for name in self.ENGINE_NAMES:
            value=self.results.get(name)
            info=value[0] if isinstance(value,list) and value else value
            pv=info.get('pv',[]) if info else []
            if pv:available.append((name,pv[0]))
        if len(available)>1:
            unanimous=len({move for _,move in available})==1
            names=', '.join(name for name,_ in available)
            notes.append(self.T(f'{names}: coinciden en la primera jugada.' if unanimous else f'{names}: proponen primeras jugadas distintas; compara las variantes.',
                                f'{names}: agree on the first move.' if unanimous else f'{names}: recommend different first moves; compare their lines.'))
        notes.append(self.T('Verifica las tácticas en la variante completa; un jaque o una captura no prueban una combinación.','Pin, fork, sacrifice and mistake labels require verification against the full variation; a check or capture alone does not prove a tactic.'))
        self.put(self.tactics,'\n'.join(notes))
    def analysis_lines(self):
        lines=[]
        for name,infos in self.results.items():
            for index,info in enumerate(infos if isinstance(infos,list) else [infos],1):
                pv=info.get('pv',[]);board=self.board.copy();moves=[]
                for move in pv:
                    if move not in board.legal_moves:break
                    moves.append(board.san(move));board.push(move)
                score=info.get('score');s=score.pov(self.board.turn) if score else None
                evaluation=('mate '+str(s.mate()) if s and s.mate() is not None else ('%+.2f'%(s.score()/100) if s and s.score() is not None else '?'))
                lines.append((name,index,info,pv,f'{name} #{index}: {evaluation}, depth {info.get("depth","?")} — '+ ' '.join(moves)))
        return lines
    def save_txt(self):
        lines=self.analysis_lines()
        if not lines:messagebox.showinfo('Analysis','Analyze a position first.');return
        path=filedialog.asksaveasfilename(defaultextension='.txt',filetypes=[('Text','*.txt')])
        if path:
            with open(path,'w',encoding='utf-8') as f:f.write('FEN: '+self.board.fen()+'\n\n'+'\n\n'.join(row[4] for row in lines)+'\n')
            self.status.set('Saved '+path)
    def save_pgn(self):
        lines=self.analysis_lines()
        if not lines:messagebox.showinfo('Analysis','Analyze a position first.');return
        path=filedialog.asksaveasfilename(defaultextension='.pgn',filetypes=[('PGN','*.pgn')])
        if not path:return
        root=self.board.root();game=chess.pgn.Game.from_board(root)
        game.headers['Event']='Dual-engine position analysis'
        node=game
        for move in self.board.move_stack:node=node.add_main_variation(move)
        for name,index,info,pv,label in lines:
            current=node;copy=self.board.copy();first=None
            for move in pv:
                if move not in copy.legal_moves:break
                current=current.add_variation(move);copy.push(move)
                if first is None:first=current
            if first:
                score=info.get('score');white=score.white() if score else None
                ev=''
                if white:
                    mate=white.mate()
                    if mate is not None:ev=f' [%eval #{mate}]'
                    elif white.score() is not None:ev=f' [%eval {white.score()/100:.2f}]'
                first.comment=f'{name} line {index}; depth {info.get("depth","?")}; perspective: player to move.'+ev
        with open(path,'w',encoding='utf-8') as f:print(game,file=f,end='\n\n')
        self.status.set('Saved '+path)
    def close(self):
        if self.engine_match_stop:self.engine_match_stop.set()
        self.stop_live_broadcast()
        self.disconnect_dgt()
        if hasattr(self,'lichess_video'):self.lichess_video.destroy()
        if hasattr(self,'pdf_reader'):self.pdf_reader.close_document()
        self.stop();self.w.destroy()

def show_splash(root):
    """Show the bundled RoboChess splash without requiring Pillow."""
    candidates=(
        os.path.join(ROOT,'assets','splash_logo.png'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)),'assets','splash_logo.png'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)),'splash_logo.png'),
    )
    logo_path=next((path for path in candidates if os.path.isfile(path)),None)
    root.withdraw()
    splash=tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.configure(bg='black')
    try:
        splash.attributes('-alpha',1.0)
    except tk.TclError:
        pass
    width,height=1100,700
    screen_w=splash.winfo_screenwidth(); screen_h=splash.winfo_screenheight()
    splash.geometry(f'{width}x{height}+{(screen_w-width)//2}+{(screen_h-height)//2}')
    holder={'image':None}
    if logo_path:
        try:
            image=tk.PhotoImage(file=logo_path)
            factor=max(1,math.ceil(max(image.width()/1040,image.height()/640)))
            if factor>1:image=image.subsample(factor,factor)
            holder['image']=image
            label=tk.Label(splash,image=image,bg='black',borderwidth=0)
            label.image=image
            label.pack(expand=True)
        except Exception:
            holder['image']=None
            tk.Label(splash,text='ROBOCHESS',fg='#3ad0ff',bg='black',font=('Arial',28,'bold')).pack(expand=True)
    else:
        tk.Label(splash,text='ROBOCHESS',fg='#3ad0ff',bg='black',font=('Arial',28,'bold')).pack(expand=True)
    state={'alpha':1.0}
    def fade():
        state['alpha']=round(state['alpha']-0.08,2)
        if state['alpha']<=0:
            splash.destroy(); root.deiconify(); root.lift(); return
        try:
            splash.attributes('-alpha',state['alpha'])
        except tk.TclError:
            splash.destroy(); root.deiconify(); return
        splash.after(45,fade)
    splash.after(1100,fade)
    splash.update()

if __name__=='__main__':
    try:
        window=tk.Tk()
        App(window)
        show_splash(window)
        window.mainloop()
    except Exception:
        _fatal('RoboChess se detuvo / crashed', traceback.format_exc())
