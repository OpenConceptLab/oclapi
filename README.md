oclapi
======

## What you'll need:
* git
* docker-compose

Source for the Open Concept Lab APIs

## Docker Environment Setup (preferred)

Fork the repo on github and clone your fork:
````sh
git clone https://github.com/{youruser}/oclapi
````

Add a remote repo to upstream in order to be able to fetch updates:
````sh
git remote add upstream https://github.com/OpenConceptLab/oclapi
````

Go to:
````sh
cd oclapi
````

Fire up containers:
````sh
docker-compose up
````

You can access the API at http://localhost:8000

The root password and the API token can be found in docker-compose.yml under api/environment.

### Docker Environment Settings

Docker `.env` file should be located under the root project folder. On development environment you don't need this file.

#### .env file details

`ENVIRONMENT=` Python module for environment, e.g. production, staging, local, qa

`AWS_ACCESS_KEY_ID=` Amazon Web Services access key.

`AWS_SECRET_ACCESS_KEY=` Amazon Web Services secret key.

`AWS_STORAGE_BUCKET_NAME=` Amazon Web Services bucket name.

`ROOT_PASSWORD=` API root user password.

`OCL_API_TOKEN=` API root token.

`SECRET_KEY=` DJANGO secret key.

`EMAIL_HOST_PASSWORD=` no-reply@openconceptlab.org password.

`SENTRY_DSN=` Sentry unique URL for the given environment.

### Running commands in a container

You can run any command in a running container. Open up a new terminal and run for example:
````sh
docker-compose exec api python manage.py syncdb
````

### Running tests in a container
You can run tests in a container as any other command.

#### Unit Tests

````sh
docker-compose run --rm api python manage.py run_test --configuration=Dev
````

#### Integration Tests

````sh
docker-compose run --rm api python manage.py test integration_tests --configuration=Dev
````

#### Rebuilding SOLR index

If the SOLR index gets out of sync, you can run the following command:
````sh
docker-compose exec api python manage.py rebuild_index --batch-size 100 --workers 4 --verbosity 2
````

### Debugging in container

To setup debugging PyCharm Professional Edition is required.

Docker-compose up starts the server in a development mode by default. It exposes all services on the host machine as well as enables SSH to the API service.

In Pycharm IDE open oclapi project and go to `Settings-> Project: oclapi -> Project Interpreter`

Click on gear icon and choose `Add Remote` option

Configure interpreter with SSH credentials as in the image (default password is `Root123`):

![alt](img/remote_interpreter_config.png)

There will be warnings about unknown host etc. but don't don't worry, just confirm.

Setup django debug configuration as in the image (Path mapping should be `absolute path to project directory=/code`):

![alt](img/docker_debug_config.png)

