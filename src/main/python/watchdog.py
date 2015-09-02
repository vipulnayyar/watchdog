import rrdtool
import ptrace
import sys
import os
import commands
from threading import Thread
import time
from time import sleep
import subprocess
import re
import sqlite3
import json
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer

processes = {}
ret = ""


def pid_thread(pid):
    
    p = subprocess.Popen(str("strace -p " + pid + " -f -e trace=network -s 10000 -S time").split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    conn = sqlite3.connect('watchdog-'+pid+'.db')
    conn.execute("CREATE TABLE IF NOT EXISTS 'data' (time INT PRIMARY KEY NOT NULL, read INT, sent INT)")    
    conn.close()    

    while(True):
        conn = sqlite3.connect('watchdog-'+pid+'.db')
        current_time = int(time.time())
        retcode = p.poll() #returns None while subprocess is running
        txt = p.stdout.read()
        
        read_bytes = 0
        sent_bytes = 0

        temp = re.search("recvmsg(\(.*\)) = [0-9]+", txt)
        if temp != None:
            # print temp.group()
            read_bytes  = read_bytes + len(temp.group())

        temp = re.search("recvfrom(\(.*\)) = [0-9]+", txt)
        if temp != None:
            # print temp.group()
            read_bytes  = read_bytes + len(temp.group())

        temp = re.search("recv(\(.*\)) = [0-9]+", txt)
        if temp != None:
            # print temp.group()
            read_bytes  = read_bytes + len(temp.group())

        temp = re.search("send(\(.*\)) = [0-9]+", txt)
        if temp != None:
            # print temp.group()
            sent_bytes  = sent_bytes + len(temp.group())

        temp = re.search("sendto(\(.*\)) = [0-9]+", txt)
        if temp != None:
            # print temp.group()
            sent_bytes  = sent_bytes + len(temp.group())

        temp = re.search("sendmsg(\(.*\)) = [0-9]+", txt)
        if temp != None:
            # print temp.group()
            sent_bytes  = sent_bytes + len(temp.group())

        if(retcode is not None):
            break
        
        conn.execute("INSERT INTO 'data' (time,read,sent) VALUES ("+ str(current_time) +", " + str(read_bytes) + ", " + str(sent_bytes) +")")

        conn.close()
        sleep(1)


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
                processes[key]["thread"] = ""

        #print processes

        #sleep(2)

class myHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):

        temp = re.search("/api/get_processes\?duration=([0-9]+)", self.path) 
        print self.path

        if temp != None:
            
            print "api processes"
            duration = temp.group(1)
            start_time = int(time.time()) - int(duration)
            print start_time

            self.send_response(200)
            self.send_header('Content-type',"text/json")
            self.end_headers()

            send = []
            
            for key in processes:

                if processes[key]["live"] == False:
                    continue
                conn = sqlite3.connect('watchdog-'+key+'.db')
                c = conn.cursor()
                # c.execute('SELECT * FROM data WHERE time >= (?)', (str(start_time),))
                c.execute('SELECT * FROM data')
                temp_data = c.fetchall()
                print temp_data

            print send

            self.wfile.write(json.dumps(send))
            return

        # if self.path=="/" or self.path=="/index.html":
        #     self.path="resources/index.html"

        # if self.path=="/" or self.path=="/index.html":
        #     self.path="resources/index.html"

        self.path = "resources/" + self.path
        try:

            sendReply = False
            if self.path.endswith(".html"):
                mimetype='text/html'
                sendReply = True
            if self.path.endswith(".jpg"):
                mimetype='image/jpg'
                sendReply = True
            if self.path.endswith(".gif"):
                mimetype='image/gif'
                sendReply = True
            if self.path.endswith(".js"):
                mimetype='application/javascript'
                sendReply = True
            if self.path.endswith(".css"):
                mimetype='text/css'
                sendReply = True

            if sendReply == True:
                f = open(os.getcwd() + "/" + self.path)
                
                self.send_response(200)
                self.send_header('Content-type',mimetype)
                self.end_headers()
                self.wfile.write(f.read())
                f.close()
            return

        except IOError, e:
            print e
            self.send_error(404,'File Not Found: %s' % self.path)


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

        try:
        
            server = HTTPServer(('', 8888), myHandler)
            print server
            server.serve_forever()
        
        except KeyboardInterrupt:

            server.socket.close()





temp = watchdog()
temp.run()

