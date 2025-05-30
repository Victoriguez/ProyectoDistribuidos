# Dockerfile para Apache Pig
# Guardar como ProyectoDistribuidos/entrega2/pig_processing/Dockerfile

FROM openjdk:11-jre-slim

ENV PIG_VERSION 0.17.0
ENV PIG_HOME /opt/pig/pig-${PIG_VERSION}
ENV HADOOP_HOME /opt/hadoop 
ENV PATH $PIG_HOME/bin:$HADOOP_HOME/bin:$PATH
ENV PIG_CLASSPATH $HADOOP_HOME/conf

ENV MONGO_HADOOP_CONNECTOR_VERSION 2.0.2 

RUN apt-get update && \
    apt-get install -y wget procps && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/pig && \
    echo "Descargando Apache Pig ${PIG_VERSION}..." && \
    wget -qO- "https://archive.apache.org/dist/pig/pig-${PIG_VERSION}/pig-${PIG_VERSION}.tar.gz" | tar -xzf - -C /opt/pig && \
    echo "Apache Pig ${PIG_VERSION} descargado y extraído." && \
    mkdir -p $HADOOP_HOME/conf && \
    echo '<configuration></configuration>' > $HADOOP_HOME/conf/core-site.xml

# --- DESCARGAR Y COLOCAR EL JAR DE MONGO-HADOOP ---
RUN mkdir -p $PIG_HOME/lib && \
    echo "Descargando mongo-hadoop-core-${MONGO_HADOOP_CONNECTOR_VERSION}.jar..." && \
    wget -O $PIG_HOME/lib/mongo-hadoop-core-${MONGO_HADOOP_CONNECTOR_VERSION}.jar \
         "http://repo1.maven.org/maven2/org/mongodb/mongo-hadoop/mongo-hadoop-core/${MONGO_HADOOP_CONNECTOR_VERSION}/mongo-hadoop-core-${MONGO_HADOOP_CONNECTOR_VERSION}.jar" && \
    echo "mongo-hadoop-core descargado." && \
    echo "Descargando mongo-hadoop-pig-${MONGO_HADOOP_CONNECTOR_VERSION}.jar..." && \
    wget -O $PIG_HOME/lib/mongo-hadoop-pig-${MONGO_HADOOP_CONNECTOR_VERSION}.jar \
         "http://repo1.maven.org/maven2/org/mongodb/mongo-hadoop/mongo-hadoop-pig/${MONGO_HADOOP_CONNECTOR_VERSION}/mongo-hadoop-pig-${MONGO_HADOOP_CONNECTOR_VERSION}.jar" && \
    echo "mongo-hadoop-pig descargado." && \
    echo "JARs de MongoDB Hadoop Connector descargados en $PIG_HOME/lib/"

WORKDIR /pig_scripts