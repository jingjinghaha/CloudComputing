import random, time, Queue, os
from multiprocessing.managers import BaseManager
from multiprocessing import Pool,Process
import multiprocessing
import time, threading
#import test
availableList = []
def add(i):
	global availableList
	while True:
		
		for j in range(500):	
			time.sleep(2)
			print " Thread %d add %d"% (os.getpid(),test.a)
			availableList.append(test.a)