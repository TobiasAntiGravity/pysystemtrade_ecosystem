FROM python:3.8.12 as builder

# LABEL
LABEL maintainer="tobias@anti-gravity.as"
LABEL version="0.1"
LABEL description="This is custom Docker Image for creating a jupyterlab container in the pysystemtrade_ecosystem"

ARG GIT_TOKEN

RUN mkdir /opt/projects
RUN git clone -b my_branch https://${GIT_TOKEN}:@github.com/GITUSERNAME/private_pysystemtrade_repo.git /opt/projects/pysystemtrade

FROM python:3.8.12 as final_stage

RUN  ln -sf /usr/share/zoneinfo/Europe/London /etc/timezone && \
     ln -sf /usr/share/zoneinfo/Europe/London /etc/localtime

RUN apt-get update
RUN yes | apt-get install vim

RUN mkdir /opt/projects
RUN mkdir /opt/projects/pysystemtrade

COPY --from=builder /opt/projects/pysystemtrade/requirements.txt /opt/projects/requirements.txt

RUN pip3 install --upgrade pip
RUN pip3 install sqlalchemy==1.3.22
RUN pip3 install psycopg2-binary

WORKDIR /opt/projects

RUN pip3 install --requirement requirements.txt
RUN pip3 install jupyterlab

COPY --from=builder /opt/projects /opt/projects

WORKDIR /opt/projects/pysystemtrade

RUN pip3 install -e .

COPY ./jupyter_server_config.py /usr/jupyter_server_config.py

RUN mkdir /home/reports
RUN mkdir /home/logs

ENTRYPOINT jupyter-lab --allow-root --no-browser --port=8888  --ip=0.0.0.0 --config=/usr/jupyter_server_config.py
