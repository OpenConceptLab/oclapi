import fetch from 'node-fetch';

export class TestHelper {
    readonly uniqueId: string;
    adminToken: string;
    regularMemberUserToken: string;
    readonly regularMemberUser: string;
    readonly regularMemberUserUrl: string;
    regularNonMemberUserToken: string;
    readonly regularNonMemberUser: string;
    readonly regularNonMemberUserUrl: string;
    readonly nonPublicOrg: string;
    readonly nonPublicOrgUrl: string;
    readonly viewOrg: string;
    readonly viewOrgUrl: string;
    readonly editOrg: string;
    readonly editOrgUrl: string;
    readonly nonPublicAdminOrg: string;
    readonly nonPublicAdminOrgUrl: string;
    urlsToDelete: string[];
    static readonly config = {
        serverUrl: process.env.npm_config_url ? process.env.npm_config_url :
            (process.env.npm_package_config_url ? process.env.npm_package_config_url : 'http://localhost:8000'),
        adminUser: process.env.npm_config_adminUser ? process.env.npm_config_adminUser :
            (process.env.npm_package_config_adminUser ? process.env.npm_package_config_adminUser : 'admin'),
        adminPassword: process.env.npm_config_adminPassword ? process.env.npm_config_adminPassword :
            (process.env.npm_package_config_adminPassword ? process.env.npm_package_config_adminPassword : 'Admin123')
    };

    constructor() {
        this.uniqueId = Math.floor(Math.random() * 100000000).toString(16);
        this.regularMemberUser = this.newId('Member-User');
        this.regularMemberUserUrl = this.toUrl('users', this.regularMemberUser);
        this.regularNonMemberUser = this.newId('NonMember-User');
        this.regularNonMemberUserUrl = this.toUrl('users', this.regularNonMemberUser);
        this.nonPublicOrg = this.newId('Private-Org');
        this.nonPublicOrgUrl = this.toUrl('orgs', this.nonPublicOrg);
        this.nonPublicAdminOrg = this.newId('Private-Org');
        this.nonPublicAdminOrgUrl = this.toUrl('orgs', this.nonPublicAdminOrg);
        this.viewOrg = this.newId('View-Org');
        this.viewOrgUrl = this.toUrl('orgs', this.viewOrg);
        this.editOrg = this.newId('Edit-Org');
        this.editOrgUrl = this.toUrl('orgs', this.editOrg);
        this.urlsToDelete = [];
    }

    async beforeAll() {
        this.adminToken = await this.authenticateAdmin();
        await this.del(this.nonPublicAdminOrgUrl, this.adminToken);
        await this.postOrg(this.nonPublicAdminOrg, this.adminToken, 'None');

        await this.newUser(this.regularMemberUser, this.regularMemberUser);

        this.regularMemberUserToken = await this.authenticate(this.regularMemberUser, this.regularMemberUser);
        await this.del(this.nonPublicOrgUrl, this.regularMemberUserToken);
        await this.postOrg(this.nonPublicOrg, this.regularMemberUserToken, 'None');
        await this.postOrg(this.viewOrg, this.regularMemberUserToken, 'View');
        await this.postOrg(this.editOrg, this.regularMemberUserToken, 'Edit');

        await this.newUser(this.regularNonMemberUser, this.regularNonMemberUser);
        this.regularNonMemberUserToken = await this.authenticate(this.regularNonMemberUser, this.regularNonMemberUser);
    }

    async afterAll() {
        await this.del(this.regularNonMemberUserUrl, this.adminToken);
        await this.del(this.regularMemberUserUrl, this.adminToken);
        await this.del(this.viewOrgUrl, this.adminToken);
        await this.del(this.editOrgUrl, this.adminToken);
        await this.del(this.nonPublicOrgUrl, this.adminToken);
        await this.del(this.nonPublicAdminOrgUrl, this.adminToken);
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

    joinUrl(url, part, query=''): string {
        url = url.endsWith('/') ? url : url + '/';
        part = part.startsWith('/') ? part.substring(1) : part;
        if (query !== '') {
            query = '?' + query;
        }
        return url + part + query;
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
        return fetch(this.joinUrl(TestHelper.config.serverUrl, url, 'limit=100'), {
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

    toOrg(orgId: string, orgName: string=orgId) {
        return {id: orgId, name: orgName, url: this.toUrl('orgs', orgId)};
    }

    newId(type: string): string {
        let id = Math.floor(Math.random() * 100000000).toString(16);
        return 'Test-' + this.uniqueId + '-' + id + '-' + type;
    }

    toUrl(type: string, id: string) {
        return '/' + type + '/' + id + '/';
    }
};
