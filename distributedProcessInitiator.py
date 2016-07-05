import random, time, Queue, threading
from multiprocessing.managers import BaseManager
from multiprocessing import Pool,Process
from copy import deepcopy
import multiprocessing #,monitoring
import boto.ec2
import boto.ec2.cloudwatch
import datetime
import time
import boto3
task_list={}
available_dict = {1:1,2:2,3:3,4:4,5:5}
cache = {'totalcheck':0,'totalcount':0}
def createSlave(imageID = 'ami-5189a661',Key = 'Haozhang_ubuntu',insType = 't2.micro',id = None):
	global task_list,available_dict
	assert 1<=id<=5
	filename = '''distributedProcessReceiver'''+str(id)+'''.py'''
	slavedata = '''#!/bin/sh
cd /home/ubuntu
rm -rf *.py
rm -rf *.tar.gz
wget http://52.27.55.20/testdata.tar.gz
wget http://52.27.55.20/traindata.tar.gz
wget http://52.27.55.20/'''+filename+'''
wget http://52.27.55.20/knn.py
tar -zxf testdata.tar.gz
tar -zxf traindata.tar.gz
sudo apt-get update
sudo apt-get -y install python-pip
sudo apt-get -y install python-dev
sudo pip install numpy
python '''+filename
	associatedGroup = []
	associatedGroup.append(getSecurityGroup('slave'))
	# print associatedGroup
	conn = boto.ec2.connect_to_region("us-west-2")
	new_reseration = conn.run_instances(imageID,key_name = Key, instance_type= insType,security_group_ids=['sg-768de412'],monitoring_enabled=True,user_data = slavedata)
	# conn.run_instances(imageID,key_name = Key, instance_type= insType,security_groups = associatedGroup,user_data = slavedata)
	# ec2 = boto3.resource('ec2')
	# instance = ec2.create_instances(ImageId=imageID,MinCount=1,MaxCount=1,KeyName=Key,SecurityGroupIds=['sg-768de412'],UserData=slavedata,InstanceType='t2.micro',Monitoring={'Enabled':True})
	instance = new_reseration.instances[0]
	while instance.state == 'pending':
		print 'instance state: %s' %instance.state
		time.sleep(10)
		instance.update() 
	# time.sleep(200)
	# return str(instance).split('=')[1].split(')')[0]
	print instance.id 
	return instance.id
	

def monitoring():
	global task_list,available_dict
	print 'in monitoring()'
	current_active_instance = get_current_active_instances()
	client = boto3.client('cloudwatch')
	CPUUtilization_dict = {}
	end = datetime.datetime.utcnow()
	start = end - datetime.timedelta(seconds=120)
	number_of_active_instance = 0
	aggregate_utilization = 0
	average_utilization = 0
	for instance in current_active_instance:
		# print instance
		datapoints = client.get_metric_statistics(Namespace='AWS/EC2',MetricName='CPUUtilization',Dimensions=[{'Name':'InstanceId','Value':instance}],StartTime=start,EndTime=end,Period=60,Statistics=['Average'],Unit='Percent')
		# print datapoints
		# print datapoints['Datapoints'][0]['Timestamp']
		# print len(datapoints['Datapoints'])
		# for i in range(len(datapoints['Datapoints'])):
		# 	print datapoints['Datapoints'][i]['Timestamp']
		if len(datapoints['Datapoints']) > 0:
			data = datapoints['Datapoints'][0]['Average']
		else:
			data = 50.0
		aggregate_utilization += data
		number_of_active_instance += 1
		CPUUtilization_dict[instance] = data
	if number_of_active_instance == 0:
		average_utilization = 0.0
	else:
		average_utilization = float(aggregate_utilization/number_of_active_instance)
	# print 'number_of_active_instance is ' + str(number_of_active_instance)
	# print 'average_utilization is ' + str(average_utilization)
	# print 'CPUUtilization_dict is ' + str(CPUUtilization_dict)
	return average_utilization, CPUUtilization_dict

def getSecurityGroup(groupName):
	global task_list,available_dict
	conn = boto.ec2.connect_to_region("us-west-2")
	rs = conn.get_all_security_groups()
	for item in rs:
		if item.name == groupName:
			return item
	for item in rs:
		if item.name == 'default':
			return item
	return None

