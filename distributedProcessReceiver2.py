import time, sys, Queue, os, random
from multiprocessing.managers import BaseManager
from multiprocessing import Pool,Process,Queue
import knn
class Task(object):
	def __init__(self, taskId=None, taskParameter=None, startTime=None, finishTime=None, isScheduled = False, scheduledChannel = None, isFinished=False, taskResult=None):
		self.taskId =  taskId
		self.taskParameter = taskParameter
		self.startTime = startTime
		self.finishTime = finishTime
		self.isFinished = isFinished
		self.isScheduled = isScheduled
		self.scheduledChannel = scheduledChannel
		self.taskResult = taskResult	
	def getResponseTime (self):
		return (self.finishTime - self.startTime)




class QueueManager(BaseManager):
	pass


QueueManager.register('get_task_queue2')
QueueManager.register('get_result_queue2')


server_addr = '52.27.55.20'
print('Connect to server %s...' % server_addr)

m = QueueManager(address=(server_addr, 5000), authkey='jingjing')

connec = True
while connec:
	try:
		m.connect()
		connec = False
	except:
		time.sleep(1)

task2 = m.get_task_queue2()
result2 = m.get_result_queue2()

#define the intensive compute task
#define the intensive compute task
def long_time_task(task,result_q):	
	#print "Run task whose parameter is %d, pid = d%.." % (parameter,os.getpid())
	#print "hahaha"
	#if parameter == 0:
		#return 1
	#else:
		#return parameter * long_time_task(parameter-1)
	# value = parameter[0] * parameter[0]
	# result = (value,parameter[1])
	# result_q.put(result)
	parameter = task.taskParameter
	result = knn.handwritingSingleTest(parameter)
	task.taskResult = result
	result_q.put(task)
			
#def read_from_innerQ_and_write_to_outerQ(inner_q,result_q):
	#while True:
		#value = inner_q.get()
		#result_q.put(value)
	

#inner_q = Queue()
#Process(target = read_from_innerQ_and_write_to_outerQ, args=(inner_q,result2)).start()
	
while True:
	try:
		task = Task()
		task = task2.get()
		Process(target = long_time_task, args = (task,result2)).start()
	except Queue.Empty:
		print('task queue is empty.')

print('worker exit.')
