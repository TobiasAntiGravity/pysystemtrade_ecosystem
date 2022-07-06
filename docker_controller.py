import time
import datetime as datetime
from pathlib import Path

import docker
from dotenv import dotenv_values
import git

from backup import backup_csv_files


def wait_until_containers_has_finished(list_of_containers_to_finish: list, docker_client: docker.client):

    set_of_containers_to_finish = set(list_of_containers_to_finish)

    while True:

        # get running containers
        list_of_container_objects = docker_client.containers.list()

        # get names of running containers
        names_of_running_containers = []

        for container_object in list_of_container_objects:
            names_of_running_containers.append(container_object.name)

        set_of_running_containers = set(names_of_running_containers)
        running_containers_waiting_for = set_of_running_containers.intersection(set_of_containers_to_finish)

        if len(running_containers_waiting_for) == 0:
            break

        else:
            time.sleep(15)


def run_container_and_wait_to_finish(container_name: str, docker_client: docker.client, name_suffix: str):

    container_object = docker_client.containers.get(container_id=container_name + name_suffix)

    if container_object.status != 'running':
        container_object.start()

    else:
        container_object.restart()

    wait_until_containers_has_finished([container_name + name_suffix], docker_client=docker_client)


def stop_container(container_name: str, docker_client: docker.client, name_suffix: str):

    container_object = docker_client.containers.get(container_id=container_name + name_suffix)

    if container_object.status == 'running':
        container_object.stop()

    wait_until_containers_has_finished([container_name + name_suffix], docker_client=docker_client)


def git_commit_and_push_reports():

    reports_repo = git.Repo('./reports')
    now = datetime.now()

    if reports_repo.is_dirty(untracked_files=True):

        reports_repo.git.add(all=True)
        reports_repo.index.commit(f'Auto commit {now.strftime("%d%m%Y %H:%M:%S")}')
        reports_repo.remotes.origin.push()


def daily_sequence_flow_management( docker_client: docker.client,
                                    name_suffix: str,
                                    samba_user: str,
                                    samba_password: str,
                                    samba_share: str,
                                    samba_server_ip: str,
                                    path_local_backup_folder: Path = Path('csv_backup')):

    """Handles the daily start and stop of the different containers"""

    container_sequence = ['stack_and_capital_handler', 'daily_processes']

    for container_name in container_sequence:
        run_container_and_wait_to_finish(container_name=container_name,
                                         docker_client=docker_client,
                                         name_suffix=name_suffix)

    run_container_and_wait_to_finish(container_name='csv_backup',
                                     docker_client=docker_client,
                                     name_suffix=name_suffix)

    git_commit_and_push_reports()

    stop_container(container_name='mongo_db' + NAME_SUFFIX,
                   docker_client=docker_client,
                   name_suffix=name_suffix)

    run_container_and_wait_to_finish(container_name='db_backup',
                                     docker_client=docker_client,
                                     name_suffix=name_suffix)

#    backup_csv_files(samba_user=samba_user,
#                     samba_password=samba_password,
#                     samba_share=samba_share,
#                     samba_server_ip=samba_server_ip,
#                     path_local_backup_folder=path_local_backup_folder)


def run_daily_container_management(docker_client: docker.client,
                                   name_suffix: str,
                                   weekday_start: int,
                                   weekday_end: int,
                                   stop_hour: int,
                                   samba_user: str,
                                   samba_password: str,
                                   samba_share: str,
                                   samba_server_ip: str,
                                   path_local_backup_folder: Path = Path('csv_backup')):
    """Main function for managing the pysystemtrade ecosystem containers. Note that;
       docker compose must create containers via docker compose create before script can run
    """

    while True:

        now = datetime.now()

        if (now.isoweekday() >= weekday_start) and (now.isoweekday() <= weekday_end and now.hour < stop_hour):

            mongo_container_object = docker_client.containers.get(container_id="mongo_db" + name_suffix)

            if mongo_container_object.status != 'running':
                mongo_container_object.start()

            ib_gateway_container_object = docker_client.containers.get(container_id ="ib_gateway" + name_suffix)

            if ib_gateway_container_object.status != 'running':
                ib_gateway_container_object.start()

            daily_sequence_flow_management(docker_client=docker_client,
                                           name_suffix=name_suffix,
                                           samba_user=samba_user,
                                           samba_password=samba_password,
                                           samba_share=samba_share,
                                           samba_server_ip=samba_server_ip,
                                           path_local_backup_folder=path_local_backup_folder)

        else:
            time.sleep(secs=60)


if __name__ == '__main__':

    config = dotenv_values(".env")

    NAME_SUFFIX = config("NAME_SUFFIX")
    WORKFLOW_WEEKDAY_START = config("WORKFLOW_WEEKDAY_START")
    WORKFLOW_WEEKDAY_END = config("WORKFLOW_WEEKDAY_END")
    HOUR_TO_STOP_WORKFLOW_ON_END_WEEKDAY = config("HOUR_TO_STOP_WORKFLOW_ON_END_WEEKDAY")
    samba_user = config['SAMBA_USER']
    samba_password = config['SAMBA_PASSWORD']
    samba_share = config['SAMBA_SHARE']         # share name of remote server
    samba_server_ip = config['SAMBA_SERVER_IP']

    client = docker.DockerClient(base_url='unix://var/run/docker.sock')

    run_daily_container_management(docker_client=client,
                                   name_suffix=NAME_SUFFIX,
                                   weekday_start=WORKFLOW_WEEKDAY_START,
                                   weekday_end=WORKFLOW_WEEKDAY_END,
                                   stop_hour=HOUR_TO_STOP_WORKFLOW_ON_END_WEEKDAY,
                                   samba_user=samba_user,
                                   samba_password=samba_password,
                                   samba_share=samba_share,
                                   samba_server_ip=samba_server_ip,
                                   path_local_backup_folder=path_local_backup_folder)


# todo: should implement surveilance on disk usage / docker cleaning if necessary
# todo: have to implement error handling accross the script
# todo: logging should be implemented
# todo: move backup files to external storage after backup;
# - csv_backup - either overwrite files, or have multiple days backup
# - db_backup. Single couple of days backup.