def get_current_instances():
	global task_list,available_dict
	conn = boto.ec2.connect_to_region("us-west-2")
	reservations = conn.get_all_reservations()
	return [item.instances[0] for item in reservations]

def get_current_active_instances():
	global task_list,available_dict
	all_instances_list = get_current_instances()
	current_active_instance = []
	for item in all_instances_list:
		if item.state == 'pending':
			time.sleep(60)
	for item in all_instances_list:
		if item.state == 'running':
			if item.id != 'i-af7aaf6b':
				current_active_instance.append(item.id)
	return current_active_instance 

def get_non_active_instance():
	global task_list,available_dict
	all_instances_list = get_current_instances()
	non_active_instance = []
	for item in all_instances_list:
		if item.state == 'stopped':
			non_active_instance.append(item.id)
	return non_active_instance

def add_instance_policy():
	global task_list,available_dict
	print 'in add_instance_policy()'
	average_utilization, CPUUtilization_dict = monitoring()
	if average_utilization >= 80.0:
		add_instance()

def remove_instance_policy():
	global task_list,available_dict
	print 'in remove_instance_policy()'
	average_utilization, CPUUtilization_dict = monitoring()
	if average_utilization <= 20.0:
		remove_instance()

def add_instance():
	global task_list,available_dict
	print 'in add_instance()'
	# current_active_instance = get_current_active_instances()
	for i in range(1,6):
		if available_dict.has_key(i):
			pass
		else:
			lock1.acquire()
			try:
				instanceid = createSlave(id=i) 
				available_dict[i] = instanceid
			finally:
				lock1.release() 	
			print 'create a slave with channel id '+str(i) 
			break

	

def remove_instance():
	global task_list,available_dict
	print 'in remove_instance()'
	average_utilization, CPUUtilization_dict = monitoring()
	last_utilized = 100.0
	instanceid = False
	for key in CPUUtilization_dict.keys():
		if last_utilized > CPUUtilization_dict[key]:
			last_utilized = CPUUtilization_dict[key]
	for key in CPUUtilization_dict.keys():
		if last_utilized == CPUUtilization_dict[key]:
			instanceid = key
	if instanceid:
		for channelid in available_dict.keys():
			if available_dict[channelid] == instanceid:
				break  
		if task_check(channelid): 
			lock1.acquire()
			try:
				available_dict.pop(channelid)
			finally:
				lock1.release() 
			conn = boto.ec2.connect_to_region("us-west-2")
			conn.terminate_instances(instance_ids=[instanceid]) 
			print 'terminate a slave with channel id ' + str(channelid)


def check_instance_status(instanceid):
	global task_list,available_dict
	conn = boto.ec2.connect_to_region("us-west-2")
	statuses = conn.get_all_instance_status()
	for status in statuses:
		temp = str(status)
		if instanceid == temp.split(':')[1]:
			return status.instance_status
			
def autoscaling():
	global task_list,available_dict
	while True:
		print 'in autoscaling()'
		current_active_instance = get_current_active_instances()
		if current_active_instance: 
			add_instance_policy()
			remove_instance_policy()
			time.sleep(60)
		else: 
			task_list_copy = deepcopy(task_list)
			for key in task_list_copy:
				if not task_list_copy[key].isFinished:
					add_instance() 
					break


				

def terminating_active_slave():
	global task_list,available_dict
	print 'in terminating_active_slave()' 
	conn = boto.ec2.connect_to_region("us-west-2")
	current_active_instance = get_current_active_instances()
	for instance in current_active_instance:
		conn.terminate_instances(instance_ids=[instance])

def task_check(channelid): 
	global task_list,available_dict
	for task in task_list.keys():
		if task_list[task].scheduledChannel == channelid:
			if task_list[task].isFinished:
				pass
			else:
				return False
	return True
		
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
toCache = multiprocessing.Queue()
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

manager = QueueManager(address=('', 5000), authkey='zhanghao')
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
def update_Cache(resultQueue):
	global cache
	cacheMaxSize = 102
	while True:
		task = resultQueue.get()
		lock2.acquire()
		try:
			if len(cache) < cacheMaxSize:
				if task.taskParameter not in cache:
					dic = cache.setdefault(task.taskParameter,{})
					dic['label'] = task.taskResult
					dic['hitcount'] = 0
			else:
				if task.taskParameter not in cache:
					count = inf
					key_copy = None
					for key in cache:
						if key != 'totalcheck' and key != 'totalcount':
							if cache[key]['hitcount'] < count:
								count = cache[key]['hitcount']
								key_copy = key
					cache.pop(key_copy)
					dic = cache.setdefault(task.taskParameter,{})
					dic['label'] = task.taskResult
					dic['hitcount'] = 0
		finally:
			lock2.release()
	
