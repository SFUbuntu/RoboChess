import os
import runpy

os.chdir(os.path.dirname(os.path.abspath(__file__)))
runpy.run_path(os.path.join(os.getcwd(), 'app.py'), run_name='__main__')
