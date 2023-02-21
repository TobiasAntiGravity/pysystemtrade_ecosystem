from sysdata.data_blob import dataBlob
from syscontrol.monitor import processMonitor, check_if_pid_running_and_if_not_finish


with dataBlob(log_name="system-monitor") as data:
    process_observatory = processMonitor(data)
    check_if_pid_running_and_if_not_finish(process_observatory)
    process_observatory.update_all_status_with_process_control()
