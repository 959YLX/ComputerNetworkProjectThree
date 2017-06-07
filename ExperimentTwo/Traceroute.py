#! /usr/local/bin/python3
import re
import sys
from json import JSONEncoder

class ResultHandle(object):
	"""处理输出结果"""
	def __init__(self):
		super(ResultHandle, self).__init__()
		self.normalpattrn = re.compile(r'^\s*\d*\s+.*')
		self.moreippattrn = re.compile(r'^\s+\d*\..*')
		self.formatpattern = re.compile(r'[^|\s]?\S+[\s|$]?')
		self.ippattern = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')

	def analyseresult(self, output):
		if not isinstance(output, str):
			print('Input Type Error')
		temp = output.split('\n')
		result = list()
		onceresult = list()
		tempstr = str()
		for once in temp:
			if not self.normalpattrn.match(once):
				continue	#非结果输出
			elif not self.moreippattrn.match(once):
				onceresult.append(once)	#正常结果输出
			else:
				current = len(onceresult) - 1
				last = onceresult[current]
				appendstr = ' {}'.format(once)
				onceresult[current] = last + appendstr
		for res in onceresult:
			result.append(self.__formate(res))
		return result


	def __formate(self, once):
		result = list()
		patternresult = re.findall(self.formatpattern, once) 
		length = len(patternresult)
		result.append(patternresult[0])
		ip = None
		for index in range(1,length):
			part = patternresult[index]
			if self.ippattern.match(part):
				ip = part.rstrip()
				continue
			if part.startswith('ms'):
				continue
			if part.startswith('*'):
				if ip:
					result.append((ip, '*'))
					continue
				result.append(('*', '*'))
				continue
			result.append((ip, float(part.rstrip())))
		return result

def to_json_result(output, sendtimes):
	result = list()
	output = ResultHandle().analyseresult(output)
	for once in output:
		totaltime = 0
		outtime_times = 0
		averagetime = 0
		iplist = list()
		for x in range(1, sendtimes + 1):
			(ip, times) = once[x]
			if times == '*':
				outtime_times += 1
			else:
				totaltime += times
			if ip not in iplist:
				iplist.append(ip)
		if totaltime != 0:
			averagetime = (totaltime) / (sendtimes - outtime_times)
		result.append({"ip": iplist, "averagetime": averagetime})
	return JSONEncoder().encode({"road": result})




def run_traceroute(hostnames, num_packets, output_filename):
	command = 'traceroute'
	argv = ['-q{}'.format(num_packets),'-n',hostnames]
	p = subprocess.Popen(([command] + argv), stdout=subprocess.PIPE, stderr=open('/dev/null', 'w'))
	p.wait()
	output = p.communicate()[0].decode().get()
	file = open(output_filename, 'w')
	file.write(output)
	file.close;
	return output


def parse_traceroute(num_packets, raw_traceroute_filename, output_filename):
	file_output = open(raw_traceroute_filename, 'r')
	output = file_output.read()
	file_output.close()
	analyse_traceroute(output,num_packets , output_filename)

def analyse_traceroute(output, num_packets, output_filename):
	result = to_json_result(output, num_packets)
	file = open(output_filename, 'w')
	file.write(result)
	file.close()

if __name__ == '__main__':
	arg = sys.argv
	helpstr = """useage: ./Traceroute.py host packets_num raw_path path
				./Traceroute.py -f packets_num raw_path path
				pipin: commands | ./Traceroute.py --pip-in packets_num path"""
	arglength = len(arg)
	if arglength == 1:
		print(helpstr)
		exit(0)
	if arg[1] == '--pip-in':
		#管道流输入
		output = sys.stdin.read()
		analyse_traceroute(output,int(arg[2]) , arg[3])
		exit(0)
	if arg[1] == '-f':
		parse_traceroute(int(arg[2]), arg[3], arg[4])
		exit(0)
	host = arg[1]
	raw_path = arg[2]
	path = arg[3]
	packets_num = int(arg[2])
	output = run_traceroute(arg[1],packets_num , raw_path)
	analyse_traceroute(output,packets_num, arg[4])
	exit(0)


