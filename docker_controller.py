import time
from datetime import datetime
from pathlib import Path
import logging

import docker
from docker.errors import APIError, NotFound
from dotenv import dotenv_values
import git

from backup import backup_csv_files

config = dotenv_values(".env")
logging_level = config['LOGGING_LEVEL']

logger = logging.getLogger(name=__name__)
logger.setLevel(logging_level)
f_handler = logging.FileHandler('backup.log')
f_handler.setLevel(logging_level)
f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')
f_handler.setFormatter(f_format)
logger.setHandler(f_handler)

def wait_until_containers_has_finished(list_of_containers_to_finish: list, docker_client: docker.client):

    try:
        set_of_containers_to_finish = set(list_of_containers_to_finish)

    except APIError as e:
        msg = 'Docker APIError, Could not retrieve list of running containers when '
        msg += f'looking for {list_of_containers_to_finish}. Must stop program'
        logger.critical(msg, exc_info=True)
        exit()

    one_debug_statement = False

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
            logger.debug(f'All containers {list_of_containers_to_finish}, have now stopped')
            break

        else:
            time.sleep(60)

            if one_debug_statement:
                logger.debug(f'Still waiting for {running_containers_waiting_for} containers to stop running')
                one_debug_statement = True


def run_container_and_wait_to_finish(container_name: str, docker_client: docker.client, name_suffix: str):

    try:
        container_object = docker_client.containers.get(container_id=container_name + name_suffix)

    except APIError as e:
        logger.critical(f'APIError - Failed to retrieve {container_name} container, stopping program', exc_info=True)
        exit()

    except NotFound as e:
        msg = f'Failed to retrieve {container_name} container - apparently does not exist'
        logger.critical(msg, exc_info=True)
        exit()

    if container_object.status != 'running':
        container_object.start()
        logger.debug(f'Container {container_name} was not running. Started it')

    else:
        container_object.restart()
        msg = f'Container {container_name} was restarted. Should not be running, probably stale. '
        msg += f'Need to resart processes'
        logger.warning(msg)

    wait_until_containers_has_finished([container_name + name_suffix], docker_client=docker_client)


def stop_container(container_name: str, docker_client: docker.client, name_suffix: str):

    try:
        container_object = docker_client.containers.get(container_id=container_name + name_suffix)

    except APIError as e:
        msg = f'APIError - Not able to stop {container_name}. Stopping program, to avoid problems like'
        msg += 'corrupt db backup because mongodb was not stopped before backup commenced'
        logger.critical(msg, exc_info=True)
        exit()

    except NotFound as e:
        msg = f'Not able to stop {container_name}. Stopping program, as a missing container'
        msg += 'will, most likely, result in critical failure at some point'
        logger.critical(msg, exc_info=True)
        exit()

    if container_object.status == 'running':
        container_object.stop()
        logger.debug(f'Container {container_name}, was running. Stopped it.')

    wait_until_containers_has_finished([container_name + name_suffix], docker_client=docker_client)


def git_commit_and_push_reports(commit_untracked_files: bool=True):
    """Will, by default, also commit utnracked files"""

    reports_repo = git.Repo('./reports')
    now = datetime.now()

    if reports_repo.is_dirty(untracked_files=commit_untracked_files):

        reports_repo.git.add(all=True)
        reports_repo.index.commit(f'Auto commit {now.strftime("%d%m%Y %H:%M:%S")}')

        push_info = reports_repo.remotes.origin.push()

        if len(push_info) == 0:
            logger.warning(f'Was not able to push repo', exc_info=True)

        elif any([head.ERROR for head in push_info]):
            logger.warning(f'Error related to head when pushing', exc_info=True)

        else:
            logger.debug(f'Git push carried out')

    else:
        logger.debug(f'Repo was not "dirty" - no commit necessary')


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

    stop_container(container_name='mongo_db' + name_suffix,
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

        if (now.isoweekday() >= int(weekday_start)) and \
                (now.isoweekday() <= int(weekday_end) and now.hour < int(stop_hour)):

            try:
                mongo_container_object = docker_client.containers.get(container_id="mongo_db" + name_suffix)

            except APIError as e:
                logger.critical(f'APIError - Failed to retrieve "mongo_db" container, stopping program', exc_info=True)
                exit()

            except NotFound as e:
                msg = f'Failed to retrieve "mongo_db" container - apparently does not exist'
                logger.critical(msg, exc_info=True)
                exit()

            if mongo_container_object.status != 'running':
                mongo_container_object.start()
                logger.debug('Had to start the "mongo_db" container, as status was not running')

            try:
                ib_gateway_container_object = docker_client.containers.get(container_id ="ib_gateway" + name_suffix)

            except APIError as e:
                msg = f'APIError - Failed to retrieve "ib_gateway" container. Stopping program'
                logger.critical(msg, exc_info=True)
                exit()

            except NotFound as e:
                msg = f'Failed to retrieve "ib_gateway" container - apparently does not exist'
                logger.critical(msg, exc_info=True)
                exit()

            if ib_gateway_container_object.status != 'running':
                ib_gateway_container_object.start()
                logger.debug('Had to start the "ib_gateway" container, as status was not running')

            daily_sequence_flow_management(docker_client=docker_client,
                                           name_suffix=name_suffix,
                                           samba_user=samba_user,
                                           samba_password=samba_password,
                                           samba_share=samba_share,
                                           samba_server_ip=samba_server_ip,
                                           path_local_backup_folder=path_local_backup_folder)

        else:
            time.sleep(600)
            logger.debug('Start and stop parameters resolved to weekend. Slowing down while loop runs')


if __name__ == '__main__':

    config = dotenv_values(".env")

    NAME_SUFFIX = config["NAME_SUFFIX"]
    WORKFLOW_WEEKDAY_START = config["WORKFLOW_WEEKDAY_START"]
    WORKFLOW_WEEKDAY_END = config["WORKFLOW_WEEKDAY_END"]
    HOUR_TO_STOP_WORKFLOW_ON_END_WEEKDAY = config["HOUR_TO_STOP_WORKFLOW_ON_END_WEEKDAY"]
    samba_user = config['SAMBA_USER']
    samba_password = config['SAMBA_PASSWORD']
    samba_share = config['SAMBA_SHARE']         # share name of remote server
    samba_server_ip = config['SAMBA_SERVER_IP']

    path_local_backup_folder = Path('/csv_backup')

    docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')

    run_daily_container_management(docker_client=docker_client,
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
# todo: implement db backup handling.
# todo: move backup files to external storage after backup;
# - csv_backup - either overwrite files, or have multiple days backup
# - db_backup. Single couple of days backup.