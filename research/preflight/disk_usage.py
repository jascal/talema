"""Run: python disk_usage.py [--watch SECONDS]. Reports actual allocated research bytes."""
from common import *
import argparse,time,subprocess
p=argparse.ArgumentParser();p.add_argument('--watch',type=int,default=0);a=p.parse_args()
end=time.monotonic()+a.watch
while True:
    used=int(subprocess.check_output(['du','-s','-B1',str(RESEARCH)],text=True).split()[0])
    print(json.dumps({'unix_time':time.time(),'research_allocated_bytes':used}),flush=True)
    if time.monotonic()>=end:break
    time.sleep(2)
