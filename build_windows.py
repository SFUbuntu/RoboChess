from pathlib import Path
import subprocess, sys, shutil, argparse
base=Path(__file__).resolve().parent
src=base/'chess_comparator'
parser=argparse.ArgumentParser()
parser.add_argument('--rebuild-engines',action='store_true')
options=parser.parse_args()
if options.rebuild_engines:
    engine=src/'engines'/'Sargon-Tal-Fischer'
    build=base/'sargon-build'
    subprocess.run(['cmake','-S',str(engine),'-B',str(build),'-A','x64','-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded'],check=True)
    subprocess.run(['cmake','--build',str(build),'--config','Release'],check=True)
    for filename in ['Sargon-Tal-Fischer-x64.exe','SargonBookBuilder.exe']:
        shutil.copy2(build/'Release'/filename,engine/filename)
    robbo_build=base/'robbo-build'
    subprocess.run(['cmake','-S',str(base/'cmake'/'robbochess'),'-B',str(robbo_build),'-A','x64','-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded'],check=True)
    subprocess.run(['cmake','--build',str(robbo_build),'--config','Release'],check=True)
    shutil.copy2(robbo_build/'Release'/'RoboChess-x64.exe',src/'robbochess'/'RoboChess-x64.exe')
args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--name','RoboChess','--icon',str(src/'assets'/'rook.ico'),'--distpath',str(base/'dist'),'--workpath',str(base/'pyinstaller-build'),'--specpath',str(base),'--paths',str(src/'vendor')]
for name in ['assets','avatars','sounds','personalities','robbochess','engines','vendor']:
    if (src/name).exists(): args+=['--add-data',f'{src/name};{name}']
for name in ['crafty.exe','Crafty-UCI.bat']:
    if (src/name).exists(): args+=['--add-data',f'{src/name};.']
for p in src.glob('*.txt'): args+=['--add-data',f'{p};.']
for name in ['chess','chess.engine','chess.pgn','chess.polyglot','chess.gaviota','chess.svg','PIL.ImageTk','zstandard','serial','pyee']:
    args+=['--hidden-import',name]
args+=['--collect-all','pymupdf','--collect-all','fitz',str(src/'app.py')]
subprocess.run(args,cwd=src,check=True)
