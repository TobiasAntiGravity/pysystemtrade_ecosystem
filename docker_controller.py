import time

import docker

client = docker.DockerClient(base_url='unix://var/run/docker.sock')

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


def daily_container_flow_management():
    """Handles the daily start and stop of the different containers"""

    container_sequence = ['stack_and_capital_handler', 'daily_']

    for container_name in container_sequence:
        run_container_and_wait_to_finish(container_name=container_name,
                                         docker_client=client,
                                         name_suffix=NAME_SUFFIX)


def run_container_managment():
    """Main function for managing the pysystemtrade ecosystem containers. Note that;
       docker compose must create containers via docker compose create before script can run
    """

    mongo_container_object = client.containers.get(container_id="mongo_db" + NAME_SUFFIX)

    if mongo_container_object.status != 'running':
        mongo_container_object.start()

    ib_gateway_container_object = client.containers.get(container_id ="ib_gateway" + NAME_SUFFIX)

    if ib_gateway_container_object.status != 'running':
        ib_gateway_container_object.start()

    daily_container_flow_management()
















#related to the container archetecture
# todo: where does systems save it's results. Must be accessible for generator
#  means must also persist through a stop and restart.
# todo: backup should also do;
#  csv dump (csv_backup_directory private_config.yaml)
#  backtest store (backtest_store_directory private_config.yaml)
# todo: echo_directory - should only be one echo directory - so that the cleaner can work as expectd.
#  make sure the writing and reading prieveliges are correct ehre

# todo: crontab does the output writing. Where to handle this if we are not using cron.

# todo: find out; When script is run manually (instead of being run through cron) is it
# running continously or closed after the day's work? - think it does not.

# todo: catxh log output

#related to the script
# todo: daily function should rest when market is not open..
# todo: have try catch on container runs
# todo: logging should be implemented
# todo: get NAME_SUFFIX from .env.
# todo: move backup files to external storage after backup
# todo: git save the reports.


