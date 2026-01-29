import json
import os
import csv
import re

def extract_json_from_log(raw_content):
    match = re.search(r"\{.*\}", raw_content, re.DOTALL)
    if match:
        json_string = match.group(0)
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            print(f"Regex found a match, but it's not valid JSON: {e}")
    return None

def parse_fio(file_path):
    with open(file_path, 'r') as f:
        try:
            raw_data = f.read()
            d = extract_json_from_log(raw_data)
            if not d:
                return {"Filename": os.path.basename(file_path), "Error": "No JSON found"}

            job = d['jobs'][0]
            rw = 'write' if job['write']['iops'] > 0 else 'read'
            stats = job[rw]

            z = {
                "Filename": os.path.basename(file_path),
                "jobname": job.get('jobname'),
                "BS": job['job options'].get('bs', '1'),
                "QD": job['job options'].get('iodepth', '1'),
                "IOPS": round(stats['iops'], 2),
                "BW_MBs": round(stats['bw'] / 1024, 2),
                "fio_sys_cpu": round(job.get('sys_cpu', 0), 2),
                "fio_usr_cpu": round(job.get('usr_cpu', 0), 2),
            }

            def get_p99(stat_block):
                pcts = stat_block.get('percentile', {})
                key = next((k for k in pcts if k.startswith("99.0")), None)
                return pcts[key] if key else 0

            z["clat_avg_us"] = round(stats['clat_ns']['mean'] / 1000, 2)
            z["clat_p99_us"] = round(get_p99(stats['clat_ns']) / 1000, 2)
            z["slat_avg_us"] = round(stats['slat_ns']['mean'] / 1000, 2)
            z["lat_avg_us"] = round(stats['lat_ns']['mean'] / 1000, 2)

            return z
        except Exception as e:
            return {"Filename": os.path.basename(file_path), "Error": str(e)}

def parse_iostat(data, file_path):
    with open(file_path, 'r') as f:
        raw_data = f.read()

    # Helper to find regex and avoid .group(1) crashes if no match is found
    def safe_search(pattern, text):
        m = re.search(pattern, text)
        return m.group(1) if m else "0.0"

    data["iostat_cpu_usr"] = safe_search(r"%user[^\d]+([\d.]+)", raw_data)
    data["iostat_cpu_sys"] = safe_search(r"%system[^\d]+([\d.]+)", raw_data)
    data["iostat_cpu_iowait"] = safe_search(r"%iowait[^\d]+([\d.]+)", raw_data)
    data["iostat_dev_util"] = safe_search(r"%util[^\d]+([\d.]+)", raw_data)
    return data

def main():
    results_dir = 'results/'
    master_output = 'results/fio_master_results.csv'
    
    if not os.path.exists(results_dir):
        print(f"Error: Directory '{results_dir}' not found.")
        return

    files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
    files.sort()

    all_results = []

    for filename in files:
        file_path = os.path.join(results_dir, filename)
        data = parse_fio(file_path)
        
        if "Error" not in data:
            # Only run iostat parse if FIO parse succeeded
            data = parse_iostat(data, file_path)
            all_results.append(data)
        else:
            print(f"Skipping {filename}: {data['Error']}")

    if not all_results:
        print("No valid data found.")
        return

    # DYNAMIC HEADERS: Use the keys from the first dictionary as headers
    fieldnames = list(all_results[0].keys())

    try:
        with open(master_output, mode='w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_results)
            
        print(f"\n--- SUCCESS ---")
        print(f"Combined {len(all_results)} files into {master_output}")

    except PermissionError:
        print(f"Error: Could not write to {master_output}. Close the file in Excel.")

if __name__ == "__main__":
    main()
