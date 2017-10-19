# idetect

## intial setup

Edit `idetect/docker.env` to add the appropriate environment variables

Start LocalDB and Notebooks, run setup script. We start the Notebooks
for this because it's the container that doesn't immediately start something
that relies on the things that get set up in the setup script. The API
wants the DB to be up already, and the Workers try to load the models that
the setup script fetches, so that leaves the Notebooks.

Exporting the UID is necessary before build so that the user that everything
runs as inside the docker container matches the user on the host machine.
Without this, there will be a bunch of permissions problems, like things
failing because they can't write to the `.jupyter` or `.newspaper_scraper`
directories. This could also be avoided by _not_ volume mounting the code
into the containers, which would be an option in production. Having to
re`build` the images every time during development would be a real drag,
though.

```
export UID
docker-compose up notebooks
docker exec -it idetect_notebooks_1 bash
python3 python/setup.py
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