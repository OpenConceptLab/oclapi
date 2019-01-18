"""
OCL Flexible Importer --
Script that uses the OCL API to import multiple resource types from a JSON lines file.
Configuration for individual resources can be set inline in the JSON.
For batch imports of concepts and mappings into a single source, the server-side import
script offers a higher performance alternative than this module.

Resources currently supported:
* Organizations
* Sources
* Collections
* Concepts
* Mappings
* References

Verbosity settings:
* 0 = show only responses from server
* 1 = show responses from server and all POSTs
* 2 = show everything minus debug output
* 3 = show everything plus debug output

Deviations from OCL API responses:
* Sources/Collections:
    - "supported_locales" response is a list in OCL, but only a comma-separated string
      is supported when posted here
"""

import json
import sys
import time
from datetime import datetime
import urllib
import requests


# Owner fields: ( owner AND owner_type ) OR ( owner_url )
# Repository fields: ( source OR source_url ) OR ( collection OR collection_url )
# Concept/Mapping fields: ( id ) OR ( url )

class OclImportError(Exception):
    """ Base exception for this module """
    pass


class UnexpectedStatusCodeError(OclImportError):
    """ Exception raised for unexpected status code """
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class InvalidOwnerError(OclImportError):
    """ Exception raised when owner information is invalid """
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class InvalidRepositoryError(OclImportError):
    """ Exception raised when repository information is invalid """
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class InvalidObjectDefinition(OclImportError):
    """ Exception raised when object definition invalid """
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class OclImportResults(object):
    """ Class to capture the results of processing an import script """

    SKIP_KEY = 'skip'
    NO_OBJECT_TYPE_KEY = 'NO-OBJECT-TYPE'
    ORGS_RESULTS_ROOT = '/orgs/'
    USERS_RESULTS_ROOT = '/users/'

    def __init__(self, total_lines=0):
        self._results = {}
        self.count = 0
        self.num_skipped = 0
        self.total_lines = total_lines

    def add(self, obj_url='', action_type='', obj_type='', obj_repo_url='',
            http_method='', obj_owner_url='', status_code=None, text='', message=''):
        """
        Add a result to this OclImportResults object
        :param obj_url:
        :param action_type:
        :param obj_type:
        :param obj_repo_url:
        :param http_method:
        :param obj_owner_url:
        :param status_code:
        :return:
        """

        # TODO: Handle logging for refs differently since they are batched and return 200

        # Determine the first dimension (the "logging root") of the results object
        logging_root = '/'
        if obj_type in [OclFlexImporter.OBJ_TYPE_CONCEPT,
                        OclFlexImporter.OBJ_TYPE_MAPPING,
                        OclFlexImporter.OBJ_TYPE_REFERENCE]:
            logging_root = obj_repo_url
        elif obj_type in [OclFlexImporter.OBJ_TYPE_SOURCE,
                          OclFlexImporter.OBJ_TYPE_COLLECTION]:
            logging_root = obj_owner_url
        elif obj_type == OclFlexImporter.OBJ_TYPE_ORGANIZATION:
            logging_root = self.ORGS_RESULTS_ROOT
        elif obj_type == OclFlexImporter.OBJ_TYPE_USER:
            logging_root = self.USERS_RESULTS_ROOT

        # Setup the results dictionary to accept this new result
        if logging_root not in self._results:
            self._results[logging_root] = {}
        if action_type not in self._results[logging_root]:
            self._results[logging_root][action_type] = {}
        if not status_code:
            status_code = self.SKIP_KEY
        if status_code not in self._results[logging_root][action_type]:
            self._results[logging_root][action_type][status_code] = []

        # Add the result to the results object
        new_result = {
            'obj_type': obj_type,
            'obj_url': obj_url,
            'action_type': action_type,
            'method': http_method,
            'obj_repo_url': obj_repo_url,
            'obj_owner_url': obj_owner_url,
            'status_code': status_code,
            'text': text,
            'message': message
        }
        self._results[logging_root][action_type][status_code].append(new_result)
        self.count += 1

    def has(self, root_key='', limit_to_success_codes=False):
        """
        Return whether this OclImportResults object contains a
        result matching the specified root_key
        :param root_key: Key to match
        :param limit_to_success_codes: Set to true to only match a successful import result
        :return: True if a match found; False otherwise
        """
        if root_key in self._results and not limit_to_success_codes:
            return True
        elif root_key in self._results and limit_to_success_codes:
            for action_type in self._results[root_key]:
                for status_code in self._results[root_key][action_type]:
                    if int(status_code) >= 200 and int(status_code) < 300:
                        return True
        return False

    def __str__(self):
        """ Get a concise summary of this results object """
        return self.get_summary()

    def get_summary(self, root_key=None):
        """
        Get a concise summary of this results object, optionally filtering by a specific root_key
        :param root_key: Optional root_key to filter the summary results
        :return:
        """
        if not root_key:
            return 'Processed %s of %s total' % (self.count, self.total_lines)
        elif self.has(root_key=root_key):
            num_processed = 0
            for action_type in self._results[root_key]:
                for status_code in self._results[root_key][action_type]:
                    num_processed += len(self._results[root_key][action_type][status_code])
            return 'Processed %s for key "%s"' % (num_processed, root_key)

    def get_detailed_summary(self, root_key=None, limit_to_success_codes=False):
        """ Get a detailed summary of the results """

        # Build results summary dictionary - organized by action type instead of root
        results_summary = {}
        if root_key:
            keys = [root_key]
        else:
            keys = self._results.keys()
        total_count = 0
        for k in keys:
            for action_type in self._results[k]:
                if action_type not in results_summary:
                    results_summary[action_type] = {}
                for status_code in self._results[k][action_type]:
                    if limit_to_success_codes and (int(status_code) < 200 or int(status_code) >= 300):
                        continue
                    status_code_count = len(self._results[k][action_type][status_code])
                    if status_code not in results_summary[action_type]:
                        results_summary[action_type][status_code] = 0
                    results_summary[action_type][status_code] += status_code_count
                    total_count += status_code_count

        # Turn the results summary dictionary into a string
        output = ''
        for action_type in results_summary:
            if output:
                output += '; '
            status_code_summary = ''
            action_type_count = 0
            for status_code in results_summary[action_type]:
                action_type_count += results_summary[action_type][status_code]
                if status_code_summary:
                    status_code_summary += ', '
                status_code_summary += '%s:%s' % (
                    status_code, results_summary[action_type][status_code])
            output += '%s %s (%s)' % (action_type_count, action_type, status_code_summary)

        # Polish it all off
        if limit_to_success_codes:
            process_str = 'Successfully processed'
        else:
            process_str = 'Processed'
        if root_key:
            output = '%s %s for key "%s"' % (process_str, output, root_key)
        else:
            output = '%s %s of %s -- %s' % (
                process_str, total_count, self.total_lines, output)

        return output

    def display_report(self):
        """ Display a full report of the results """
        print 'REPORT OF IMPORT RESULTS:'
        for logging_root in self._results:
            print '%s:' % logging_root
            for action_type in self._results[logging_root]:
                for status_code in self._results[logging_root][action_type]:
                    if action_type == status_code == self.SKIP_KEY:
                        print '  %s:' % (self.SKIP_KEY)
                    else:
                        print '  %s %s:' % (action_type, status_code)
                    for result in self._results[logging_root][action_type][status_code]:
                        print '    %s  %s' % (result['message'], result['text'])


