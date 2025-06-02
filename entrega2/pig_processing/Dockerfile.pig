# Dockerfile para Apache Pig
FROM openjdk:11-jdk-slim

ENV PIG_VERSION 0.17.0
ENV PIG_HOME /opt/pig/pig-${PIG_VERSION}
ENV HADOOP_VERSION_PIG_EXPECTS 2.7.3
ENV HADOOP_HOME /opt/hadoop 
ENV HADOOP_CONF_DIR $HADOOP_HOME/etc/hadoop
ENV PATH $PIG_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH
ENV PIG_CLASSPATH $HADOOP_CONF_DIR
ENV PYTHONIOENCODING UTF-8 # Buena práctica, aunque no usemos UDFs Python ahora

# MONGO_HADOOP_CONNECTOR_VERSION y MONGO_JAVA_DRIVER_VERSION ya no son necesarios
# si Pig solo lee de TSV, pero no hace daño dejarlos por si usas MongoLoader en el futuro.

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        wget \
        procps \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/pig && \
    wget -qO- "https://archive.apache.org/dist/pig/pig-${PIG_VERSION}/pig-${PIG_VERSION}.tar.gz" | tar -xzf - -C /opt/pig

RUN mkdir -p $HADOOP_CONF_DIR && \
    echo '<configuration></configuration>' > $HADOOP_CONF_DIR/core-site.xml && \
    echo '<configuration></configuration>' > $HADOOP_CONF_DIR/hdfs-site.xml && \
    echo '<configuration><property><name>mapreduce.framework.name</name><value>local</value></property><property><name>mapred.job.tracker</name><value>local</value></property></configuration>' > $HADOOP_CONF_DIR/mapred-site.xml && \
    echo '<configuration><property><name>yarn.nodemanager.aux-services</name><value>mapreduce_shuffle</value></property></configuration>' > $HADOOP_CONF_DIR/yarn-site.xml && \
    echo '#!/bin/bash\n# export JAVA_HOME=${JAVA_HOME}' > $HADOOP_CONF_DIR/hadoop-env.sh && \
    chmod +x $HADOOP_CONF_DIR/hadoop-env.sh

# Ya no necesitamos los JARs de mongo-hadoop si Pig no se conecta a Mongo
# Las líneas de descarga de JARs de mongo pueden ser eliminadas o comentadas

WORKDIR /pig_scripts