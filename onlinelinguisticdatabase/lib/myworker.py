import Queue
import threading
import subprocess
import os
import time, datetime

worker_q = Queue.Queue()

from pylons import config, app_globals

def generateBinaryFomaFSTFile():

    parserDataDir = config['app_conf']['parser_data']

    fstSourceFileName = 'phonology.foma'
    fstSourceFilePath = os.path.join(parserDataDir, fstSourceFileName)

    fstBinaryFileName = 'phon_bin.foma'
    fstBinaryFilePath = os.path.join(parserDataDir, fstBinaryFileName)

    process = subprocess.Popen(
        ['foma'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    msg = 'source %s\nsave stack %s\n' % (fstSourceFilePath, fstBinaryFilePath)
    result = process.communicate(msg)[0]

class MyWorkerThread(threading.Thread):

    def loadFomaSourceFile(self):
        print 'just entered load foma source file method'
        print 'now we are going to wait 2 seconds %s' % datetime.datetime.now()
        time.sleep(2)
        print 'now we have awoken %s' % datetime.datetime.now()
        parserDataDir = config['app_conf']['parser_data']
        fstSourceFileName = 'phonology.foma'
        fstSourceFilePath = os.path.join(parserDataDir, fstSourceFileName)
        self.fomaProcess.stdin.write('source %s\n' % fstSourceFilePath)
        print 'loaded foma source file'
    
    def writeFomaBinaryFile(self):
        print 'just entered the write foma binary file method'
        print 'now we are going to wait 2 seconds %s' % datetime.datetime.now()
        time.sleep(2)
        print 'now we have awoken %s' % datetime.datetime.now()
        parserDataDir = config['app_conf']['parser_data']
        fstBinaryFileName = 'phon_bin.foma'
        fstBinaryFilePath = os.path.join(parserDataDir, fstBinaryFileName)
        self.fomaProcess.stdin.write('save stack %s\n' % fstBinaryFilePath)
        print 'wrote foma binary file to %s' % fstBinaryFilePath

    def setFomaProcess(self, fomaProcess):
        self.fomaProcess = fomaProcess

    def run(self):
        print 'Worker thread is running.'
        self.app_globals = app_globals

        while True:
            msg = worker_q.get()
            print 'msg is %s' % msg
            try:
                if msg['msg'] == 'load foma source file':
                    self.loadFomaSourceFile()
                elif msg['msg'] == 'write foma binary file':
                    self.writeFomaBinaryFile()
                else:
                    print 'We got %s, what to do with it!' % (msg['msg'])
            except Exception, e:
                print 'Unable to process in worker thread: ' + str(e)
            worker_q.task_done()
   
def start_myworker():
    def startFomaProcess():
        fomaProcess = subprocess.Popen(
            ['foma'], shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        print 'started foma process'
        return fomaProcess

    fomaProcess = startFomaProcess()
    worker = MyWorkerThread()
    worker.setFomaProcess(fomaProcess)
    worker.start()