 # pysystemtrade_ecosystem

A dockerized pysystemtrade ecosystem. The daily pysystemtrade has been split into two different containers. 
A container running the ib gateway. A mongodb container. A jupyter notebook container enabling interacive GUI access 
to the data and the interactive scripts. The container workflow is managed by a python script, that starts and 
stops containers 



by a python script.  

by starting and 


how it differs from the standard implementation of pysystemtrade


- container with pysystemtrade repo clone running. 
- container with ib gateway running
- container with mongodb running
- container with ipython running
- A docker network 
- A docker volume where mongo db is stored. 
- A docker volume where ipython notebooks are stored

This readme explains how to deploy. 
 
## Step by step setup: 
 
1) clone this repo to host machine.
2) Add public fork of ib_gateway as subtree - see "Add ib_gateway subtree" section below. (added as the second step to avoid git throwing error that working tree has modifications. If this appears  commiting changes will resolve)
3) The setup assumes you have a private branch of pysystemtrade. ([discussed here](https://github.com/robcarver17/pysystemtrade/discussions/533)), To import this repo into both the pysystemtrade container and into the ipython container, you need to modify the following placeholder URI below in two files `pysystemtrade_ecosystem/pysystemtrade/Dockerfile` and `pysystemtrade_ecosystem/ipython/Dockerfile`;\

`RUN git clone -b my_branch https://${GIT_TOKEN}:@github.com/GITUSERNAME/private_pysystemtrade_repo.git /opt/projects/pysystemtrade`\
\
*Notes;*\
*i) my_branch is the branch with the production code. If this is master ignore -b section* \
*ii) private_pysystemtrade_repo is of course your repo.* \
*iii)`GIT_TOKEN` is an environment variable set in the `docker-compose.yml` file - see the Parameterization/docker-compose.yml section below. Only relevant if repo is in github and using personal access token*

4) Fill parameters into project see "Parameterization" section below  
5) In the command line, while in the repo root folder, write; \
`docker compose up --build -d`

6) To connect to the pysystemtrade container (or any other container for that matter)\
`docker exec -it pysystemtrade /bin/bash`

7) Check that you have recieved a test email, so that you know for sure that the email credentials setup in private_config.yaml are correct. 

8) Do any setups necessary for your specific pysystemtrade repo. - like adding your local curreny, if it is not already present in the pysystemtrade repo.   
9) Should perhaps delete login credentials that was added in step 5 after things are up and running. **note that some of the login credentials are presisted in the docker image / environment variables,
so it should be stressed that this is not a secure way of handling credentials, regardless if you delete hard coded credentials after launching the machines**


## Add ib_gateway subtree
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
 
## Parameterization
What parameters to add before running the system, as these parameters  should not be included in vcs.

### docker-compose file
Under ib_gateway and environment add; 

`TWSUSERID: "userID"`\
`TWSPASSWORD: "password"`

**As explained under step 3. above;**\
The `GIT_TOKEN` arg variable under pysystemstrade>build>args must recieve the github personal access token. 
This is needed for the pull of the private version of the private_pysystemtrade repo into the pysystemtrade container. (this assumes your repo is in github)

The same has to be done under ipython>build>args. The `GIT_TOKEN` arg variable must be filled with the github personal access token. 
This is needed for the pull of the private version of the private_pysystemtrade repo into the iptyhon container. (this assumes your repo is in github)
 
### .env file
Add the environment variable;

`IPV4_NETWORK_PART='172.25.' #example`

This is an environment variable that gives all containers in the ecosystem the same network address (the first two parts of the ip address), so that They can interact on a docker network. [unfortunatley it is not possible to dynamically insert an environment](https://stackoverflow.com/a/41620747/1020693) variable into a .yaml file - therefore the network address will have to be statically typed into the private_config.yaml file.

`NAME_SUFFIX='_dev'` 

Optional environment variable. Standard is empty string. Used when running multiple ecosystems in parallel. Suffix prevents naming conflicts for containers, networks and volumes. **Note that if paralell ecosystems are spun up - host network facing ports, from the ib gateway controller, would have to be
changed to an available port number. Naming convention is host_port:container_port. So in docker-compose.yml "5900":"5900", could be changed to "5901":"5900". Same applies to "4002":"4002", of course.

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
.env file is correct for the ecosystem setup.

## About Ipython

The root folder is the root folder of the private pysystemtrade repo. A `pysystemtrade/private/notebooks` folder is created,
for storing notebooks. Push to private repo for version control. 

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
`docker compose run --rm db-backup`\
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
`docker compose run --rm db-restore`

4) Start the compose environment
`docker compose up --build -d`
 
## Remarks

- Environment variables mentioned in the [production guide](https://github.com/robcarver17/pysystemtrade/blob/master/docs/production.md), like `PYSYS_CODE`,  has not been added to a `~/.profile` file. Have not had a system in production in the ecosystem yet. Have been able to do data wrangling without the envrionment variables.
- The Mongo db is setup without any login credentials. Probably not the recommended way of doing it - might come back to this later.

### Tip's on running psystemtrade in the ecosystem
- For the cron deamon to be able to execute the scripts; i) Do not use environment variables in the cron syntax. ii) In the file `sysproduction/linux/scripts/p`, the path of the python interpreter has to be added to the p file like so;\
`/usr/local/bin/python run.py $1`
- System time on every container is, as far I can see is UTC/GMT. Works for my purpose, changing this looks to involve package installations and more.

