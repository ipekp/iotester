import sys
import re
import json

def format_job(out_fio, out_iostat, averages):
    # header
    output = {}
    # body
    # grab the json from fio
    m = re.search(r"({.*}).*set", out_fio, re.DOTALL)
    # m = re.search(r"(\{.*\})", out_fio, re.DOTALL)
    t = m.group(1).strip()
    fio_json = json.loads(m.group(1).strip())
    fio_json = fio_json['jobs'][0]
    # get our vals

    # determine if read or write or both
    if int(fio_json['read']['bw']) != 0 and int(fio_json['write']['bw']) == 0:
        tt = ['read']
    elif int(fio_json['read']['bw']) == 0 and int(fio_json['write']['bw']) != 0:
        tt = ['write']
    else:
        tt = ['read', 'write']
        # R and W test
    # globals
    output['jobname'] = fio_json['jobname']
    output['bs'] = fio_json['job options']['bs']
    output['qd'] = fio_json['job options']['iodepth']
    output['fio_sys_cpu'] = round(fio_json['sys_cpu'], 2)
    output['fio_usr_cpu'] = round(fio_json['usr_cpu'], 2)

    if len(tt) == 1:
        # find units
        su = next((k for k in ('ns','ms') if f"slat_{k}" in fio_json[tt[0]]), 'us')
        cu = next((k for k in ('ns','ms') if f"clat_{k}" in fio_json[tt[0]]), 'us')
        lu = next((k for k in ('ns','ms') if f"lat_{k}" in fio_json[tt[0]]), 'us')
        # test type dependent
        output['iops'] = round(float(fio_json[tt[0]]['iops']), 2)
        output['BW_MBs'] = round(float(fio_json[tt[0]]['iops']), 2)
        output[f"clat_avg_us"] = tous(float(fio_json[tt[0]][f"clat_{cu}"]['mean']), cu)
        output[f"clat_p99_us"] = tous(float(fio_json[tt[0]][f"clat_ns"]['percentile']['99.000000']), cu)
        output[f"clat_ratio"] = round(output[f"clat_p99_us"]/output[f"clat_avg_us"],2)
        output[f"slat_avg_us"] = tous(float(fio_json[tt[0]][f"slat_{su}"]['mean']), su)
        output[f"lat_avg_us"] = tous(float(fio_json[tt[0]][f"lat_{lu}"]['mean']), lu)

    else:
        # TODO to implement
        output['iops'] = 0.00
        output['BW_MBs'] = 0.00
        for t in tt:

            output['iops'] += round(float(fio_json[t]['iops']), 2)
            output['BW_MBs'] += round(float(fio_json[t]['BW_MBs']), 2)

        output['iops'] = round(float(fio_json[t]['iops'])/2, 2)
        output['BW_MBs'] = round(float(fio_json[t]['BW_MBs'])/2, 2)


    if averages:
        output['iostat_user'] = averages['iostat_user']
        output['iostat_system'] = averages['iostat_system']
        output['iostat_iowait'] = averages['iostat_iowait']
        output['iostat_util'] = averages['iostat_util']
        output['iostat_aqu-sz'] = averages['iostat_aqu-sz']
        output['iostat_ws'] = averages['iostat_ws']
        output['iostat_rs'] = averages['iostat_rs']
    # print(averages)
    # sys.exit(1)
    return output


def tous(time: float, unit: str = 'us'):
    if unit == 'ms':
        return round(time/(1000*1000), 2)
    elif unit == 'us':
        return round(time, 2)
    elif unit == 'ns':
        return round(time/1000, 2)


# TODO maybe used
def to_sheet(output: list):
    # print(isinstance(output,list))
    for result in output:
        print(result)
        for k, v in result.items():
            print(k, ",", v)
    sys.exit(1)
    # return output

def tocsv(output: list):
    # dynamic headers
    headers = []
    for k, v in output[0].items():
        headers.append(k.strip())
    print(",".join(headers))

    for result in output:
        row = []
        for k, v in result.items():
            row.append(str(v))
        print(",".join(row))
    sys.exit(1)
