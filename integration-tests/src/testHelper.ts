import fetch from 'node-fetch';

export class TestHelper {
    readonly uniqueId: string;

    adminToken: string;

    regularMemberUserToken: string;
    readonly regularMemberUser: string;
    readonly regularMemberUserUrl: string;

    regularMemberUser2Token: string;
    readonly regularMemberUser2: string;
    readonly regularMemberUser2Url: string;

    regularNonMemberUserToken: string;
    readonly regularNonMemberUser: string;
    readonly regularNonMemberUserUrl: string;

    readonly org1: string;
    readonly org1Url: string;

    readonly privateOrg: string;
    readonly privateOrgUrl: string;

    readonly viewOrg: string;
    readonly viewOrgUrl: string;

    readonly editOrg: string;
    readonly editOrgUrl: string;

    readonly privateAdminOrg: string;
    readonly privateAdminOrgUrl: string;

    readonly privateSource: string;
    readonly privateSourceUrl: string;

    readonly viewSource: string;
    readonly viewSourceUrl: string;

    readonly editSource: string;
    readonly editSourceUrl: string;

    readonly privateEditOrgOwnedSource: string;
    readonly privateEditOrgOwnedSourceUrl: string;

    readonly privateCollection: string;
    readonly privateCollectionUrl: string;

    readonly viewCollection: string;
    readonly viewCollectionUrl: string;

    readonly editCollection: string;
    readonly editCollectionUrl: string;

    readonly privateEditOrgOwnedCollection: string;
    readonly privateEditOrgOwnedCollectionUrl: string;

    readonly privateUserOwnedSource: string;
    readonly privateUserOwnedSourceUrl: string;

    readonly privateOrg1OwnedSource: string;
    readonly privateOrg1OwnedSourceUrl: string;

    readonly viewUserOwnedSource: string;
    readonly viewUserOwnedSourceUrl: string;

    readonly privateUserOwnedCollection: string;
    readonly privateUserOwnedCollectionUrl: string;

    readonly viewUserOwnedCollection: string;
    readonly viewUserOwnedCollectionUrl: string;

    readonly privateUserOwnedConcept1: string;
    readonly privateUserOwnedConcept1Url: string;

    readonly privateUserOwnedConcept2: string;
    readonly privateUserOwnedConcept2Url: string;

    readonly privateOrg1OwnedConcept1: string;
    readonly privateOrg1OwnedConcept1Url: string;

    readonly privateOrg1OwnedConcept2: string;
    readonly privateOrg1OwnedConcept2Url: string;

    urlsToDelete: string[];
    static readonly config = {
        serverUrl: process.env.npm_config_url ? process.env.npm_config_url :
            (process.env.npm_package_config_url ? process.env.npm_package_config_url : 'http://localhost:8000'),
        adminUser: process.env.npm_config_adminUser ? process.env.npm_config_adminUser :
            (process.env.npm_package_config_adminUser ? process.env.npm_package_config_adminUser : 'root'),
        adminPassword: process.env.npm_config_adminPassword ? process.env.npm_config_adminPassword :
            (process.env.npm_package_config_adminPassword ? process.env.npm_package_config_adminPassword : 'Root123')
    };

