import boto.ec2
import boto.ec2.cloudwatch
import boto.ec2.address
import socket
import fcntl
import struct


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])
	
def init_securityGroups():
	conn = boto.ec2.connect_to_region("us-west-2")
	rs = conn.get_all_security_groups()
	master = conn.create_security_group('master', 'Our Master')
	myIP =  get_ip_address('eth0')
	master.authorize('tcp', 80, 80, '0.0.0.0/0')
	master.authorize('tcp', 22, 22, myIP + '/32')
	slave = conn.create_security_group('slave', 'Our Slaves')
	slave.authorize(src_group = master)
	#print rs[index].name
	#print rs[index].rules
	#print rs
	#slave_security_group = conn.create_security_group('slave', 'The application tier')
	
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
	
def listSecurityGroups():
	conn = boto.ec2.connect_to_region("us-west-2")
	rs = conn.get_all_security_groups()
	return [item.name for item in rs]
	
def createMaster(imageID = 'ami-5189a661',Key = 'jingjing_ubuntu',insType = 't2.micro'):
	default_userdata = """#!/bin/sh
sudo apt-get install git
git clone https://github.com/sunnyyeti/CloudComputing.git
sudo apt-get install apache2
sudo /etc/init.d/apache2 start"""
	conn = boto.ec2.connect_to_region("us-west-2")
	associatedGroup = []
	associatedGroup.append(getSecurityGroup('master'))
	conn.run_instances(imageID,key_name = Key, instance_type= insType,security_groups = associatedGroup,user_data=default_userdata)
	
def createSlave(imageID = 'ami-5189a661',Key = 'jingjing_ubuntu',insType = 't2.micro',id = None):
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



	conn = boto.ec2.connect_to_region("us-west-2")
	associatedGroup = []
	associatedGroup.append(getSecurityGroup('slave'))
	conn.run_instances(imageID,key_name = Key, instance_type= insType,security_groups = associatedGroup,user_data = slavedata )
 
def removeinstance(indtanceId):
	pass
	
def allocate_elasticIP():
	conn = boto.ec2.connect_to_region("us-west-2")
	return conn.allocate_address()
	
def get_current_instances():
	conn = boto.ec2.connect_to_region("us-west-2")
	reservations = conn.get_all_reservations()
	return [item.instances[0] for item in reservations]
	
#init_securityGroups()
# print listSecurityGroups()
# createMaster()
# createSlave()
# conn = boto.ec2.connect_to_region("us-west-2")
# reservations = conn.get_all_reservations()
# instance = reservations[0].instances[0]
# print instance.id,instance.instance_type,instance.placement,instance.state,instance.public_dns_name
# elasticIP = conn.allocate_address()
# print elasticIP.public_ip, elasticIP.instance_id
#print "type of conn",type(conn)
# for i in get_current_instances():
	# print i.state
#createMaster()
instancelist = get_current_instances()
print [item.id for item in instancelist]
print [item.state for item in instancelist]
print getSecurityGroup('master')

#createSlave(id=2)
#createSlave(id=3)
# elasticIP = allocate_elasticIP()
# while instancelist[0].state == u'pending':
	# pass
# elasticIP.associate(instancelist[0].id)	
