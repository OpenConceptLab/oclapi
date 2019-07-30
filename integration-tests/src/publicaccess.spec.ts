import {get, post, del, put, authenticateAdmin, authenticate} from './utils';

describe('User', () => {
    const uniqueId = '6a5bb179';
    const testUser = 'Test' + uniqueId + 'User';
    const testUserUrl = '/users/' + testUser + '/';
    const nonPublicOrg = 'Test' + uniqueId + 'Org';
    const nonPublicOrgUrl = '/orgs/' + nonPublicOrg + '/';
    const nonPublicAdminOrg = 'Test' + uniqueId + 'AdminOrg';
    const nonPublicAdminOrgUrl = '/orgs/' + nonPublicAdminOrg + '/';
    let adminToken = null;
    let userToken = null;

    beforeAll(async () => {
        adminToken = await authenticateAdmin();
        await del(nonPublicAdminOrgUrl, adminToken); //just in case
        await post('orgs/', {id: nonPublicAdminOrg, name: nonPublicAdminOrg, public_access: 'None'}, adminToken);

        await del(testUserUrl, adminToken);
        await post('users/', {username: testUser, password: testUser, name: testUser, email: testUser + '@openconceptlab.org'}, adminToken);
        await put(testUserUrl + 'reactivate/', {username: testUser, password: testUser, name: testUser, email: testUser + '@openconceptlab.org'}, adminToken);

        userToken = await authenticate(testUser, testUser);
        await del(nonPublicOrgUrl, userToken); //just in case
        await post('orgs/', {id: nonPublicOrg, name: nonPublicOrg, public_access: 'None'}, userToken);
    });

    afterAll(async () => {
        await del(nonPublicOrgUrl, adminToken);
        await del(nonPublicAdminOrgUrl, adminToken);
        await del(testUserUrl, adminToken);
    });

    it('anonymous should list only public orgs', async () => {
        const res = await get('orgs/');
        const json = await res.json();

        expect(json).toEqual(expect.arrayContaining([ { id: 'OCL', name: 'Open Concept Lab', url: '/orgs/OCL/' } ]));
        expect(json).toEqual(expect.not.arrayContaining([ { id: nonPublicOrg, name: nonPublicOrg, url: nonPublicOrgUrl } ]));
        expect(json).toEqual(expect.not.arrayContaining([ { id: nonPublicAdminOrg, name: nonPublicAdminOrg, url: nonPublicAdminOrgUrl } ]));
    });

    it('admin should list all orgs', async () => {
        const res = await get('orgs/', adminToken);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([ { id: 'OCL', name: 'Open Concept Lab', url: '/orgs/OCL/' },
            {id: nonPublicOrg, name: nonPublicOrg, url: nonPublicOrgUrl},
            {id: nonPublicAdminOrg, name: nonPublicAdminOrg, url: nonPublicAdminOrgUrl}]));
    });

    it('test should list public and belonging orgs', async () => {
        const res = await get('orgs/', userToken);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([ { id: 'OCL', name: 'Open Concept Lab', url: '/orgs/OCL/' },
            {id: nonPublicOrg, name: nonPublicOrg, url: nonPublicOrgUrl} ]));
    });
});


