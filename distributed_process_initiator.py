import random, time, Queue, threading
from multiprocessing.managers import BaseManager
from multiprocessing import Pool,Process
import multiprocessing #,monitoring

class Task(object):
	def __init__(self, taskId, taskParameter, startTime=None, finishTime=None, isScheduled = False, scheduledChannel = None, isFinished=False, taskResult=None):
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
	
task_queue1 = Queue.Queue()
result_queue1 = Queue.Queue()
task_queue2 = Queue.Queue()
result_queue2 = Queue.Queue()
task_queue3 = Queue.Queue()
result_queue3 = Queue.Queue()
task_queue4 = Queue.Queue()
result_queue4 = Queue.Queue()
task_queue5 = Queue.Queue()
result_queue5 = Queue.Queue()

inner_Q = multiprocessing.Queue()
task_list={}
available_dict = {1:1,2:2,3:3,4:4,5:5}
class QueueManager(BaseManager):
    pass


QueueManager.register('get_task_queue1', callable=lambda: task_queue1)
QueueManager.register('get_result_queue1', callable=lambda: result_queue1)
QueueManager.register('get_task_queue2', callable=lambda: task_queue2)
QueueManager.register('get_result_queue2', callable=lambda: result_queue2)
QueueManager.register('get_task_queue3', callable=lambda: task_queue3)
QueueManager.register('get_result_queue3', callable=lambda: result_queue3)
QueueManager.register('get_task_queue4', callable=lambda: task_queue4)
QueueManager.register('get_result_queue4', callable=lambda: result_queue4)
QueueManager.register('get_task_queue5', callable=lambda: task_queue5)
QueueManager.register('get_result_queue5', callable=lambda: result_queue5)

manager = QueueManager(address=('', 5000), authkey='jingjing')
manager.start()
task1 = manager.get_task_queue1()
result1 = manager.get_result_queue1()
task2 = manager.get_task_queue2()
result2 = manager.get_result_queue2()
task3 = manager.get_task_queue3()
result3 = manager.get_result_queue3()
task4 = manager.get_task_queue4()
result4 = manager.get_result_queue4()
task5 = manager.get_task_queue5()
result5 = manager.get_result_queue5()

lock1 = threading.Lock()
lock2 = threading.Lock()

def get_result_from_slave(intra_q):
	global task_list
	while True:
		value = intra_q.get()
		value.finishTime = time.time()
		value.isFinished = True
		lock1.acquire()
		try:
			task_list[value.taskId] = value
		finally:
			lock1.release()
		print "Got result %.2f from channel %d" % (value.taskResult,value.scheduledChannel)	
		
def scheduleTasks(inner_Q,task1,task2,task3,task4,task5):
	global task_list
	while True:
		task = inner_Q.get()
		#channel = makeDecision()
		channel = random_makeDecision()
		task.scheduledChannel = channel
		task.isScheduled = True
		print ("put task %d into channel %d" % (task.taskParameter,channel))
		if channel == 1:
			task1.put(task)
		elif channel == 2:
			task2.put(task)
		elif channel == 3:
			task3.put(task)
		elif channel == 4:
			task4.put(task)
		elif channel == 5:
			task5.put(task)
		lock1.acquire()
		try:
			task_list[task.taskId] = task
		finally:
			lock1.release()
		
lastChannel = 0			
def makeDecision():
	global lastChannel,available_dict
	channel = (lastChannel)%5 + 1
	lock1.acquire()
	try:
		while channel not in available_dict.keys():
			channel = (lastChannel)%5 + 1
	finally:
		lock1.release()
	lastChannel = channel
	return channel
	
def random_makeDecision():
	return random.randint(1,5)

#Process responsible for fetching data from slave		
threading.Thread(target = get_result_from_slave, args = (result1,)).start()	
threading.Thread(target = get_result_from_slave, args = (result2,)).start()
threading.Thread(target = get_result_from_slave, args = (result3,)).start()
threading.Thread(target = get_result_from_slave, args = (result4,)).start()
threading.Thread(target = get_result_from_slave, args = (result5,)).start()
#Process for scheduling
threading.Thread(target = scheduleTasks, args = (inner_Q,task1,task2,task3,task4,task5)).start()
	
	
for i in range(100):
	time.sleep(1)
	#n = random.randint(0, 10000)
	#print('Put task %d...' % i)
	parameter = random.randint(2,10)
	newtask = Task(taskId = i,taskParameter = parameter,startTime = time.time())
	lock1.acquire()
	try:
		task_list[i] = newtask
	finally:
		lock1.release()
	inner_Q.put(newtask)
	

def channel_log_specifics(task):
	channel = task.scheduledChannel
	fw = open('channel'+str(channel)+'_log.txt','a')
	fw.write("Task %3s comes at %10.2f, and ends at %10.2f, response time is %10.2f\n" % (task.taskId,task.startTime,task.finishTime,task.getResponseTime()))
	fw.close()

def channels_log_statistics(sta):
	fw = open('all_channels_statictis.txt','w')
	fw.write("%-30s%-30s%-30s%-30s%-30s" % ('channel','totalTaskNumber','totalTime','max_time','averageTime'))
	fw.write('\n')
	for item in sta:
		nr = sta[item]
		fw.write("%-30s%-30s%-30s%-30s%-30s" % (item,nr['task_numbers'],nr['total_time'],nr['max_time'],nr['average_time']))
		fw.write('\n')
	fw.close()
		
# print('Try get results...')
# for i in range(11):
    # r = result.get()
    # print'Result:',r
sleepforever = False
while True:	
	if sleepforever:
		while True:
			time.sleep(100)
	else:
		end = True
		lock1.acquire()
		try:
			for id in task_list.keys():
				if task_list[id].isFinished == False:
					end = False
					break
		finally:
			lock1.release()
			
		if end:
			print "all tasks have been finished......"
			#filename = 'loadBalanceRandom.txt'
			# fw = open(filename,'w')
			sta = {}
			lock1.acquire()
			try:
				for id in range(100):
					nr = sta.setdefault(task_list[id].scheduledChannel,{})
					tasknum = nr.setdefault('task_numbers',0) 
					nr['task_numbers'] = tasknum + 1
					total_time = nr.setdefault('total_time',0) 
					nr['total_time'] = total_time + task_list[id].getResponseTime()
					maxtime = nr.setdefault('max_time',0) 
					if task_list[id].getResponseTime() > maxtime:
						nr['max_time'] = task_list[id].getResponseTime()
					average_time = nr.setdefault('average_time',0)
					nr['average_time'] = float(nr['total_time'])/float(nr['task_numbers'])
					sta[task_list[id].scheduledChannel] = nr
					channel_log_specifics(task_list[id])
			finally:
				lock1.release()
			channels_log_statistics(sta)
			# for item in sta:
				# fw.write("channel " +str(item)+" received " + str(sta[item])+" jobs\n")
			# fw.close()
			print "Writing finished"
			sleepforever = True
			print "Sleep forever....."
		time.sleep(30)
manager.shutdown()