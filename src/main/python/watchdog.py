import rrdtool
import ptrace
import sys
import os
import commands
from threading import Thread
import time
from time import sleep
import subprocess

processes = {}


def pid_thread(pid):
    
    print pid

    print "strace -p " + pid + " -f -e trace=network -s 10000 -S time"
    p = subprocess.Popen(str("strace -p " + pid + " -f -e trace=network -s 10000 -S time").split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    while(True):
        retcode = p.poll() #returns None while subprocess is running
        line = p.stdout.readline()
        print line
        if(retcode is not None):
            break


def net_process_monitor():
    while True:
        net_processes = commands.getoutput("netstat -tap 2> /dev/null | awk '{print $7}' | grep -oE \"[0-9]+\" | uniq") 
        parr = net_processes.split()
        
        current_time = int(time.time())

        for i in xrange(0,len(parr)-1):
            
            if parr[i] not in processes:
                processes[parr[i]] = {}
            
            processes[parr[i]]["live"] = True
            processes[parr[i]]["thread"] = Thread(target = pid_thread, args = (parr[i],))
            processes[parr[i]]["entry"] =  current_time
            processes[parr[i]]["thread"].daemon = True
            processes[parr[i]]["thread"].start()

        for key in processes:
            if processes[key]["entry"] != current_time:
                processes[key]["live"] = False
                processes[parr[i]]["thread"]._stop()
                processes[parr[i]["thread"]] = null

        #print processes

        #sleep(2)


class watchdog:
    """ """
    
    def __init__(self):
        pass
    
    def run(self):

        try:
            thread = Thread(target = net_process_monitor)
            thread.start()
        except KeyboardInterrupt:
            print "vdf"
            thread.stop()
            sys.exit(0)

        
    def handler():
        pass
        

temp = watchdog()
temp.run()

