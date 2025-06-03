FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    default-jdk \
    python3.9 \
    python3-pip \
    libapr1 \
    libqpid-proton-cpp12 \
    vim \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1

# Install GMSEC Python dependencies
RUN pip3 install psycopg2-binary dataset influxdb-client

# Install GMSEC
# https://github.com/nasa/GMSEC_API/releases/download/API-5.2-release/GMSEC_API-5.2-Ubuntu20.04_x86_64.tar.gz
ARG GMSEC_VERSION=5.2
ARG GMSEC_TARBALL="GMSEC_API-${GMSEC_VERSION}-Ubuntu20.04_x86_64.tar.gz"
RUN curl -L -o ${GMSEC_TARBALL} https://github.com/nasa/GMSEC_API/releases/download/API-${GMSEC_VERSION}-release/${GMSEC_TARBALL} \
    && tar -xvzf ${GMSEC_TARBALL} \
    && rm ${GMSEC_TARBALL}

# Install activemq-cpp client library
# http://www.apache.org/dyn/closer.lua/activemq/activemq-cpp/3.9.5/activemq-cpp-library-3.9.5-src.tar.gz
ARG ACTIVEMQ_CPP_VERSION=3.9.5
ARG ACTIVEMQ_CPP="activemq-cpp-${ACTIVEMQ_CPP_VERSION}"
ARG ACTIVEMQ_CPP_TARBALL="${ACTIVEMQ_CPP}-src.tar.gz"
RUN curl -L -o ${ACTIVEMQ_CPP_TARBALL} http://archive.apache.org/dist/activemq/activemq-cpp/${ACTIVEMQ_CPP_VERSION}/${ACTIVEMQ_CPP_TARBALL} \
    && tar -xvzf ${ACTIVEMQ_CPP_TARBALL} \
    && rm ${ACTIVEMQ_CPP_TARBALL}

ENV GMSEC_HOME="/app/GMSEC_API"
ENV ACTIVEMQ_CPP_HOME="/app/${ACTIVEMQ_CPP}"

ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV JDK_HOME=/usr/lib/jvm/default-java
ENV GMSEC_API_HOME=${GMSEC_HOME}
ENV CLASSPATH=${GMSEC_HOME}/bin/gmsecapi.jar:.
ENV PATH=${GMSEC_HOME}/bin:$PATH
ENV LD_LIBRARY_PATH=${GMSEC_HOME}/bin:${ACTIVEMQ_CPP_HOME}/lib:$LD_LIBRARY_PATH
ENV PYTHONPATH=${GMSEC_HOME}/bin:${GMSEC_HOME}/bin/lib/GMSECAPI5:.

# Install ISS Python dependencies
RUN pip3 install --upgrade pip setuptools wheel
RUN pip3 install requests fastapi pydantic uvicorn maap_py

# Copy cert
COPY auth/truststore.pem ./auth/truststore.pem
COPY config/ ./config/

COPY gmsec_service/ ./gmsec_service

CMD ["python3"]