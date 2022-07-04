FROM python:3.8.12 as builder

# LABEL
LABEL maintainer="tobias@anti-gravity.as"
LABEL version="0.1"
LABEL description="This is custom Docker Image for creating a pysystemtrade container in the pysystemtrade_ecosystem"

ARG GIT_TOKEN

RUN mkdir /opt/projects
RUN git clone -b my_branch https://${GIT_TOKEN}:@github.com/GITUSERNAME/private_pysystemtrade_repo.git /opt/projects/pysystemtrade

FROM python:3.8.12 as final_stage

ARG SCRIPT_PATH=$SCRIPT_PATH
ARG ECHO_PATH=$ECHO_PATH

ENV IPV4_NETWORK_PART=$IPV4_NETWORK_PART
ENV PYSYS_CODE=$PYSYS_CODE
ENV SCRIPT_PATH=$SCRIPT_PATH
ENV ECHO_PATH=$ECHO_PATH
ENV PATH "$PATH:$SCRIPT_PATH"

RUN apt-get update
RUN yes | apt-get install cron
RUN yes | apt-get install vim

RUN pip3 install --upgrade pip
RUN pip3 install sqlalchemy==1.3.22
RUN pip3 install psycopg2-binary
RUN pip3 install pandas==1.0.5
RUN pip3 install matplotlib>=3.0.0
RUN pip3 install pyyaml==5.4
RUN pip3 install numpy>1.19.4
RUN pip3 install scipy>=1.0.0
RUN pip3 install pymongo==3.9.0
RUN pip3 install arctic==1.79.2
RUN pip3 install ib-insync==0.9.70
RUN pip3 install psutil==5.6.6
RUN pip3 install pytest>6.2
RUN pip3 install Flask>=2.0.1
RUN pip3 install Werkzeug>=2.0.1
RUN pip3 install statsmodels==0.12.2

RUN mkdir /opt/projects
COPY --from=builder /opt/projects /opt/projects

WORKDIR /opt/projects/pysystemtrade

RUN mkdir command_scripts
COPY ./command_scripts /opt/projects/pysystemtrade/command_scripts

RUN pip install -e .

RUN mkdir $ECHO_PATH
RUN mkdir /home/backups
RUN mkdir /home/csv_backup

CMD ["/bin/bash", "-c", "tail -f /dev/null"]

