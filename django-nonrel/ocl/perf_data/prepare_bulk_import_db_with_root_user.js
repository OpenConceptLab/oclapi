var user_coll = db.auth_user;
var root_user = user_coll.find({username: "root"})[0];
var token = root_user._id;

var user_profile_object = { mnemonic: "root_user",
							hashed_password: "pbkdf2_sha256$12000$yMqFqGO18PDJ$EBtldEM060wWn0cgsQ+gW7Gr5BLy/Xl/9sXZw82bsbI=",
							user_id: root_user._id,
							updated_by: "root", 
							organizations: [ ], 
							created_at: new Date(), 
							is_active: true, 
							updated_at: new Date(),
							created_by: "root", 
							uri: "/users/root_user/",
							full_name: "Root",
							public_access: "View"};

var user_profile_coll = db.users_userprofile;
var root_user_profile = user_profile_coll.find(user_profile_object)[0];
if(!root_user_profile) {
  user_profile_coll.insert(user_profile_object);
  root_user_profile = user_profile_coll.find(user_profile_object)[0];
}

var org_sources = [{org: 'perf', source: 'src'},
				{org: 'IHTSDO', source: 'SNOMED-CT'},
				{org: 'WHO', source: 'ICD-10-WHO'},
				{org: 'AMPATH', source: 'AMPATH'},
				{org: 'IMO', source: 'IMO-ProblemIT'},
				{org: '3BT', source: '3BT'},
				{org: 'WICC', source: 'ICPC2'},
				{org: 'IHTSDO', source: 'SNOMED-NP'},
				{org: 'PIH', source: 'PIH'},
				{org: 'IMO', source: 'IMO-ProcedureIT'},
				{org: 'HL7', source: 'HL-7-CVX'},
				{org: 'Regenstrief', source: 'LOINC'},
				{org: 'PIH', source: 'PIH-Malawi'},
				{org: 'OpenMRS', source: 'org.openmrs.module.mdrtb'},
				{org: 'NLM', source: 'RxNORM'},
				{org: 'WHO', source: 'ICD-10-WHO-2nd'},
				{org: 'CIEL', source: 'SNOMED-MVP'},
				{org: 'NLM', source: 'RxNORM-Comb'},
				{org: 'OpenMRS', source: 'org.openmrs.module.emrapi'}
];

var org_coll = db.orgs_organization;
var source_coll = db.sources_source;
var source_version_coll = db.sources_sourceversion;
var creation_date = new Date();
for(var i=0;i<org_sources.length;i++) {
	var org_source = org_sources[i];
	var org_object = {full_name: 'perf_test_org ' + org_source.org, 
							mnemonic: org_source.org,
							name: org_source.org, 
							uri: '/orgs/'+org_source.org+'/', 
							public_access: 'View',
							created_by: 'root', 
							updated_by: 'root', 
							is_active: true, 
							created_at: creation_date, 
							updated_at: creation_date};
	var perf_org = org_coll.find(org_object)[0];
	if(!perf_org) {
		org_coll.insert(org_object);
		perf_org = org_coll.find(org_object)[0];
	}

	var org_type_object = db.django_content_type.find({model: 'organization'})[0];
	var source_object = {full_name: 'perf_test_source ' + org_source.source,
							mnemonic: org_source.source, 
							name: org_source.source,
							uri:'/orgs/'+org_source.org+'/sources/' + org_source.source + '/', 
							parent_id: perf_org._id.valueOf(), 
							parent_type_id: org_type_object._id, 
							default_locale: 'en', 
							source_type: 'Dictionary',
							public_access: 'View',
							created_by: 'root', 
							updated_by: 'root', 
							is_active: true, 
							created_at: creation_date, 
							updated_at: creation_date}

	var perf_source = source_coll.find(source_object)[0];
	if(!perf_source) {
		source_coll.insert(source_object);
		perf_source = source_coll.find(source_object)[0];
	}

	var source_type_object = db.django_content_type.find({model: 'source'})[0];
	var source_version_object = {full_name: 'perf_test_source ' + org_source.source, 
							mnemonic: 'HEAD',
							name: org_source.source, 
							uri:'/orgs/'+org_source.org+'/sources/' + org_source.source + '/HEAD/',
							concepts: [],
							mappings: [],
							versioned_object_id: perf_source._id.valueOf(), 
							versioned_object_type_id: source_type_object._id,
							default_locale: 'en',
							source_type: 'Dictionary',
							previous_version_id: null,
							released: false, 
							public_access: 'View',
							created_by: 'root', 
							updated_by: 'root', 
							is_active: true, 
							created_at: creation_date, 
							updated_at: creation_date};
	var perf_source_version = source_version_coll.find(source_version_object)[0];
	if(!perf_source_version) {
		source_version_coll.insert(source_version_object);
		perf_source_version = source_version_coll.find(source_version_object)[0];
	}
}
var perf_source = db.sources_source.find({mnemonic: 'src'})[0];
printjson(perf_source._id);