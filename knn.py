from numpy import *
# import matplotlib
# import matplotlib.pyplot as plt
import operator
from os import listdir
filename1 = "datingTestSet.txt"
filename2 = "datingTestSet2.txt"
def createDataSet():
	group = array([[1.0,1.1],[1.0,1.0],[0,0],[0,0.1]])
	labels = ['A',"A",'B','B']
	return group, labels

def classify0 (inX, dataSet, labels, k):
	number_of_samples = dataSet.shape[0]
	new_dataSet_inX = tile(inX,(number_of_samples,1))
	diff_dataSet = new_dataSet_inX - dataSet
	tmp1 = diff_dataSet**2
	tmp2 = tmp1.sum(axis=1)
	distance = tmp2**0.5
	index = distance.argsort()
	dic = {}
	for i in range(k):
		var = labels[index[i]]
		dic[var] = dic.get(var,0)+1
	count = sorted(dic.iteritems(),key = operator.itemgetter(1), reverse = True)
	return count[0][0]
	
#group,labels = createDataSet()
#print classify0([1,1],group,labels,2)

def file2matrix(filename):
	file = open(filename)
	file_list = file.readlines()
	number_of_lines = len(file_list)
	dataMatrix = zeros((number_of_lines,3))
	index = 0
	labelsVector = []
	for line in file_list:
		line = line.strip()
		stringFromLine = line.split('\t')
		dataMatrix[index,:] = stringFromLine[0:3]
		labelsVector.append(int(stringFromLine[-1]))
		index += 1
	return dataMatrix, labelsVector

#data, labels = file2matrix("datingTestSet2.txt")
# fig = plt.figure()
# ax = fig.add_subplot(111)
# ax.scatter(data[:,0],data[:,1],s=15.0*array(labels),c=15.0*array(labels))
# plt.show()
		
def autoNorm(dataSet):
	minvalues = dataSet.min(axis = 0)
	maxvalues = dataSet.max(axis = 0)
	ranges = maxvalues - minvalues
	#empty = zeros((shape(dataSet)))
	minMatrix = tile(minvalues,(dataSet.shape[0],1))
	rangeMatrix = tile(ranges,(dataSet.shape[0],1))
	normMatrix = (dataSet-minMatrix)/rangeMatrix
	return normMatrix,ranges,minvalues

# normMat,range,minivalues = autoNorm(data)
# print normMat,range,minivalues

def datingClassTest():
	hoRatio = 0.1
	datingData,datingLabels = file2matrix(filename2)
	datingNormData,ranges,minValues = autoNorm(datingData)
	number = datingNormData.shape[0]
	numTest = int(number * hoRatio)
	errorCount = 0.0
	for i in range(numTest):
		classifyResult = classify0(datingNormData[i,:],datingNormData[numTest:number,:],datingLabels[numTest:number],10)
		print "Classifier result is %d, the real answer is %d" % (classifyResult,datingLabels[i])
		if (classifyResult != datingLabels[i]):
			errorCount += 1.0
	print "The error rate is %.2f%%" % (errorCount*100 / numTest)
	
#datingClassTest()

def classifyPerson():
	resultList = ["didn't like", "like in small doses","like in large doses"]
	ffmiles = float(raw_input("Number of frequent flyer miles earned per year:"))
	percentageVideogames = float(raw_input("percentage of time spent playing video games:"))
	icecream = float(raw_input("liters of ice cream connsumed every year:"))
	datingData,labels = file2matrix(filename2)
	datingNormData,ranges,minValues = autoNorm(datingData)
	inArr = array([ffmiles,percentageVideogames,icecream])
	classifyresult = classify0((inArr - minValues)/ranges,datingNormData,labels,3)
	print "you may %s this person" % resultList[classifyresult-1]

#classifyPerson()

def image2vector(filename):
	vector = zeros((1,32*32))
	fr = open(filename)
	for i in range(32):
		strLine = fr.readline()
		for j in range(32):
			vector[0,i*32+j] = int(strLine[j])
	return vector

def handwritingTest(k):
	labels = []
	trFileNameList = listdir("trainingDigits")
	nuOfTrainSamples = len(trFileNameList)
	trainMatrix = zeros((nuOfTrainSamples,1024))
	for i in range(nuOfTrainSamples):
		name = trFileNameList[i]
		labels.append(int(name[0]))
		trainMatrix[i,:] = image2vector("trainingDigits/"+name)
	errorCount = 0.0
	testFileNameList = listdir("testDigits")
	numberOfTestSamples = len(testFileNameList)
	for j in range(numberOfTestSamples):
		resultFromclassify0 = classify0(image2vector("testDigits/"+testFileNameList[j]),trainMatrix,labels,k)
		realResult =int(testFileNameList[j][0])
		#print "result from classifier is %d; real result is %d" % (resultFromclassify0,realResult)
		if (resultFromclassify0 != realResult):
			errorCount += 1.0
	print "Error rate is %.2f%%" % (errorCount / numberOfTestSamples * 100)
	return (errorCount / numberOfTestSamples * 100)
#handwritingTest(4)
def handwritingSingleTest(testPos):
	labels = []
	trFileNameList = listdir("trainingDigits")
	nuOfTrainSamples = len(trFileNameList)
	trainMatrix = zeros((nuOfTrainSamples,1024))
	for i in range(nuOfTrainSamples):
		name = trFileNameList[i]
		labels.append(int(name[0]))
		trainMatrix[i,:] = image2vector("trainingDigits/"+name)
	#errorCount = 0.0
	testFileNameList = listdir("testDigits")
	numberOfTestSamples = len(testFileNameList)
	resultFromclassify0 = classify0(image2vector("testDigits/"+testFileNameList[testPos]),trainMatrix,labels,5)
	#realResult =int(testFileNameList[j][0])
		#print "result from classifier is %d; real result is %d" % (resultFromclassify0,realResult)
		#if (resultFromclassify0 != realResult):
			#errorCount += 1.0
	#print "Error rate is %.2f%%" % (errorCount / numberOfTestSamples * 100)
	#return (errorCount / numberOfTestSamples * 100)
	return resultFromclassify0