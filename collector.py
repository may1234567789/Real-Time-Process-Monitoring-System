# collector.py
import psutil

def get_system_stats():
    """
    Returns a dict with overall CPU and memory stats.
    """
    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()

    return {
        "cpu_percent": cpu_percent,
        "memory_used": mem.used,
        "memory_total": mem.total,
        "memory_percent": mem.percent
    }


def get_process_list():
    """
    Returns a list of dicts with process info.
    Each dict: pid, name, status, cpu_percent, memory_mb
    """
    processes = []
    # First call to initialize cpu_percent so next is meaningful
    psutil.cpu_percent(interval=None)

    for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_info']):
        try:
            info = proc.info
            mem_info = info.get('memory_info', None)
            memory_mb = (mem_info.rss / (1024 * 1024)) if mem_info else 0.0

            processes.append({
                "pid": info.get('pid', 0),
                "name": info.get('name', 'N/A'),
                "status": info.get('status', 'N/A'),
                "cpu_percent": info.get('cpu_percent', 0.0),
                "memory_mb": memory_mb
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Sort by CPU usage descending
    processes.sort(key=lambda p: p["cpu_percent"], reverse=True)
    return processes


def kill_process(pid: int) -> bool:
    """
    Tries to terminate a process by PID.
    Returns True if success, False otherwise.
    """
    try:
        p = psutil.Process(pid)
        p.terminate()
        p.wait(timeout=3)
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
        return False
