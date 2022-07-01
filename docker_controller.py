import time
from datetime import datetime

import docker

client = docker.from_env()

NAME_SUFFIX = ""

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

    ontainer_object = client.containers.get(container_id=container_name + name_suffix)

    if ontainer_object.status != 'running':
        ontainer_object.start()

    else:
        ontainer_object.restart()

    wait_until_containers_has_finished([container_name + name_suffix], docker_client=docker_client)


def run_container_managment():
    '''docker compose must create containers via docker compose create before script can run'''

    stack_container_object = client.containers.get(container_id="stack_handler" + NAME_SUFFIX)

    if stack_container_object.status != 'running':
        stack_container_object.start()

    capital_container_object = client.containers.get(container_id ="capital_update" + NAME_SUFFIX)

    if capital_container_object.status != 'running':
        capital_container_object.start()

    #Find out when stack handler and capital update stops (process stop time from private_control_config passed)
    wait_until_containers_has_finished(['stack_handler' + NAME_SUFFIX, 'capital_update' + NAME_SUFFIX],
                                       docker_client=client)

    # hack to ensure that processes are started at the right time. Manually added the
    # stack handler and capital update stop times from private_control_config
    now = datetime.now()
    if (now.hour == 19 and now.minute >= 45) or (now.hour > 19):

        #continue starting containers with processes according to required sequence
        container_sequence = ['price_update', 'system', 'generator', 'cleaner', 'db_backup']

        for container_name in container_sequence:
            run_container_and_wait_to_finish(container_name=container_name,
                                             docker_client=client,
                                             name_suffix=NAME_SUFFIX)

    else:
        #place holder for logger
        print('Critical: something unexpected happened. Stack handler and capital update stopped before')
        print('the defined stop time. Should be checked')

# todo: move backup files to external storage after backup
# todo: git save the reports.
# todo: get NAME_SUFFIX from .env.
# todo: logging should be implemented
# todo: backup should also do csv dump.


