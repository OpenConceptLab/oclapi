import os

# PyCharm remote debugging requires importer.install call
try:
    if os.environ.get('JETBRAINS_REMOTE_RUN'):
        from configurations import importer
        importer.install()
except KeyError:
    pass