Run your configuration! Debugging server will run on [http://0.0.0.0:8001/](http://0.0.0.0:8001/)

In case of any problems with `.pycharm_helpers` just delete remote interpreter and create new with same configuration, it will write pycharm helpers in Your ocl container again.

## Continuous Integration

The project is built by CI at https://ci.openmrs.org/browse/OCL

You can see 3 plans there:
* OCL API
* OCL WEB
* OCL QA UI Tests

OCL API and OCL WEB are triggered by commits to respective repos. First docker images are built and pushed with a nightly tag to dockerhub at https://hub.docker.com/u/openconceptlab/dashboard/. Next unit and integration tests are being run. Finally a qa tag is being pushed to dockerhub and deployed to https://ocl-qa.openmrs.org/. On each deployment data is wiped out of the qa environment. You can login to the server using username 'admin' and password 'Admin123'.

### Deplying to staging and production

If you want to deploy to staging or production, you need to be logged in to Bamboo. Please request access via helpdesk@openmrs.org

1. Go to https://ci.openmrs.org/browse/OCL and click the cloud icon next to the project you want to deploy.
2. Click the related deployment plan.
3. Click the cloud icon next in the actions column for the chosen environment.
4. Choose whether to create a new release from build result or redeploy an existing release. You will choose the latter when promoting a release from staging to production, downgrading to a previous release or restarting services.
5. When creating a new release, choose the build result, which you want to deploy (usually the latest successful build). Leave the release title unchanged and click the Start deployment button.
6. Wait for the release to complete.

## Manual Environment Setup (on a Mac)

Follow this [guide](http://docs.python-guide.org/en/latest/starting/install/osx/) to install Python 2.7
and set up a virtual environment.  You may wish to name your virtual environment something more descriptive,
for example replace:

    virtualenv venv

With:

    virtualenv oclenv

And then run:

    source oclenv/bin/activate

### Mongo

The OCL API uses MongoDB as its backend datastore.  If you don't have it already, use Homebrew to install it:

    brew install mongodb

Once installed, use the `mongod` command to start a local instance of the MongoDB server.
Then, in a separate console window, run `mongo` to start the interactive command-line client.
Using the Mongo command-line, create a database named `ocl`:

     > use ocl

### Solr 4.9.0

Solr is used to support searching across OCL API entities.  To download Solr 4.9.0, visit the Solr [mirrors](http://www.apache.org/dyn/closer.cgi/lucene/solr/4.9.0) page and select a mirror.  Then download solr-4.9.0.tgz (NOT solr-4.9.0-src.tgz).

Choose an install directory (e.g. `~/third-party`, henceforth `$INSTALL_DIR`) and extract the tarball there.  You will then need to set 2 environment variables:

       export SOLR_ROOT=$INSTALL_DIR/solr-4.9.0
       export SOLR_HOME=$OCLAPI_ROOT/solr

`$OCLAPI_ROOT` refers to your Git project root (i.e. the location of this Readme file).

This should enable you to run `$OCLAPI_ROOT/run_solr.sh`, which starts Solr in a Jetty instance listening on port 8983.  Verify this by visiting:

     http://localhost:8983/solr

### The Django Project

Clone this repository, and `cd` into the `ocl` directory.
Before you can run the server, you will need to execute the following steps:

1. Install the project dependencies:

    pip install -r requirements.txt

2. Use `syncdb` to create your backing Mongo collections.

   ```sh
   ./manage.py syncdb
   ```

   If you are starting with a clean Mongo database, `syncdb` will prompt you to create a superuser.
   Follow that prompt.

   If you are not prompted to create a superuser, or wish to do so later, you can also use the command:

   ```sh
   ./manage.py createsuperuser
   ```
   
3. Verify your superuser and make note of your token.

   ```sh
   $ mongo
   > use ocl
   > db.auth_user.find({'is_superuser':true})
   ```

   This should revel the superuser you just created.  Note the user's _id (e.g. `ObjectId("528927fb2f3e986be1627d6d")`),
   and use it to locate your token:

   ```sh
   > db.authtoken_token.find({'user_id': ObjectId("528927fb2f3e986be1627d6d")})[0]
   ```

   Make note of the token `_id` (e.g. `"20e6ac8fe09129debac2929f4a20a56bea801165"`).  You will need this to access your endpoints
   once you start up your server.

4. Run the lightweight web server that ships with Django.

   ./manage.py runserver

   The OCL API should now be running at `http://localhost:8000`.

5. Test an endpoint.
   
   Remember, the API uses token-based authentication, so you can't just plug an endpoint into a browser and hit Return.
   You'll need to use a tool that allows you to specify a header with your request.  One simple example is `curl`:

   ```sh   
   curl -H "Authorization: Token c1328d443285f2c933775574e83fe3abfe6d7c0d" http://localhost:8000/users/
   ```

   I recommend using the [Advanced REST Client](https://chrome.google.com/webstore/detail/advanced-rest-client/hgmloofddffdnphfgcellkdfbfbjeloo?hl=en-US) app for Chrome.
   This provides you with a nice editor for passing parameters along with your `POST` and `PUT` requests.

6. Create an API user.
   
   Your superuser is not a valid API user, because it was not created via the `POST /users/` operation.
   However, you can use your superuser to access that endpoint and _create_ an API user:

   ```sh
   curl -H "Authorization: Token c1328d443285f2c933775574e83fe3abfe6d7c0d" -H "Content-Type: application/json" -d '{"username":"test","email":"test@test.com", "name":"TestyMcTest"}' http://localhost:8000/users/   
   ```

7. (Optional) Make your API user an admin (staff) user.

   Log into the Django admin console with the superuser credentials you established in step 4:

   ```sh
   http://localhost:8000/admin/
   ```

   Then navigate to the user list:

   ```sh
   http://localhost:8000/admin/auth/user/
   ```

   Select the user you just created, and check the box next to "staff status".  Now your user is an admin within the context of the OCL API.
   
   

## Data Import Before Concept Creation
We need to have data before we go on creating a concept. 

The dropdowns that require preloaded data are Concept Class, Datatype, Name/Description Type, Locale, Map Type. 


### How to import Data
1. Create a new org `OCL`. 
2. Create a new user source `Classes` under org `OCL`. This will be be used for Concept Class dropdown.
3. Import the data as concepts in `Classes` from https://github.com/OpenConceptLab/ocl_import/blob/master/OCL_Classes/classes.json .

Follow https://github.com/OpenConceptLab/oclapi/wiki/Bulk-Importing#how-to-import to know how to import concepts in a source.

Proceed in same fashion for rest of the dropdown fields. Create sources `Datatypes`, `NameTypes`, `DescriptionTypes`, `Locales`, `MapTypes` under org `OCL`. 

Refer to following files for data: 

Datatypes: https://github.com/OpenConceptLab/ocl_import/blob/master/OCL_Datatypes/datatypes_fixed.json

NameTypes: https://github.com/OpenConceptLab/ocl_import/blob/master/OCL_NameTypes/nametypes_fixed.json

DescriptionTypes: https://github.com/OpenConceptLab/ocl_import/blob/master/OCL_DescriptionTypes/description_types.json

Locales: https://github.com/OpenConceptLab/ocl_import/blob/master/OCL_Locales/locales.json

MapTypes: https://github.com/OpenConceptLab/ocl_import/blob/master/OCL_MapTypes/maptypes_fixed.json


---------------------------------------------------------------------
Copyright (C) 2016 Open Concept Lab. Use of this software is subject
to the terms of the Mozille Public License v2.0. Open Concept Lab is
also distributed under the terms the Healthcare Disclaimer
described at http://www.openconceptlab.com/license/.
---------------------------------------------------------------------
