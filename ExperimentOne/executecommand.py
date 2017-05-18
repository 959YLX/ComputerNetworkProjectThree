import subprocess
import multiprocessing
import math
import json


def run(command, argv):
    p = subprocess.Popen(([command] + argv), stdout=subprocess.PIPE, stderr=open('/dev/null','w'))
    if p.wait() == 0:
        output = p.communicate()[0]
        result = output.decode()
        return result
    return 'error'


def multexecute(command, argv, taskcount):
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    result = list()
    for i in range(0, taskcount):
        result.append(pool.apply_async(run, (command, argv)))
    pool.close()
    pool.join()
    total = list()
    for res in result:
        total.append(res.get())
    return total


def ping_one(hostnames, num_packets, taskcount):
    command = 'ping'
    arg = math.ceil(num_packets / float(taskcount))
    argv = list()
    argv.append(hostnames)
    argv.append(('-c%d' % arg))
    result_list = multexecute(command, argv, taskcount)
    analysed_result = analyse_ping_result(result_list,int(arg))
    return {hostnames : analysed_result}


def analyse_ping_result(result, times):
    totallist = list()
    for once in result:
        temp = once.split('\n')[1:times + 1]
        for oneResult in temp:
            if oneResult.startswith('Request timeout'):
                totallist.append(-1.0)
                continue
            res = oneResult[oneResult.rfind('time')+5:oneResult.rfind('ms') - 1]
            totallist.append(float(res))
    return totallist


def statistic(result_list):
    result = dict()
    for (hostname, times) in result_list.items():
        totalcount = len(times)
        if totalcount == 0:
            continue
        times = times.copy()
        times.sort()
        value = dict()
        max_rtt = times[-1]
        if max_rtt == -1.0:
            value.update({'drop_rate': 100.0})
            value.update({'max_rtt': -1.0})
            value.update({'median_rtt': -1.0})
        drop_rate = times.count(-1.0)
        if drop_rate != 0:
            times = times[-1:drop_rate - 1:-1]
        half = len(times) // 2
        median_rtt = (times[half] + times[~half]) / 2
        value.update({'drop_rate': (drop_rate / float(totalcount))})
        value.update({'max_rtt': max_rtt})
        value.update({'median_rtt': median_rtt})
        result.update({hostname: value})
    if len(result) == 0:
        return False
    return result


def run_ping(hostnames, num_packets, raw_ping_output_filename, aggregated_ping_output_filename):
    raw_result = dict()
    if isinstance(hostnames,list) :
        for host in hostnames:
            print('Testing host : ' + host)
            raw_result.update(ping_one(host, num_packets, multiprocessing.cpu_count()))
    raw_output = json.JSONEncoder().encode(raw_result)
    statisticResult = statistic(raw_result)
    if isinstance(statisticResult, bool):
        print("Network Error")
        return
    aggregated_output = json.JSONEncoder().encode(statisticResult)
    file = open(raw_ping_output_filename, 'w')
    file.write(raw_output)
    file.close()
    file = open(aggregated_ping_output_filename, 'w')
    file.write(aggregated_output)
    file.close()


if __name__ == '__main__':
    hostnames = ['127.0.0.1']
    run_ping(hostnames, 50, '/Users/ylx/Desktop/raw.json', '/Users/ylx/Desktop/aggregated.json')