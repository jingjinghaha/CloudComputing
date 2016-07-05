import random, time, Queue,os
from multiprocessing.managers import BaseManager
from multiprocessing import Pool,Process
import multiprocessing
import test2
import time, threading
a = 34
def printLen():
	threading.Thread(target = test2.add, args = (2,)).start()
	while True:		
		time.sleep(10)
		print " Thread Id %d, len of list is %d "%(os.getpid(),len(test2.availableList) )
		
Process(target = printLen, args=()).start()
#Process(target = test2.add, args=()).start()
