import json
from ocldev.oclfleximporter import OclFlexImporter

from users.models import UserProfile


class BulkImport:
    def __init__(self):
        pass

    def run_import(self, to_import, username):
        input_list = []
        for line in to_import.splitlines():
            input_list.append(json.loads(line))

        profile = UserProfile.objects.get(mnemonic=username)
        importer = OclFlexImporter(input_list=input_list, api_url_root='http://api.openconceptlab.org:8000', api_token=profile.user.auth_token.key)
        importer.process()

        return importer.import_results