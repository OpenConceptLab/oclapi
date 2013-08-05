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
        
def formatcollection(result):
    
    collectionOutput = {}
    properties = {}
    auditInfo ={}
    collectionname = {}
    myusers ={}
    
    result['changedBy'] = result['changedby']
    
    tocopy = ['uuid','display','displayLocale','retired','collectionType','owner','publicAccess','starCount']
    for key in tocopy:
        copy_item(key,result,collectionOutput,'')
    
    tocopycollection = ['__type__']
    for key in tocopycollection:
        copy_item(key,result,collectionOutput,'OclCollection')
        
    toproperties= ['hl7Code','openmrsResourceVersion']
    for key in toproperties:
        copy_item(key,result,properties,'')
        
    toauditInfo = ['creator','dateCreated','changedBy','dateChanged']
    for key in toauditInfo:
        copy_item(key,result,auditInfo,'')
        
    tocollectionName = ['name','locale','preferred']
    for key in tocollectionName:
        copy_item(key,result,collectionname,'')
        
    tosharedUsers = ['username','access']
    for key in tosharedUsers:
        copy_item(key,result,myusers,'')

    #properties    
    collectionOutput['properties']= properties
    #auditInfo
    collectionOutput['auditInfo']= auditInfo
    
    #names
    names = []    
    names.append(collectionname)
    collectionOutput['names']= names
    
    sharedUsers =[]
    sharedUsers.append(myusers)
    collectionOutput['sharedUsers']= sharedUsers
    
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