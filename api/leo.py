'''
Created on Jun 19, 2013

@author: judyw
'''

# import modules
from flask import  Flask, url_for, request, json, Response, jsonify
import json
import urllib2
import requests
import sunburnt
import uuid
import format_api_output 

# variables
api_url_root = 'http://staging.openconceptlab.org/rest/v1/'

# url = 'http://staging.openconceptlab.org:8983/solr/types'
# concepturl='http://staging.openconceptlab.org:8983/solr/concepts'

url = 'http://localhost:8983/solr/types'
concepturl = 'http://localhost:8983/solr/concepts'

solr_interface = sunburnt.SolrInterface(url)

# set default results to return 
defaultcount = 50

# start point for search 
startcount = 0

# format header 

app = Flask(__name__)

@app.route('/rest/v1/source/<source>/concept/<uuid>', methods=['GET', 'PUT', 'DELETE'])  
def api_conceptbysourceuuid(source, uuid):     
    if request.method == 'GET':
        concepts = []    
        solr_interface = sunburnt.SolrInterface(concepturl)
        results = solr_interface.query(uuid=str(uuid)).query(source=source).paginate(startcount, defaultcount).execute()       
        if int(len(results)) > 0:     
            for result in results:
                result = formatconcept(result)
                concepts.append(result)                                            
                js = json.dumps(concepts, indent=4)
                resp = Response(js, status=200)
                resp.headers['Link'] = 'http://openconceptlab.org'  
                resp.headers['Count'] = defaultcount
                resp.headers['StartIndex'] = startcount                       
            return resp
        else: 
            conceptId = str(source).lower() + '_' + str(uuid)
            results = solr_interface.query(conceptId=str(conceptId)).exclude(uuid=str(uuid)).paginate(startcount, defaultcount).execute()       
            if int(len(results)) > 0:     
                for result in results:
                    result = formatconcept(result)
                    concepts.append(result)                                            
                    js = json.dumps(concepts, indent=4)
                    resp = Response(js, status=200)
                    resp.headers['Link'] = 'http://openconceptlab.org'    
                    resp.headers['Count'] = defaultcount
                    resp.headers['StartIndex'] = startcount                      
                return resp
            else: return not_found() 
            
    elif request.method == 'DELETE':  
        # search if the existing  resource exists using the uuid
        solr_interface = sunburnt.SolrInterface(concepturl)
        results = solr_interface.query(uuid=str(uuid)).query(source=source).paginate(startcount, defaultcount).execute()      
        if int(len(results)) > 0:  # means the existing resource is present 
            # solr  deletes existing index
            solr_interface.delete(queries=solr_interface.Q(uuid=uuid))
            solr_interface.commit()           
            return success()        
        else: return not_found()
    elif request.method == 'PUT':  
        solr_interface = sunburnt.SolrInterface(concepturl)
        results = solr_interface.query(uuid=uuid).query(source=source).paginate(startcount, defaultcount).execute()
        if int(len(results)) > 0:
            solr_interface.delete(queries=solr_interface.Q(uuid=str(uuid)))
            solr_interface.commit() 
            postconcept = request.data  
            return putoclconcept(postconcept)
        else: return not_found()  
          
    else: return not_allowed()      

@app.route('/rest/v1/source/<source>/concept', methods=['POST'])  
def api_conceptcreate(source):
    # API methods
    if request.method == 'POST':  # must specify the source 
        poststar = json.loads(request.data)
        poststar['source'] = source
        return postconcept(poststar)
    else: return not_allowed() 
                  
