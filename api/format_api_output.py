'''
Created on Jul 31, 2013

@author: judyw
'''
def formatcollection(result):
    collectionOutput = {}
    if '__type__' in result.keys():collectionOutput['__type__'] = 'OclCollection'
    else:collectionOutput['__type__'] = ''
    
    if 'uuid' in result.keys():
        collectionOutput['uuid'] = result['uuid']
    else:collectionOutput['uuid'] = ''
    
    if 'display' in result.keys():collectionOutput['display']= result['display']
    else: collectionOutput['display'] =''
    
    if 'displayLocale' in result.keys():collectionOutput['displayLocale']= result['displayLocale']
    else: collectionOutput['displayLocale'] = ''
    
    if 'retired' in result.keys():collectionOutput['retired']= result['retired']
    collectionOutput['retired']= ''
    
    #properties
    properties = {}
    if 'hl7Code' in result.keys():properties['hl7Code'] = result['hl7Code']
    else: properties['hl7Code'] =''
    
    if 'openmrsResourceVersion' in result.keys():properties['openmrsResourceVersion'] = result['openmrsResourceVersion']
    else: properties['openmrsResourceVersion'] =''
    
    collectionOutput['properties']= properties

    #auditInfo
    auditInfo ={}
    if 'creator' in result.keys(): auditInfo['creator'] = result['creator']
    else: auditInfo['creator'] = ''
    if 'dateCreated' in result.keys():auditInfo['dateCreated'] = result['dateCreated']
    else: auditInfo['dateCreated'] = ''
    if 'changedBy' in result.keys():auditInfo['changedBy'] = result['changedby']
    else: auditInfo['changedBy'] = ''
    if 'dateChanged' in result.keys():auditInfo['dateChanged'] = result['dateChanged']
    else:auditInfo['dateChanged'] = ''
    
    collectionOutput['auditInfo']= auditInfo
    
    if 'creator' in result.keys(): auditInfo['creator'] = result['creator']
    else: auditInfo['creator'] = ''
    
    names = []
    collectionname = {}
    if 'name' in result.keys(): collectionname['name'] = result['name']
    else: collectionname['name'] = ''
    if 'locale' in result.keys(): collectionname['locale'] = result['locale']
    else: collectionname['locale'] = ''
    if 'preferred' in result.keys(): collectionname['preferred'] = result['preferred']
    else: collectionname['preferred'] = ''
    
    names.append(collectionname)
    collectionOutput['names']= names
    
    if 'collectionType' in result.keys(): collectionOutput['collectionType'] = result['collectionType']
    else: collectionOutput['collectionType'] = ''

    if 'owner' in result.keys(): collectionOutput['owner'] = result['owner']
    else: collectionOutput['owner'] = ''
    
    if 'publicAccess' in result.keys(): collectionOutput['publicAccess'] = result['publicAccess']
    else: collectionOutput['publicAccess'] = ''
    
    sharedUsers =[]
    myusers ={}
    if 'username' in result.keys(): myusers['username'] = result['username']
    else: myusers['username'] = ''
    if 'access' in result.keys(): myusers['access'] = result['access']
    else: myusers['access'] = ''
    sharedUsers.append(myusers)
    collectionOutput['sharedUsers']= sharedUsers

    if 'starCount' in result.keys(): collectionOutput['starCount'] = result['starCount']
    else: collectionOutput['starCount'] = ''
    
    #concepts format 
    myurl =''
    myuuid = ''
    conceptlist = []
    conceptdict ={}
    
    if 'concept_uuid' in result.keys():             
        u = str(result['concept_uuid']).split('|')
        for x in u:
            myuuid = x
            myurl = str('http://www.openconceptlab.org/rest/v1/source/ciel/concept/') + str(myuuid)
            conceptdict ={'uuid':myuuid,'url':myurl}
            conceptlist.append(conceptdict)
        collectionOutput['concepts']=conceptlist
                         
    return collectionOutput