def is_cache_hit(task):
	global cache
	lock2.acquire()
	try:
		cache['totalcheck'] += 1
		if task.taskParameter not in cache:
			return None
		else:
			cache[task.taskParameter]['hitcount'] += 1
			cache['totalcount'] += 1
			return cache[task.taskParameter]['label']
	finally:
		lock2.release()
		
def get_result_from_slave(intra_q,toCache):
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
		toCache.put(value)
		
def scheduleTasks(inner_Q,task1,task2,task3,task4,task5):
	global task_list,cache
	while True:
		task = inner_Q.get()
		#check_cache_result = is_cache_hit(task)
		check_cache_result = None
		if check_cache_result == None:
			channel = makeDecision()
			#channel = 1
			#channel = random_makeDecision()
			task.scheduledChannel = channel
			task.isScheduled = True
			lock1.acquire()
			print ("put task %d with paremeter %d into channel %d" % (task.taskId,task.taskParameter,channel))
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
			try:
				task_list[task.taskId] = task
			finally:
				lock1.release()
		else:
			task.scheduledChannel = -1
			task.isScheduled = True
			task.isFinished  = True
			task.taskResult = check_cache_result
			task.finishTime = time.time()
			lock1.acquire()
			try:
				task_list[task.taskId] = task
			finally:
				lock1.release()
			print ("cache hit for task %s with parameter %s" % (task.taskId,task.taskParameter))
				
def isfull(channel,MAX):
	global task_list,available_dict
	count = 0
	lock1.acquire()
	try:
		for task in task_list:
			if task_list[task].isScheduled and (not task_list[task].isFinished):
				if task_list[task].scheduledChannel == channel:
					count +=1
		return count > MAX
	finally:
		lock1.release()
		
lastChannel = 0			
def makeDecision():
	global lastChannel,available_dict
	channel = (lastChannel)%5 + 1 
	while (channel not in available_dict.keys()) or ((channel in available_dict.keys()) and isfull(channel,20)):
		#print "in while loop in makeDecision"
		channel = (channel)%5 + 1
	print "make a decision ",channel
	lastChannel = channel
	return channel
	
def random_makeDecision():
	return random.randint(1,5)

#Process responsible for fetching data from slave		
threading.Thread(target = get_result_from_slave, args = (result1,toCache)).start()	
threading.Thread(target = get_result_from_slave, args = (result2,toCache)).start()
threading.Thread(target = get_result_from_slave, args = (result3,toCache)).start()
threading.Thread(target = get_result_from_slave, args = (result4,toCache)).start()
threading.Thread(target = get_result_from_slave, args = (result5,toCache)).start()
#Process for scheduling
threading.Thread(target = scheduleTasks, args = (inner_Q,task1,task2,task3,task4,task5)).start()
#Process for auto scaling:
#threading.Thread(target = autoscaling, args = ()).start()
#Updating cache
#threading.Thread(target = update_Cache, args = (toCache,)).start()
TASKNUM = 500
for i in range(TASKNUM):
	#time.sleep(random.randint(3,12))
	#time.sleep(random.randint(5,10))
	time.sleep(0.1)
	#n = random.randint(0, 10000)
	#print('Put task %d...' % i)
	parameter = random.randint(0,94)
	#parameter = 5
	print "Generating new task......"
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
	global cache
	fw = open('all_channels_statictis.txt','w')
	fw.write("%-30s%-30s%-30s%-30s%-30s" % ('channel','totalTaskNumber','totalTime','max_time','averageTime'))
	fw.write('\n')
	for item in sta:
		nr = sta[item]
		fw.write("%-30s%-30s%-30s%-30s%-30s" % (item,nr['task_numbers'],nr['total_time'],nr['max_time'],nr['average_time']))
		fw.write('\n')
	#fw.write (" total check %-20s, hit counts %-20s, hit ratio is %.2f" % (cache['totalcheck'],cache['totalcount'],float(cache['totalcount'])/cache['totalcheck']))
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
			for id in range(TASKNUM):
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
				for id in range(TASKNUM):
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