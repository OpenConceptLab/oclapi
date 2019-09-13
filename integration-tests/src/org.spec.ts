import {get, post, del, newUser, authenticateAdmin, authenticate} from './utils';
import api from "./api";

describe('Org', () => {
    const uniqueId = '6a5bb179';
    const regularUser = 'Test' + uniqueId + 'User';
    const regularUserUrl = '/users/' + regularUser + '/';
    const nonPublicOrg = 'Test' + uniqueId + 'Org';
    const nonPublicOrgUrl = '/orgs/' + nonPublicOrg + '/';
    const nonPublicAdminOrg = 'Test' + uniqueId + 'AdminOrg';
    const nonPublicAdminOrgUrl = '/orgs/' + nonPublicAdminOrg + '/';
    let adminToken = null;
    let regularUserToken = null;
    let cleanup = async () => {};

    const orgIdToUrl = (orgId: string): string => {
        return '/orgs/' + orgId + '/';
    };

    const newOrgId = (): string => {
        return 'Test' + uniqueId + new Date().getTime() + 'Org';
    };

    const newOrg = api.organizations.new;

    const newCleanup = (url: string): (() => Promise<void>) => {
        return async () => {
            await del(url, adminToken);
        };
    };

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

    afterEach( async() => {
        await cleanup();
    });

    it('should list only public orgs for anonymous', async () => {
        const res = await get('orgs/');
        const json = await res.json();

        expect(json).toEqual(expect.arrayContaining([ { id: 'OCL', name: 'Open Concept Lab', url: '/orgs/OCL/' } ]));
        expect(json).toEqual(expect.not.arrayContaining([ { id: nonPublicOrg, name: nonPublicOrg, url: nonPublicOrgUrl } ]));
        expect(json).toEqual(expect.not.arrayContaining([ { id: nonPublicAdminOrg, name: nonPublicAdminOrg, url: nonPublicAdminOrgUrl } ]));
    });

    test('orgs list should not be affected by query params', async () => {
        const res = await get('orgs/?q=*');
        const json = await res.json();

        expect(json).toEqual(expect.arrayContaining([ { id: 'OCL', name: 'Open Concept Lab', url: '/orgs/OCL/' } ]));
        expect(json).toEqual(expect.not.arrayContaining([ { id: nonPublicOrg, name: nonPublicOrg, url: nonPublicOrgUrl } ]));
        expect(json).toEqual(expect.not.arrayContaining([ { id: nonPublicAdminOrg, name: nonPublicAdminOrg, url: nonPublicAdminOrgUrl } ]));
    });

    it('should not be created by anonymous', async () => {
        const orgId = newOrgId();
        const orgUrl = orgIdToUrl(orgId);
        cleanup = newCleanup(orgUrl);
        const res = await newOrg(orgId, null, true);
        expect(res.status).toBe(401);

        const res2 = await get('orgs/', adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.not.arrayContaining([ { id: orgId, name: orgId, url: orgUrl} ]));
    });

    it('should not be updated by anonymous', async () => {
        const res = await post('orgs/OCL/', {'name': 'test'});
        expect(res.status).toBe(401);

        const res2 = await get('orgs/', adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ { id: 'OCL', name: 'Open Concept Lab', url: '/orgs/OCL/' } ]));
    });

    it('should not be deleted by anonymous', async () => {
        const res = await del('orgs/OCL/');
        expect(res.status).toBe(401);

        const res2 = await get('orgs/', adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ { id: 'OCL', name: 'Open Concept Lab', url: '/orgs/OCL/' } ]));
    });


    it('should list all orgs for staff', async () => {
        const res = await get('orgs/', adminToken);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([ { id: 'OCL', name: 'Open Concept Lab', url: '/orgs/OCL/' },
            {id: nonPublicOrg, name: nonPublicOrg, url: nonPublicOrgUrl},
            {id: nonPublicAdminOrg, name: nonPublicAdminOrg, url: nonPublicAdminOrgUrl}]));
    });

    it('should list public and belonging orgs for authenticated', async () => {
        const res = await get('orgs/', regularUserToken);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([ { id: 'OCL', name: 'Open Concept Lab', url: '/orgs/OCL/' },
            {id: nonPublicOrg, name: nonPublicOrg, url: nonPublicOrgUrl} ]));
        expect(json).toEqual(expect.not.arrayContaining([ { id: nonPublicAdminOrg, name: nonPublicAdminOrg, url: nonPublicAdminOrgUrl } ]));
    });

    it('should be updated by authenticated member', async () => {
        const orgId = newOrgId();
        const orgUrl = orgIdToUrl(orgId);
        await newOrg(orgId, regularUserToken);
        cleanup = newCleanup(orgUrl);

        const res = await post(orgUrl, {'name': 'test'}, regularUserToken);
        const json = await res.json();

        expect(json).toEqual(expect.objectContaining({ id: orgId, name: 'test', url: orgUrl }));
    });

    it('should not be updated by authenticated nonmember', async () => {
        const org = newOrgId();
        const res = await post('orgs/OCL/', {'name': org});
        expect(res.status).toBe(401);

        const res2 = await get('orgs/', adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ { id: 'OCL', name: 'Open Concept Lab', url: '/orgs/OCL/' } ]));
    });

    it('should not be deleted by authenticated member', async () => {
        const org = newOrgId()
        const orgUrl = orgIdToUrl(org);
        const res = await newOrg(org, regularUserToken, false);
        cleanup = newCleanup(orgUrl);
        ;
        const json = await res.json();
        expect(json).toEqual(expect.objectContaining({ id: org, name: org, url: orgUrl }));

        const res2 = await del(orgUrl, regularUserToken);
        expect(res2.status).toBe(403);

        const res3 = await get('orgs/', adminToken);
        const json3 = await res3.json();

        expect(json3).toEqual(expect.arrayContaining([ { id: org, name: org, url: orgUrl } ]));
    });

    it('should not be deleted by authenticated nonmember', async () => {
        const res = await del('orgs/OCL/', regularUserToken);
        expect(res.status).toBe(403);

        const res2 = await get('orgs/', adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ { id: 'OCL', name: 'Open Concept Lab', url: '/orgs/OCL/' } ]));
    });
});