    constructor() {
        this.uniqueId = Math.floor(Math.random() * 100000000).toString(16);

        this.regularMemberUser = this.newId('Member-User');
        this.regularMemberUserUrl = this.joinUrl('users', this.regularMemberUser);

        this.regularMemberUser2 = this.newId('Member-User-2');
        this.regularMemberUser2Url = this.joinUrl('users', this.regularMemberUser2);

        this.regularNonMemberUser = this.newId('NonMember-User');
        this.regularNonMemberUserUrl = this.joinUrl('users', this.regularNonMemberUser);

        this.org1 = this.newId('Org-1');
        this.org1Url = this.joinUrl('orgs', this.org1);

        this.privateOrg = this.newId('Private-Org');
        this.privateOrgUrl = this.joinUrl('orgs', this.privateOrg);

        this.privateAdminOrg = this.newId('Private-Org');
        this.privateAdminOrgUrl = this.joinUrl('orgs', this.privateAdminOrg);

        this.viewOrg = this.newId('View-Org');
        this.viewOrgUrl = this.joinUrl('orgs', this.viewOrg);

        this.editOrg = this.newId('Edit-Org');
        this.editOrgUrl = this.joinUrl('orgs', this.editOrg);

        this.privateSource = this.newId('Private-Source');
        this.privateSourceUrl = this.joinUrl('orgs', this.viewOrg, 'sources', this.privateSource);

        this.viewSource = this.newId('View-Source');
        this.viewSourceUrl = this.joinUrl(this.viewOrgUrl, 'sources', this.viewSource);

        this.editSource = this.newId('Edit-Source');
        this.editSourceUrl = this.joinUrl(this.viewOrgUrl, 'sources', this.editSource);

        this.privateEditOrgOwnedSource = this.newId('Private-Edit-Org-Owned-Source');
        this.privateEditOrgOwnedSourceUrl = this.joinUrl('orgs', this.editOrg, 'sources', this.privateEditOrgOwnedSource);

        this.privateCollection = this.newId('Private-Collection');
        this.privateCollectionUrl = this.joinUrl('orgs', this.viewOrg, 'collections', this.privateCollection);

        this.viewCollection = this.newId('View-Collection');
        this.viewCollectionUrl = this.joinUrl(this.viewOrgUrl, 'collections', this.viewCollection);

        this.editCollection = this.newId('Edit-Collection');
        this.editCollectionUrl = this.joinUrl(this.viewOrgUrl, 'collections', this.editCollection);

        this.privateEditOrgOwnedCollection = this.newId('Private-Edit-Org-Owned-Collection');
        this.privateEditOrgOwnedCollectionUrl = this.joinUrl('orgs', this.editOrg, 'collections', this.privateEditOrgOwnedCollection);

        this.privateUserOwnedSource = this.newId('Private-User-Owned-Source');
        this.privateUserOwnedSourceUrl = this.joinUrl(this.regularNonMemberUserUrl, 'sources', this.privateUserOwnedSource);

        this.privateOrg1OwnedSource = this.newId('Private-Org-1-Owned-Source');
        this.privateOrg1OwnedSourceUrl = this.joinUrl(this.org1Url, 'sources', this.privateOrg1OwnedSource);

        this.viewUserOwnedSource = this.newId('View-User-Owned-Source');
        this.viewUserOwnedSourceUrl = this.joinUrl(this.regularNonMemberUserUrl, 'sources', this.viewUserOwnedSource);

        this.privateUserOwnedCollection = this.newId('Private-User-Owned-Collection');
        this.privateUserOwnedCollectionUrl = this.joinUrl(this.regularNonMemberUserUrl, 'collections', this.privateUserOwnedCollection);

        this.viewUserOwnedCollection = this.newId('View-User-Owned-Collection');
        this.viewUserOwnedCollectionUrl = this.joinUrl(this.regularNonMemberUserUrl, 'collections', this.viewUserOwnedCollection);

        this.privateUserOwnedConcept1 = this.newId('Private-User-Owned-Concept-1');
        this.privateUserOwnedConcept1Url = this.joinUrl(this.privateUserOwnedSourceUrl, 'concepts', this.privateUserOwnedConcept1);

        this.privateUserOwnedConcept2 = this.newId('Private-User-Owned-Concept-2');
        this.privateUserOwnedConcept2Url = this.joinUrl(this.privateUserOwnedSourceUrl, 'concepts', this.privateUserOwnedConcept2);

        this.privateOrg1OwnedConcept1 = this.newId('Private-Org-1-Owned-Concept-1');
        this.privateOrg1OwnedConcept1Url = this.joinUrl(this.privateOrg1OwnedSourceUrl, 'concepts', this.privateOrg1OwnedConcept1);

        this.privateOrg1OwnedConcept2 = this.newId('Private-Org-1-Owned-Concept-2');
        this.privateOrg1OwnedConcept2Url = this.joinUrl(this.privateOrg1OwnedSourceUrl, 'concepts', this.privateOrg1OwnedConcept2);

        this.urlsToDelete = [];
    }

