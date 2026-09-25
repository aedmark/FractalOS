def get_process_list(jobs):
    """
    Gathers and formats the list of active processes (jobs).
    The 'jobs' dictionary is passed from the CommandExecutor's context.
    """
    if not jobs:
        return []

    processes = []
    for pid, job_details in jobs.items():
        processes.append({
            "pid": pid,
            "user": job_details.get('user', 'system'),
            "status": job_details.get('status', 'RUNNING')[0].upper(),
            "command": job_details.get('command', '')
        })

    processes.sort(key=lambda p: int(p['pid']))
    return processes

