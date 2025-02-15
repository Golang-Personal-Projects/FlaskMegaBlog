# FlaskMegaBlog

## Create secret key

`python3 -c "import uuid; print(uuid.uuid4().hex)"`

### Docker configuration

#### Docker network creation

```commandline
docker network create microblog-network
```

#### Postgres Docker installation

```commandline
docker run --name postgres -e POSTGRES_PASSWORD=mysecretpassword -e POSTGRES_USER=microblog -e POSTGRES_DB=microblog --network microblog-network -d postgres:13-alpine3.20 
```

#### Elasticsearch Docker Installation

```commandline
docker run --name elasticsearch -d --rm -p 9200:9200  --network microblog-network   --memory="2GB"     -e discovery.type=single-node -e xpack.security.enabled=false     -t docker.elastic.co/elasticsearch/elasticsearch:8.11.1
```

#### Docker build image for blog

```commandline
docker build -t microblog:latest .
```

#### Docker run image

```commandline
docker run --name microblog -d -p 8000:5000 --network microblog-network  microblog:latest 
```

### Docker Exec into postgres container

```commandline
docker exec -it postgres  psql -U microblog -d microblog -W
```