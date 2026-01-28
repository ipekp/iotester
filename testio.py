import json
import os
import csv
import re

def extract_json_from_log(raw_content):
    # r"\{.*\} matches from the first { to the last }
    # re.DOTALL is mandatory so '.' includes newlines
    match = re.search(r"\{.*\}", raw_content, re.DOTALL)

    if match:
        json_string = match.group(0)

        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            print(f"Regex found a match, but it's not valid JSON: {e}")
    else:
        print("No JSON block found in the file.")
    return None

def parse_fio(file_path):
    """
    Parses a single FIO JSON output file and extracts key performance metrics.
    """
    with open(file_path, 'r') as f:
        try:
            raw_data = f.read()
            d = extract_json_from_log(raw_data)
            job = d['jobs'][0]
            
            # Identify the primary I/O direction
            rw = 'write' if job['write']['iops'] > 0 else 'read'
            stats = job[rw]
            
            # Handle the "000000" percentile key formatting
            pcts = stats['clat_ns'].get('percentile', {})
            p99_key = next((k for k in pcts if k.startswith("99.0")), None)
            p99_val = pcts[p99_key] if p99_key else 0
            
            p9999_key = next((k for k in pcts if k.startswith("99.99")), None)
            p9999_val = pcts[p9999_key] if p9999_key else 0

            return {
                "jobname": job.get('jobname'),
                "BS": job['job options'].get('bs', '1'),
                "QD": job['job options'].get('iodepth', '1'),
                "IOPS": round(stats['iops'], 2),
                "BW_MBs": round(stats['bw'] / 1024, 2),
                "clat_avg_us": round(stats['clat_ns']['mean'] / 1000, 2),
                "p99_us": round(p99_val / 1000, 2),
                "sys_cpu": round(job.get('sys_cpu', 0), 2),
                "usr_cpu": round(job.get('usr_cpu', 0), 2),
            }
        except Exception as e:
            return {"Filename": os.path.basename(file_path), "Error": str(e)}

def parse_iostat(data, file_path):
    with open(file_path, 'r') as f:
        raw_data = f.read()
    
    data["iostat_cpu_usr"] = re.search(r"%user[^\d]+([\d.]+)", raw_data).group(1)
    data["iostat_cpu_sys"] = re.search(r"%system[^\d]+([\d.]+)", raw_data).group(1)
    data["iostat_cpu_iowait"] = re.search(r"%iowait[^\d]+([\d.]+)", raw_data).group(1)
    data["iostat_dev_util"] = re.search(r"%util[^\d]+([\d.]+)", raw_data).group(1)
    return data

def main():
    results_dir = 'results/'
    
    if not os.path.exists(results_dir):
        print(f"Error: Directory '{results_dir}' not found.")
        return

    # Get and sort files
    files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
    files.sort()

    # Define the CSV headers based on our dictionary keys
    fieldnames = ["jobname", "BS", "QD",
    "IOPS", "BW_MBs", 
    "clat_avg_us", "p99_us",
    "sys_cpu", "usr_cpu",
    "iostat_cpu_usr", "iostat_cpu_sys", "iostat_cpu_iowait",
    "iostat_dev_util"
    ]

    try:
        for filename in files:
            file_path = os.path.join(results_dir, filename)
            data = parse_fio(file_path)
            data = parse_iostat(data, file_path)

            output_file = 'results/' + filename + '.csv'
            with open(output_file, mode='w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                if "Error" not in data:
                    writer.writerow(data)
                else:
                    print(f"Skipping {filename} due to error: {data['Error']}")
        print(f"Successfully wrote results to {output_file}")
    
    except PermissionError:
        print(f"Error: Could not write to {output_file}. Close the file if it is open in Excel.")

if __name__ == "__main__":
    main()