    async beforeAll() {
        this.adminToken = await this.authenticateAdmin();
        await this.del(this.privateAdminOrgUrl, this.adminToken);
        await this.postOrg(this.privateAdminOrg, this.adminToken, 'None');

        await this.newUser(this.regularMemberUser, this.regularMemberUser);
        this.regularMemberUserToken = await this.authenticate(this.regularMemberUser, this.regularMemberUser);

        await this.newUser(this.regularMemberUser2, this.regularMemberUser2);
        this.regularMemberUser2Token = await this.authenticate(this.regularMemberUser2, this.regularMemberUser2);

        await this.newUser(this.regularNonMemberUser, this.regularNonMemberUser);
        this.regularNonMemberUserToken = await this.authenticate(this.regularNonMemberUser, this.regularNonMemberUser);

        await this.del(this.org1Url, this.regularMemberUserToken);
        await this.postOrg(this.org1, this.regularMemberUserToken, 'None');
        await this.del(this.privateOrgUrl, this.regularMemberUserToken);
        await this.postOrg(this.privateOrg, this.regularMemberUserToken, 'None');
        await this.postOrg(this.viewOrg, this.regularMemberUserToken, 'View');
        await this.postOrg(this.editOrg, this.regularMemberUserToken, 'Edit');

        await this.addUserToOrg(this.org1, this.regularMemberUser);
        await this.addUserToOrg(this.org1, this.regularMemberUser2);

        await this.postSource(this.viewOrg, this.privateSource, this.regularMemberUserToken, 'None');
        await this.postSource(this.viewOrg, this.viewSource, this.regularMemberUserToken, 'View');
        await this.postSource(this.viewOrg, this.editSource, this.regularMemberUserToken, 'Edit');

        await this.postSource(this.editOrg, this.privateEditOrgOwnedSource, this.regularMemberUserToken, 'None');

        await this.postOrgCollection(this.viewOrg, this.privateCollection, this.regularMemberUserToken, 'None');
        await this.postOrgCollection(this.viewOrg, this.viewCollection, this.regularMemberUserToken, 'View');
        await this.postOrgCollection(this.viewOrg, this.editCollection, this.regularMemberUserToken, 'Edit');

        await this.postOrgCollection(this.editOrg, this.privateEditOrgOwnedCollection, this.regularMemberUserToken, 'None');

        await this.postUserSource(this.regularNonMemberUser, this.privateUserOwnedSource, this.regularNonMemberUserToken, 'None');
        await this.postOrgSource(this.org1, this.privateOrg1OwnedSource, this.regularMemberUserToken, 'None');
        await this.postUserSource(this.regularNonMemberUser, this.viewUserOwnedSource, this.regularNonMemberUserToken, 'View');

        await this.postUserCollection(this.regularNonMemberUser, this.privateUserOwnedCollection, this.regularNonMemberUserToken, 'None');
        await this.postUserCollection(this.regularNonMemberUser, this.viewUserOwnedCollection, this.regularNonMemberUserToken, 'View');

        await this.postConcept(this.privateUserOwnedSourceUrl, this.privateUserOwnedConcept1, this.regularNonMemberUserToken);
        await this.postConcept(this.privateUserOwnedSourceUrl, this.privateUserOwnedConcept2, this.regularNonMemberUserToken);

        await this.postConcept(this.privateOrg1OwnedSourceUrl, this.privateOrg1OwnedConcept1, this.regularMemberUserToken);
        await this.postConcept(this.privateOrg1OwnedSourceUrl, this.privateOrg1OwnedConcept2, this.regularMemberUserToken);
    }

    async afterAll() {
        await this.del(this.privateOrg1OwnedConcept2Url, this.adminToken);
        await this.del(this.privateOrg1OwnedConcept1Url, this.adminToken);

        await this.del(this.privateUserOwnedConcept2Url, this.adminToken);
        await this.del(this.privateUserOwnedConcept1Url, this.adminToken);

        await this.del(this.privateUserOwnedCollectionUrl, this.adminToken);
        await this.del(this.viewUserOwnedCollectionUrl, this.adminToken);

        await this.del(this.privateOrg1OwnedSourceUrl, this.adminToken);
        await this.del(this.privateUserOwnedSourceUrl, this.adminToken);
        await this.del(this.viewUserOwnedSourceUrl, this.adminToken);

        await this.del(this.privateEditOrgOwnedCollectionUrl, this.adminToken);

        await this.del(this.privateCollectionUrl, this.adminToken);
        await this.del(this.editCollectionUrl, this.adminToken);
        await this.del(this.viewCollectionUrl, this.adminToken);

        await this.del(this.privateEditOrgOwnedSourceUrl, this.adminToken);

        await this.del(this.privateSourceUrl, this.adminToken);
        await this.del(this.editSourceUrl, this.adminToken);
        await this.del(this.viewSourceUrl, this.adminToken);

        await this.del(this.viewOrgUrl, this.adminToken);
        await this.del(this.editOrgUrl, this.adminToken);
        await this.del(this.privateOrgUrl, this.adminToken);
        await this.del(this.org1Url, this.adminToken);
        await this.del(this.privateAdminOrgUrl, this.adminToken);

        await this.del(this.regularNonMemberUserUrl, this.adminToken);
        await this.del(this.regularMemberUser2Url, this.adminToken);
        await this.del(this.regularMemberUserUrl, this.adminToken);
    }

