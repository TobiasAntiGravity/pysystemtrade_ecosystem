import time
from datetime import datetime, timedelta
from pathlib import Path
import logging

import docker
from docker.errors import APIError, NotFound
from dotenv import dotenv_values
import git
import pytz

from move_backups import move_backup_csv_files, move_db_backup_files

config = dotenv_values(".env")
logging_level = config['LOGGING_LEVEL']

logger = logging.getLogger(name=__name__)
logger.setLevel(logging_level)

f_handler = logging.FileHandler('container_management.log')
f_handler.setLevel(logging_level)

c_handler = logging.StreamHandler()
c_handler.setLevel('INFO')

f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')

f_handler.setFormatter(f_format)
c_handler.setFormatter(f_format)

logger.addHandler(f_handler)
logger.addHandler(c_handler)


def wait_until_containers_has_finished(list_of_containers_to_finish: list,
                                       docker_client: docker.client,
                                       name_suffix: str):

    container_names_with_suffix = [name + name_suffix for name in list_of_containers_to_finish]

    try:
        set_of_containers_to_finish = set(container_names_with_suffix)

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
            logger.info(f'All containers {list_of_containers_to_finish}, have now stopped, as intended')
            break

        else:
            time.sleep(60)

            if one_debug_statement:
                logger.info(f'Still waiting for {running_containers_waiting_for} containers to stop running')
                one_debug_statement = True


def run_container(container_name: str, docker_client: docker.client, name_suffix: str):
    '''Starts a container, handles exception, but re-raises exception for handling further upstream'''

    try:
        container_object = docker_client.containers.get(container_id=container_name + name_suffix)

    except APIError as e:
        logger.critical(f'APIError - Failed to retrieve {container_name} container, stopping program', exc_info=True)
        raise e

    except NotFound as e:
        msg = f'Failed to retrieve {container_name} container - apparently does not exist'
        logger.critical(msg, exc_info=True)
        raise e

    if container_object.status != 'running':
        container_object.start()
        logger.info(f'Container {container_name} was not running. Started it')

    else:
        container_object.restart()
        msg = f'Container {container_name} was restarted. Should not be running, probably stale. '
        msg += f'Need to resart processes'
        logger.warning(msg)


def run_container_and_wait_to_finish(container_name: str, docker_client: docker.client, name_suffix: str):
    '''Runs a container and waits for it to finish. Stops program execution if something occurs'''

    try:
        run_container(container_name=container_name, docker_client=docker_client, name_suffix=name_suffix)

    except Exception as e:
        logger.critical(f'{container_name} failed to run. Flow depends on wait until finsih. Exit.', exc_info=True)
        exit()

    wait_until_containers_has_finished([container_name], docker_client=docker_client, name_suffix=name_suffix)


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
        logger.info(f'Container {container_name}, was running. Stopped it.')

    wait_until_containers_has_finished([container_name],
                                       docker_client=docker_client,
                                       name_suffix=name_suffix)


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
            logger.info(f'Git push carried out')

    else:
        logger.debug(f'Repo was not "dirty" - no commit necessary')


def daily_pysys_flow(docker_client: docker.client,
                     name_suffix: str):

    """Handles the daily start and stop of the containers housing different pysys processes"""

    clean_slate_containers = ['cleaner']

    for container_name in clean_slate_containers:
        run_container_and_wait_to_finish(container_name=container_name,
                                         docker_client=docker_client,
                                         name_suffix=name_suffix)

    continous_containers = ['stack_handler', 'capital_update']

    for container_name in continous_containers:
        run_container(container_name=container_name,
                      docker_client=docker_client,
                      name_suffix=name_suffix)

    wait_until_containers_has_finished(list_of_containers_to_finish=continous_containers,
                                       docker_client=docker_client, name_suffix=name_suffix)

    end_of_day_processes = ['cleaner', 'daily_processes']

    for container_name in end_of_day_processes:
        run_container_and_wait_to_finish(container_name=container_name,
                                         docker_client=docker_client,
                                         name_suffix=name_suffix)

    try:
        run_container_and_wait_to_finish(container_name='csv_backup',
                                         docker_client=docker_client,
                                         name_suffix=name_suffix)

    except Exception:
        logger.warning(f'csv backup failed. Continuing program', exc_info=True)

    try:
        git_commit_and_push_reports()

    except Exception:
        logger.info(f'git handling failed. Continuing program', exc_info=True)


    stop_container(container_name='mongo_db',
                   docker_client=docker_client,
                   name_suffix=name_suffix)

    try:
        run_container_and_wait_to_finish(container_name='db_backup',
                                         docker_client=docker_client,
                                         name_suffix=name_suffix)

    except Exception:
        logger.warning(f'db backup failed. Continuing program', exc_info=True)


