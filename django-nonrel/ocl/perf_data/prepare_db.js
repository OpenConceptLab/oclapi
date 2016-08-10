db.concepts_concept.remove({});
db.concepts_conceptversion.remove({});
var user_object = {first_name: 'Perf', 
					last_name: 'Test', 
					is_staff: true, 
					is_superuser: true, 
					username: 'perftest', 
					email: 'perftest@ocl.com', 
					date_joined: new Date()};

var user_coll = db.auth_user;
user_coll.remove({});
var perf_user = user_coll.find(user_object)[0];
if(!perf_user) {
  user_coll.insert(user_object);
  perf_user = user_coll.find(user_object)[0];
}

var user_profile_object = { mnemonic: "perftest", 
							hashed_password: "pbkdf2_sha256$12000$yMqFqGO18PDJ$EBtldEM060wWn0cgsQ+gW7Gr5BLy/Xl/9sXZw82bsbI=",
							user_id: perf_user._id, 
							updated_by: "perftest", 
							organizations: [ ], 
							created_at: new Date(), 
							is_active: true, 
							updated_at: new Date(),
							created_by: "perftest", 
							uri: "/users/perftest/", 
							full_name: "Perf Test", 
							public_access: "View"}

var user_profile_coll = db.users_userprofile;
user_profile_coll.remove({});
var perf_user_profile = user_profile_coll.find(user_profile_object)[0];
if(!perf_user_profile) {
  user_profile_coll.insert(user_profile_object);
  perf_user_profile = user_profile_coll.find(user_profile_object)[0];
}

var token_object = {_id: 'PERF_TEST_TOKEN', user_id: perf_user._id, created: new Date()}
var token_coll = db.authtoken_token;
token_coll.remove({});
var perf_user_token = token_coll.find(token_object)[0];
if(!perf_user_token) {
	token_coll.insert(token_object);
	perf_user_token = token_coll.find(token_object)[0];
}

var org_object = {full_name: 'perf_test_org', 
						mnemonic: 'perf',
						name: 'perf', 
						uri: '/orgs/perf/', 
						public_access: 'View',
						created_by: 'perftest', 
						updated_by: 'perftest', 
						is_active: true, 
						created_at: new Date(), 
						updated_at: new Date()}
var org_coll = db.orgs_organization;
org_coll.remove({});
var perf_org = org_coll.find(org_object)[0];
if(!perf_org) {
	org_coll.insert(org_object);
	perf_org = org_coll.find(org_object)[0];
}

var org_type_object = db.django_content_type.find({model: 'organization'})[0];
var source_object = {full_name: 'perf_test_source', 
						mnemonic: 'src', 
						name: 'src',
						uri:'/orgs/perf/sources/src/', 
						parent_id: perf_org._id.valueOf(), 
						parent_type_id: org_type_object._id, 
						default_locale: 'en', 
						source_type: 'Dictionary',
						public_access: 'View',
						created_by: 'perftest', 
						updated_by: 'perftest', 
						is_active: true, 
						created_at: new Date(), 
						updated_at: new Date()}
var source_coll = db.sources_source;
source_coll.remove({});
var perf_source = source_coll.find(source_object)[0];
if(!perf_source) {
	source_coll.insert(source_object);
	perf_source = source_coll.find(source_object)[0];
}

var source_type_object = db.django_content_type.find({model: 'source'})[0];
var source_version_object = {full_name: 'perf_test_source', 
						mnemonic: 'HEAD',
						name: 'src', 
						uri:'/orgs/perf/sources/src/HEAD/',
						concepts: [],
						mappings: [],
						versioned_object_id: perf_source._id.valueOf(), 
						versioned_object_type_id: source_type_object._id,
						default_locale: 'en',
						source_type: 'Dictionary',
						previous_version_id: null,
						released: false, 
						public_access: 'View',
						created_by: 'perftest', 
						updated_by: 'perftest', 
						is_active: true, 
						created_at: new Date(), 
						updated_at: new Date()}
var source_version_coll = db.sources_sourceversion;
source_version_coll.remove({});
var perf_source_version = source_version_coll.find(source_version_object)[0];
if(!perf_source_version) {
	source_version_coll.insert(source_version_object);
	perf_source_version = source_version_coll.find(source_version_object)[0];
}

printjson(perf_source._id);