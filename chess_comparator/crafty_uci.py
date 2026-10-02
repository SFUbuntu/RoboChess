"""Personal-use UCI bridge for the unmodified Crafty XBoard engine."""
import os, sys, threading, logging, tempfile
ROOT=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(ROOT,'vendor'))
import chess, chess.engine
logging.getLogger('chess.engine').setLevel(logging.CRITICAL)

class Bridge:
    def __init__(self):
        self.path=os.environ.get('CRAFTY_PATH',os.path.join(ROOT,'crafty.exe' if os.name=='nt' else 'crafty-linux'))
        self.engine=None;self.board=chess.Board();self.worker=None;self.analysis=None
        self.workdir=tempfile.TemporaryDirectory(prefix='crafty-uci-')
        self.lock=threading.RLock();self.out=threading.Lock();self.generation=0;self.best=None
    def emit(self,s):
        with self.out:print(s,flush=True)
    def connect(self):
        if self.engine is None:self.engine=chess.engine.SimpleEngine.popen_xboard([self.path,'xboard'] if os.name=='nt' else self.path,timeout=30,cwd=self.workdir.name,env={**os.environ,'CRAFTY_LOG_PATH':'.'})
    def stop(self):
        active=self.worker is not None and self.worker.is_alive()
        self.generation+=1
        with self.lock:a=self.analysis
        if a:
            try:a.stop()
            except Exception:pass
        if self.worker and self.worker.is_alive():self.worker.join(timeout=3)
        if active:self.emit('bestmove '+(self.best.uci() if self.best else '0000'))
        self.worker=None;self.analysis=None
    def go(self,params):
        self.stop(); generation=self.generation; board=self.board.copy();self.best=None
        args=params.split(); depth=None; movetime=None; nodes=None
        for key in ('depth','movetime','nodes'):
            if key in args:
                try:
                    val=int(args[args.index(key)+1]);
                    if key=='depth':depth=val
                    if key=='movetime':movetime=val/1000
                    if key=='nodes':nodes=val
                except (ValueError,IndexError):pass
        limit=chess.engine.Limit(depth=depth,time=movetime,nodes=nodes)
        if not any((depth,movetime,nodes)):limit=None
        def work():
            best=None
            try:
                self.connect()
                with self.engine.analysis(board,limit=limit,info=chess.engine.INFO_ALL) as a:
                    with self.lock:self.analysis=a
                    for item in a:
                        if generation!=self.generation:break
                        pv=item.get('pv',[])
                        if pv:best=pv[0];self.best=best
                        fields=['info']
                        for key in ('depth','seldepth','nodes','nps','time'):
                            if key in item:fields += [key,str(int(item[key]*1000) if key=='time' else item[key])]
                        score=item.get('score')
                        if score:
                            score=score.pov(board.turn); mate=score.mate()
                            fields += ['score','mate',str(mate)] if mate is not None else ['score','cp',str(score.score())]
                        if pv:fields += ['pv']+[m.uci() for m in pv]
                        if len(fields)>1:self.emit(' '.join(fields))
                    if generation==self.generation:
                        result=a.wait();best=result.move or best
            except Exception as exc:self.emit('info string Crafty bridge error: '+str(exc).replace('\n',' '))
            finally:
                with self.lock:self.analysis=None
                if generation==self.generation:self.emit('bestmove '+(best.uci() if best else '0000'))
        self.worker=threading.Thread(target=work,daemon=True);self.worker.start()
    def run(self):
        for raw in sys.stdin:
            line=raw.strip();parts=line.split();
            if not parts:continue
            cmd=parts[0]
            if cmd=='uci':
                self.emit('id name Crafty (XBoard-UCI bridge)');self.emit('id author Robert M. Hyatt et al.');self.emit('uciok')
            elif cmd=='isready':
                try:self.connect();self.emit('readyok')
                except Exception as exc:self.emit('info string '+str(exc));self.emit('readyok')
            elif cmd=='ucinewgame':self.stop();self.board=chess.Board()
            elif cmd=='position':
                self.stop()
                try:
                    if len(parts)>1 and parts[1]=='startpos':board=chess.Board()
                    elif len(parts)>2 and parts[1]=='fen':board=chess.Board(' '.join(parts[2:parts.index('moves') if 'moves' in parts else len(parts)]))
                    else:continue
                    if 'moves' in parts:
                        for uci in parts[parts.index('moves')+1:]:board.push_uci(uci)
                    self.board=board
                except (ValueError,IndexError) as exc:self.emit('info string Invalid position: '+str(exc))
            elif cmd=='go':self.go(line[3:])
            elif cmd=='stop':self.stop()
            elif cmd=='quit':self.stop();break
        if self.engine:
            try:self.engine.quit()
            except Exception:pass
        self.workdir.cleanup()
if __name__=='__main__':Bridge().run()
