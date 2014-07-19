oclapi
======

Source for the Open Concept Lab APIs

## Local Environment Setup (on a Mac)

Follow this [guide](http://docs.python-guide.org/en/latest/starting/install/osx/) to install Python 2.7
and set up a virtual environment.  You may wish to name your virtual environment something more descriptive,
for example replace:

    virtualenv venv

With:

    virtualenv ocl

And then run:

    source ocl/bin/activate

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

*** More details required here ***

### The Django Project

Clone this repository, and `cd` into the `django/ocl` directory.
Before you can run the server, you will need to execute the following steps:

1. Install the project dependencies:

    pip install -r requirements.txt

2. Create a Django `Site` and make note of its ID:

   ```sh
    ./manage.py shell
    >>> from django.contrib.sites.models import Site
    >>> s = Site()
    >>> s.save()
    >>> [Ctrl-D] (to exit)
    ./manage.py tellsiteid
    ```

3. Replace the `SITE_ID` in your settings file.

   a. Open `oclapi/settings.py` and find the line containing `SITE_ID=`.

   b. Replace the assigned value with the one returned above.

   c. Keep the `u` and the single-quotes intact.  (This denotes a unicode String).

4. Use `syncdb` to create your backing Mongo collections.

   ```sh
   ./manage.py syncdb
   ```

   If you are starting with a clean Mongo database, `syncdb` will prompt you to create a superuser.
   Follow that prompt.

   If you are not prompted to create a superuser, or wish to do so later, you can also use the command:

   ```sh
   ./manage.py createsuperuser
   ```
   
5. Verify your superuser and make note of your token.

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

6. Run the lightweight web server that ships with Django.

   ./manage.py runserver

   The OCL API should now be running at `http://localhost:8000`.

7. Test an endpoint.
   
   Remember, the API uses token-based authentication, so you can't just plug an endpoint into a browser and hit Return.
   You'll need to use a tool that allows you to specify a header with your request.  One simple example is `curl`:

   ```sh   
   curl -H "Authorization: Token c1328d443285f2c933775574e83fe3abfe6d7c0d" http://localhost:8000/users/
   ```

   I recommend using the [Advanced REST Client](https://chrome.google.com/webstore/detail/advanced-rest-client/hgmloofddffdnphfgcellkdfbfbjeloo?hl=en-US) app for Chrome.
   This provides you with a nice editor for passing parameters along with your `POST` and `PUT` requests.

8. Create an API user.
   
   Your superuser is not a valid API user, because it was not created via the `POST /users/` operation.
   However, you can use your superuser to access that endpoint and _create_ an API user:

   ```sh
   curl -H "Authorization: Token c1328d443285f2c933775574e83fe3abfe6d7c0d" -H "Content-Type: application/json" -d '{"username":"test","email":"test@test.com", "name":"TestyMcTest"}' http://localhost:8000/users/   
   ```

9. (Optional) Make your API user an admin (staff) user.

   Log into the Django admin console with the superuser credentials you established in step 4:

   ```sh
   http://localhost:8000/admin/
   ```

   Then navigate to the user list:

   ```sh
   http://localhost:8000/admin/auth/user/
   ```

   Select the user you just created, and check the box next to "staff status".  Now your user is an admin within the context of the OCL API.





    
