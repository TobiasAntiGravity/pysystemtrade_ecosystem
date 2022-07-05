import time

import docker


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


def daily_sequence_flow_management( docker_client: docker.client, name_suffix: str):
    """Handles the daily start and stop of the different containers"""

    container_sequence = ['stack_and_capital_handler', 'daily_processes']

    for container_name in container_sequence:
        run_container_and_wait_to_finish(container_name=container_name,
                                         docker_client=docker_client,
                                         name_suffix=name_suffix)

    run_container_and_wait_to_finish(container_name='csv_backup',
                                     docker_client=docker_client,
                                     name_suffix=name_suffix)

    stop_container(container_name='mongo_db' + NAME_SUFFIX,
                   docker_client=docker_client,
                   name_suffix=name_suffix)

    run_container_and_wait_to_finish(container_name='db_backup',
                                     docker_client=docker_client,
                                     name_suffix=name_suffix)


def run_daily_container_managment(docker_client: docker.client, name_suffix: str):
    """Main function for managing the pysystemtrade ecosystem containers. Note that;
       docker compose must create containers via docker compose create before script can run
    """

    while True:
        mongo_container_object = docker_client.containers.get(container_id="mongo_db" + name_suffix)

        if mongo_container_object.status != 'running':
            mongo_container_object.start()

        ib_gateway_container_object = docker_client.containers.get(container_id ="ib_gateway" + name_suffix)

        if ib_gateway_container_object.status != 'running':
            ib_gateway_container_object.start()

        daily_sequence_flow_management(docker_client=docker_client, name_suffix=name_suffix)


if __name__ == '__main__':

    client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    NAME_SUFFIX = ""

    run_daily_container_managment(docker_client=client, name_suffix=NAME_SUFFIX)




#related to the container archetecture
# todo: Check where does systems save backtest results?. (backtest_store_directory private_config.yaml)
#  Does this have to be be accessible for generator?

# todo: Remember to define (csv_backup_directory private_config.yaml) in private_config.yaml

#  todo: note in readme: make sure the writing and reading prieveliges of command_scripts are correct.

# todo: note in readme: define size constraint of docker logs - explain where to set.

# todo: Assume that When script is run manually (instead of being run through cron) is it
# running continously or closed after the day's work? - think it does not.

#related to the script
# todo: daily function should rest when market is not open..
# todo: have try catch on container runs
# todo: logging should be implemented
# todo: get NAME_SUFFIX from .env.
# todo: move backup files to external storage after backup
# todo: git save the reports.


