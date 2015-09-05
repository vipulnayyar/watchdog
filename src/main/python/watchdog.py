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
import MySQLdb

processes = {}
plock = False
ret = ""


def pid_thread(pid):
    
    print "started"
    global plock
    p = subprocess.Popen(str("strace -p " + pid + " ").split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    global processes
    
    retcode = p.poll() #returns None while subprocess is running
    txt = p.stdout.read()

    print " read"

    if txt.find("strace: attach: ptrace(PTRACE_ATTACH, ...): Operation not permitted") >= 0:
        while plock:
            plock =True

        processes[pid]["live"] = False
        processes[pid]["state"] = "remove"
        processes[pid]["thread"] = ""
        
        plock = False

        return

    print "ready"

    db = MySQLdb.connect(host="localhost", # your host, usually localhost
                     user="root", # your username
                      passwd="qwerty", # your password
                      db="watchdog")

    cur = db.cursor()
    query =  "CREATE TABLE IF NOT EXISTS `" + pid + "` (`time` INT PRIMARY KEY NOT NULL, `read` INT, `sent` INT)"
    print query
    cur.execute(query)
    db.commit()
    db.close()
    # conn = sqlite3.connect('watchdog-'+pid+'.db')
    # conn.execute("CREATE TABLE IF NOT EXISTS 'data' (time INT PRIMARY KEY NOT NULL, read INT, sent INT)")    
    # conn.close()    
        
    while(True):
        
        print "in"

        # # print pid 
        # # print txt

        read_bytes = 0
        sent_bytes = 0

        temp = re.search("^recvmsg(\(.*\)) = [0-9]+", txt)
        if temp != None:
            # print temp.group()
            read_bytes  = read_bytes + len(temp.group())

        temp = re.search("^recvfrom(\(.*\)) = [0-9]+", txt)
        if temp != None:
            # print temp.group()
            read_bytes  = read_bytes + len(temp.group())

        temp = re.search("^recv(\(.*\)) = [0-9]+", txt)
        if temp != None:
            # print temp.group()
            read_bytes  = read_bytes + len(temp.group())

        temp = re.search("^send(\(.*\)) = [0-9]+", txt)
        if temp != None:
            # print temp.group()
            sent_bytes  = sent_bytes + len(temp.group())

        temp = re.search("^sendto(\(.*\)) = [0-9]+", txt)
        if temp != None:
            # print temp.group()
            sent_bytes  = sent_bytes + len(temp.group())

        temp = re.search("^sendmsg(\(.*\)) = [0-9]+", txt)
        if temp != None:
            # print temp.group()
            sent_bytes  = sent_bytes + len(temp.group())

        if(retcode is not None):
            break
       
        db = MySQLdb.connect(host="localhost", # your host, usually localhost
                     user="root", # your username
                      passwd="qwerty", # your password
                      db="watchdog")

        cur = db.cursor()  
        current_time = int(time.time())
        cur.execute("INSERT INTO `" + pid +"` (`time`,`read`,`sent`) VALUES ("+ str(current_time) +", " + str(read_bytes) + ", " + str(sent_bytes) +")")
        db.commit()
        db.close()

        # conn = sqlite3.connect('watchdog-'+pid+'.db')        
        # c = conn.cursor()
        # # print current_time
        # c.execute("INSERT INTO 'data' (time,read,sent) VALUES ("+ str(current_time) +", " + str(read_bytes) + ", " + str(sent_bytes) +")")
        print " inserted " + str(current_time) + " " +  str(sent_bytes) + " " + str(read_bytes)
        
        # conn.commit()
        # conn.close()
        
        sleep(1)

        if processes[pid]["live"] == False:
            return

        retcode = p.poll() #returns None while subprocess is running
        txt = p.stdout.read()


def net_process_monitor():

    global processes
    global plock

    while True:
        net_processes = commands.getoutput("netstat -tap 2> /dev/null | awk '{print $7}' | grep -oE \"[0-9]+\" | uniq") 
        parr = net_processes.split()
        
        current_time = int(time.time())

        # print processes
        #print parr
        for i in xrange(0,len(parr)-1):
            
            while plock:
                plock = True


            if parr[i] not in processes:
                processes[parr[i]] = {}
            
            if "state" in processes[parr[i]] and processes[parr[i]]["state"] == "remove":
                continue

            if "live" not in processes[parr[i]] or processes[parr[i]]["live"] != True:
                processes[parr[i]]["thread"] = Thread(target = pid_thread, args = (parr[i],))
                processes[parr[i]]["entry"] =  current_time
                processes[parr[i]]["thread"].daemon = True
                processes[parr[i]]["thread"].start()
                processes[parr[i]]["live"] = True

        for key in processes:
            if processes[key]["live"] == True and processes[key]["entry"] != current_time:
                processes[key]["live"] = False
                processes[key]["thread"] = ""

        #sleep(2)
        plock = False

class myHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):

        temp = re.search("/api/get_processes\?duration=([0-9]+)", self.path) 
        print self.path

        global processes

        if temp != None:
            
            print "api processes"
            duration = temp.group(1)
            start_time = int(time.time()) - int(duration)
            #print start_time

            self.send_response(200)
            self.send_header('Content-type',"text/json")
            self.end_headers()

            send = []

            #print processes
            
            for key in processes:
                #print "key"

                if processes[key]["live"] == False:
                    continue
                print "con"
                db = MySQLdb.connect(host="localhost", # your host, usually localhost
                     user="root", # your username
                      passwd="qwerty", # your password
                      db="watchdog")

                cur = db.cursor()  
                current_time = int(time.time())
                cur.execute('SELECT * FROM data WHERE time >= (?)', (str(start_time),))
                db.commit()
                db.close()

                # conn = sqlite3.connect('watchdog-'+key+'.db')
                # c = conn.cursor()
                # c.execute('SELECT * FROM data WHERE time >= (?)', (str(start_time),))
                #c.execute('SELECT * FROM data')
                temp_data = cur.fetchall()
                # print temp_data
                temp_obj = {}
                temp_obj["pid"] = key
                temp_obj["data"] = temp_data
                send.append(temp_obj)
                # conn.close()

            print send

            self.wfile.write(json.dumps(send))
            return

        temp = re.search("/process/([0-9]+).*", self.path) 
        print self.path

        if temp != None:
            
            print "process page"
            pid = temp.group(1)

            temp = re.search("\?duration=([0-9]+)", self.path) 

            start_time = -1
            if temp!=None:
                duration = temp.group(1)
                start_time = int(time.time()) - int(duration)
            
            self.send_response(200)
            self.send_header('Content-type',"text/json")
            self.end_headers()

            send = []
            
            conn = sqlite3.connect('watchdog-'+pid+'.db')
            c = conn.cursor()

            if start_time == -1:
                start_time = int(time.time()) - 86400

            c.execute('SELECT * FROM data WHERE time >= (?)', (str(start_time),))
            # c.execute('SELECT * FROM data')
            
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
            server = HTTPServer(('', 9888), myHandler)
            print server
            thread2= Thread(target = server.serve_forever)
            thread2.start()
            print "stop"
        except KeyboardInterrupt:
            print "KeyboardInterrupt"
            #thread.stop()
            server.socket.close()
            sys.exit(0)




temp = watchdog()
temp.run()

