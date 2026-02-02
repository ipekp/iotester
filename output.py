import sys
import re
import json

def format_job(out_fio, out_iostat, averages):
    # header
    output = {}
    header = ['jobname','bs','qd','iops','bw_mbs']
    # body
    with open("F", 'r') as f:
        out_fio = f.read()
    # grab the json from fio
    fio_json = re.search(r"({.*}).*{'iostat", out_fio, flags=re.DOTALL)
    fio_json = json.loads(fio_json.group(1))
    fio_json = fio_json['jobs'][0]
    # get our vals

    # determine if read or write or both

    if int(fio_json['read']['bw']) and not int(fio_json['write']['bw']):
        tt = ['read']
    elif not int(fio_json['read']['bw']) and int(fio_json['write']['bw']):
        tt = ['write']
    else:
        tt = ['read', 'write']
        # R and W test
    print(len(tt))

    # globals
    output['jobname'] = fio_json['jobname']
    output['bs'] = fio_json['job options']['bs']
    output['qd'] = fio_json['job options']['iodepth']
    output['fio_sys_cpu'] = round(fio_json['sys_cpu'], 2)
    output['fio_usr_cpu'] = round(fio_json['usr_cpu'], 2)

    if len(tt) == 1:
        # test type dependent
        output['iops'] = round(float(fio_json[tt[0]]['iops']), 2)
        output['BW_MBs'] = round(float(fio_json[tt[0]]['iops']), 2)
        output['clat_avg_us'] = round(float(fio_json[tt[0]]['clat_ns']['mean'])/1000, 2)
        output['clat_p99_us'] = round(float(fio_json[tt[0]]['clat_ns']['percentile']['99.000000'])/1000, 2)
        #output['slat_avg_us'] = round(float(fio_json[tt[0]]['slat_avg_us'])/1000, 2)

    else:
        print("HERE ======")

        output['iops'] = 0.00
        output['BW_MBs'] = 0.00
        for t in tt:

            output['iops'] += round(float(fio_json[t]['iops']), 2)
            output['BW_MBs'] += round(float(fio_json[t]['BW_MBs']), 2)

        output['iops'] = round(float(fio_json[t]['iops'])/2, 2)
        output['BW_MBs'] = round(float(fio_json[t]['BW_MBs'])/2, 2)


    print(output)

    # add average to it
    # print(json.dumps(fio_json, indent = 2))
    # print(fio_json)
    # # add averages
    # print(out_fio)
    # print(out_iostat)
    # print(averages)
    sys.exit(1)
    # tailer
    return output


def tous(time: float, unit: str = 'us'):
    if unit == 'ms':
        return round(time/(1000*1000), 2)
    elif unit == 'us':
        return round(time, 2)
    elif unit == 'ns':
        return round(time/1000, 2)
