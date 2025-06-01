# Dockerfile para Apache Pig
FROM openjdk:11-jdk-slim

ENV PIG_VERSION 0.17.0
ENV PIG_HOME /opt/pig/pig-${PIG_VERSION}
ENV HADOOP_VERSION_PIG_EXPECTS 2.7.3
ENV HADOOP_HOME /opt/hadoop 
ENV HADOOP_CONF_DIR $HADOOP_HOME/etc/hadoop
ENV PATH $PIG_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH
ENV PIG_CLASSPATH $HADOOP_CONF_DIR

# Variable de entorno para Python/Jython (puede ayudar con problemas de encoding)
ENV PYTHONIOENCODING UTF-8 

ENV MONGO_HADOOP_CONNECTOR_VERSION 2.0.2
ENV MONGO_JAVA_DRIVER_VERSION 3.12.11

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        wget \
        procps \
        ca-certificates \
        gnupg \
        dirmngr \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/pig && \
    echo "Descargando Apache Pig ${PIG_VERSION}..." && \
    wget -qO- "https://archive.apache.org/dist/pig/pig-${PIG_VERSION}/pig-${PIG_VERSION}.tar.gz" | tar -xzf - -C /opt/pig && \
    echo "Apache Pig ${PIG_VERSION} descargado y extraído."

RUN mkdir -p $HADOOP_CONF_DIR && \
    echo '<configuration></configuration>' > $HADOOP_CONF_DIR/core-site.xml && \
    echo '<configuration></configuration>' > $HADOOP_CONF_DIR/hdfs-site.xml && \
    echo '<configuration><property><name>mapreduce.framework.name</name><value>local</value></property><property><name>mapred.job.tracker</name><value>local</value></property></configuration>' > $HADOOP_CONF_DIR/mapred-site.xml && \
    echo '<configuration><property><name>yarn.nodemanager.aux-services</name><value>mapreduce_shuffle</value></property></configuration>' > $HADOOP_CONF_DIR/yarn-site.xml && \
    echo '#!/bin/bash\n# export JAVA_HOME=${JAVA_HOME}' > $HADOOP_CONF_DIR/hadoop-env.sh && \
    chmod +x $HADOOP_CONF_DIR/hadoop-env.sh

RUN mkdir -p $PIG_HOME/lib && \
    echo "Descargando mongo-hadoop-core-${MONGO_HADOOP_CONNECTOR_VERSION}.jar..." && \
    wget --timeout=60 -O $PIG_HOME/lib/mongo-hadoop-core-${MONGO_HADOOP_CONNECTOR_VERSION}.jar \
         "https://repo1.maven.org/maven2/org/mongodb/mongo-hadoop/mongo-hadoop-core/${MONGO_HADOOP_CONNECTOR_VERSION}/mongo-hadoop-core-${MONGO_HADOOP_CONNECTOR_VERSION}.jar" && \
    echo "mongo-hadoop-core descargado." && \
    echo "Descargando mongo-hadoop-pig-${MONGO_HADOOP_CONNECTOR_VERSION}.jar..." && \
    wget --timeout=60 -O $PIG_HOME/lib/mongo-hadoop-pig-${MONGO_HADOOP_CONNECTOR_VERSION}.jar \
         "https://repo1.maven.org/maven2/org/mongodb/mongo-hadoop/mongo-hadoop-pig/${MONGO_HADOOP_CONNECTOR_VERSION}/mongo-hadoop-pig-${MONGO_HADOOP_CONNECTOR_VERSION}.jar" && \
    echo "mongo-hadoop-pig descargado." && \
    echo "Descargando mongo-java-driver-${MONGO_JAVA_DRIVER_VERSION}.jar..." && \
    wget --timeout=60 -O $PIG_HOME/lib/mongo-java-driver-${MONGO_JAVA_DRIVER_VERSION}.jar \
         "https://repo1.maven.org/maven2/org/mongodb/mongo-java-driver/${MONGO_JAVA_DRIVER_VERSION}/mongo-java-driver-${MONGO_JAVA_DRIVER_VERSION}.jar" && \
    echo "mongo-java-driver descargado."

RUN mkdir -p /pig_udfs
RUN mkdir -p /pig_data
COPY ./udfs/waze_udfs.py /pig_udfs/waze_udfs.py
COPY comunas_rm.geojson /pig_data/comunas_rm.geojson

WORKDIR /pig_scripts