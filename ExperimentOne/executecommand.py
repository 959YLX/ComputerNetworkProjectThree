#! /usr/local/bin/python3
import subprocess
import multiprocessing
import math
import json
import sys
import matplotlib.pyplot as plt
import numpy as np

def run(command, argv):
    p = subprocess.Popen(([command] + argv), stdout=subprocess.PIPE, stderr=open('/dev/null', 'w'))
    res = p.wait()
    if res == 0 or res == 2 :
        output = p.communicate()[0]
        result = output.decode()
        return result
    return 'error'


def multexecute(command, argv, taskcount):
    pool = multiprocessing.Pool(processes = multiprocessing.cpu_count())
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
    if num_packets <= 8:
        taskcount = 1
    command = 'ping'
    argv = list()
    arg = math.ceil(num_packets / float(taskcount))
    argv.append(hostnames)
    argv.append(('-c%d' % arg))
    result_list = multexecute(command, argv, taskcount)
    analysed_result = analyse_ping_result(result_list, arg * taskcount)
    return {hostnames: analysed_result}


def analyse_ping_result(result, totalTimes):
    totallist = list()
    for once in result:
        sublines = once.split('\n')
        endline = 0
        for index in range(1,len(sublines)):
            if sublines[index].startswith('---'):
                endline = index - 1
                break;
        temp = list()
        for index in range(1, endline):
            temp.append(sublines[index])
        for oneResult in temp:
            if oneResult.startswith('Request timeout'):
                totallist.append(-1.0)
                continue
            res = oneResult[oneResult.rfind('time')+5:oneResult.rfind('ms') - 1]
            totallist.append(float(res))
        if len(totallist) == totalTimes - 1:
            totallist.append(-1.0)
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
        else:
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


def execute(hostnames, num_packets):
    raw_result = dict()
    if isinstance(hostnames, list):
        for host in hostnames:
            print('Testing host : ' + host)
            raw_result.update(ping_one(host, num_packets, multiprocessing.cpu_count()))
    return raw_result


def run_ping(hostnames, num_packets, raw_ping_output_filename, aggregated_ping_output_filename):
    raw_result = execute(hostnames, num_packets)
    raw_output = json.JSONEncoder().encode(raw_result)
    statisticResult = statistic(raw_result)
    if isinstance(statisticResult, bool):
        print("Network Error")
        return
    draw(statisticResult)
    aggregated_output = json.JSONEncoder().encode(statisticResult)
    file = open(raw_ping_output_filename, 'w')
    file.write(raw_output)
    file.close()
    file = open(aggregated_ping_output_filename, 'w')
    file.write(aggregated_output)
    file.close()

def draw(data):
    host = list()
    max_rtt = list()
    median_rtt = list()
    drop_rate = list()
    for (hotsname, result) in data.items():
        host.append(hotsname)
        for (key, value) in result.items():
            if key == 'max_rtt':
                max_rtt.append(value)
                continue
            if key == 'median_rtt':
                median_rtt.append(value)
                continue
            if key == 'drop_rate':
                drop_rate.append(value)
    host_count = len(host)
    max_rtt = tuple(max_rtt)
    median_rtt = tuple(median_rtt)
    drop_rate = tuple(drop_rate)
    width = 0.1
    x1 = range(0,host_count)
    x2 = [i + width for i in x1]
    x3 = [i + width for i in x2]

    fig, ax = plt.subplots(figsize=(15, 9))
    max_rtt_bar = ax.bar(x1, max_rtt, width, color = 'r', label = 'max_rtt')
    median_rtt_bar = ax.bar(x2, median_rtt, width, color = 'g', label = 'median_rtt')
    

    ax.set_ylabel('RTT')
    ax.set_title('Ping Result')
    ax.set_xticks(x2)
    ax.set_xticklabels(tuple(host))
    max_y = math.ceil(max(max_rtt)) + 5
    print(max_y)
    ax.set_ylim([0, max_y])
    ax.set_xticklabels(tuple(host))
    ax.legend(loc = 'upper left')
    ax1 = ax.twinx()
    drop_rate_bar = ax1.bar(x3, drop_rate, width, color = 'b', label = 'drop_rate')
    ax1.set_ylabel('Drop Rate(%)')
    ax1.set_ylim([0, 115])
    ax1.legend(loc = 'upper right')
    plt.show()

if __name__ == '__main__':
    arg = sys.argv[1:]
    if len(arg) < 3:
        print('command hostnumber packagenumber raw_ping_output_filename aggregated_ping_output_filename host1 host2 ...')
        exit(0)
    amount = int(arg[0])
    packagenumber = int(arg[1])
    raw_ping_output_filename = arg[2]
    aggregated_ping_output_filename = arg[3]
    hosts = arg[4: amount + 4]
    run_ping(hosts, packagenumber, raw_ping_output_filename, aggregated_ping_output_filename)
    