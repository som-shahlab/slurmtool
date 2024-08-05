import subprocess
import re
import argparse
from colorama import Fore, Style, init

def get_all_node_names():
    try:
        command = "sinfo -N -h -o '%N'"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stdout.strip().split("\n")
        return output
    except Exception as e:
        print(f"Error: {e}")
        return []

def get_node_state(node_name):
    try:
        command = f"sinfo -N -h -n {node_name} -o '%T'"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stdout.strip()
        return output
    except Exception as e:
        print(f"Error: {e}")
        return '-'

def is_node_idle_or_down(node_name):
    try:
        command = f"sinfo -N -h -n {node_name} -o '%t'"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stdout.strip().lower()
        return output == 'idle', output == 'down'
    except Exception as e:
        print(f"Error: {e}")
        return False, False

def get_node_resources(node_name):
    try:
        command = f"scontrol show node {node_name}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stdout

        cfg_tres_match = re.search(r'CfgTRES=(\S+)', output)
        alloc_tres_match = re.search(r'AllocTRES=(\S*)', output)
        partition_match = re.search(r'Partitions=(\S+)', output)

        if not cfg_tres_match or not partition_match:
            raise ValueError(f"Could not find CfgTRES or Partitions for node {node_name}")

        cfg_tres = cfg_tres_match.group(1)
        partition = partition_match.group(1)

        alloc_tres = alloc_tres_match.group(1) if alloc_tres_match else ''

        cfg_dict = dict(item.split('=') for item in cfg_tres.split(','))
        alloc_dict = dict(item.split('=') for item in alloc_tres.split(',')) if alloc_tres else {}

        available_features_match = re.search(r'AvailableFeatures=(\S+)', output)
        available_features = available_features_match.group(1) if available_features_match else ''
        
        # Extract GPU info
        gpu_type_match = re.search(r'GPU_SKU:([^,]+)', available_features)
        gpu_type = gpu_type_match.group(1) if gpu_type_match else '-'

        gpu_mem_match = re.search(r'GPU_MEM:([^,]+)', available_features)
        gpu_mem = gpu_mem_match.group(1) if gpu_mem_match else '-'

        gpu_cc_match = re.search(r'GPU_CC:([^,]+)', available_features)
        gpu_cc = gpu_cc_match.group(1) if gpu_cc_match else '-'

        total_cpus = int(cfg_dict.get('cpu', 0))
        total_mem = int(cfg_dict.get('mem', '0M')[:-1])
        total_gpus = int(cfg_dict.get('gres/gpu', 0))

        alloc_cpus = int(alloc_dict.get('cpu', 0)) if 'cpu' in alloc_dict else 0
        alloc_mem = int(alloc_dict.get('mem', '0G')[:-1]) * 1024 if 'mem' in alloc_dict else 0
        alloc_gpus = int(alloc_dict.get('gres/gpu', 0)) if 'gres/gpu' in alloc_dict else 0

        free_cpus = total_cpus - alloc_cpus
        free_mem = total_mem - alloc_mem
        free_gpus = total_gpus - alloc_gpus

        cpu_util = (alloc_cpus / total_cpus) * 100 if total_cpus > 0 else 0
        mem_util = (alloc_mem / total_mem) * 100 if total_mem > 0 else 0
        gpu_util = (alloc_gpus / total_gpus) * 100 if total_gpus > 0 else 0

        node_state = get_node_state(node_name)

        return node_name, partition, node_state, free_cpus, free_mem / 1024, free_gpus, gpu_type, gpu_mem, gpu_cc, cpu_util, mem_util, gpu_util, total_gpus
    except ValueError as ve:
        print(ve)
        return node_name, None, None, None, '-', '-', '-', '-', None, '-', None, None
    except Exception as e:
        print(f"Error: {e}")
        return node_name, None, None, None, '-', '-', '-', '-', None, '-', None, None

def print_table(node_resources):
    header = f"{'Node Name':<20} {'Partition':<19} {'State':<10} {'Free CPUs':<10} {'Free Memory (GB)':<20} {'Free GPUs':<10} {'GPU Type':<15} {'GPU Memory':<10} {'GPU CC':<10}"
    print(header)
    print("=" * len(header))
    
    for node_name, partition, node_state, free_cpus, free_mem, free_gpus, gpu_type, gpu_mem, gpu_cc, cpu_util, mem_util, gpu_util, total_gpus in node_resources:
        if free_cpus is not None and free_mem is not None:
            if re.search(r'down[$*]*', node_state, re.I):
                node_color = Fore.RED
                cpu_color = Fore.RED
                mem_color = Fore.RED
                gpu_color = Fore.RED

            else:
                node_color = Fore.RESET
                cpu_color = Fore.RED if cpu_util > 75 else Fore.RESET if cpu_util == 0 else Fore.YELLOW
                mem_color = Fore.RED if mem_util > 75 else Fore.RESET if mem_util == 0 else Fore.YELLOW
                gpu_color = Fore.RED if gpu_util > 75 or free_gpus == 0 else Fore.RESET if gpu_util == 0 else Fore.YELLOW
            
            free_cpus_display = str(free_cpus) if isinstance(free_cpus, (int, float)) else free_cpus
            free_mem_display = f"{free_mem:.2f}" if isinstance(free_mem, (int, float)) else free_mem
            free_gpus_display = str(free_gpus) if isinstance(free_gpus, (int, float)) else free_gpus

            print(f"{node_color}{node_name:<20}{Style.RESET_ALL} "
                  f"{node_color}{partition:<19}{Style.RESET_ALL} "
                  f"{node_color}{node_state:<10}{Style.RESET_ALL} "
                  f"{cpu_color}{free_cpus_display:<10}{Style.RESET_ALL} "
                  f"{mem_color}{free_mem_display:<20}{Style.RESET_ALL} "
                  f"{gpu_color}{free_gpus_display:<10}{Style.RESET_ALL} "
                  f"{Fore.RESET}{gpu_type:<15}{Style.RESET_ALL} "
                  f"{Fore.RESET}{gpu_mem:<10}{Style.RESET_ALL} "
                  f"{Fore.RESET}{gpu_cc:<10}{Style.RESET_ALL}")
        else:
            continue

def main():
    init(autoreset=True)
    parser = argparse.ArgumentParser(description="List available resources on specified Slurm nodes.")
    parser.add_argument("nodes", metavar="N", type=str, nargs="*", help="List of node names")
    parser.add_argument("--all", action="store_true", help="Print all information about the Slurm cluster")
    args = parser.parse_args()

    if args.all:
        nodes = get_all_node_names()
    else:
        nodes = args.nodes

    node_resources = []
    for node in nodes:
        node_resources.append(get_node_resources(node))
    
    print_table(node_resources)

if __name__ == "__main__":
    main()
