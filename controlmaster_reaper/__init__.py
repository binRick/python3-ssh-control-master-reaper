import os, sys, json, psutil, time, threading

DEBUG_killInactiveControlMasters = True
POLL_PIDS_INTERVAL = 5.0
IO_ACTIVITY_INTERVAL = 5.0
DO_KILL = True
MAX_PROC_RUNTIME_SECONDS_WITHOUT_IO = 10


def getControlMasterProcs(CONTROL_MASTER_PATH):
    PROCS = {}
    for proc in psutil.process_iter(attrs=['pid', 'name', 'cmdline', 'connections', 'io_counters','create_time']):
        if proc.info['name'] == 'ssh':
            cmdline = " ".join(" ".join(proc.info['cmdline']).split(" ")).strip()
            if  cmdline.lower().startswith('ssh:') and CONTROL_MASTER_PATH in cmdline:
                PROCS[proc.info['pid']] = proc.info['io_counters']
    return PROCS

def killInactiveControlMasters(CONTROL_MASTER_PATH):
    while True:
        pre_candidates = getControlMasterProcs(CONTROL_MASTER_PATH)
        time.sleep(IO_ACTIVITY_INTERVAL)
        post_candidates = getControlMasterProcs(CONTROL_MASTER_PATH)
        for pid in post_candidates.keys():
            if pid in pre_candidates.keys() and post_candidates.keys():
                P = {
                    "post_io_sum": sum(post_candidates[pid]),
                    "pre_io_sum": sum(pre_candidates[pid]),
                }
                if P['post_io_sum'] == P['pre_io_sum']:
                    P = psutil.Process(pid)
                    RUN_TIME_SECONDS = int(time.time()) - int(P.create_time())
                    if RUN_TIME_SECONDS >= MAX_PROC_RUNTIME_SECONDS_WITHOUT_IO:
                        if DEBUG_killInactiveControlMasters:
                            print("PID {} has been running for {} seconds and has had no io activity in {} seconds (max {}). it has {} connections open.".format(
                                pid,
                                RUN_TIME_SECONDS,
                                IO_ACTIVITY_INTERVAL,        
                                MAX_PROC_RUNTIME_SECONDS_WITHOUT_IO,
                                len(P.as_dict()['connections']),
                            ))
                        if DO_KILL:
                            P.kill()
    
        time.sleep(POLL_PIDS_INTERVAL)

def killInactiveControlMasters_startThread(CONTROL_MASTER_PATH):
    t = threading.Thread(target=killInactiveControlMasters, args=(CONTROL_MASTER_PATH, ))
    t.daemon = True
    t.start()
