import boto3
import boto.ec2
import boto.ec2.cloudwatch
import datetime
import time

def get_current_instances():
	conn = boto.ec2.connect_to_region("us-west-2")
	reservations = conn.get_all_reservations()
	return [item.instances[0] for item in reservations]

def get_current_active_instances():
	all_instances_list = get_current_instances()
	current_active_instance = []
	for item in all_instances_list:
		if item.state == 'running':
			if item.id != 'i-af7aaf6b':
				current_active_instance.append(item.id)
	return current_active_instance

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
		datapoints = client.get_metric_statistics(Namespace='AWS/EC2',MetricName='CPUUtilization',Dimensions=[{'Name':'InstanceId','Value':instance}],StartTime=start,EndTime=end,Period=60,Statistics=['Average'],Unit='Percent')
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
	print 'number_of_active_instance is ' + str(number_of_active_instance)
	print 'average_utilization is ' + str(average_utilization)
	print 'CPUUtilization_dict is ' + str(CPUUtilization_dict)
	return average_utilization, number_of_active_instance, CPUUtilization_dict


# all_instances_list = get_current_instances()
# print all_instances_list

# # conn = boto.ec2.connect_to_region("us-west-2")
# # conn.run_instances('ami-5189a661')
# ec2 = boto3.resource('ec2')
# instance = ec2.create_instances(ImageId='ami-5189a661',MinCount=1,MaxCount=1,KeyName='Haozhang_ubuntu',SecurityGroupIds=['sg-768de412'],InstanceType='t2.micro',Monitoring={'Enabled':True})
# print str(instance).split('=')[1].split(')')[0]

print time.time()
fw = open('utilization_monitoring.txt','w')
fw.write("%-5s%-8s%-10s%s"%('n','number','average','utilization_list'))
fw.write('\n')
fw.close()
n = 0
while True:
	n += 1
	average_utilization, number_of_instance, CPUUtilization_dict = monitoring() 
	fw = open('utilization_monitoring.txt','a')
	fw.write("%-5s%-8s%-10s%s"%(n,number_of_instance,average_utilization,CPUUtilization_dict))
	fw.write('\n')
	fw.close()
	time.sleep(60)