def run_daily_container_management(docker_client: docker.client,
                                   name_suffix: str,
                                   weekday_start: int,
                                   weekday_end: int,
                                   stop_hour: int,
                                   samba_user: str,
                                   samba_password: str,
                                   samba_share: str,
                                   samba_server_ip: str,
                                   samba_remote_name: str,
                                   path_local_backup_folder: Path = Path('csv_backup')):
    """Main function for managing the pysystemtrade ecosystem containers. Note that;
       docker compose must create containers via docker compose create before script can run
    """

    managment_run_on_this_day = datetime(1971, 1, 1)

    while True:

        now = datetime.now(pytz.timezone('Europe/London'))

        if ((int(weekday_start) <= now.isoweekday() <= int(int(weekday_end) - 1)) or
            (now.isoweekday() >= int(weekday_start) and (now.isoweekday() == int(weekday_end) and
                                                         now.hour < int(stop_hour)))) and \
                managment_run_on_this_day.date() != now.date():

            managment_run_on_this_day = now

            try:
                run_container(container_name='mongo_db', docker_client=docker_client, name_suffix=name_suffix)
                #should be down either from daily_pysys_flow, or from startup

            except Exception:
                logger.critical(f'Something happened when starting mongo_db, terminating', exc_info=True)
                exit()

            try:
                run_container(container_name='ib_gateway', docker_client=docker_client, name_suffix=name_suffix)
                #should be down either from shut down end of this function, or from startup

            except Exception:
                logger.critical(f'Something happened when starting ib_gateway, terminating', exc_info=True)
                exit()

            logger.info('Giving ib_gateway 30 sec to create connection before starting daily sequence')
            time.sleep(30)

            daily_pysys_flow(docker_client=docker_client,
                             name_suffix=name_suffix)

            stop_container(container_name='ib_gateway',
                           docker_client=docker_client,
                           name_suffix=name_suffix)

            try:
                move_backup_csv_files(samba_user=samba_user,
                                      samba_password=samba_password,
                                      samba_share=samba_share,
                                      samba_server_ip=samba_server_ip,
                                      samba_remote_name=samba_remote_name,
                                      path_local_backup_folder=path_local_backup_folder)

            except Exception:
                logger.warning('Failed when trying to move csv backup to external share', exc_info=True)

            try:
                move_db_backup_files(samba_user=samba_user,
                                     samba_password=samba_password,
                                     samba_share=samba_share,
                                     samba_server_ip=samba_server_ip,
                                     samba_remote_name=samba_remote_name,
                                     path_local_backup_folder=path_local_backup_folder,
                                     path_remote_backup_folder=Path('db_backup'))

            except Exception:
                logger.warning('Failed when trying to move db backup to external share', exc_info=True)

        else:
            logger.debug('Start and stop parameters resolved to weekend. Slowing down while loop runs')
            time.sleep(600)


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
    samba_remote_name = config['SAMBA_REMOTE_NAME']

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
                                   samba_remote_name=samba_remote_name,
                                   path_local_backup_folder=path_local_backup_folder)


# todo: should implement surveilance on disk usage / docker cleaning if necessary
# todo: notification of warnings and critical should be implemented.