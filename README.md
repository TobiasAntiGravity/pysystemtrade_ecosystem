 # pysystemtrade_ecosystem

A dockerized pysystemtrade ecosystem made for quick deployment and migration of production and testing environments.

The environment consists of the following components; 
- container running the continous processes; 
  - stack_handler
  - capital_update. 
- container running sequentially running end of day processes; 
  - run_daily_price_updates
  - run_systems
  - run_strategy_order_generator
  - run_cleaners
  - run_reports
- container with ib gateway running
- container with mongodb running
- container with jupyter running
- container for saving db backup files to host machine
- container for saving csv backup files to host machine
- container for restoring db backup to mongodb
- A docker network 
- A docker volume where mongo db is stored. 
- A python script that handles;
  - container management
  - moving csv and db backup files to external storage via samba
  - committing and pushing reports to remote repo

Prerequisits
- Required; A private branch of pysystemtrade as ([discussed here](https://github.com/robcarver17/pysystemtrade/discussions/533)), The repo is pulled when image is built. All configs must be in the repo. 
- Optional; A remote git repo for saving your psystemtrade reports,  [like Mr. Carver himself does](https://github.com/robcarver17/reports)

Table of Contents
=================
* [Initial setup instructions](#Initial-setup-instructions)
    * [Add ib_gateway subtree](#Add-ib_gateway-subtree)
    * [Parameterization](#Parameterization)
        * [.env file](#.env-file)
* [Start container management](#Start-container-management)
* [About docker_controller.py](#About-docker_controller.py)
* [Tweaks to original setup, due to the docker environment](#Tweaks-to-original-setup,-due-to-the-docker-environment)
* [About Jupyter](#About-Jupyter)
* [Backup and restore](#Backup-and-restore)
  * [Backup](#Bacup)
  * [Restore](#Restore)
* [Misc useful commands](#*Misc-useful-commands)
* [Remarks](#Remarks)
* [Tip's on running psystemtrade in the ecosystem](#Tip's-on-running-psystemtrade-in-the-ecosystem)

## Initial setup instructions

1) clone this repo to host machine.
2) Add public fork of ib_gateway as subtree - see [Add ib_gateway subtree](#Add-ib_gateway-subtree) section below. (added as the second step to avoid git throwing error that working tree has modifications. If this appears  commiting changes will resolve)
3) Add private repo URI in place of placeholder URI in two files `pysystemtrade_ecosystem/pysystemtrade/Dockerfile` and `pysystemtrade_ecosystem/ipython/Dockerfile`;

`RUN git clone -b my_branch https://${GIT_TOKEN}:@github.com/GITUSERNAME/private_pysystemtrade_repo.git /opt/projects/pysystemtrade`
* Remarks to git code; \
    *i) my_branch is the branch with the production code. If this is master ignore -b section* \
    *ii) private_pysystemtrade_repo is of course your repo.* \
    *iii)`GIT_TOKEN` is an environment variable set in the `docker-compose.yml` file - see the Parameterization/docker-compose.yml section below. Only relevant if repo is in github and using personal access token*

4) Parameterize project see [Parameterization](#Parameterization) section below  
5) Before building images, make sure that file privelieges for the repo is not too restrictive. Will result in a failed build.  
6) To build the images; In the command line, while in the repo root folder, run following command; \
`docker compose build`
7) To create the containers without starting them, run the following; \
`docker compose create --force-recreate`
8) Start jupyter container, (this will also start the mongodb container, and the ib gateway); \
`docker compose up jupyter`
9) Doing the inital setup of pysystemtrade can be done either through jupyter notebooks. (Notebooks will then have to be made of course), or 
in the command line of the jupyter container. The setup entails populating the databases, set total capital, set position limits et cetera, 
as required and described in the pysystemtrade project. To access the jupyter container command line;
`docker exec -it jupyter /bin/bash` \
   (depending on the suffix you set in the `.env` file, you need to modify the above command)

**Optional step** If you would like to save your daily pysystemtrade reports in a git repo, [like Mr. Carver does](https://github.com/robcarver17/reports), clone the repo remote repo into the root structure of this repo. The remote repo must be placed into a `reports` folder, such that the relative path is `pysystemtrade_ecosystem/reports`. A placeholder folder has been created to designate where to add the repo. (FYI the reports folder has been added to .gitignore) Example of clone code when present directory is root folder; \
`git clone https://${GIT_TOKEN}:@github.com/GITUSERNAME/reports.git reports`\


### Add ib_gateway subtree
**Disclaimer; My fork is used here. As you will see - any repo can be dropped in here, so other docker solutions can be used [like this proposal](https://github.com/robcarver17/pysystemtrade/discussions/544). Substituting would require other changes - at least docker-compose.yml would have to be changed**

The "TobiasAntiGravity/ib-gateway-docker" is a public fork of "antequant/ib-gateway-docker". Some changes had to be done to get it working - see commit messages in fork. This repo has to be pulled in as a subfolder into the pysystemtrade_ecosystem to get the IBKR gateway up and running. This is done in the following way; 

1) Add the remote fork repo as a remote into pysystemtrade_ecosystem git repo\
`git remote add -f ib_gateway https://github.com/TobiasAntiGravity/ib-gateway-docker.git` (public repo no need for personal access token)

2) Pull the ib_gateway repo into the local repo of pysystemtrade_ecosystem, such that the folder structure becomes `pysystemtrade_ecosystem/ib-gateway`. Run the following git command:\
\
`git subtree add --prefix ib_gateway ib_gateway/master --squash`\
*Note; important that cwd is pysystemtrade_ecosystem before command is run*\
\
for primer on subtree [see this link](https://www.atlassian.com/git/tutorials/git-subtree)
 
### Parameterization
The following parameters should not be added to a vcs system, and is therefore set now;

#### .env file
Add the environment variable;

`IPV4_NETWORK_PART='172.25.' #example`

This is an environment variable that gives all containers in the ecosystem the same network address (the first two parts of the ip address), so that They can interact on a docker network. [unfortunatley it is not possible to dynamically insert an environment](https://stackoverflow.com/a/41620747/1020693) variable into a .yaml file - therefore the network address will have to be statically typed into the private_config.yaml file.

`NAME_SUFFIX='_dev'` 

Optional environment variable. Standard is empty string. Used when running multiple ecosystems in parallel. Suffix prevents naming conflicts for containers, networks and volumes. 
**Note that if parallell ecosystems are spun up - host network facing ports, from the ib gateway and jupyter containers, would have to be
changed to an available port number. Naming convention is host_port:container_port. So in the case of the ib gateway container, the docker-compose.yml "5900":"5900", could be changed to "5901":"5900". Same applies to "4002":"4002", of course.
An additional change will have to be done in the case of jupyter; The port number is hardcoded in the command section in the `jupyter/Dockerfile` - so this will have to be changed to the same port as in the compose file. 

`PYSYS_CODE`

[The subsection Quick start guide](https://github.com/robcarver17/pysystemtrade/blob/master/docs/production.md#quick-start-guide)
under Prerequisites, this environment variable is listed as `PYSYS_CODE=/home/user_name/pysystemtrade`. The default value in the
.env file is correct for the ecosystem setup.

`SCRIPT_PATH`

[The subsection Quick start guide](https://github.com/robcarver17/pysystemtrade/blob/master/docs/production.md#quick-start-guide)
under Prerequisites, this environment variable is listed as `SCRIPT_PATH=/home/user_name/pysystemtrade/sysproduction/linux/scripts`. The default value in the
.env file is correct for the ecosystem setup.

`ECHO_PATH`

[The subsection Quick start guide](https://github.com/robcarver17/pysystemtrade/blob/master/docs/production.md#quick-start-guide)
under Prerequisites, this environment variable is listed as `ECHO_PATH=/home/user_name/echos`. The default value in the
.env file is set to an existing folder. Echo files are not used in this ecosystem. The reason being that stdout is captured and stored by docker logs, 
instead of the echo specification in crontab.  

`GIT_TOKEN`

Github Personal access token 

`TWSUSERID`

User for IBKR gateway

`TWSPASSWORD`

Password for IBKR gateway

`WORKFLOW_WEEKDAY_START`

Used to separate the weekend, when pysystemtrade does not need to run, and the work week. Used by the python container managment script 
(`docker_controller.py`) during the weekend. Can be set to a custom time, default should match with times in pysystemtrade's crontab example. 
Should be set as an integer between 1 (monday) and 7 (sunday)

`WORKFLOW_WEEKDAY_END`

Used to separate the weekend, when pysystemtrade does not need to run, and the work week. Used by the python container managment script 
(`docker_controller.py`) during the weekend. Can be set to a custom time, default should match with times in pysystemtrade's crontab example
Should be set as an integer between 1 (monday) and 7 (sunday)

`HOUR_TO_STOP_WORKFLOW_ON_END_WEEKDAY`

Used to separate the weekend, when pysystemtrade does not need to run, and the work week. Used by the python container managment script 
(`docker_controller.py`) during the weekend. Can be set to a custom time, default should match with times in pysystemtrade's crontab example
Should be set as an integer between 1 and 24


## Start container management
When inital setup is finished the python script used for container management, can be started. 
`python3 docker-controller.py`
Make sure that dependencies as per `requirements.txt` have been pip3 installed. 

## About docker_controller.py
This script handles both the container managment, moving backups to external storage, and git committing and pushing the pysystem reports to remote repo. 

## Tweaks to original setup, due to the docker environment
Dockerizing pysystemtrade, meant having to do some changes compared to what is described in pysystemtrade's documentation. Below is a listing of the 
changes done, and the reason for them. 

### Crontab replaced by container flow management
Crontab is not used. The container management is based on the container stopping when the proccesses are finished. Crontab is a continously running process. 
and could therefore not be used

### Echo files replaced with docker Logs
Echo files are not used in this ecosystem. The reason being that stdout is captured and stored by docker logs, 
instead of the echo specification in crontab. This is a consequence of not being able to run Crontab - as explained above.

Log clean up is done by docker itself, according to the specifications declared under each service (container) in `the docker-compose.yml` file.
Example from the stack_and_capital_handler service;
```      
      logging:
        options:
          max-size: "10m"
          max-file: "3" 
```
This specifies that max size of a json log file is 10 Mb and max number of log files are 3. 

Logs can be viewed with the following command; \
`docker compose Logs "service name as per docker-compose.yml"`

A grep filter command that can come in handy is; \
`docker compose  logs daily_processes --until 2022-07-06T23:59:00 2>&1 | grep -v "because Previous process still running"`


### Monitor not running
This is a continous process, and is therefore not started in the pysystemtrade containers. Might look into adding a separate 
container where monitor can run from, as per possibility described in pysystemtrade documentation.  

### Backup of database
Not done via pysystemtrade, but done as per best practice described for the mongodb docker image. Saved on host machine, in `db_backup` folder under this repo.

## About Jupyter
Address to jupyter's web UI is "local ip of docker host":"port number" (8888 by default) The root folder is the root folder of the private pysystemtrade repo. 
A useful tip is to save notebooks in a subfolder of `pysystemtrade/private`, and commit them to your private repo. 


## Backup and restore
Simple backup and restore facilities has been added. Below are the details on how to implement a scheduled backup, and how to restore data. Please try the backup and restore routine in advance to ensure that it actually works, before you need it. 

### Backup
Docker volumes can be backed up by starting a temporary container mounted with volume to be backed up. The temporary container creates two tar backup files to a a host directory mounted to the temporary container. From there, the host machine 
will have to handle the two backup files, moving them to a backup location, perhaps via a cron job. (did look into using https://github.com/offen/docker-volume-backup, but required swarm. Too involved for right now, perhaps at a later point) 

(Backups be done for the mongo_db volumes and for the notebooks. All one has to do is to change change between the "db-backup" and the "notebooks" profile names in the below examples)

This method does a complete database dump, as it copies all the data. The size of the mongo database might become too large to handle in such a manner, requiring a snapshot incremental backup approach in the future. 

**Commands to schedule for periodic backups;**

For the below commands to work; a directory named `backup` must be located in the pysystemtrade_ecosystem root directory (this directory is included in the repo. Content has been added to .gitignore), and that commands are run from this same root directory (that it is pwd).
 
- stop containers consuming the mongodb volume; \
\
`docker compose stop pysystemtrade; docker compose stop mongo_db`
\
*Note; the name of the containers might have a suffix depending on the `NAME_SUFFIX` environment variable in the .env file*

- Run the temporary backup container;\
\
`docker compose run --rm db_backup`\
\
*--rm ensures that the container is deleted after run is completed*\
\
this will have created the files `(pwd)/backup/backup_db.tar` and `(pwd)/backup/backup_conf.tar` for the cron job to move to a suitable backup location. 

- Start the stopped containers\
\
`docker compose start pysystemtrade; docker compose start mongo_db`\
\
*Note; the name of the containers might have a suffix depending on the `NAME_SUFFIX` environment variable in the .env file*\

### Restore
A temporary container is created and mounted with the volume where backup is to be deployed. The temporary container unpacks the tar file `backup.tar`, located in the mounted host directory `(pwd)/backup/`. 
the new volumes with the backup data should be created before the mongo container, to avoid any overwrite issues. 

**Commands to restore a backup;**

1) 	Ensure that the backup files exists as follows; `(pwd)/backup/backup_db.tar` and `(pwd)/backup/backup_conf.tar`

2) Containers consuming the mongodb volumes should be removed, along with removal of old volumes 

3) Run the  container that uploads the backup into the db volume;\
`docker compose run --rm db_restore`

4) Start the compose environment
`docker compose up --build -d`
 
## Misc useful commands 
To handle all of the containers in the environment simultaionously use compose while in the repo root folder;

List all compose projects;\
`docker compose ls`

Stopping all containers for example: \
`docker compose -p project_name stop`

List all docker networks; \
`docker network list`

Inspect network to see ip address and more;\
`docker network inspect network_name`

To connect to the pysystemtrade container (or any other container for that matter);\
`docker exec -it pysystemtrade /bin/bash`

## Remarks

- Environment variables mentioned in the [production guide](https://github.com/robcarver17/pysystemtrade/blob/master/docs/production.md), like `PYSYS_CODE`,  has not been added to a `~/.profile` file. Have not had a system in production in the ecosystem yet. Have been able to do data wrangling without the envrionment variables.
- The Mongo db is setup without any login credentials. Probably not the recommended way of doing it - might come back to this later.
- Should perhaps delete login credentials that was added in step 5 after things are up and running. **note that some of the login credentials are presisted in the docker image / environment variables,
so it should be stressed that this is not a secure way of handling credentials, regardless if you delete hard coded credentials after launching the machines**


### Tip's on running psystemtrade in the ecosystem
- For the cron deamon to be able to execute the scripts; i) Do not use environment variables in the cron syntax. ii) In the file `sysproduction/linux/scripts/p`, the path of the python interpreter has to be added to the p file like so;\
`/usr/local/bin/python run.py $1`
- System time on every container is, as far I can see is UTC/GMT. Works for my purpose, changing this looks to involve package installations and more.

