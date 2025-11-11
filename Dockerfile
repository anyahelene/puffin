FROM python:bullseye

ARG TIMEZONE
RUN apt-get -y update && apt-get -y install tzdata less vim sqlite3 && apt-get clean && rm -rf /var/lib/apt/lists/* 
RUN if [ ! -z "$TIMEZONE" ]; then rm -f /etc/localtime && ln -s "/usr/share/zoneinfo/$TIMEZONE" /etc/localtime && echo "$TIMEZONE" > /etc/timezone; fi
ARG USE_GIT UID GID PORT LOG_DIR
ENV HOME=/home/puffin
ENV INSTALL_DIR=/srv/puffin
ENV VENV=$HOME/venv
# for dash:
ENV ENV=$HOME/.bashrc
RUN if ! id puffin; then adduser --system ${UID:+--uid $UID} ${GID:+--gid $GID} --home "$HOME" puffin ; fi
RUN if [ -z $PORT ]; then mkdir /run/puffin; chown puffin /run/puffin; fi
#RUN if [ ! -d $INSTALL_DIR ]; then mkdir $INSTALL_DIR ; chown puffin $INSTALL_DIR ; fi
RUN if [ ! -z "$LOG_DIR" -a ! -d "$LOG_DIR" ]; then mkdir "$LOG_DIR" ; chown puffin "$LOG_DIR" ; fi
USER puffin
WORKDIR $INSTALL_DIR
COPY --chown=puffin --chmod=555 requirements.txt .
RUN if [ ! -z "$USE_GIT" ]; then rm -f requirements.txt; git clone https://github.com/anyahelene/puffin.git "$INSTALL_DIR"; fi
RUN python -m venv "$VENV" && ls -la "$HOME" && . "$VENV/bin/activate" && pip install --only-binary :all: -r requirements.txt && pip install --only-binary :all: gunicorn
COPY --chmod=755 <<EOF $HOME/runit.sh
    . $VENV/bin/activate
    if [ ! -z "$LOG_DIR" ]; then
        LOGGING="--access-logfile $LOG_DIR/access.log --error-logfile $LOG_DIR/error.log"
    else
        LOGGING="--access-logfile - --error-logfile -"
    fi
    if [ -z "$PORT" ]; then
        BIND="--bind unix:/run/puffin/gunicorn.sock"
    else
        BIND="--bind 127.0.0.1:$PORT"
    fi
    LOG_FORMAT='%({x-real-ip}i)s %(l)s %({x-user}o)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
    cd "$INSTALL_DIR" 
    ls -l /run /run/puffin
    export TRUST_X_REAL_IP=True
    exec gunicorn \$BIND \$LOGGING --access-logformat="\$LOG_FORMAT" puffin.app:app
EOF
COPY <<EOF $HOME/.bashrc
. $VENV/bin/activate
EOF
EXPOSE $PORT
CMD ["/bin/sh", "-c", "$HOME/runit.sh"]
