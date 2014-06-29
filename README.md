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

### Solr

Solr is used to support searching across OCL API entities.  You can use Homebrew to install it as well:

    brew install solr

*** More details required here ***

### The Django Project

Clone this repository, and `cd` into the `django/ocl` directory.
Before you can run the server, you will need to execute the following steps:

1. Install the project dependencies:

    pip install -r requirements.txt

2. Create a Django `Site` and make note of its ID:

    ./manage.py shell
    >>> from django.contrib.sites.models import Site
    >>> s = Site()
    >>> s.save()
    >>> \[Ctrl-D\] (to exit)
    
