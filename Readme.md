# idetect

## intial setup

Edit `idetect/docker.env` to add the appropriate environment variables

Exporting the UID is necessary before build so that the user that everything
runs as inside the docker container matches the user on the host machine.
Without this, there will be a bunch of permissions problems, like things
failing because they can't write to the `.jupyter` or `.newspaper_scraper`
directories. This could also be avoided by _not_ volume mounting the code
into the containers, which would be an option in production. Having to
re`build` the images every time during development would be a real drag,
though.

We start the workers in order to get it to run the setup.py script.

```
export UID
docker-compose build
docker-compose up workers
```

## running after initial setup

Start LocalDB, Workers, Flask App, Jupyter:
```
docker-compose up
```

Rebuild after changing requirements.txt:
```
docker-compose build
```

Just start LocalDB (eg. for running unit tests in an IDE):
```
docker-compose up localdb
```

Run unit tests in docker:
```
docker-compose up unittests
```

## manipulating the workers that are running

```
docker exec -it idetect_workers_1 bash
supervisorctl status                          # see what's running
supervisorctl stop all                        # stop all workers
supervisorctl start classifier:classifier-00  # start a single classifier
supervisorctl start extractor:*               # start all extractors
```

Logs for the workers are available on the host machine in `idetect/logs/workers` or
inside the docker container at `/var/log/workers`

## find the token for the notebook server

```
docker logs idetect_notebooks_1
```