import boto.ec2
import boto.ec2.cloudwatch
import datetime
import time
import boto3

available_dict = {}

def createSlave(imageID = 'ami-5189a661',Key = 'Haozhang_ubuntu',insType = 't2.micro',id = None):
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
			data = 0.0
		aggregate_utilization += data
		number_of_active_instance += 1
		CPUUtilization_dict[instance] = data
	if number_of_active_instance == 0:
		average_utilization = 0.0
	else:
		average_utilization = float(aggregate_utilization/number_of_active_instance)
	print 'number_of_active_instance is ' + str(number_of_active_instance)
	print 'average_utilization is ' + str(average_utilization)
	print 'CPUUtilization_dict is ' + str(CPUUtilization_dict)
	return average_utilization, CPUUtilization_dict

def getSecurityGroup(groupName):
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
	conn = boto.ec2.connect_to_region("us-west-2")
	reservations = conn.get_all_reservations()
	return [item.instances[0] for item in reservations]

def get_current_active_instances():
	all_instances_list = get_current_instances()
	current_active_instance = []
	for item in all_instances_list:
		if item.state == 'pending':
			time.sleep(120)
	for item in all_instances_list:
		if item.state == 'running':
			if item.id != 'i-af7aaf6b':
				current_active_instance.append(item.id)
	return current_active_instance 

def get_non_active_instance():
	all_instances_list = get_current_instances()
	non_active_instance = []
	for item in all_instances_list:
		if item.state == 'stopped':
			non_active_instance.append(item.id)
	return non_active_instance

def add_instance_policy():
	print 'in add_instance_policy()'
	average_utilization, CPUUtilization_dict = monitoring()
	if average_utilization >= 80.0:
		add_instance()

def remove_instance_policy():
	print 'in remove_instance_policy()'
	average_utilization, CPUUtilization_dict = monitoring()
	if average_utilization <= 20.0:
		remove_instance()

def add_instance():
	print 'in add_instance()'
	# current_active_instance = get_current_active_instances()
	# lock1.acquire()
	# try:
	for i in range(1,6):
		if available_dict.has_key(i):
			pass
		else:
			instanceid = createSlave(id=i) 
			time.sleep(10) 
			available_dict[i] = instanceid
			print 'create a slave with channel id '+str(i) 
			break
	# finally: 
	# 	lock1.release() 

def remove_instance():
	print 'in remove_instance()'
	average_utilization, CPUUtilization_dict = monitoring()
	last_utilized = 100.0
	for key in CPUUtilization_dict.keys():
		if last_utilized > CPUUtilization_dict[key]:
			last_utilized = CPUUtilization_dict[key]
	for key in CPUUtilization_dict.keys():
		if last_utilized == CPUUtilization_dict[key]:
			instanceid = key
	if instanceid:
		# print instanceid
		lock1.acquire()
		try:
			for channelid in available_dict.keys():
				if available_dict[channelid] == instanceid:
					break  
			if task_check(channelid): 
				available_dict.pop(channelid)
				conn = boto.ec2.connect_to_region("us-west-2")
				conn.terminate_instances(instance_ids=[instanceid]) 
				print 'terminate a slave with channel id ' + str(channelid)
		finally:
			lock1.release() 

def check_instance_status(instanceid):
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
			time.sleep(120)
		else: 
			if len(task_list)>0:
				add_instance() 
		

def terminating_active_slave():
	print 'in terminating_active_slave()' 
	conn = boto.ec2.connect_to_region("us-west-2")
	current_active_instance = get_current_active_instances()
	for instance in current_active_instance:
		conn.terminate_instances(instance_ids=[instance])

def task_check(channelid): 
	for task in task_list.keys():
		if task_list[task].scheduledChannel == channedid:
			if task_list[task].isFinished:
				return True
	return False

# terminating_active_slave() 
# instanceid = createSlave(id=1) 
# time.sleep(10) 
# available_dict[1] = instanceid
# print available_dict
# instanceid = createSlave(id=2) 
# time.sleep(10) 
# available_dict[2] = instanceid
# print available_dict

terminating_active_slave()
add_instance() 
add_instance() 
add_instance() 
add_instance() 
add_instance() 
# autoscaling()

# average_utilization, CPUUtilization_dict = monitoring()
# print average_utilization
# print CPUUtilization_dict

# while True: 
# 	autoscaling()
# 	sleep(300)     #....
# 	f = open('Lock')
# 	f.close()
# 	sleep(300)


# instancelist = get_current_instances()
# print [item.id for item in instancelist]
# print [item.state for item in instancelist]


# current_active_instance = get_current_active_instances()
# response = check_instance_status(current_active_instance[0])
# print current_active_instance[0]
# print response

# conn = boto.ec2.connect_to_region("us-west-2")
# statuses = conn.get_all_instance_status()
# status = statuses[0]
# print status.instance_status