class OclFlexImporter(object):
    """
    Class to flexibly import multiple resource types into OCL from JSON lines files via
    the OCL API rather than the batch importer.
    """

    INTERNAL_MAPPING = 1
    EXTERNAL_MAPPING = 2

    OBJ_TYPE_USER = 'User'
    OBJ_TYPE_ORGANIZATION = 'Organization'
    OBJ_TYPE_SOURCE = 'Source'
    OBJ_TYPE_COLLECTION = 'Collection'
    OBJ_TYPE_CONCEPT = 'Concept'
    OBJ_TYPE_MAPPING = 'Mapping'
    OBJ_TYPE_REFERENCE = 'Reference'
    OBJ_TYPE_SOURCE_VERSION = 'Source Version'
    OBJ_TYPE_COLLECTION_VERSION = 'Collection Version'

    ACTION_TYPE_NEW = 'new'
    ACTION_TYPE_UPDATE = 'update'
    ACTION_TYPE_RETIRE = 'retire'
    ACTION_TYPE_DELETE = 'delete'
    ACTION_TYPE_OTHER = 'other'
    ACTION_TYPE_SKIP = 'skip'

    # Resource type definitions
    obj_def = {
        OBJ_TYPE_ORGANIZATION: {
            "id_field": "id",
            "url_name": "orgs",
            "has_owner": False,
            "has_source": False,
            "has_collection": False,
            "allowed_fields": ["id", "company", "extras", "location", "name", "public_access", "extras", "website"],
            "create_method": "POST",
            "update_method": "POST",
        },
        OBJ_TYPE_SOURCE: {
            "id_field": "id",
            "url_name": "sources",
            "has_owner": True,
            "has_source": False,
            "has_collection": False,
            "allowed_fields": ["id", "short_code", "name", "full_name", "description", "source_type", "custom_validation_schema", "public_access", "default_locale", "supported_locales", "website", "extras", "external_id"],
            "create_method": "POST",
            "update_method": "POST",
        },
        OBJ_TYPE_COLLECTION: {
            "id_field": "id",
            "url_name": "collections",
            "has_owner": True,
            "has_source": False,
            "has_collection": False,
            "allowed_fields": ["id", "short_code", "name", "full_name", "description", "collection_type", "custom_validation_schema", "public_access", "default_locale", "supported_locales", "website", "extras", "external_id"],
            "create_method": "POST",
            "update_method": "POST",
        },
        OBJ_TYPE_CONCEPT: {
            "id_field": "id",
            "url_name": "concepts",
            "has_owner": True,
            "has_source": True,
            "has_collection": False,
            "allowed_fields": ["id", "external_id", "concept_class", "datatype", "names", "descriptions", "retired", "extras"],
            "create_method": "POST",
            "update_method": "PUT",
        },
        OBJ_TYPE_MAPPING: {
            "id_field": "id",
            "url_name": "mappings",
            "has_owner": True,
            "has_source": True,
            "has_collection": False,
            "allowed_fields": ["id", "map_type", "from_concept_url", "to_source_url", "to_concept_url", "to_concept_code", "to_concept_name", "extras", "external_id"],
            "create_method": "POST",
            "update_method": "POST",
        },
        OBJ_TYPE_REFERENCE: {
            "url_name": "references",
            "has_owner": True,
            "has_source": False,
            "has_collection": True,
            "allowed_fields": ["data"],
            "create_method": "PUT",
            "update_method": None,
        },
        OBJ_TYPE_SOURCE_VERSION: {
            "id_field": "id",
            "url_name": "versions",
            "has_owner": True,
            "has_source": True,
            "has_collection": False,
            "omit_resource_name_on_get": True,
            "allowed_fields": ["id", "external_id", "description", "released"],
            "create_method": "POST",
            "update_method": "POST",
        },
        OBJ_TYPE_COLLECTION_VERSION: {
            "id_field": "id",
            "url_name": "versions",
            "has_owner": True,
            "has_source": False,
            "has_collection": True,
            "omit_resource_name_on_get": True,
            "allowed_fields": ["id", "external_id", "description", "released"],
            "create_method": "POST",
            "update_method": "POST",
        },
        OBJ_TYPE_USER: {
            "id_field": "username",
            "url_name": "users",
            "has_owner": False,
            "has_source": False,
            "has_collection": False,
            "allowed_fields": ["username", "name", "email", "company", "location", "preferred_locale"],
            "create_method": "POST",
            "update_method": "POST",
        }
    }

    def __init__(self, file_path='', input_list=None, api_url_root='', api_token='', limit=0,
                 test_mode=False, verbosity=1, do_update_if_exists=False, import_delay=0):
        """ Initialize this object """

        self.input_list = input_list
        self.file_path = file_path
        if file_path:
            self.load_from_file(file_path)
        self.api_token = api_token
        self.api_url_root = api_url_root
        self.test_mode = test_mode
        self.do_update_if_exists = do_update_if_exists
        self.verbosity = verbosity
        self.limit = limit
        self.import_delay = import_delay
        self.skip_line_count = False

        self.import_results = None
        self.cache_obj_exists = {}

        # Prepare the headers
        self.api_headers = {
            'Authorization': 'Token ' + self.api_token,
            'Content-Type': 'application/json'
        }

    def log(self, *args):
        """ Output log information """
        sys.stdout.write('[' + str(datetime.now()) + '] ')
        for arg in args:
            sys.stdout.write(str(arg))
            sys.stdout.write(' ')
        sys.stdout.write('\n')
        sys.stdout.flush()

    def log_settings(self):
        """ Output log of the object settings """
        self.log("**** OCL IMPORT SCRIPT SETTINGS ****",
                 "API Root URL:", self.api_url_root,
                 ", API Token:", self.api_token,
                 ", Import File:", self.file_path,
                 ", Test Mode:", self.test_mode,
                 ", Update Resource if Exists:", self.do_update_if_exists,
                 ", Verbosity:", self.verbosity,
                 ", Import Delay: ", self.import_delay)

    def load_from_file(self, file_path):
        """ Load the OCL-formatted JSON file from the specified path """
        self.file_path = file_path
        self.input_list = []
        with open(self.file_path) as json_file:
            for json_line_raw in json_file:
                self.input_list.append(json.loads(json_line_raw))

    def process(self):
        """
        Imports a JSON-lines file using OCL API
        :return: int Number of JSON lines processed
        """

        # Display global settings
        if self.verbosity:
            self.log_settings()

        # Count lines
        num_lines = 0
        if not self.skip_line_count:
            num_lines = len(self.input_list)

        # Loop through each JSON object in the file
        self.import_results = OclImportResults(total_lines=num_lines)
        obj_def_keys = self.obj_def.keys()
        count = 0
        num_processed = 0
        num_skipped = 0
        for json_line_obj in self.input_list:
            json_line_raw = json.dumps(json_line_obj)
            if self.limit > 0 and count >= self.limit:
                break
            count += 1
            if "type" in json_line_obj:
                obj_type = json_line_obj.pop("type")
                if obj_type in obj_def_keys:
                    self.log('')
                    self.process_object(obj_type, json_line_obj)
                    num_processed += 1
                    self.log('[%s]' % self.import_results.get_detailed_summary())

                    # Optionally delay before processing next row
                    if self.import_delay and not self.test_mode:
                        time.sleep(self.import_delay)
                else:
                    message = "Unrecognized 'type' attribute '%s' for object: %s" % (obj_type, json_line_raw)
                    self.import_results.add(action_type=self.ACTION_TYPE_SKIP, obj_type=obj_type,
                                            text=json_line_raw, message=message)
                    self.log('**** SKIPPING: %s' % message)
                    num_skipped += 1
            else:
                message = "No 'type' attribute: %s" % json_line_raw
                self.import_results.add(action_type=self.ACTION_TYPE_SKIP, text=json_line_raw, message=message)
                self.log('**** SKIPPING: %s' % message)
                num_skipped += 1

        return count

    def does_object_exist(self, obj_url, use_cache=True):
        """ Returns whether an object at the specified URL already exists """

        # If obj existence cached, then just return True
        if use_cache and obj_url in self.cache_obj_exists and self.cache_obj_exists[obj_url]:
            return True

        # Object existence not cached, so use API to check if it exists
        request_existence = requests.head(self.api_url_root + obj_url, headers=self.api_headers)
        if request_existence.status_code == requests.codes.ok:
            self.cache_obj_exists[obj_url] = True
            return True
        elif request_existence.status_code == requests.codes.not_found:
            return False
        else:
            raise UnexpectedStatusCodeError(
                "GET " + self.api_url_root + obj_url,
                "Unexpected status code returned: " + str(request_existence.status_code))

    def does_mapping_exist(self, obj_url, obj):
        """
        Returns whether the specified mapping already exists --
        Equivalent mapping must have matching source, from_concept, to_concept, and map_type
        """

        '''
        # Return false if correct fields not set
        mapping_target = None
        if ('from_concept_url' not in obj or not obj['from_concept_url']
                or 'map_type' not in obj or not obj['map_type']):
            # Invalid mapping -- no from_concept or map_type
            return False
        if 'to_concept_url' in obj:
            mapping_target = self.INTERNAL_MAPPING
        elif 'to_source_url' in obj and 'to_concept_code' in obj:
            mapping_target = self.EXTERNAL_MAPPING
        else:
            # Invalid to_concept
            return False

        # Build query parameters
        params = {
            'fromConceptOwner': '',
            'fromConceptOwnerType': '',
            'fromConceptSource': '',
            'fromConcept': obj['from_concept_url'],
            'mapType': obj['map_type'],
            'toConceptOwner': '',
            'toConceptOwnerType': '',
            'toConceptSource': '',
            'toConcept': '',
        }
        #if mapping_target == self.INTERNAL_MAPPING:
        #    params['toConcept'] = obj['to_concept_url']
        #else:
        #    params['toConcept'] = obj['to_concept_code']

        # Use API to check if mapping exists
        request_existence = requests.head(
            self.api_url_root + obj_url, headers=self.api_headers, params=params)
        if request_existence.status_code == requests.codes.ok:
            if 'num_found' in request_existence.headers and int(request_existence.headers['num_found']) >= 1:
                return True
            else:
                return False
        elif request_existence.status_code == requests.codes.not_found:
            return False
        else:
            raise UnexpectedStatusCodeError(
                "GET " + self.api_url_root + obj_url,
                "Unexpected status code returned: " + str(request_existence.status_code))
        '''

        return False

    def does_reference_exist(self, obj_url, obj):
        """ Returns whether the specified reference already exists """

        '''
        # Return false if no expression
        if 'expression' not in obj or not obj['expression']:
            return False

        # Use the API to check if object exists
        params = {'q': obj['expression']}
        request_existence = requests.head(
            self.api_url_root + obj_url, headers=self.api_headers, params=params)
        if request_existence.status_code == requests.codes.ok:
            if 'num_found' in request_existence.headers and int(request_existence.headers['num_found']) >= 1:
                return True
            else:
                return False
        elif request_existence.status_code == requests.codes.not_found:
            return False
        else:
            raise UnexpectedStatusCodeError(
                "GET " + self.api_url_root + obj_url,
                "Unexpected status code returned: " + str(request_existence.status_code))
        '''

        return False

    def process_object(self, obj_type, obj):
        """ Processes an individual document in the import file """

        # Grab the ID
        obj_id = ''
        if 'id_field' in self.obj_def[obj_type] and self.obj_def[obj_type]['id_field'] in obj:
            obj_id = obj[self.obj_def[obj_type]['id_field']]

        # Determine whether this resource has an owner, source, or collection
        has_owner = False
        has_source = False
        has_collection = False
        if self.obj_def[obj_type]["has_owner"]:
            has_owner = True
        if self.obj_def[obj_type]["has_source"] and self.obj_def[obj_type]["has_collection"]:
            err_msg = "Object definition for '%s' must not have both 'has_source' and 'has_collection' set to True" % obj_type
            raise InvalidObjectDefinition(obj, err_msg)
        elif self.obj_def[obj_type]["has_source"]:
            has_source = True
        elif self.obj_def[obj_type]["has_collection"]:
            has_collection = True

        # Set owner URL using ("owner_url") OR ("owner" AND "owner_type")
        # e.g. /users/johndoe/ OR /orgs/MyOrganization/
        # NOTE: Owner URL always ends with a forward slash
        obj_owner_url = None
        if has_owner:
            if "owner_url" in obj:
                obj_owner_url = obj.pop("owner_url")
                obj.pop("owner", None)
                obj.pop("owner_type", None)
            elif "owner" in obj and "owner_type" in obj:
                obj_owner_type = obj.pop("owner_type")
                obj_owner = obj.pop("owner")
                if obj_owner_type == self.OBJ_TYPE_ORGANIZATION:
                    obj_owner_url = "/" + self.obj_def[self.OBJ_TYPE_ORGANIZATION]["url_name"] + "/" + obj_owner + "/"
                elif obj_owner_url == self.OBJ_TYPE_USER:
                    obj_owner_url = "/" + self.obj_def[self.OBJ_TYPE_USER]["url_name"] + "/" + obj_owner + "/"
                else:
                    raise InvalidOwnerError(obj, "Valid owner information required for object of type '" + obj_type + "'")
            elif has_source and 'source_url' in obj and obj['source_url']:
                # Extract owner info from the source URL
                obj_owner_url = obj['source_url'][:self.find_nth(obj['source_url'], '/', 3) + 1]
            elif has_collection and 'collection_url' in obj and obj['collection_url']:
                # Extract owner info from the collection URL
                obj_owner_url = obj['collection_url'][:self.find_nth(obj['collection_url'], '/', 3) + 1]
            else:
                raise InvalidOwnerError(obj, "Valid owner information required for object of type '" + obj_type + "'")

        # Set repository URL using ("source_url" OR "source") OR ("collection_url" OR "collection")
        # e.g. /orgs/MyOrganization/sources/MySource/ OR /orgs/CIEL/collections/StarterSet/
        # NOTE: Repository URL always ends with a forward slash
        obj_repo_url = None
        if has_source:
            if "source_url" in obj:
                obj_repo_url = obj.pop("source_url")
                obj.pop("source", None)
            elif "source" in obj:
                obj_repo_url = obj_owner_url + 'sources/' + obj.pop("source") + "/"
            else:
                raise InvalidRepositoryError(obj, "Valid source information required for object of type '" + obj_type + "'")
        elif has_collection:
            if "collection_url" in obj:
                obj_repo_url = obj.pop("collection_url")
                obj.pop("collection", None)
            elif "collection" in obj:
                obj_repo_url = obj_owner_url + 'collections/' + obj.pop("collection") + "/"
            else:
                raise InvalidRepositoryError(obj, "Valid collection information required for object of type '" + obj_type + "'")

        # Build object URLs -- note that these always end with forward slashes
        obj_url = new_obj_url = ''
        if has_source or has_collection:
            if 'omit_resource_name_on_get' in self.obj_def[obj_type] and self.obj_def[obj_type]['omit_resource_name_on_get']:
                # Source or collection version does not use 'versions' in endpoint
                new_obj_url = obj_repo_url + self.obj_def[obj_type]["url_name"] + "/"
                obj_url = obj_repo_url + obj_id + "/"
            elif obj_id:
                # Concept
                new_obj_url = obj_repo_url + self.obj_def[obj_type]["url_name"] + "/"
                obj_url = new_obj_url + obj_id + "/"
            else:
                # Mapping, reference, etc.
                new_obj_url = obj_url = obj_repo_url + self.obj_def[obj_type]["url_name"] + "/"
        elif has_owner:
            # Repositories (source or collection) and anything that also has a repository
            new_obj_url = obj_owner_url + self.obj_def[obj_type]["url_name"] + "/"
            obj_url = new_obj_url + obj_id + "/"
        else:
            # Only organizations and users don't have an owner or repository -- and only orgs can be created here
            new_obj_url = '/' + self.obj_def[obj_type]["url_name"] + "/"
            obj_url = new_obj_url + obj_id + "/"

        # Handle query parameters
        # NOTE: This is hard coded just for references for now
        query_params = {}
        if obj_type == self.OBJ_TYPE_REFERENCE:
            if "__cascade" in obj:
                query_params["cascade"] = obj.pop("__cascade")

        # Pull out the fields that aren't allowed
        obj_not_allowed = {}
        for k in obj.keys():
            if k not in self.obj_def[obj_type]["allowed_fields"]:
                obj_not_allowed[k] = obj.pop(k)

        # Display some debug info
        if self.verbosity >= 1:
            self.log("**** Importing " + obj_type + ": " + self.api_url_root + obj_url + " ****")
        if self.verbosity >= 2:
            self.log("** Allowed Fields: **", json.dumps(obj))
            self.log("** Removed Fields: **", json.dumps(obj_not_allowed))

        # Check if owner exists - at this point obj_url, obj_owner_url, and obj_repo_url are set
        if has_owner and obj_owner_url:
            try:
                if self.does_object_exist(obj_owner_url):
                    self.log("** INFO: Owner exists at: " + obj_owner_url)
                else:
                    message = "Owner does not exist at: %s" % obj_owner_url
                    self.log("** SKIPPING: %s" % message)
                    self.import_results.add(action_type=self.ACTION_TYPE_SKIP, obj_type=obj_type,
                                            obj_url=obj_url, obj_repo_url=obj_repo_url,
                                            obj_owner_url=obj_owner_url,
                                            text=json.dumps(obj), message=message)
                    if not self.test_mode:
                        return
            except UnexpectedStatusCodeError as e:
                message = "Unexpected error occurred: %s, %s" % (e.expression, e.message)
                self.import_results.add(action_type=self.ACTION_TYPE_SKIP, obj_type=obj_type,
                                        obj_url=obj_url, obj_repo_url=obj_repo_url,
                                        obj_owner_url=obj_owner_url,
                                        text=json.dumps(obj), message=message)
                self.log("** SKIPPING: %s" % message)
                return

        # Check if repository exists
        if (has_source or has_collection) and obj_repo_url:
            try:
                if self.does_object_exist(obj_repo_url):
                    self.log("** INFO: Repository exists at: " + obj_repo_url)
                else:
                    message = "Repository does not exist at: %s" % obj_repo_url
                    self.import_results.add(action_type=self.ACTION_TYPE_SKIP, obj_type=obj_type,
                                            obj_url=obj_url, obj_repo_url=obj_repo_url,
                                            obj_owner_url=obj_owner_url,
                                            text=json.dumps(obj), message=message)
                    self.log("** SKIPPING: %s" % message)
                    if not self.test_mode:
                        return
            except UnexpectedStatusCodeError as e:
                message = "Unexpected error occurred: %s, %s" % (e.expression, e.message)
                self.import_results.add(action_type=self.ACTION_TYPE_SKIP, obj_type=obj_type,
                                        obj_url=obj_url, obj_repo_url=obj_repo_url,
                                        obj_owner_url=obj_owner_url,
                                        text=json.dumps(obj), message=message)
                self.log("** SKIPPING: %s" % message)
                return

        # Check if object already exists: GET self.api_url_root + obj_url
        obj_already_exists = False
        try:
            if obj_type == 'Reference':
                obj_already_exists = self.does_reference_exist(obj_url, obj)
            elif obj_type == 'Mapping':
                obj_already_exists = self.does_mapping_exist(obj_url, obj)
            else:
                obj_already_exists = self.does_object_exist(obj_url)
        except UnexpectedStatusCodeError as e:
            message = "Unexpected error occurred: %s, %s" % (e.expression, e.message)
            self.import_results.add(action_type=self.ACTION_TYPE_SKIP, obj_type=obj_type,
                                    obj_url=obj_url, obj_repo_url=obj_repo_url,
                                    obj_owner_url=obj_owner_url,
                                    text=json.dumps(obj), message=message)
            self.log("** SKIPPING: %s" % message)
            return
        if obj_already_exists and not self.do_update_if_exists:
            message = "Object already exists at: %s%s" % (self.api_url_root, obj_url)
            self.import_results.add(action_type=self.ACTION_TYPE_SKIP, obj_type=obj_type,
                                    obj_url=obj_url, obj_repo_url=obj_repo_url,
                                    obj_owner_url=obj_owner_url,
                                    text=json.dumps(obj), message=message)
            self.log("** SKIPPING: %s" % message)
            if not self.test_mode:
                return
        elif obj_already_exists:
            self.log("** INFO: Object already exists at: " + self.api_url_root + obj_url)
        else:
            self.log("** INFO: Object does not exist so we'll create it at: " + self.api_url_root + obj_url)

        # TODO: Validate the JSON object

        # Create/update the object
        try:
            self.update_or_create(
                obj_type=obj_type,
                obj_id=obj_id,
                obj_owner_url=obj_owner_url,
                obj_repo_url=obj_repo_url,
                obj_url=obj_url,
                new_obj_url=new_obj_url,
                obj_already_exists=obj_already_exists,
                obj=obj, obj_not_allowed=obj_not_allowed,
                query_params=query_params)
        except requests.exceptions.HTTPError as e:
            self.log("ERROR: ", e)

    def update_or_create(self, obj_type='', obj_id='', obj_owner_url='',
                         obj_repo_url='', obj_url='', new_obj_url='',
                         obj_already_exists=False,
                         obj=None, obj_not_allowed=None,
                         query_params=None):
        """ Posts an object to the OCL API as either an update or create """

        # Determine which URL to use based on whether or not object already exists
        action_type = None
        if obj_already_exists:
            method = self.obj_def[obj_type]['update_method']
            url = obj_url
            action_type = self.ACTION_TYPE_UPDATE
        else:
            method = self.obj_def[obj_type]['create_method']
            url = new_obj_url
            action_type = self.ACTION_TYPE_NEW

        # Add query parameters (if provided)
        if query_params:
            url += '?' + urllib.urlencode(query_params)

        # Get out of here if in test mode
        if self.test_mode:
            self.log("[TEST MODE] ", method, self.api_url_root + url + '  ', json.dumps(obj))
            return

        # Create or update the object
        self.log(method, " ", self.api_url_root + url + '  ', json.dumps(obj))
        if method == 'POST':
            request_result = requests.post(self.api_url_root + url, headers=self.api_headers,
                                           data=json.dumps(obj))
        elif method == 'PUT':
            request_result = requests.put(self.api_url_root + url, headers=self.api_headers,
                                          data=json.dumps(obj))
        self.log("STATUS CODE:", request_result.status_code)
        self.log(request_result.headers)
        self.log(request_result.text)
        self.import_results.add(
            obj_url=obj_url, action_type=action_type, obj_type=obj_type, obj_repo_url=obj_repo_url,
            http_method=method, obj_owner_url=obj_owner_url, status_code=request_result.status_code,
            text=json.dumps(obj), message=request_result.text)
        request_result.raise_for_status()

    def find_nth(self, haystack, needle, n):
        """ Find nth occurrence of a substring within a string """
        start = haystack.find(needle)
        while start >= 0 and n > 1:
            start = haystack.find(needle, start+len(needle))
            n -= 1
        return start

class BulkImport:
    def __init__(self):
        pass

    def run_import(self, to_import):
        from manage.imports.bulk_import import OclFlexImporter
        from users.models import UserProfile

        input_list = []
        for line in to_import.splitlines():
            input_list.append(json.loads(line))

        profile = UserProfile.objects.get(mnemonic='root')
        importer = OclFlexImporter(input_list=input_list, api_url_root='http://api.openconceptlab.org:8000', api_token=profile.user.auth_token.key)
        importer.process()

        return importer.import_results