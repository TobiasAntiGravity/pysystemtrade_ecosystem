 # pysystemtrade_ecosystem

docker ecosystem for pysystemtrade. Contains; 
- container with pysystemtrade repo clone. 
- container with ib gateway running
- container with mongodb installed. 

This readme explains how to deploy. 
 
## Step by step setup: 
 
1) clone this repo to host machine. 
2) Change the pysystemtrade repo to be cloned (if you have a private branch with customizations to run, - [discussed here](https://github.com/robcarver17/pysystemtrade/discussions/533)) In `pysystemtrade_ecosystem/pysystemtrade/Dockerfile`, change URI to fit your needs;\
\
`RUN git clone -b my_branch https://${GIT_TOKEN}:@github.com/GITUSERNAME/private_pysystemtrade_repo.git /opt/projects/pysystemtrade`\
\
\*Notes;\
i) my_branch is the branch with the production code. If this is master ignore -b section\
ii) private_pysystemtrade_repo is of course your repo. \
iii) `GIT_TOKEN` is a environment variable set in the `docker-compose.yml` file - see the Parameterization section below.*

3) Create a personal access token (if you are using github) and add it to the compose file under `GIT_TOKEN`
4) Add public fork of ib_gateway as subtree - see "Add ib_gateway subtree" section below 
5) Fill parameters into project see "Parameterization" section below  
6) In the repo root folder write; \
`docker compose up --build -d`

7) To connect to the pysystemtrade container (or any other container for that matter)\
`docker exec -it pysystemtrade /bin/bash`

8) Should perhaps delete login credentials that was added in step 5 after things are up and running. **note that some of the login credentials are presisted in the docker image / environment variables,
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
 
### .env file
Add the environment variable;

`IPV4_NETWORK_PART='172.25.' #example`

This is an environment variable that gives all containers in the ecosystem the same network address (the first two parts of the ip address), so that They can interact on a docker network. [unfortunatley it is not possible to dynamically insert an environment](https://stackoverflow.com/a/41620747/1020693) variable into a .yaml file - therefore the network address will have to be statically typed into the private_config.yaml file.

### private_config.yaml
Reason for having this important file outside of the private psysystemtrade repo is ease of ip address config for the containers. The file exists in; `./pysystemtrade>private_config.yaml` (When image is buildt, file is copied into /opt/projects/pysystemtrade/private in the pysystemtrade container.)

`ib_ipaddress: '{STATICALLY_TYPE_IPV4_NETWORK_PART}0.3'`\
Add the IPV4_NETWORK_PART from the .env file, into the placeholder "STATICALLY_TYPE_IPV4_NETWORK_PART". With the example above "172.25." would be entered.

`mongo_host: mongodb://{STATICALLY_TYPE_IPV4_NETWORK_PART}0.2:27017`\
Add the IPV4_NETWORK_PART from the .env file, into the placeholder "STATICALLY_TYPE_IPV4_NETWORK_PART". With the example above "172.25." would be entered.
*Note that the mongodb container is setup without any username password. URI therefore only needs IP address.*

`broker_account:`\
Is an account identifier


`email_address: 'email_sender_address'`\
`email_pwd: 'your_password'`\
`email_server: 'smtp.gmail.com'`\
`email_to: 'your@email.com'`

Created a new gmail account for the task. Had to change setting in gmail account to allow "less secure access". Whitelisted the created gmail address. Still ended in junk - had to mark as non junk
   
### docker-compose.yml
The `GIT_TOKEN` arg variable under pysystemstrade>build>args must recieve the github personal access token. 
This is needed for the pull of the private version of the private_pysystemtrade repo

### Misc useful commands 
To handle all of the containers in the environment simultaionously use compose;

List all compose projects;\
`docker compose ls`

Stopping all containers for example: \
`docker compose -p project_name stop`

List all docker networks; \
`docker network list`

Inspect network to see ip address and more;\
`docker network inspect network_name`
 
 
