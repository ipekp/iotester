import sys
import re
import json
import csv

def format_job(out_fio, out_iostat, averages, cmd):
    # header
    output = {}
    # body
    # grab the json from fio
    m = re.search(r"({.*}).*set", out_fio, re.DOTALL)
    # m = re.search(r"(\{.*\})", out_fio, re.DOTALL)
    fio_json = json.loads(m.group(1).strip())
    fio_json = fio_json['jobs'][0]
    # get our vals
    m = re.search(r".*set1(.*)", out_fio, re.DOTALL)
    if isinstance(cmd, list):
        cmd = " ".join(cmd)

    fio_cmd = f"{cmd}\n"
    fio_log = m.group(1).strip()

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

    # find units
    # Note: separated READ from WRITE but not R and W
    # for bidir tests, Im only testing read latency
    su = next((k for k in ('ns','ms') if f"slat_{k}" in fio_json[tt[0]]), 'us')
    cu = next((k for k in ('ns','ms') if f"clat_{k}" in fio_json[tt[0]]), 'us')
    lu = next((k for k in ('ns','ms') if f"lat_{k}" in fio_json[tt[0]]), 'us')
    # test type dependent
    output['iops'] = round(float(fio_json[tt[0]]['iops']), 2)
    output['BW_MBs'] = round(float(fio_json[tt[0]]['bw'])/1024, 2)
    output[f"clat_avg_us"] = tous(float(fio_json[tt[0]][f"clat_{cu}"]['mean']), cu)
    output[f"clat_p99_us"] = tous(float(fio_json[tt[0]][f"clat_ns"]['percentile']['99.000000']), cu)
    output[f"clat_ratio"] = round(output[f"clat_p99_us"]/output[f"clat_avg_us"],2)
    output[f"slat_avg_us"] = tous(float(fio_json[tt[0]][f"slat_{su}"]['mean']), su)
    output[f"lat_avg_us"] = tous(float(fio_json[tt[0]][f"lat_{lu}"]['mean']), lu)

    if averages:
        output['iostat_user'] = averages['iostat_user']
        output['iostat_system'] = averages['iostat_system']
        output['iostat_iowait'] = averages['iostat_iowait']
        output['iostat_util'] = averages['iostat_util']
        output['iostat_aqu-sz'] = averages['iostat_aqu-sz']
        output['iostat_ws'] = averages['iostat_ws']
        output['iostat_rs'] = averages['iostat_rs']

    # suffix with logs
    output['fio_cmd'] = fio_cmd.strip()
    output['fio_log'] = fio_log.strip()
    return output


def tous(time: float, unit: str = 'us'):
    if unit == 'ms':
        return round(time/(1000*1000), 3)
    elif unit == 'us':
        return round(time, 3)
    elif unit == 'ns':
        return round(time/1000, 3)

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
    print("========== CUT =========")
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(headers)

    for result in output:
        row = []
        for k, v in result.items():
            row.append(str(v))
        # print(",".join(row))
        writer.writerow(row)
    print("========== CUT =========")
