import {get, post, del, newUser, authenticateAdmin, authenticate} from './utils';

describe('User', () => {
    const uniqueId = '6a5bb179';
    const regularUser = 'Test' + uniqueId + 'User';
    const regularUserUrl = '/users/' + regularUser + '/';
    const nonPublicOrg = 'Test' + uniqueId + 'Org';
    const nonPublicOrgUrl = '/orgs/' + nonPublicOrg + '/';
    const nonPublicAdminOrg = 'Test' + uniqueId + 'AdminOrg';
    const nonPublicAdminOrgUrl = '/orgs/' + nonPublicAdminOrg + '/';
    let adminToken = null;
    let regularUserToken = null;

    beforeAll(async () => {
        adminToken = authenticateAdmin();
        await del(nonPublicAdminOrgUrl, adminToken);
        await post('orgs/', {id: nonPublicAdminOrg, name: nonPublicAdminOrg, public_access: 'None'}, adminToken);

        await newUser(regularUser, regularUser, adminToken);

        regularUserToken = authenticate(regularUser, regularUser);
        await del(nonPublicOrgUrl, regularUserToken);
        await post('orgs/', {id: nonPublicOrg, name: nonPublicOrg, public_access: 'None'}, regularUserToken);
    });

    afterAll(async () => {
        await del(nonPublicOrgUrl, adminToken);
        await del(nonPublicAdminOrgUrl, adminToken);
        await del(regularUserUrl, adminToken);
    });

    it('without authentication should list only public orgs', async () => {
        const res = await get('orgs/');
        const json = await res.json();

        expect(json).toEqual(expect.arrayContaining([ { id: 'OCL', name: 'Open Concept Lab', url: '/orgs/OCL/' } ]));
        expect(json).toEqual(expect.not.arrayContaining([ { id: nonPublicOrg, name: nonPublicOrg, url: nonPublicOrgUrl } ]));
        expect(json).toEqual(expect.not.arrayContaining([ { id: nonPublicAdminOrg, name: nonPublicAdminOrg, url: nonPublicAdminOrgUrl } ]));
    });

    it('with staff privileges should list all orgs', async () => {
        const res = await get('orgs/', adminToken);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([ { id: 'OCL', name: 'Open Concept Lab', url: '/orgs/OCL/' },
            {id: nonPublicOrg, name: nonPublicOrg, url: nonPublicOrgUrl},
            {id: nonPublicAdminOrg, name: nonPublicAdminOrg, url: nonPublicAdminOrgUrl}]));
    });

    it('with regular privileges should list public and belonging orgs', async () => {
        const res = await get('orgs/', regularUserToken);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([ { id: 'OCL', name: 'Open Concept Lab', url: '/orgs/OCL/' },
            {id: nonPublicOrg, name: nonPublicOrg, url: nonPublicOrgUrl} ]));
        expect(json).toEqual(expect.not.arrayContaining([ { id: nonPublicAdminOrg, name: nonPublicAdminOrg, url: nonPublicAdminOrgUrl } ]));
    });
});