    async afterEach() {
        for (let url of this.urlsToDelete.reverse()) {
            await this.del(url, this.adminToken);
        }
    }

    cleanup(...urls: string[]) {
        this.urlsToDelete.push(...urls);
    }

    async newUser(username, password) {
        await this.post('users/', {username: username, password: password, name: username, email: username + '@openconceptlab.org'}, this.adminToken);
        await this.put('users/' + username + '/reactivate/', {username: username, password: password, name: username, email: username + '@openconceptlab.org'}, this.adminToken);
    }

    async addUserToOrg(orgId: string, userId: string) {
        return this.put(this.joinUrl('orgs', orgId, 'members', userId), undefined, this.adminToken);
    }

    async authenticateAdmin(): Promise<string> {
        return this.authenticate(TestHelper.config.adminUser, TestHelper.config.adminPassword);
    }

    async authenticate(username, password): Promise<string> {
        const user = {username: username, password: password};
        const response = await this.post('users/login/', user);
        const json = await response.json();
        return json.token;
    }

    initHeaders(token, headers={}) {
        headers['Content-type'] = 'application/json';
        if (token != null) {
            headers['Authorization'] = 'Token ' + token;
        }
        return headers;
    }

    joinUrl(...parts: string[]): string {
        let url = '';
        let firstPart = parts[0];
        if (firstPart.startsWith('http')) {
            if (firstPart.endsWith('/')) {
                firstPart = firstPart.substr(0, firstPart.length - 1);
            }
            url = firstPart;
            parts.shift();
        }
        for (let part of parts) {
            if (part.startsWith('/')) {
                part = part.substr(1);
            }
            if (part.endsWith('/')) {
                part = part.substr(0, part.length - 1);
            }
            url = url + '/' + part;
        }
        if (url.indexOf('?') === -1) url = url + '/';
        return url;
    }

    async post(url, body, token=null) {
        return fetch(this.joinUrl(TestHelper.config.serverUrl, url), {
            method: 'post',
            headers: this.initHeaders(await token),
            body: JSON.stringify(body)
        });
    }

    async put(url, body, token=null) {
        return fetch(this.joinUrl(TestHelper.config.serverUrl, url), {
            method: 'put',
            headers: this.initHeaders(await token),
            body: JSON.stringify(body)
        });
    }

    async del(url, token=null) {
        return fetch(this.joinUrl(TestHelper.config.serverUrl, url), {
            method: 'delete',
            headers: this.initHeaders(await token)
        });
    }

    async get(url, token=null) {
        let limitedUrl;
        if (url.indexOf('?') !== -1) {
            limitedUrl = url + '&limit=1000';
        } else {
            limitedUrl = url + '?limit=1000';
        }

        return fetch(this.joinUrl(TestHelper.config.serverUrl, limitedUrl), {
            method: 'get',
            headers: this.initHeaders(await token)
        });;
    }

    async postOrg(orgId: string, token: string, publicAccess: string=null): Promise<Response> {
        if (publicAccess == null) {
            return this.post('orgs/', {id: orgId, name: orgId}, token);
        } else {
            return this.post('orgs/', {id: orgId, name: orgId, public_access: publicAccess}, token);
        }
    }

    async postSource(orgId: string, sourceId: string, token: string, publicAccess: string=null): Promise<Response> {
        let response;
        if (publicAccess == null) {
            response = await this.post(this.joinUrl('orgs', orgId, 'sources'), {id: sourceId, name: sourceId}, token);
        } else {
            response = await this.post(this.joinUrl('orgs', orgId, 'sources'), {id: sourceId, name: sourceId, public_access: publicAccess}, token);
        }

        //hacky way to wait for index to be updated, implement proper query
        await new Promise(resolve => setTimeout(resolve, 1000));
        return response;
    }

    async postOrgCollection(orgId: string, collectionId: string, token: string, publicAccess: string=null): Promise<Response> {
        let response;
        if (publicAccess == null) {
            response = await this.post(this.joinUrl('orgs', orgId, 'collections'), {id: collectionId, name: collectionId}, token);
        } else {
            response = await this.post(this.joinUrl('orgs', orgId, 'collections'), {id: collectionId, name: collectionId, public_access: publicAccess}, token);
        }

        //hacky way to wait for index to be updated, implement proper query
        await new Promise(resolve => setTimeout(resolve, 1000));
        return response;
    }

