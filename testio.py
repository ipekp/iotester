import json
import os
import csv



def parse_fio_json(file_path):
    """
    Parses a single FIO JSON output file and extracts key performance metrics.
    """
    with open(file_path, 'r') as f:
        try:
            d = json.load(f)
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
                "Filename": os.path.basename(file_path),
                "IOPS": round(stats['iops'], 2),
                "BW_MBs": round(stats['bw'] / 1024, 2),
                "clat_avg_us": round(stats['clat_ns']['mean'] / 1000, 2),
                "p99_us": round(p99_val / 1000, 2),
                "p9999_us": round(p9999_val / 1000, 2),
                "sys_cpu": round(job.get('sys_cpu', 0), 2),
                "usr_cpu": round(job.get('usr_cpu', 0), 2),
                "QD": job['job options'].get('iodepth', '1')
            }
        except Exception as e:
            return {"Filename": os.path.basename(file_path), "Error": str(e)}

def main():
    results_dir = 'results/'
    
    if not os.path.exists(results_dir):
        print(f"Error: Directory '{results_dir}' not found.")
        return

    # Get and sort files
    files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
    files.sort()

    # Define the CSV headers based on our dictionary keys
    fieldnames = ["Filename", "IOPS", "BW_MBs", "clat_avg_us", "p99_us", "p9999_us", "sys_cpu", "usr_cpu", "QD"]

    try:
        for filename in files:
            file_path = os.path.join(results_dir, filename)
            data = parse_fio_json(file_path)

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
