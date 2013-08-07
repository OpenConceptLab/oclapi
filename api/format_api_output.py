'''
Created on Jul 31, 2013

@author: judyw
'''
def copy_item(keyname, indict, outdict, default):
    """
    Copy an item with keyname from the input dictionary to output
    dictionary using the default value for the output dictionary if
    the key does not exist in the input dictionary.
    """
    if keyname in indict.keys():
        outdict[keyname] = indict[keyname]
    else:
        outdict[keyname] = default
        
def changekeyname(dict, inkey, outkey):
    if 'inkey' in dict.keys():
        dict['outkey'] = dict['inkey']
        del dict['inkey']
    
def formatcollection(result):
    
    collectionOutput = {}
    properties = {}
    auditInfo = {}
    collectionname = {}
    myusers = {}
    collectiondesc = {}
    
    changekeyname(result, 'changedby', 'changedBy')
    
    tocopy = ['uuid', 'url', 'resourceVersion', 'display', 'displayLocale', 'retired', 'collectionType', 'owner', 'publicAccess', 'starCount']
    for key in tocopy:
        copy_item(key, result, collectionOutput, '')
    
    tocopycollection = ['__type__']
    for key in tocopycollection:
        copy_item(key, result, collectionOutput, 'OclCollection')
        
    toproperties = ['hl7Code', 'openmrsResourceVersion']
    for key in toproperties:
        copy_item(key, result, properties, '')
        
    toauditInfo = ['creator', 'dateCreated', 'changedBy', 'dateChanged']
    for key in toauditInfo:
        copy_item(key, result, auditInfo, '')
        
    tocollectionName = ['name', 'locale', 'preferred']
    for key in tocollectionName:
        copy_item(key, result, collectionname, '')
        
    tocollectionDesc = ['descriptionPreferred', 'descriptionLocale', 'description']
    for key in tocollectionDesc:
        copy_item(key, result, collectiondesc, '')
    collectiondesc['locale'] = collectiondesc['descriptionLocale']
    del collectiondesc['descriptionLocale']
    collectiondesc['preferred'] = collectiondesc['descriptionPreferred']
    del collectiondesc['descriptionPreferred']

    tosharedUsers = ['username', 'access']
    for key in tosharedUsers:
        copy_item(key, result, myusers, '')

    # properties    
    collectionOutput['properties'] = properties
    
    # auditInfo
    collectionOutput['auditInfo'] = auditInfo
    
    # names
    names = []    
    names.append(collectionname)
    collectionOutput['names'] = names
    
    sharedUsers = []
    sharedUsers.append(myusers)
    collectionOutput['sharedUsers'] = sharedUsers
    
    description = []
    description.append(collectiondesc)
    collectionOutput['descriptions'] = description
    
    # concepts format 
    myurl = ''
    myuuid = ''
    conceptlist = []
    conceptdict = {}
    
    if 'concept_uuid' in result.keys():             
        u = str(result['concept_uuid']).split('|')
        for x in u:
            myuuid = x
            myurl = str('http://www.openconceptlab.org/rest/v1/source/ciel/concept/') + str(myuuid)
            conceptdict = {'uuid':myuuid, 'url':myurl}
            conceptlist.append(conceptdict)
        collectionOutput['concepts'] = conceptlist
                         
    return collectionOutput

def formatsource(result):

    sourceOutput ={}
    auditInfo ={}
    properties = {}
    sourcename = {}
    sourcedesc = {}
    
    changekeyname(result, 'changedby', 'changedBy')

    tocopy = ['shortCode','sourceType','owner','publicAccess','starCount','__type__','uuid','url','display','displayLocale','retired','resourceVersion']
    for key in tocopy:
        copy_item(key, result, sourceOutput, '')
        
    toproperties = ['versionStatus']
    for key in toproperties:
        copy_item(key, result, properties, '')
    sourceOutput['properties'] = properties

    # format audit INFo   
    toauditInfo = ['creator', 'dateCreated', 'changedBy', 'dateChanged','dateReleased']
    for key in toauditInfo:
        copy_item(key, result, auditInfo, '')
    sourceOutput['auditInfo'] = auditInfo
                  
    # format names
    toName = ['name', 'locale', 'preferred' ,'nameType']
    for key in toName:
        copy_item(key, result, sourcename, '')
        
    names = []    
    names.append(sourcename)
    sourceOutput['names'] = names
                   
    # format descriptions
    toDesc = ['descriptionPreferred', 'descriptionLocale', 'description']
    for key in toDesc:
        copy_item(key, result, sourcedesc, '')
    sourcedesc['locale'] = sourcedesc['descriptionLocale']
    del sourcedesc['descriptionLocale']
    sourcedesc['preferred'] = sourcedesc['descriptionPreferred']
    del sourcedesc['descriptionPreferred']
    
    description = []
    description.append(sourcedesc)
    sourceOutput['descriptions'] = description
                      
    # format sources
    sourceOutput['sharedUsers'] = [result.get('username')]
    
    return sourceOutput