    async postUserSource(userId: string, sourceId: string, token: string, publicAccess: string=null): Promise<Response> {
        let response;
        if (publicAccess == null) {
            response = await this.post(this.joinUrl('users', userId, 'sources'), {id: sourceId, name: sourceId}, token);
        } else {
            response = await this.post(this.joinUrl('users', userId, 'sources'), {id: sourceId, name: sourceId, public_access: publicAccess}, token);
        }

        //hacky way to wait for index to be updated, implement proper query
        await new Promise(resolve => setTimeout(resolve, 1000));
        return response;
    }

    async postOrgSource(orgId: string, sourceId: string, token: string, publicAccess: string=null): Promise<Response> {
        let response;
        if (publicAccess == null) {
            response = await this.post(this.joinUrl('orgs', orgId, 'sources'), {id: sourceId, name: sourceId}, token);
        } else {
            response = await this.post(this.joinUrl('orgs', orgId, 'sources'), {id: sourceId, name: sourceId, public_access: publicAccess}, token);
        }

        //hacky way to wait for index to be updated, implement proper query
        await new Promise(resolve => setTimeout(resolve, 1000));
        return response;
    }

    async postUserCollection(userId: string, collectionId: string, token: string, publicAccess: string=null): Promise<Response> {
        let response;
        if (publicAccess == null) {
            response = await this.post(this.joinUrl('users', userId, 'collections'), {id: collectionId, name: collectionId}, token);
        } else {
            response = await this.post(this.joinUrl('users', userId, 'collections'), {id: collectionId, name: collectionId, public_access: publicAccess}, token);
        }

        //hacky way to wait for index to be updated, implement proper query
        await new Promise(resolve => setTimeout(resolve, 1000));
        return response;
    }

    async postConcept(sourceUrl: string, conceptId: string, token: string=null): Promise<Response> {
        let response;
        response = await this.post(this.joinUrl(sourceUrl, 'concepts'), {id: conceptId, datatype: 'None',
            concept_class: 'Test', names:[ { name: conceptId, locale: 'en', name_type: "FULLY_SPECIFIED" }]}, token);

        //hacky way to wait for index to be updated, implement proper query
        await new Promise(resolve => setTimeout(resolve, 1000));
        return response;
    }

    async postMapping(sourceUrl: string, fromUrl: string, toUrl: string, token: string=null): Promise<Response> {
        let response;
        response = await this.post(
            this.joinUrl(sourceUrl, 'mappings'),
            {from_concept_url: fromUrl, to_concept_url: toUrl, map_type: "NARROWER-THAN", external_id: this.newId('Mapping-External-Id')},
            token,
        );

        //hacky way to wait for index to be updated, implement proper query
        await new Promise(resolve => setTimeout(resolve, 1000));
        return response;
    }

    toOrg(orgId: string, orgName: string=orgId) {
        return {id: orgId, name: orgName, url: this.joinUrl('orgs', orgId)};
    }

    newId(type: string): string {
        let id = Math.floor(Math.random() * 100000000).toString(16);
        return 'Test-' + this.uniqueId + '-' + id + '-' + type;
    }

    toSource(orgId: string, sourceId: string, sourceName: string=sourceId) {
        return {name: sourceName, owner: orgId, owner_type: 'Organization', owner_url: this.joinUrl('orgs', orgId),
            short_code: sourceId, url: this.joinUrl('orgs', orgId, 'sources', sourceId)};
    }

    toUserSource(userId: string, sourceId: string, sourceName: string=sourceId) {
        return {name: sourceName, owner: userId, owner_type: 'User', owner_url: this.joinUrl('users', userId),
            short_code: sourceId, url: this.joinUrl('users', userId, 'sources', sourceId)};
    }

    toOrgCollection(orgId: string, collectionId: string, collectionName: string=collectionId) {
        return {id: collectionId, name: collectionName, owner: orgId, owner_type: 'Organization', owner_url: this.joinUrl('orgs', orgId),
            short_code: collectionId, url: this.joinUrl('orgs', orgId, 'collections', collectionId)};
    }

    toUserCollection(userId: string, collectionId: string, collectionName: string=collectionId) {
        return {id: collectionId, name: collectionName, owner: userId, owner_type: 'User', owner_url: this.joinUrl('users', userId),
            short_code: collectionId, url: this.joinUrl('users', userId, 'collections', collectionId)};
    }
};