@app.route('/rest/v1/concept', methods=['GET'])  
def api_concept():
    if request.method == 'GET':  # searches all sources available from different dictionaries
        # need to determine if there are any arguements passed in to the url for the GET
        requestparams = {}
        concepts = []       
        requestparams = request.args
        number_of_params_requested = int(len(requestparams))
        
        solr_interface = sunburnt.SolrInterface(concepturl)
        
        if number_of_params_requested == 0 :
            # no parameters passed in the url is just /rest/v1/concept
            results = solr_interface.query('*').paginate(startcount, defaultcount).execute()   
            if int(len(results)) > 0:   
                for result in results:
                    result = formatconcept(result)
                    concepts.append(result)                   
                    js = json.dumps(concepts, indent=4)
                    resp = Response(js, status=200)
                    resp.headers['Link'] = 'http://openconceptlab.org'  
                    resp.headers['Count'] = defaultcount
                    resp.headers['StartIndex'] = startcount
                return resp 
            else: return not_found()        
        elif number_of_params_requested == 1 :
            # http://127.0.0.1:5000/rest/v1/concept?q=malaria&count=20&startIndex=20&sortAsc=True&source=uuid
            # check if its a q, count,startindex,sortAsc or the source
            if  requestparams.has_key('q'):
                # search by a concept keyword
                name = requestparams['q']
                results = solr_interface.query(name).paginate(startcount, defaultcount).execute()    
                if int(len(results)) > 0:               
                    for result in results:
                        result = formatconcept(result)
                        concepts.append(result)            
                        js = json.dumps(concepts, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org' 
                        resp.headers['Count'] = defaultcount
                        resp.headers['StartIndex'] = startcount             
                    return resp  # ends the elif for 1 parameter for name search 
                else: return not_found()              
            elif requestparams.has_key('count'):
                # set the number of returns to return
                count = requestparams['count']                
                results = solr_interface.query('*').paginate(startcount, count).execute()              
                if int(len(results)) > 0:
                    for result in results:
                        result = formatconcept(result)
                        concepts.append(result)            
                        js = json.dumps(concepts, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                        resp.headers['Count'] = count
                        resp.headers['StartIndex'] = startcount
                    return resp  
                else: return not_found()         
            elif requestparams.has_key('startIndex'):
                # set the start index
                startIndex = requestparams['startIndex']
                results = solr_interface.query('*').paginate(startIndex, defaultcount).execute()  
                if int(len(results)) > 0:           
                    for result in results:
                        result = formatconcept(result)
                        concepts.append(result)            
                        js = json.dumps(concepts, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                        resp.headers['Count'] = defaultcount
                        resp.headers['StartIndex'] = startIndex
                    return resp 
                else: return not_found()           
            elif requestparams.has_key('source'):
                source = requestparams['source']
                results = solr_interface.query('*').query(source=source).paginate(startcount, defaultcount).execute()
                if int(len(results)) > 0: 
                    for result in results:
                        result = formatconcept(result)
                        concepts.append(result)            
                        js = json.dumps(concepts, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'  
                        resp.headers['Count'] = defaultcount
                        resp.headers['StartIndex'] = startcount            
                    return resp
                else: return not_found() 
            else:
                return invalid_arguement()  # invalid parameter passed in
        elif number_of_params_requested == 2 :
            # start with is there a query name for search
            if requestparams.has_key('q') and requestparams.has_key('source') :
                # http://127.0.0.1:5000/rest/v1/concept?source='ampath'&q=cough
                source = requestparams['source']
                name = requestparams['q']                
                results = solr_interface.query(name).query(dict=source).paginate(startcount, defaultcount).execute()                
                if int(len(results)) > 0: 
                    for result in results:
                        result = formatconcept(result)
                        concepts.append(result)            
                        js = json.dumps(concepts, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                        resp.headers['Count'] = defaultcount
                        resp.headers['StartIndex'] = startcount
                    return resp  
                else: return not_found()           
            elif requestparams.has_key('q') and requestparams.has_key('startIndex') :  # has a bug
                name = requestparams['q']
                startIndex = requestparams['startIndex']
                results = solr_interface.query(name).paginate(startIndex, defaultcount).execute()   
                if int(len(results)) > 0: 
                    for result in results:
                        result = formatconcept(result)
                        concepts.append(result)            
                        js = json.dumps(concepts, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                        resp.headers['Count'] = defaultcount
                        resp.headers['StartIndex'] = startIndex
                    return resp  
                else: return not_found()           
            elif requestparams.has_key('q') and requestparams.has_key('count'):
                # search by a concept keyword
                name = requestparams['q']
                count = requestparams['count']  
                results = solr_interface.query(name).paginate(startcount, count).execute()                  
                if int(len(results)) > 0: 
                    for result in results:
                        result = formatconcept(result)
                        concepts.append(result)            
                        js = json.dumps(concepts, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                        resp.headers['Count'] = count
                        resp.headers['StartIndex'] = startcount
                    return resp  
                else: return not_found()           
            else:  # last one
                return invalid_arguement()
            # end of 2 params
        else: 
            return invalid_arguement()

    else: return not_allowed()

# changed the structure of the API so this method is not helpful
@app.route('/rest/v1/concept/<uuid>', methods=['GET', 'PUT', 'DELETE'])  
def api_conceptbyuuid(uuid):     
    if request.method == 'GET':
        solr_interface = sunburnt.SolrInterface(concepturl)
        concepts = []        
        # implement exception to handle and validate the uuid
        results = solr_interface.query(uuid=uuid).paginate(startcount, defaultcount).execute()
        if int(len(results)) > 0:     
            for result in results:
                result = formatconcept(result)
                concepts.append(result)                                            
                js = json.dumps(concepts, indent=4)
                resp = Response(js, status=200)
                resp.headers['Link'] = 'http://openconceptlab.org'
            return resp
        else: return not_found() 
    elif request.method == 'DELETE':  
        # search if the existing  resource exists using the uuid
        solr_interface = sunburnt.SolrInterface(concepturl)
        results = solr_interface.query(uuid=uuid).paginate(startcount, defaultcount).execute()
        if int(len(results)) > 0:  # means the existing resource is present 
            solr_interface.delete(queries=solr_interface.Q(uuid=uuid))
            solr_interface.commit()           
            return success()        
        else: return not_found()     
    elif request.method == 'PUT':  
        # search if the existing  resource exists using the uuid
        solr_interface = sunburnt.SolrInterface(concepturl)
        results = solr_interface.query(uuid=uuid).paginate(startcount, defaultcount).execute()
        data = request.data
        return postocl(data)
    else: return not_allowed()

@app.route('/rest/v1/datatype', methods=['GET', 'POST'])  
def api_datatype():
    if request.method == 'GET':  # searches all datatypes available from different dictionaries        
        requestparams = {}
        datatype = []        
        requestparams = request.args
        number_of_params_requested = int(len(requestparams))
                
        if number_of_params_requested == 0 :
            # no parameters passed in the url is just /rest/v1/classes
            results = solr_interface.query('*').query(type='datatype').paginate(startcount, defaultcount).execute()
            if int(len(results)) > 0:
                for result in results:
                    result = formatdatatype(result)
                    datatype.append(result)                                            
                    js = json.dumps(datatype, indent=4)
                    resp = Response(js, status=200)
                    resp.headers['Link'] = 'http://openconceptlab.org'             
                return resp
            else: return not_found()
        elif number_of_params_requested == 1 :
            # http://127.0.0.1:5000/rest/v1/datatypes?q=number
            # /datatypes?source=snomed        
            # /datatypes?q=blood&count=15&startIndex=30                                  
            if  requestparams.has_key('q'):
                # search by a datatypes keyword or name
                name = requestparams['q']
                results = solr_interface.query(name).query(type='datatype').paginate(startcount, defaultcount).execute()
                if int(len(results)) > 0:
                    for result in results:
                        result = formatdatatype(result)
                        datatype.append(result)                                            
                        js = json.dumps(datatype, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'                    
                    return resp
                else: return not_found()                        
            elif requestparams.has_key('source'):
                source = requestparams['source']
                results = solr_interface.query(dict=source).query(type='datatype').paginate(startcount, defaultcount).execute()   
                if int(len(results)) > 0:
                    for result in results:
                        result = formatdatatype(result)
                        datatype.append(result)                                            
                        js = json.dumps(datatype, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'             
                    return resp
                else: return not_found()
            elif requestparams.has_key('count'):
                # set the number of returns to return
                count = requestparams['count']                
                results = solr_interface.query('*').query(type='datatype').paginate(startcount, count).execute()
                if int(len(results)) > 0:
                    for result in results:
                        result = formatdatatype(result)
                        datatype.append(result)                                            
                        js = json.dumps(datatype, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'              
                    return resp
                else: return not_found()
            elif requestparams.has_key('startIndex'):
                # set the start index
                startIndex = requestparams['startIndex']
                results = solr_interface.query('*').query(type='datatype').paginate(startIndex, defaultcount).execute()
                if int(len(results)) > 0:
                    for result in results:
                        result = formatdatatype(result)
                        datatype.append(result)                                            
                        js = json.dumps(datatype, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'              
                    return resp
                else: return not_found()
        
        elif number_of_params_requested == 2 :  # implement count and startIndex               
                
            if  requestparams.has_key('count') and requestparams.has_key('startIndex'):
                count = requestparams['count']
                startIndex = requestparams['startIndex']
                results = solr_interface.query('*').query(type='datatype').paginate(startIndex, count).execute()

                if int(len(results)) > 0:
                    for result in results:
                        result = formatsource(result)
                        source.append(result)                                            
                        js = json.dumps(source, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                        resp.headers['Count'] = count
                        resp.headers['StartIndex'] = startIndex
                    return resp
                else: return not_found()               
                
        elif number_of_params_requested == 3 :
            # start with is there a query name for search
            if requestparams.has_key('q') and requestparams.has_key('count') and requestparams.has_key('startIndex') :
                count = requestparams['count']
                name = requestparams['q']
                startIndex = requestparams['startIndex']
                results = solr_interface.query(name).query(type='datatype').paginate(startIndex, count).execute()
                if int(len(results)) > 0:
                    for result in results:
                        result = formatdatatype(result)
                        datatype.append(result)                                            
                        js = json.dumps(datatype, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'             
                    return resp
                else: return not_found()
            else:  # closes the end of the three parameters
                return not_found()
        else:  # last one for GET
            return not_found()
            
    elif request.method == 'POST':  # must specify the source 
        data = json.load(request.data)
        solr_interface.add(data)
        solr_interface.commit()     
    # end these URL calls
    else: return not_allowed()
    
@app.route('/rest/v1/datatype/<uuid>', methods=['GET', 'PUT', 'DELETE'])  
def api_datatypebyuuid(uuid):     
    if request.method == 'GET':
        datatype = []
        results = solr_interface.query(uuid=uuid).query(type='datatype').paginate(startcount, defaultcount).execute()       
        if int(len(results)) > 0:     
            for result in results:
                result = formatdatatype(result)                    
                datatype.append(result)                                            
                js = json.dumps(datatype, indent=4)
                resp = Response(js, status=200)
                resp.headers['Link'] = 'http://openconceptlab.org'                         
            return resp
        else: return not_found()
    elif request.method == 'PUT':  # not sure if we can do this method
        # search if the existing  resource exists using the uuid
        results = solr_interface.query(uuid=uuid).query(type='datatype').paginate(startcount, defaultcount).execute()
       
        if int(len(results)) > 0:  # means the existing resource is present 
            postdata = json.loads(request.data)
            return putocl(postdata)
        else: not_found()
    elif request.method == 'DELETE':  # must specify the source
        # search if the existing  resource exists using the uuid
        results = solr_interface.query(uuid=uuid).query(type='datatype').paginate(startcount, defaultcount).execute()       
        if int(len(results)) > 0:  # means the existing resource is present                    
            # solr  deletes existing index
            solr_interface.delete(queries=solr_interface.Q(uuid=uuid))
            solr_interface.commit()           
            return success()       
        else: return not_found()   
    else: return not_allowed()  

@app.route('/rest/v1/collection', methods=['GET', 'POST'])  
def api_collection():
    if request.method == 'GET':  # searches all classes available from different dictionaries  
        
        requestparams = {}
        collections = []       
        requestparams = request.args
        number_of_params_requested = int(len(requestparams))
                
        if number_of_params_requested == 0 :
            # no parameters passed in the url is just /rest/v1/collections
            results = solr_interface.query('*').query(type='collection').paginate(startcount, defaultcount).execute()

            if int(len(results)) > 0:
                for result in results:
                    result = format_api_output.formatcollection(result)
                    collections.append(result)                   
                    js = json.dumps(collections, indent=4)
                    resp = Response(js, status=200)
                    resp.headers['Link'] = 'http://openconceptlab.org'               
                return resp
            else: return not_found()
        elif number_of_params_requested == 1 :
            # http://127.0.0.1:5000/rest/v1/collection?q=antenatal
            # /collections?owner=johndoe
            # collections?concept=1234-5678-9012-3456 search by concept  
            # /collections?q=blood&count=15&startIndex=30          
            # check if its a q, count,startindex,sortAsc or the source
                       
            if  requestparams.has_key('q'):
                # search by a collection keyword
                name = requestparams['q']
                results = solr_interface.query(name=name).query(type='collection').paginate(startcount, defaultcount).execute()   
                if int(len(results)) > 0:
                    for result in results:
                        result = format_api_output.formatcollection(result)
                        collections.append(result)                   
                        js = json.dumps(collections, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                    return resp  # ends the elif for 1 parameter for name search
                else:
                    return not_found()
            elif requestparams.has_key('owner'):
                # search collection by owner name
                owner = requestparams['owner']
                results = solr_interface.query(owner=owner).query(type='collection').paginate(startcount, defaultcount).execute()   
                
                if int(len(results)) > 0:
                    for result in results:
                        result = format_api_output.formatcollection(result)
                        collections.append(result)                   
                        js = json.dumps(collections, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                    return resp  # ends the elif for 1 parameter for name search
                else: 
                    return not_found()
            # search collections with specific concepts
            elif requestparams.has_key('concept'):
                                
                # search collection by concept UUID ..This is  the  concept UUID assigned by OCL
                concept = requestparams['concept']
                # search for all collections in the index
                results = solr_interface.query('*').query(type='collection').paginate(startcount, defaultcount).execute()   
                if int(len(results)) > 0:
                    for result in results:
                        if 'concept_id' in result.keys(): concept_id = str(result['concept_id']).split('|')
                        if concept in concept_id:  # the concept is in that list                             
                            result = format_api_output.formatcollection(result)
                            collections.append(result)
                        # else: return not_found()
                    
                    if int(len(collections)) > 0 :                        
                        # try return the resp now
                        js = json.dumps(collections, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'                        
                        return resp
                    else: return not_found()

                else: return not_found()
                                                                     
            elif requestparams.has_key('count'):
                # set the number of returns to return
                count = requestparams['count']                
                results = solr_interface.query('*').query(type='collection').paginate(startcount, count).execute()

                if int(len(results)) > 0:
                    for result in results:
                        result = format_api_output.formatcollection(result)
                        collections.append(result)                   
                        js = json.dumps(collections, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'              
                    return resp
                else:
                    return not_found()
            
            elif requestparams.has_key('startIndex'):
                # set the start index
                startIndex = requestparams['startIndex']
                results = solr_interface.query('*').query(type='collection').paginate(startIndex, defaultcount).execute()
                
                if int(len(results)) > 0:
                    for result in results:
                        result = format_api_output.formatcollection(result)
                        collections.append(result)                   
                        js = json.dumps(collections, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                    return resp
                else:
                    return not_found()
            else:
                return invalid_arguement()  # may need to test this
        elif number_of_params_requested == 2 :
            if requestparams.has_key('q') and requestparams.has_key('startIndex') :  # has a bug
                name = requestparams['q']
                startIndex = requestparams['startIndex']
                results = solr_interface.query(name).paginate(startIndex, defaultcount).execute()   
                if int(len(results)) > 0: 
                    for result in results:
                        result = format_api_output.formatcollection(result)
                        collections.append(result)            
                        js = json.dumps(collections, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                        resp.headers['Count'] = defaultcount
                        resp.headers['StartIndex'] = startIndex
                    return resp  
                else: return not_found()           
            elif requestparams.has_key('q') and requestparams.has_key('count'):
                # search by a concept keyword
                name = requestparams['q']
                count = requestparams['count']  
                results = solr_interface.query(name).paginate(startcount, count).execute()                  
                if int(len(results)) > 0: 
                    for result in results:
                        result = format_api_output.formatcollection(result)
                        collections.append(result)            
                        js = json.dumps(collections, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                        resp.headers['Count'] = count
                        resp.headers['StartIndex'] = startcount
                    return resp  
                else: return not_found()   
            else : return invalid_arguement()  # invalid arguement passed in         
                                    
        elif number_of_params_requested == 3 :
            # start with is there a query name for search
            if requestparams.has_key('q') and requestparams.has_key('count') and requestparams.has_key('startIndex') :
                count = requestparams['count']
                name = requestparams['q']
                startIndex = requestparams['startIndex']
                results = solr_interface.query(name).query(type='collection').paginate(startIndex, count).execute()
                if int(len(results)) > 0:
                    for result in results:
                        result = format_api_output.formatcollection(result)
                        collections.append(result)                   
                        js = json.dumps(collections, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                    return resp
                else:
                    return not_found()
            else:  # closes the end of the three parameters
                return not_found()
             
        else:  # last one for GET
            return not_found()
            
    elif request.method == 'POST':  
        poststar = request.data 
        return postmycollection(poststar)    
    # end these URL calls
    else: return not_allowed()

def generateuuid():
    myuuid = uuid.uuid1()
    return myuuid

def postcollection(result):
        
    if result.has_key('full_id'):
        result['full_id'] = result['full_id']
    else:
        myuuid = generateuuid()
        full_id = str('COLLECTION') + '_' + str(myuuid)
        result['full_id'] = full_id
    
    if '__type__' not in result.keys():
        result['__type__'] = 'OclCollection'
        
    if 'url' not in result.keys():
        url = str("http://www.openconceptlab.org/rest/v1/collection/") + str(myuuid)
        result['url'] = url
        
    if 'uuid' not in result.keys():
        result['uuid'] = myuuid
        
    if result.has_key('sharedUsers'):
        user = result['sharedUsers'][0]
        result['username'] = user['username']
        result['access'] = user['access']
        del result['sharedUsers']
        
    if result.has_key('names'):
        name = result['names'][0]
        result['name'] = name['name']
        result['preferred'] = name['preferred']
        result['locale'] = name['locale']
        del result['names']        
    
    if result.has_key('properties'):
        props = {}
        props = result['properties']
        result['openmrsResourceVersion'] = props['openmrsResourceVersion']
        result['hl7Code'] = props['hl7Code']
        del result['properties']
    
    
    if result.has_key('descriptions'):
        desc = result['descriptions'][0]
        result['descriptionLocale'] = desc['locale']
        result['descriptionPreferred'] = desc['preferred']
        # result['description'] = desc['description']
        del result['descriptions']
        
    if result.has_key('concepts'):
        concepts = result['concepts']
        c_url = []
        c_uuid = []
        for c in concepts:
            # create a list then join all concepts 
            c_url.append(c['url'])
            c_uuid.append(c['uuid'])
        url = '|'.join(c_url)
        uuid = '|'.join(c_uuid)            
        result['concept_uuid'] = uuid
        result['concept_url'] = url
        del result['concepts']
    
    if result.has_key('sources'):
        so = result['sources'][0]
        result['dict'] = so
        del result['sources']
        
    return result
        
@app.route('/rest/v1/collection/<uuid>', methods=['GET', 'PUT', 'DELETE'])  
def api_collectionbyuuid(uuid):     
    if request.method == 'GET':
        collections = []        
        # implement exception to handle and validate the uuid 8-4-4-4-12 hexadecimal digits.
        results = solr_interface.query(uuid=uuid).query(type='collection').paginate(startcount, defaultcount).execute()
       
        if int(len(results)) > 0:     
            for result in results:
                result = formatcollection(result)                    
                collections.append(result)                                            
                js = json.dumps(collections, indent=4)
                resp = Response(js, status=200)
                resp.headers['Link'] = 'http://openconceptlab.org'
                         
            return resp
        else: return not_found()
    elif request.method == 'PUT':  # not sure if we can do this method
        # search if the existing  resource exists using the uuid
        results = solr_interface.query(uuid=uuid).query(type='collection').paginate(startcount, defaultcount).execute()
       
        if int(len(results)) > 0:  # means the existing resource is present 
            document = json.loads(request.data)
            document = postcollection(document)
            try:
                solr_interface.add(document)
                solr_interface.commit()                    
                return success()
            except:
                return invalidput()
        else: not_found()
    elif request.method == 'DELETE':  # must specify the source
        # search if the existing  resource exists using the uuid
        results = solr_interface.query(uuid=uuid).query(type='collection').paginate(startcount, defaultcount).execute()
        if int(len(results)) > 0:  # means the existing resource is present 
            solr_interface.delete(queries=solr_interface.Q(uuid=uuid))
            solr_interface.commit()           
            return success()        
        else: return not_found() 

@app.route('/rest/v1/class', methods=['GET', 'POST'])  
def api_class():
    if request.method == 'GET':  # searches all classes available from different dictionaries
        
        requestparams = {}
        classes = []        

        requestparams = request.args
        number_of_params_requested = int(len(requestparams))
                
        if number_of_params_requested == 0 :
            # no parameters passed in the url is just /rest/v1/classes
            results = solr_interface.query('*').query(type='class').paginate(startcount, defaultcount).execute()

            if int(len(results)) > 0:
                for result in results:
                    # format object to final specifications                                       
                    result = formatclass(result)       
                    classes.append(result)                                            
                    js = json.dumps(classes, indent=4)
                    resp = Response(js, status=200)
                    resp.headers['Link'] = 'http://openconceptlab.org'             
                return resp
            else: return not_found()
        elif number_of_params_requested == 1 :
            # http://127.0.0.1:5000/rest/v1/classes?q=diagnosis
            # /classes?source=snomed        
            # /classes?q=blood&count=15&startIndex=30                      
            
            if  requestparams.has_key('q'):
                # search by a class keyword or name
                name = requestparams['q']
                results = solr_interface.query(name).query(type='class').paginate(startcount, defaultcount).execute()

                if int(len(results)) > 0:
                    for result in results:
                        result = formatclass(result) 
                        classes.append(result)                                            
                        js = json.dumps(classes, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'             
                    return resp
                else: return not_found()
                        
            elif requestparams.has_key('source'):
                # search classes by owner name
                source = requestparams['source']
                results = solr_interface.query(dict=source).query(type='class').paginate(startcount, defaultcount).execute()   
                
                if int(len(results)) > 0:
                    for result in results:
                        result = formatclass(result) 
                        classes.append(result)                                            
                        js = json.dumps(classes, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'             
                    return resp
                else: return not_found()
                                                                           
            elif requestparams.has_key('count'):
                # set the number of returns to return
                count = requestparams['count']                
                results = solr_interface.query('*').query(type='class').paginate(startcount, count).execute()

                if int(len(results)) > 0:
                    for result in results:
                        result = formatclass(result) 
                        classes.append(result)                                            
                        js = json.dumps(classes, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'             
                    return resp
                else: return not_found()
            
            elif requestparams.has_key('startIndex'):
                # set the start index
                startIndex = requestparams['startIndex']
                results = solr_interface.query('*').query(type='class').paginate(startIndex, defaultcount).execute()
                
                if int(len(results)) > 0:
                    for result in results:
                        result = formatclass(result) 
                        classes.append(result)                                            
                        js = json.dumps(classes, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
             
                    return resp
                else: return not_found()
                                    
        elif number_of_params_requested == 3 :
            # start with is there a query name for search
            if requestparams.has_key('q') and requestparams.has_key('count') and requestparams.has_key('startIndex') :
                count = requestparams['count']
                name = requestparams['q']
                startIndex = requestparams['startIndex']
                
                results = solr_interface.query(name).query(type='class').paginate(startIndex, count).execute()
                
                if int(len(results)) > 0:
                    for result in results:
                        result = formatclass(result) 
                        classes.append(result)                                            
                        js = json.dumps(classes, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'             
                    return resp
                else: return not_found()
            else:  # closes the end of the three parameters
                return not_found()
             
        else:  # last one for GET
            return not_found()
            
    elif request.method == 'POST':  # must specify the source 
        poststar = request.data 
        return postocl(poststar)    
    # end these URL calls
    else: return not_allowed()
              
def postocl(post):            
    document = json.loads(post)  
    document = postcollection(document)
    solr_interface.add(document)
    solr_interface.commit()
    return created()


def postmycollection(post):            
    document = json.loads(post)  
    document = validatecollectionpostdata(document)
    # check at least a name is present 
    if 'names' not in document.keys():
        return 'A collection must have a name'
    else:
        document = formatpostcollection(document)
        solr_interface.add(document)
        solr_interface.commit()
        url = document['url']
        return created(url)
    
def postsource(post):            
    document = json.loads(post)  
    # check at least a name is present 
    if 'names' not in document.keys():
        return 'A source must have a name'
    else:
        document = formatpostsource(document)
        solr_interface.add(document)
        solr_interface.commit()
        url = document['url']
        return created(url)
    
def postconcept(document):            
    # check at least a name is present 
    if 'names' not in document.keys():
        return 'A concept must have a name'
    else:
        document = formatpostconcept(document)
        solr_interface = sunburnt.SolrInterface(concepturl)
        solr_interface.add(document)
        solr_interface.commit()
        url = document['url']
        return created(url)

def formatpostcollection(result):
    if result.has_key('full_id'):
        result['full_id'] = result['full_id']
    else:
        myuuid = generateuuid()
        full_id = str('COLLECTION') + '_' + str(myuuid)
        result['full_id'] = full_id
    
    if '__type__' not in result.keys():
        result['__type__'] = 'OclCollection'
        
    if 'url' not in result.keys():
        url = str("http://www.openconceptlab.org/rest/v1/collection/") + str(myuuid)
        result['url'] = url
        
    if 'uuid' not in result.keys():
        result['uuid'] = myuuid
        
    if result.has_key('sharedUsers'):
        user = result['sharedUsers'][0]
        result['username'] = user['username']
        result['access'] = user['access']
        del result['sharedUsers']
        
    if result.has_key('names'):
        name = result['names'][0]
        result['name'] = name['name']
        result['preferred'] = name['preferred']
        result['locale'] = name['locale']
        del result['names']        
    
    if result.has_key('properties'):
        props = {}
        props = result['properties']
        result['openmrsResourceVersion'] = props['openmrsResourceVersion']
        result['hl7Code'] = props['hl7Code']
        del result['properties']
    
    
    if result.has_key('descriptions'):
        desc = result['descriptions'][0]
        result['descriptionLocale'] = desc['locale']
        result['descriptionPreferred'] = desc['preferred']
        # result['description'] = desc['description']
        del result['descriptions']
        
    if result.has_key('concepts'):
        concepts = result['concepts']
        c_url = []
        c_uuid = []
        for c in concepts:
            # create a list then join all concepts 
            c_url.append(c['url'])
            c_uuid.append(c['uuid'])
        url = '|'.join(c_url)
        uuid = '|'.join(c_uuid)            
        result['concept_uuid'] = uuid
        result['concept_url'] = url
        del result['concepts']
    
    if result.has_key('sources'):
        so = result['sources'][0]
        result['dict'] = so
        del result['sources']
        
    return result
    
def formatpostconcept(result):
    myuuid = generateuuid()
    if result.has_key('full_id'):
        result['full_id'] = result['full_id']
    else:
        full_id = str('CONCEPT') + '_' + str(myuuid)
        result['full_id'] = full_id
    
    if '__type__' not in result.keys():
        result['__type__'] = 'OclCollection'
        
    if 'url' not in result.keys():
        source = str(result['source'])
        url = str("http://www.openconceptlab.org/rest/v1/") + source + str("/concept/") + str(myuuid)
        result['url'] = url
        
    if 'uuid' not in result.keys():
        result['uuid'] = myuuid
        
    if result.has_key('names'):
        name = result['names'][0]
        result['name'] = name['name']
        result['nameuuid'] = name['uuid']
        result['namelocale'] = name['locale']
        del result['names']        
    
    if result.has_key('properties'):del result['properties']
    
    if result.has_key('descriptions'):
        desc = result['descriptions'][0]
        result['localeDesc'] = desc['locale']
        result['preferredDesc'] = desc['preferred']
        result['description'] = desc['description']
        result['DescUuid'] = desc['uuid']
        del result['descriptions']
        
    if result.has_key('mappings'):
        mymap = result['mappings'][0]
        result['mappingUuid'] = mymap['uuid']
        result['conceptMapType'] = mymap['conceptMapType']
        result['mappingDisplay'] = mymap['display']
        del result['mappings']
        
    if result.has_key('auditInfo'):
        audit = {}
        audit = result['auditInfo']
        result['dateChanged'] = audit['dateChanged']
        result['changedby'] = audit['changedBy']
        result['creator'] = audit['creator']
        result['dateCreated'] = audit['dateCreated']
        del result['auditInfo']
    if result.has_key('collections'): del result['collections']
    
    if result.has_key('setMembers'):
        myset = result['setMembers'][0]  # may prefer to loop throu this array
        result['setParent'] = myset['setParent']
        del result['setMembers']
        
    if result.has_key('answers'):
        ans = result['answers'][0]  # may prefer to loop throu this array
        result['answerDisplay'] = ans['display']
        del result['answers']
        
    return result

def formatpostsource(result):
    
    myuuid = generateuuid()
    if result.has_key('full_id'):
        result['full_id'] = result['full_id']
    else:
        full_id = str('SOURCE') + '_' + str(myuuid)
        result['full_id'] = full_id
        
    if 'type' not in result.keys():
        result['type'] = 'source'
        
    if '__type__' not in result.keys():
        result['__type__'] = 'OclSource'
        
    if 'url' not in result.keys():
        url = str("http://www.openconceptlab.org/rest/v1/source/") + str(myuuid)
        result['url'] = url
        
    if 'uuid' not in result.keys():
        result['uuid'] = myuuid
        
    if result.has_key('sharedUsers'):
        user = result['sharedUsers'][0]
        result['username'] = user['username']
        result['access'] = user['access']
        del result['sharedUsers']
        
    if result.has_key('names'):
        name = result['names'][0]
        result['name'] = name['name']
        result['preferred'] = name['preferred']
        result['locale'] = name['locale']
        del result['names']
           
    if result.has_key('properties'):
        props = {}
        props = result['properties']
        result['versionStatus'] = props['versionStatus']
        del result['properties']
       
    if result.has_key('descriptions'):
        desc = {}
        desc = result['descriptions']
        result['descriptionLocale'] = desc['locale']
        result['descriptionPreferred'] = desc['preferred']
        result['description'] = desc['description']
        del result['descriptions']
        
    return result

def putocl(results):
    if int(len(results)) > 0:  # means the existing resource is present 
        postdata = json.loads(request.data)
        try:
            solr_interface.add(postdata)
            solr_interface.commit()
            return success()
        except:
            return invalidput()
    else: not_found()
    
def putoclconcept(post):
    document = json.loads(post)
    if 'uuid' not in document.keys():
        return 'A source must have a uuid to be updated'
    else:
        document = formatpostconcept(document)
        solr_interface = sunburnt.SolrInterface(concepturl)
        solr_interface.add(document)
        solr_interface.commit()
        url = document['url']
        return success(url)  
    
def putoclsource(post):    
    document = json.loads(post)  
        # check at least a name is present 
    if 'uuid' not in document.keys():
        return 'A source must have a uuid to be updated'
    else:
        document = formatpostsource(document)
        solr_interface.add(document)
        solr_interface.commit()
        url = document['url']
        return success(url)    
        
def validatesourcepostdata(result):
    if '__type__' not in result.keys():
        result['__type__'] = 'OclSource'
    if 'type' not in result.keys():
        result['type'] = 'source'
    return result

        
def validatecollectionpostdata(result):
    if '__type__' not in result.keys():
        result['__type__'] = 'OclCollection'
    if 'type' not in result.keys():
        result['type'] = 'collection'
    return result

@app.route('/rest/v1/class/<uuid>', methods=['GET', 'PUT', 'DELETE'])  
def api_classbyuuid(uuid):     
    if request.method == 'GET':

        classes = []
        results = solr_interface.query(uuid=uuid).query(type='class').paginate(startcount, defaultcount).execute()
       
        if int(len(results)) > 0:     
            for result in results:
                result = formatclass(result)                     
                classes.append(result)                                            
                js = json.dumps(classes, indent=4)
                resp = Response(js, status=200)
                resp.headers['Link'] = 'http://openconceptlab.org'
                         
            return resp
        else: return not_found()
    elif request.method == 'PUT':  # not sure if we can do this method
        # search if the existing  resource exists using the uuid
        results = solr_interface.query(uuid=uuid).query(type='class').paginate(startcount, defaultcount).execute()      
        if int(len(results)) > 0:  # means the existing resource is present 
            document = json.loads(request.data)            
            document = postcollection(document)
            try:
                solr_interface.add(document)
                solr_interface.commit()                    
                return success()
            except:
                return invalidput()
            else: not_found()
        else: not_found()
    elif request.method == 'DELETE':  # must specify the source
        # search if the existing  resource exists using the uuid
        results = solr_interface.query(uuid=uuid).query(type='class').paginate(startcount, defaultcount).execute()
       
        if int(len(results)) > 0:  # means the existing resource is present 
                    
            # solr  deletes existing index
            solr_interface.delete(queries=solr_interface.Q(uuid=uuid))
            solr_interface.commit()           
            return success()
        
        else: return not_found() 
 
@app.route('/rest/v1/maptype', methods=['GET', 'POST'])  
def api_maptype():
    if request.method == 'GET':  # searches all classes available from different dictionaries
        
        requestparams = {}
        maptype = []        

        requestparams = request.args
        number_of_params_requested = int(len(requestparams))
                
        if number_of_params_requested == 0 :
            # no parameters passed in the url is just /rest/v1/classes
            results = solr_interface.query('*').query(type='maptype').paginate(startcount, defaultcount).execute()

            if int(len(results)) > 0:
                for result in results:
                    result = mapdatatype(result)
                    maptype.append(result)                                            
                    js = json.dumps(maptype, indent=4)
                    resp = Response(js, status=200)
                    resp.headers['Link'] = 'http://openconceptlab.org'            
                return resp
            else: return not_found()
        elif number_of_params_requested == 1 :
            # http://127.0.0.1:5000/rest/v1/maptype?q=diagnosis
            # /maptype?source=snomed        
            # /maptype?q=sameas&count=15&startIndex=30                      
            
            if  requestparams.has_key('q'):
                # search by a class keyword or name
                name = requestparams['q']
                results = solr_interface.query(name).query(type='maptype').paginate(startcount, defaultcount).execute()

                if int(len(results)) > 0:
                    for result in results:
                        result = mapdatatype(result)
                        maptype.append(result)                                            
                        js = json.dumps(maptype, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                    return resp
                else: return not_found()
                        
            elif requestparams.has_key('source'):
                # search classes by owner name
                source = requestparams['source']
                results = solr_interface.query(dict=source).query(type='maptype').paginate(startcount, defaultcount).execute()   
                
                if int(len(results)) > 0:
                    for result in results:   
                        result = mapdatatype(result)                 
                        maptype.append(result)                                            
                        js = json.dumps(maptype, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'           
                    return resp
                else: return not_found()                                                                           
            elif requestparams.has_key('count'):
                # set the number of returns to return
                count = requestparams['count']                
                results = solr_interface.query('*').query(type='maptype').paginate(startcount, count).execute()

                if int(len(results)) > 0:
                    for result in results: 
                        result = mapdatatype(result)                
                        maptype.append(result)                                            
                        js = json.dumps(maptype, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'          
                    return resp
                else: return not_found()
            
            elif requestparams.has_key('startIndex'):
                # set the start index
                startIndex = requestparams['startIndex']
                results = solr_interface.query('*').query(type='maptype').paginate(startIndex, defaultcount).execute()
                
                if int(len(results)) > 0:
                    for result in results:
                        result = mapdatatype(result)
                        maptype.append(result)                                            
                        js = json.dumps(maptype, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'       
                    return resp
                else: return not_found()
                                    
        elif number_of_params_requested == 3 :
            # start with is there a query name for search
            if requestparams.has_key('q') and requestparams.has_key('count') and requestparams.has_key('startIndex') :
                count = requestparams['count']
                name = requestparams['q']
                startIndex = requestparams['startIndex']
                
                results = solr_interface.query(name).query(type='maptype').paginate(startIndex, count).execute()
                
                if int(len(results)) > 0:
                    for result in results:
                        result = mapdatatype(result)
                        maptype.append(result)                                            
                        js = json.dumps(maptype, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'         
                    return resp
                else: return not_found()
            else:  # closes the end of the three parameters
                return not_found()
             
        else:  # last one for GET
            return not_found()
            
    elif request.method == 'POST':  # must specify the source 
        poststar = json.loads(request.data) 
        return postocl(poststar)
    
    # end these URL calls
    else: return not_allowed()
    
@app.route('/rest/v1/maptype/<uuid>', methods=['GET', 'PUT', 'DELETE'])  
def api_maptypebyuuid(uuid):     
    if request.method == 'GET':

        maptype = []
        results = solr_interface.query(uuid=uuid).query(type='maptype').paginate(startcount, defaultcount).execute()
       
        if int(len(results)) > 0:     
            for result in results:
                result = mapdatatype(result)                    
                maptype.append(result)                                            
                js = json.dumps(maptype, indent=4)
                resp = Response(js, status=200)
                resp.headers['Link'] = 'http://openconceptlab.org'                        
            return resp
        else: return not_found()
    elif request.method == 'PUT':  # not sure if we can do this method
        # search if the existing  resource exists using the uuid
        results = solr_interface.query(uuid=uuid).query(type='maptype').paginate(startcount, defaultcount).execute()
        return putocl(results)
    elif request.method == 'DELETE':  # must specify the source
        # search if the existing  resource exists using the uuid
        results = solr_interface.query(uuid=uuid).query(type='maptype').paginate(startcount, defaultcount).execute()
       
        if int(len(results)) > 0:  # means the existing resource is present 
                    
            # solr  deletes existing index
            solr_interface.delete(queries=solr_interface.Q(uuid=uuid))
            solr_interface.commit()           
            return success()
        
        else: return not_found()   
                 
@app.route('/rest/v1/source', methods=['GET', 'POST'])  
def api_source():
    if request.method == 'GET':  # searches all classes available from different dictionaries
        
        requestparams = {}
        source = []        

        requestparams = request.args
        number_of_params_requested = int(len(requestparams))
                
        if number_of_params_requested == 0 :
            # no parameters passed in the url is just /rest/v1/classes
            results = solr_interface.query('*').query(type='source').paginate(startcount, defaultcount).execute()

            if int(len(results)) > 0:
                for result in results:
                    result = format_api_output.formatsource(result)
                    source.append(result)                                            
                    js = json.dumps(source, indent=4)
                    resp = Response(js, status=200)
                    resp.headers['Link'] = 'http://openconceptlab.org'
                    resp.headers['Count'] = defaultcount
                    resp.headers['StartIndex'] = startcount
                return resp
            else: return not_found()
        elif number_of_params_requested == 1 :

            # http://127.0.0.1:5000/rest/v1/source?q=icd
            # /source?q=sameas&count=15&startIndex=30                      
            
            if  requestparams.has_key('q'):
                # search by a class keyword or name
                name = requestparams['q']
                results = solr_interface.query(display=name).query(type='source').paginate(startcount, defaultcount).execute()
                
                if int(len(results)) > 0:
                    for result in results:
                        result = format_api_output.formatsource(result)
                        source.append(result)                                            
                        js = json.dumps(source, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                        resp.headers['Count'] = defaultcount
                        resp.headers['StartIndex'] = startcount
                    return resp
                else: return not_found()
                                                                           
            elif requestparams.has_key('count'):
                # set the number of returns to return
                count = requestparams['count']                
                results = solr_interface.query('*').query(type='source').paginate(startcount, count).execute()

                if int(len(results)) > 0:
                    for result in results:   
                        result = format_api_output.formatsource(result)             
                        source.append(result)                                            
                        js = json.dumps(source, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'     
                        resp.headers['Count'] = count
                        resp.headers['StartIndex'] = startcount    
                    return resp
                else: return not_found()
            
            elif requestparams.has_key('startIndex'):
                # set the start index
                startIndex = requestparams['startIndex']
                results = solr_interface.query('*').query(type='source').paginate(startIndex, defaultcount).execute()
                
                if int(len(results)) > 0:
                    for result in results:
                        result = format_api_output.formatsource(result)
                        source.append(result)                                            
                        js = json.dumps(source, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'    
                        resp.headers['Count'] = defaultcount
                        resp.headers['StartIndex'] = startIndex
                    return resp
                else: return not_found()               
        elif number_of_params_requested == 2 :  # implement count and startIndex               
            if  requestparams.has_key('q') and requestparams.has_key('count'):
                name = requestparams['q']
                count = requestparams['count']
                results = solr_interface.query(display=name).query(type='source').paginate(startcount, count).execute()

                if int(len(results)) > 0:
                    for result in results:
                        result = format_api_output.formatsource(result)
                        source.append(result)                                            
                        js = json.dumps(source, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                        resp.headers['Count'] = count
                        resp.headers['StartIndex'] = startcount
                    return resp
                else: return not_found()
                
            if  requestparams.has_key('q') and requestparams.has_key('startIndex'):
                name = requestparams['q']
                startIndex = requestparams['startIndex']
                results = solr_interface.query(display=name).query(type='source').paginate(startIndex, defaultcount).execute()

                if int(len(results)) > 0:
                    for result in results:
                        result = format_api_output.formatsource(result)
                        source.append(result)                                            
                        js = json.dumps(source, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                        resp.headers['Count'] = defaultcount
                        resp.headers['StartIndex'] = startIndex
                    return resp
                else: return not_found()                                          
                                    
        elif number_of_params_requested == 3 :
            # start with is there a query name for search
            if requestparams.has_key('q') and requestparams.has_key('count') and requestparams.has_key('startIndex') :
                count = requestparams['count']
                name = requestparams['q']
                startIndex = requestparams['startIndex']
                
                results = solr_interface.query(display=name).query(type='source').paginate(startIndex, count).execute()
                
                if int(len(results)) > 0:
                    for result in results:
                        result = format_api_output.formatsource(result)
                        source.append(result)                                            
                        js = json.dumps(source, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'  
                        resp.headers['Count'] = count
                        resp.headers['StartIndex'] = startIndex      
                    return resp
                else: return not_found()
            else:  # closes the end of the three parameters
                return not_found()
             
        else:  # last one for GET
            return not_found()
            
    elif request.method == 'POST':  # must specify the source 
        poststar = request.data 
        return postsource(poststar)
     
    # end these URL calls
    else: return not_allowed()

@app.route('/rest/v1/source/<uuid>', methods=['GET', 'PUT', 'DELETE'])  # search by uuid and short code
def api_sourcebyuuid(uuid):     
    if request.method == 'GET':

        source = []
        results = solr_interface.query(uuid=uuid).query(type='source').paginate(startcount, defaultcount).execute()
       
        if int(len(results)) > 0:     
            for result in results:
                result = format_api_output.formatsource(result)           
                source.append(result)                                            
                js = json.dumps(source, indent=4)
                resp = Response(js, status=200)
                resp.headers['Link'] = 'http://openconceptlab.org'
                resp.headers['Count'] = defaultcount
                resp.headers['StartIndex'] = startcount 
                         
            return resp
        else:
            results = solr_interface.query(shortCode=uuid).query(type='source').paginate(startcount, defaultcount).execute()
            code = []
            if int(len(results)) > 0:     
                for result in results:
                    result = format_api_output.formatsource(result)           
                    code.append(result)                                            
                    js = json.dumps(code, indent=4)
                    resp = Response(js, status=200)
                    resp.headers['Link'] = 'http://openconceptlab.org'
                    resp.headers['Count'] = defaultcount
                    resp.headers['StartIndex'] = startcount                                       
                return resp
            else: return not_found() 

    elif request.method == 'PUT':  # not sure if we can do this method
        # search if the existing  resource exists using the uuid
        results = solr_interface.query(uuid=uuid).query(type='source').paginate(startcount, defaultcount).execute()
        if int(len(results)) > 0:
            solr_interface.delete(queries=solr_interface.Q(uuid=uuid))
            solr_interface.commit() 
            
            poststar = request.data 
            return putoclsource(poststar)
        else: return not_found()  
            
    elif request.method == 'DELETE':  # must specify the source
        # search if the existing  resource exists using the uuid
        results = solr_interface.query(uuid=uuid).query(type='source').paginate(startcount, defaultcount).execute()
       
        if int(len(results)) > 0:  # means the existing resource is present 
                    
            # solr  deletes existing index
            solr_interface.delete(queries=solr_interface.Q(uuid=uuid))
            solr_interface.commit()           
            return success()
        
        else: return not_found()   

        
@app.route('/rest/v1/star', methods=['GET', 'POST'])  
def api_star():
    if request.method == 'GET':  # searches all stars available from different dictionaries
        requestparams = {}
        star = []        

        requestparams = request.args
        number_of_params_requested = int(len(requestparams))
                
        if number_of_params_requested == 0 :
            # no parameters passed in the url is just /rest/v1/star
            results = solr_interface.query('*').query(type='star').paginate(startcount, defaultcount).execute()

            if int(len(results)) > 0:
                for result in results:                    
                    star.append(result)                                            
                    js = json.dumps(star, indent=4)
                    resp = Response(js, status=200)
                    resp.headers['Link'] = 'http://openconceptlab.org'
             
                return resp
            else: return not_found()
        elif number_of_params_requested == 1 :
            if  requestparams.has_key('username'):
                # search by user 
                name = requestparams['username']
                results = solr_interface.query(username=name).query(type='star').paginate(startcount, defaultcount).execute()

                if int(len(results)) > 0:
                    for result in results:
                        star.append(result)                                            
                        js = json.dumps(star, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                    return resp
                else: return not_found()
                                                                           
            elif requestparams.has_key('count'):
                # set the number of returns to return
                count = requestparams['count']                
                results = solr_interface.query('*').query(type='star').paginate(startcount, count).execute()

                if int(len(results)) > 0:
                    for result in results:                 
                        star.append(result)                                            
                        js = json.dumps(star, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'         
                    return resp
                else: return not_found()
            
            elif requestparams.has_key('startIndex'):
                # set the start index
                startIndex = requestparams['startIndex']
                results = solr_interface.query('*').query(type='star').paginate(startIndex, defaultcount).execute()
                
                if int(len(results)) > 0:
                    for result in results:
                        star.append(result)                                            
                        js = json.dumps(star, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'    
                    return resp
                else: return not_found()
                                    
        elif number_of_params_requested == 3 :
            # start with is there a query name for search
            if requestparams.has_key('username') and requestparams.has_key('count') and requestparams.has_key('startIndex') :
                count = requestparams['count']
                name = requestparams['username']
                startIndex = requestparams['startIndex']
                
                results = solr_interface.query(username=name).query(type='star').paginate(startIndex, count).execute()
                
                if int(len(results)) > 0:
                    for result in results:
                        star.append(result)                                            
                        js = json.dumps(star, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'        
                    return resp
                else: return not_found()
            else:  # closes the end of the three parameters
                return not_found()
             
        else:  # last one for GET
            return not_found()
    elif request.method == 'POST':  # must specify the resource id and username
        # check the minimum number of criteria is met 
        poststar = json.loads(request.data)
        return postocl(poststar)

''' implement user routes'''
    
@app.route('/rest/v1/user', methods=['GET', 'POST', 'PUT', 'DELETE'])  
def api_user():    
    if request.method == 'GET':  # searches all user available from different dictionaries
        requestparams = {}
        user = []        

        requestparams = request.args
        number_of_params_requested = int(len(requestparams))
                
        if number_of_params_requested == 0 :
            # no parameters passed in the url is just /rest/v1/star
            results = solr_interface.query('*').query(type='user').paginate(startcount, defaultcount).execute()

            if int(len(results)) > 0:
                for result in results: 
                    result = formatuser(result)                   
                    user.append(result)                                            
                    js = json.dumps(user, indent=4)
                    resp = Response(js, status=200)
                    resp.headers['Link'] = 'http://openconceptlab.org'            
                return resp
            else: return not_found()
    elif request.method == 'POST':  # must specify the source 
        poststar = json.loads(request.data)
        return postocl(poststar)
    elif request.method == 'PUT':  # not sure if we can do this method
        results = solr_interface.query(uuid=uuid).query(type='user').paginate(startcount, defaultcount).execute()
        return putocl(results)
    elif request.method == 'DELETE':  # must specify the source
        results = solr_interface.query(uuid=uuid).query(type='user').paginate(startcount, defaultcount).execute()
       
        if int(len(results)) > 0:  # means the existing resource is present 
                    
            # solr  deletes existing index
            solr_interface.delete(queries=solr_interface.Q(uuid=uuid))
            solr_interface.commit()           
            return success()
        
    else: return not_found()
    
@app.route('/rest/v1/mapping', methods=['GET', 'POST'])  
def api_mapping():
    if request.method == 'GET':  # searches all classes available from different dictionaries
        
        requestparams = {}
        mapping = []        

        requestparams = request.args
        number_of_params_requested = int(len(requestparams))
                
        if number_of_params_requested == 0 :
            # no parameters passed in the url is just /rest/v1/mapping
            results = solr_interface.query('*').query(type='mapping').paginate(startcount, defaultcount).execute()

            if int(len(results)) > 0:
                for result in results:
                    result = formatmapping(result)
                    mapping.append(result)                                            
                    js = json.dumps(mapping, indent=4)
                    resp = Response(js, status=200)
                    resp.headers['Link'] = 'http://openconceptlab.org'
             
                return resp
            else: return not_found()
        elif number_of_params_requested == 1 :
            # http://127.0.0.1:5000/mapping?concept=1234-5678-9012-3456
            # /mapping?conceptA=1234-5678-9012-3456
            # /mapping?conceptB=1234-5678-9012-3456
            # /mapping?count=15&startIndex=30                      
            
            if  requestparams.has_key('concept'):
                # search by a class keyword or name
                concept = requestparams['concept']
                results = solr_interface.query(uuid=concept).query(type='mapping').paginate(startcount, defaultcount).execute()

                if int(len(results)) > 0:
                    for result in results:
                        mapping.append(result)                                            
                        js = json.dumps(mapping, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'
                    return resp
                else: return not_found()
                                                                           
            elif requestparams.has_key('conceptA'):
                # set the number of returns to return
                conceptA = requestparams['conceptA']                
                results = solr_interface.query(conceptA_id=conceptA).query(type='mapping').paginate(startcount, defaultcount).execute()

                if int(len(results)) > 0:
                    for result in results:                 
                        mapping.append(result)                                            
                        js = json.dumps(mapping, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'       
                    return resp
                else: return not_found()
            
            elif requestparams.has_key('conceptB'):
                # set the start index
                conceptB = requestparams['conceptB']
                results = solr_interface.query(conceptB_id=conceptB).query(type='mapping').paginate(startcount, defaultcount).execute()
                
                if int(len(results)) > 0:
                    for result in results:
                        mapping.append(result)                                            
                        js = json.dumps(mapping, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'  
                    return resp
                else: return not_found()
                
            elif requestparams.has_key('count'):
                # set the number of returns to return
                count = requestparams['count']                
                results = solr_interface.query('*').query(type='mapping').paginate(startcount, count).execute()

                if int(len(results)) > 0:
                    for result in results:                 
                        mapping.append(result)                                            
                        js = json.dumps(mapping, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'          
                    return resp
                else: return not_found()
            
            elif requestparams.has_key('startIndex'):
                # set the start index
                startIndex = requestparams['startIndex']
                results = solr_interface.query('*').query(type='mapping').paginate(startIndex, defaultcount).execute()
                
                if int(len(results)) > 0:
                    for result in results:
                        mapping.append(result)                                            
                        js = json.dumps(mapping, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'      
                    return resp
                else: return not_found()
                                    
        elif number_of_params_requested == 3 :
            # start with is there a query name for search
            if requestparams.has_key('q') and requestparams.has_key('count') and requestparams.has_key('startIndex') :
                count = requestparams['count']
                name = requestparams['q']
                startIndex = requestparams['startIndex']
                
                results = solr_interface.query(name).query(type='source').paginate(startIndex, count).execute()
                
                if int(len(results)) > 0:
                    for result in results:
                        mapping.append(result)                                            
                        js = json.dumps(mapping, indent=4)
                        resp = Response(js, status=200)
                        resp.headers['Link'] = 'http://openconceptlab.org'         
                    return resp
                else: return not_found()
            else:  # closes the end of the three parameters
                return not_found()
             
        else:  # last one for GET
            return not_found()
            
    elif request.method == 'POST':  # must specify the source 
        poststar = request.data 
        document = json.loads(poststar)  
        document = postcollection(document)
        solr_interface.add(document)
        solr_interface.commit()
        return created()
#         return postocl(poststar) 
    
    # end these URL calls
    else: return not_allowed()
             
@app.errorhandler(404)
def not_found(error=None):
    message = {
               'status' : 404,
               'message' :'Resource not found' + '   ' + request.url ,
               } 
    resp = jsonify(message)
    resp.headers['Link'] = 'http://openconceptlab.org'
    resp.status_code = 404
    
    return resp

@app.errorhandler(201)
def created(url):
    message = {
               'status' : 201,
               'message' :'Resource' + '   ' + url + '  ' + 'successfully created' + '   ',
               } 
    resp = jsonify(message)
    resp.headers['Link'] = 'http://openconceptlab.org'
    resp.status_code = 201
    
    return resp

@app.errorhandler(405)
def not_allowed(error=None):
    message = {
               'status' : 405,
               'message' :'The method' + '   ' + request.method + '  ' + 'is not allowed for the requested URL' + '   ' + request.url ,
               } 
    resp = jsonify(message)
    resp.headers['Link'] = 'http://openconceptlab.org'
    resp.status_code = 405
    
    return resp

@app.errorhandler(200)
def success(error=None):
    message = {
               'status' : 200,
               'message' :request.method + ' on Resource' + '   ' + request.url + '   ' + 'successful ' + '  ' ,
               } 
    resp = jsonify(message)
    resp.headers['Link'] = 'http://openconceptlab.org'
    resp.status_code = 200
    
    return resp
 
@app.errorhandler(400)
def bad_request(error=None):
    message = {
               'status' : 400,
               'message' :'The  proxy sent a request that this server could not understand' + '   ' + request.url ,
               } 
    resp = jsonify(message)
    resp.headers['Link'] = 'http://openconceptlab.org'
    resp.status_code = 400
    
    return resp

@app.errorhandler(407)
def invalid_arguement(error=None):
    message = {
               'status' : 407,
               'message' :'Invalid argument passed in ' + '   ' + request.url,
               } 
    resp = jsonify(message)
    resp.status_code = 407
    
    return resp

@app.errorhandler(415)
def unsupported():
    message = {
               'status' : 415,
               'message' :'Unsupported Media Type Posted using  ' + '   ' + request.header,
               } 
    resp = jsonify(message)
    resp.status_code = 415
    
    return resp

def formatclass(result):
    # format properties section
    result['properties'] = {'hl7Code':result['hl7Code'], 'openmrsResourceVersion':result['openmrsResourceVersion'], }
    del result['hl7Code']
    del result['openmrsResourceVersion']
                    
    # format AuditInfo
    result['auditInfo'] = {'creator':result['creator'], 'dateCreated':result['dateCreated'], 'changedBy':result['changedby'], 'dateChanged':result['dateChanged']}
    del result['creator']
    del result['dateCreated']
    del result['changedby']
    del result['dateChanged']
                    
    # format names
    result['names'] = [{'name':result['name'], 'locale':result['locale'], 'preferred':result['preferred'].replace('"', '')}]
    del result['name']
    del result['locale']
    del result['preferred']
                    
    # format descriptions
    result['descriptions'] = [{'description':result['description'], 'locale':result['descriptionLocale'], 'preferred':result['descriptionPreferred'].replace('"', '')}]
    del result['description']
    del result['descriptionLocale']
    del result['descriptionPreferred']
                    
    # format sources
    result['sources'] = [result.get('dict')]
    del result['dict']
    del result['_version_']
    del result['type']
    
    return result

def formatdatatype(result):
    # format properties section
    result['properties'] = {'hl7Abbreviation':result['hl7Abbreviation'], 'openmrsResourceVersion':result['openmrsResourceVersion'], }
    del result['hl7Abbreviation']
    del result['openmrsResourceVersion']
                    
    # format AuditInfo
    result['auditInfo'] = {'creator':result['creator'], 'dateCreated':result['dateCreated'], 'changedBy':result['changedby'], 'dateChanged':result['dateChanged']}
    del result['creator']
    del result['dateCreated']
    del result['changedby']
    del result['dateChanged']
                    
    # format names
    result['names'] = [{'name':result['name'], 'locale':result['locale'], 'preferred':result['preferred'].replace('"', '')}]
    del result['name']
    del result['locale']
    del result['preferred']
                    
    # format descriptions
    result['descriptions'] = [{'description':result['description'], 'locale':result['descriptionLocale'], 'preferred':result['descriptionPreferred'].replace('"', '')}]
    del result['description']
    del result['descriptionLocale']
    del result['descriptionPreferred']
                    
    # format sources
    result['sources'] = [result.get('dict')]
    del result['dict']
    del result['_version_']
    del result['type']
    
    return result

def mapdatatype(result):
    # format properties section
    result['properties'] = {'openmrsResourceVersion':result['openmrsResourceVersion'], }
    del result['openmrsResourceVersion']
                    
    # format AuditInfo
    result['auditInfo'] = {'creator':result['creator'], 'dateCreated':result['dateCreated']}
    del result['creator']
    del result['dateCreated']
    
                    
    # format names
    result['names'] = [{'name':result['name'], 'locale':result['locale'], 'preferred':result['preferred'].replace('"', '')}]
    del result['name']
    del result['locale']
    del result['preferred']
                    
    # format descriptions
    result['descriptions'] = [{'locale':result['descriptionLocale'], 'preferred':result['descriptionPreferred'].replace('"', '')}]
    del result['descriptionLocale']
    del result['descriptionPreferred']
                    
    # format sources
    result['sources'] = [result.get('dict')]
    del result['dict']
    del result['_version_']
    del result['type']
    
    return result

def formatsource(result):
    if result.has_key('versionStatus'):
    # format properties section
        result['properties'] = {'versionStatus':result['versionStatus']}
        del result['versionStatus']

    # format audit INFo             
    audit = {}
    if result.has_key('creator'): 
        audit['creator'] = result['creator']
        del result['creator']
    if result.has_key('dateCreated'): 
        audit['dateCreated'] = result['dateCreated']
        del result['dateCreated']
    if result.has_key('changedby'): 
        audit['changedBy'] = result['changedby']
        del result['changedby']
    if result.has_key('dateChanged'): 
        audit['dateChanged'] = result['dateChanged']
        del result['dateChanged']
    if result.has_key('dateReleased'): 
        audit['dateReleased'] = result['dateReleased']
        del result['dateReleased']

    if int(len(audit)) == 1:
        if audit.has_key('creator'):
            result['auditInfo'] = {'creator':audit['creator']}
        elif audit.has_key('dateCreated'):
            result['auditInfo'] = {'dateCreated':audit['dateCreated']}
        elif audit.has_key('changedBy'):
            result['auditInfo'] = {'changedBy':audit['changedBy']}
        elif audit.has_key('dateChanged'):
            result['auditInfo'] = {'dateChanged':audit['dateChanged']}
        elif audit.has_key('dateReleased'):
            result['auditInfo'] = {'dateReleased':audit['dateReleased']}
    elif int(len(audit)) == 2:
        if audit.has_key('creator') and audit.has_key('dateCreated'):
            result['auditInfo'] = {'creator':audit['creator'], 'dateCreated':audit['dateCreated']}
        elif audit.has_key('creator') and audit.has_key('changedBy'):
            result['auditInfo'] = {'creator':audit['creator'], 'changedBy':audit['changedBy']}
        elif audit.has_key('creator') and audit.has_key('dateChanged'):
            result['auditInfo'] = {'creator':audit['creator'], 'dateChanged':audit['dateChanged']}
        elif audit.has_key('dateCreated') and audit.has_key('changedBy'):
            result['auditInfo'] = {'dateCreated':audit['dateCreated'], 'changedBy':audit['changedBy']}
        elif audit.has_key('dateCreated') and audit.has_key('dateChanged'):
            result['auditInfo'] = {'dateCreated':audit['dateCreated'], 'dateChanged':audit['dateChanged']}
        elif audit.has_key('changedBy') and audit.has_key('dateChanged'):
            result['auditInfo'] = {'changedBy':audit['changedBy'], 'dateChanged':audit['dateChanged']}       
    elif int(len(audit)) == 3: 
        if audit.has_key('creator') and audit.has_key('dateCreated') and audit.has_key('changedBy'):
            result['auditInfo'] = {'creator':audit['creator'], 'dateCreated':audit['dateCreated'], 'changedBy':audit['changedBy']}
    elif int(len(audit)) == 4: 
        result['auditInfo'] = {'dateChanged':audit['dateChanged'], 'changedBy':audit['changedBy'], 'creator':audit['creator'], 'dateCreated':audit['dateCreated']}   
    elif int(len(audit)) == 5: 
        result['auditInfo'] = {'dateChanged':audit['dateChanged'], 'changedBy':audit['changedBy'], 'creator':audit['creator'], 'dateCreated':audit['dateCreated'], 'dateReleased':audit['dateReleased']}   
                   
    # format names
    if result.has_key('nameType'): 
        result['names'] = [{'name':result['name'], 'locale':result['locale'], 'nameType':result['nameType'], 'preferred':result['preferred'].replace('"', '')}]
        del result['name']
        del result['locale']
        del result['preferred']
        del result['nameType']
    else:
        result['names'] = [{'name':result['name'], 'locale':result['locale'], 'preferred':result['preferred'].replace('"', '')}]
        del result['name']
        del result['locale']
        del result['preferred']
                   
    # format descriptions
    if result.has_key('description'):
        result['descriptions'] = {'description':result['description'], 'locale':result['descriptionLocale'], 'preferred':result['descriptionPreferred'].replace('"', '')}
        del result['description']
        del result['descriptionLocale']
        del result['descriptionPreferred']
                      
    # format sources
    result['sharedUsers'] = [result.get('username')]
    
    if result.has_key('dict'): del result['dict']
    del result['_version_']
    del result['type']

    
    return result

def formatauditinfo(result):
    # format audit INFo             
    audit = {}
    if result.has_key('creator'): 
        audit['creator'] = result['creator']
        del result['creator']
    if result.has_key('dateCreated'): 
        audit['dateCreated'] = result['dateCreated']
        del result['dateCreated']
    if result.has_key('changedby'): 
        audit['changedBy'] = result['changedby']
        del result['changedby']
    if result.has_key('dateChanged'): 
        audit['dateChanged'] = result['dateChanged']
        del result['dateChanged']

    if int(len(audit)) == 1:
        if audit.has_key('creator'):
            result['auditInfo'] = {'creator':audit['creator']}
        elif audit.has_key('dateCreated'):
            result['auditInfo'] = {'dateCreated':audit['dateCreated']}
        elif audit.has_key('changedBy'):
            result['auditInfo'] = {'changedBy':audit['changedBy']}
        elif audit.has_key('dateChanged'):
            result['auditInfo'] = {'dateChanged':audit['dateChanged']}
    elif int(len(audit)) == 2:
        if audit.has_key('creator') and audit.has_key('dateCreated'):
            result['auditInfo'] = {'creator':audit['creator'], 'dateCreated':audit['dateCreated']}
        elif audit.has_key('creator') and audit.has_key('changedBy'):
            result['auditInfo'] = {'creator':audit['creator'], 'changedBy':audit['changedBy']}
        elif audit.has_key('creator') and audit.has_key('dateChanged'):
            result['auditInfo'] = {'creator':audit['creator'], 'dateChanged':audit['dateChanged']}
        elif audit.has_key('dateCreated') and audit.has_key('changedBy'):
            result['auditInfo'] = {'dateCreated':audit['dateCreated'], 'changedBy':audit['changedBy']}
        elif audit.has_key('dateCreated') and audit.has_key('dateChanged'):
            result['auditInfo'] = {'dateCreated':audit['dateCreated'], 'dateChanged':audit['dateChanged']}
        elif audit.has_key('changedBy') and audit.has_key('dateChanged'):
            result['auditInfo'] = {'changedBy':audit['changedBy'], 'dateChanged':audit['dateChanged']}       
    elif int(len(audit)) == 3: 
        if audit.has_key('creator') and audit.has_key('dateCreated') and audit.has_key('changedBy'):
            result['auditInfo'] = {'creator':audit['creator'], 'dateCreated':audit['dateCreated'], 'changedBy':audit['changedBy']}
    elif int(len(audit)) == 4: 
        result['auditInfo'] = {'dateChanged':audit['dateChanged'], 'changedBy':audit['changedBy'], 'creator':audit['creator'], 'dateCreated':audit['dateCreated']}   

def formatmapping(result):
    # format properties section
    result['properties'] = {'properties': result['properties']}
                    
    # format AuditInfo
    result['auditInfo'] = {'creator':result['creator'], 'dateCreated':result['dateCreated']}
    del result['creator']
    del result['dateCreated']
    
    # conceptA
    result['conceptA'] = {'source':result['conceptA_source'], 'id':result['conceptA_id']}
    del result['conceptA_source']
    del result['conceptA_id']
    
    # conceptB
    result['conceptB'] = {'source':result['conceptB_source'], 'id':result['conceptB_id']}
    del result['conceptB_source']
    del result['conceptB_id']
    
    del result['dict']
    del result['_version_']
    del result['type']
    
    return result

def formatconcept(result):
    # format properties section  
    if result.has_key('hiNormal'):
        # result['properties'] = {'hiNormal':result['hiNormal'],'hiCritical':result['hiCritical'],'lowNormal':result['lowNormal'],'lowAbsolute':result['lowAbsolute'],'lowCritical':result['lowCritical'],'units':result['units'],'precise':result['precise'],'hiAbsolute':result['hiAbsolute']}
        result['properties'] = {'hiNormal':result['hiNormal'], 'lowNormal':result['lowNormal'], 'lowAbsolute':result['lowAbsolute'], 'lowCritical':result['lowCritical'], 'units':result['units'], 'precise':result['precise'], 'hiAbsolute':result['hiAbsolute']}
        del result['hiNormal']
        del result['hiAbsolute']
        # del result['hiCritical']
        del result['lowNormal']
        del result['lowAbsolute']
        del result['lowCritical']
        del result['units']
        del result['precise']
    else: 
        result['properties'] = {'properties':'null'}
        
    # format questions
    if result.has_key('questions') :
        u = str(result['questions']).split('|')
        for x in u:
            conceptlist = []
            conceptlist.append(x)
        result['questions'] = conceptlist
        
    # format answer
    if result.has_key('answerDisplay'):
        result['answers'] = [{'display':result['answerDisplay']}]
        del result['answerDisplay']

    temp = {}
    # setlist = []    
    # setMembers
    if result.has_key('setParent') :
        m = str(result['setParent']).split('|')
        for i in m:
            setlist = []
            setlist.append(i)
        result['setParent'] = setlist  
        temp['setParent'] = result['setParent']
        del result['setParent']
    
        
    # set children    
    if result.has_key('setChildren') :
        m = str(result['setChildren']).split('|')
        for j in m:
            setlist = []
            setlist.append(j)
        result['setChildren'] = setlist  
        temp['setChildren'] = result['setChildren']
        del result['setChildren']
    
    # set sibling
    if result.has_key('setSibling') :
        b = str(result['setSibling']).split('|')
        for a in b:
            setlist = []
            setlist.append(a)
        result['setSibling'] = setlist  
        temp['setSibling'] = result['setSibling']
        del result['setSibling']
    
    
    if int(len(temp)) == 1:
        if temp.has_key('setParent'):
            result['setMembers'] = [{'setParent':temp['setParent']}]
        elif temp.has_key('setChildren'): 
            result['setMembers'] = [{'setChildren':temp['setChildren']}]
        elif temp.has_key('setSibling'): 
            result['setMembers'] = [{'setSibling':temp['setSibling']}]
    elif int(len(temp)) == 2:
        if temp.has_key('setParent') and temp.has_key('setChildren'):
            result['setMembers'] = [{'setParent':temp['setParent'], 'setChildren':temp['setChildren']}]
        elif temp.has_key('setParent') and temp.has_key('setSibling'):
            result['setMembers'] = [{'setParent':temp['setParent'], 'setSibling':temp['setSibling']}]
        elif temp.has_key('setSibling') and temp.has_key('setChildren'): 
            result['setMembers'] = [{'setSibling':temp['setSibling'], 'setChildren':temp['setChildren']}]
    elif int(len(temp)) == 3:   
        result['setMembers'] = [{'setParent':temp['setParent'], 'setChildren':temp['setChildren'], 'setSibling':temp['setSibling']}]
    
    # format audit INFo             
    audit = {}
    if result.has_key('creator'): 
        audit['creator'] = result['creator']
        del result['creator']
    if result.has_key('dateCreated'): 
        audit['dateCreated'] = result['dateCreated']
        del result['dateCreated']
    if result.has_key('changedby'): 
        audit['changedBy'] = result['changedby']
        del result['changedby']
    if result.has_key('dateChanged'): 
        audit['dateChanged'] = result['dateChanged']
        del result['dateChanged']

    if int(len(audit)) == 1:
        if audit.has_key('creator'):
            result['auditInfo'] = {'creator':audit['creator']}
        elif audit.has_key('dateCreated'):
            result['auditInfo'] = {'dateCreated':audit['dateCreated']}
        elif audit.has_key('changedBy'):
            result['auditInfo'] = {'changedBy':audit['changedBy']}
        elif audit.has_key('dateChanged'):
            result['auditInfo'] = {'dateChanged':audit['dateChanged']}
    elif int(len(audit)) == 2:
        if audit.has_key('creator') and audit.has_key('dateCreated'):
            result['auditInfo'] = {'creator':audit['creator'], 'dateCreated':audit['dateCreated']}
        elif audit.has_key('creator') and audit.has_key('changedBy'):
            result['auditInfo'] = {'creator':audit['creator'], 'changedBy':audit['changedBy']}
        elif audit.has_key('creator') and audit.has_key('dateChanged'):
            result['auditInfo'] = {'creator':audit['creator'], 'dateChanged':audit['dateChanged']}
        elif audit.has_key('dateCreated') and audit.has_key('changedBy'):
            result['auditInfo'] = {'dateCreated':audit['dateCreated'], 'changedBy':audit['changedBy']}
        elif audit.has_key('dateCreated') and audit.has_key('dateChanged'):
            result['auditInfo'] = {'dateCreated':audit['dateCreated'], 'dateChanged':audit['dateChanged']}
        elif audit.has_key('changedBy') and audit.has_key('dateChanged'):
            result['auditInfo'] = {'changedBy':audit['changedBy'], 'dateChanged':audit['dateChanged']}       
    elif int(len(audit)) == 3: 
        if audit.has_key('creator') and audit.has_key('dateCreated') and audit.has_key('changedBy'):
            result['auditInfo'] = {'creator':audit['creator'], 'dateCreated':audit['dateCreated'], 'changedBy':audit['changedBy']}
    elif int(len(audit)) == 4: 
        result['auditInfo'] = {'dateChanged':audit['dateChanged'], 'changedBy':audit['changedBy'], 'creator':audit['creator'], 'dateCreated':audit['dateCreated']}                       
                                      
    # format names
    result['names'] = [{'uuid':result['nameuuid'], 'name':result['name'], 'locale':result['namelocale']}]
    del result['name']
    del result['namelocale']
    del result['nameuuid']
                
    # format descriptions
    result['descriptions'] = [{'uuid':result['DescUuid'], 'description':result['description'], 'locale':result['localeDesc'], 'preferred':result['preferredDesc']}]
    del result['DescUuid']
    del result['description']
    del result['localeDesc']
    del result['preferredDesc']

    del result['_version_']
    
    # mappings
    conceptdisplay = str(result.get('conceptId'))
    conceptdisplay.replace('_', ':')
    mymap = getconceptmapping(conceptdisplay)
    result['mappings'] = mymap
     
    if result.has_key('precise'):del result['precise']    
    if result.has_key('mappingDisplay'):del result['mappingDisplay']
    if result.has_key('conceptMapType'):del result['conceptMapType']    
    if result.has_key('mappingUuid'):del result['mappingUuid']        
    
    # return collections for this concept 
    conceptid = str(result.get('conceptId')).split('_')
    conceptid = conceptid[1]
    mycollection = getconceptcollections(conceptid)
    result['collections'] = mycollection
    
    # return stars
    conceptuuid = result['uuid']
    result['starCount'] = getconceptstars(conceptuuid)
         
    return result

def formatuser(result):
    # format properties section   
    properties = []
    properties.append('')
    result['properties'] = properties
    
    '''                    
    #format AuditInfo
    result['auditInfo'] = {'creator':result['creator'],'dateCreated':result['dateCreated'],'changedBy':result['changedbywhom'],'dateChanged':result['dateChange']}
    del result['creator']
    del result['dateCreated']
    del result['changedbywhom']
    del result['dateChange']
    '''
                
    # format roles
    result['roles'] = [{'uuid':result['roleuuid'], 'display':result['roledisplay'], 'name':result['rolename'], 'description':result['roledescription'], 'retired':result['roleretired'], 'privileges':result['roleprivileges']}]
    del result['roleuuid']
    del result['roledisplay']
    del result['rolename']
    del result['roledescription']
    del result['roleretired']
    del result['roleprivileges']

    del result['_version_']
    
    return result

def getconceptmapping(conceptdisplay):
    # display Mappings     
    results = solr_interface.query(display=conceptdisplay).query(type='mapping').paginate(startcount, defaultcount).execute()
    conceptmappings = []
    mapping = {}
    if int(len(results)) > 0:
        for result in results:
            mapping['uuid'] = result['uuid']
            mapping['display'] = result['display']
            mapping['conceptMapType'] = result['map_type']
        conceptmappings.append(mapping) 
        return conceptmappings                                         
    else: 
        conceptmappings = {'':'null'}
        return conceptmappings
    
def getconceptstars(concept):
    results = solr_interface.query(concept).query(type='star').paginate(startcount, defaultcount).execute()
    if int(len(results)) > 0:
        starCount = 0
        for result in results:
            starCount + 1
        return starCount                                        
    else: 
        starCount = 0
        return starCount
    
def getconceptcollections(concept):
    # display Mappings  
    conceptcollections = []
    collection = {}   
    results = solr_interface.query('*').query(type='collection').paginate(startcount, defaultcount).execute()   
    if int(len(results)) > 0:
        for result in results:
            conceptuuids = str(result['concept_uuid']).split('|')
            if concept in conceptuuids:
                collection['uuid'] = result['uuid']
                collection['name'] = result['display']
                collection['url'] = result['url']
        conceptcollections.append(collection)
        return conceptcollections                                        
    else: 
        conceptcollections = {'null'}
        return conceptcollections    
    
def wrongjson():
    message = { 
               'message' : 'Invalid Json format passed in your request on' + '     ' + request.url,
               }
    resp = jsonify(message)
    return resp

def invalidput():
    message = { 
               'message' : 'PUT resource missing minimum fields' + '     ' + request.url,
               }
    resp = jsonify(message)
    return resp

'''
@app.errorhandler(500)
def error_unknown(error=None):
    message = { 
               'status' : 500,
               'message' : 'Wrong URL/ check the UUID' + '     '  + request.url,
               }
    resp = jsonify(message)
    resp.status_code = 500
    
    return resp
'''


if __name__ == '__main__':
    app.run(debug=True)
    
    

    
