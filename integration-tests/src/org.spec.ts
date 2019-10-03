import { TestHelper } from './testHelper';

describe('Org', () => {
    const helper = new TestHelper();

    beforeAll(async () => {
        await helper.beforeAll();
    });

    afterAll(async () => {
        await helper.afterAll();
    });

    afterEach( async() => {
        await helper.afterEach();
    });

    it('should list only public orgs for anonymous', async () => {
        const res = await helper.get('orgs/');
        const json = await res.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg('OCL', 'Open Concept Lab'),
            helper.toOrg(helper.viewOrg), helper.toOrg(helper.editOrg)]));
        expect(json).toEqual(expect.not.arrayContaining([ helper.toOrg(helper.privateOrg) ]));
        expect(json).toEqual(expect.not.arrayContaining([ helper.toOrg(helper.privateAdminOrg) ]));
    });

    test('orgs list should not be affected by query params', async () => {
        const res = await helper.get('orgs/?q=*');
        const json = await res.json();

        expect(json).toEqual(expect.arrayContaining([ { id: 'OCL', name: 'Open Concept Lab', url: '/orgs/OCL/' } ]));
        expect(json).toEqual(expect.not.arrayContaining([ helper.toOrg(helper.privateOrg) ]));
        expect(json).toEqual(expect.not.arrayContaining([ helper.toOrg(helper.privateAdminOrg) ]));
    });

    it('should not be created by anonymous', async () => {
        const orgId = helper.newId('Org');
        const orgUrl = helper.joinUrl('orgs', orgId);
        helper.cleanup(orgUrl);
        const res = await helper.postOrg(orgId, null);
        expect(res.status).toBe(401);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.not.arrayContaining([ helper.toOrg(orgId) ]));
    });

    it('should not be updated by anonymous', async () => {
        const res = await helper.post('orgs/OCL/', {'name': 'test'});
        expect(res.status).toBe(401);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg('OCL', 'Open Concept Lab') ]));
    });

    it('with none access should not be updated by anonymous', async () => {
        const res = await helper.post(helper.privateOrg, {'name': 'test'});
        expect(res.status).toBe(404);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg(helper.privateOrg) ]));
    });

    it('with view access should not be updated by anonymous', async () => {
        const res = await helper.post(helper.viewOrgUrl, {'name': 'test'});
        expect(res.status).toBe(401);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg(helper.viewOrg) ]));
    });

    it('with edit access should not be updated by anonymous', async () => {
        const res = await helper.post(helper.editOrgUrl, {'name': 'test'});
        expect(res.status).toBe(401);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg(helper.editOrg) ]));
    });

    it('should not be deleted by anonymous', async () => {
        const res = await helper.del('orgs/OCL/');
        expect(res.status).toBe(401);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg('OCL', 'Open Concept Lab')]));
    });

    it('with none access should not be deleted by anonymous', async () => {
        const res = await helper.del(helper.privateOrgUrl);
        expect(res.status).toBe(401);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg(helper.privateOrg)]));
    });

    it('with view access should not be deleted by anonymous', async () => {
        const res = await helper.del(helper.viewOrgUrl);
        expect(res.status).toBe(401);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg(helper.viewOrg)]));
    });

    it('with edit access should not be deleted by anonymous', async () => {
        const res = await helper.del(helper.editOrgUrl);
        expect(res.status).toBe(401);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg(helper.editOrg)]));
    });

    it('should list all orgs for staff', async () => {
        const res = await helper.get('orgs/', helper.adminToken);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([ helper.toOrg('OCL', 'Open Concept Lab'),
            helper.toOrg(helper.privateOrg), helper.toOrg(helper.privateAdminOrg),
            helper.toOrg(helper.viewOrg), helper.toOrg(helper.editOrg)]));
    });

    it('should be updated by staff', async () => {
        const orgId = helper.newId('Org')
        const orgUrl = helper.joinUrl('orgs', orgId);
        await helper.postOrg(orgId, helper.regularMemberUserToken);
        helper.cleanup(orgUrl);

        const res2 = await helper.post(orgUrl, {'name': 'test'}, helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.objectContaining(helper.toOrg(orgId, 'test')));
    });

    it('with none access should be updated by staff', async () => {
        const orgId = helper.newId('Org')
        const orgUrl = helper.joinUrl('orgs', orgId);
        await helper.postOrg(orgId, helper.regularMemberUserToken, 'None');
        helper.cleanup(orgUrl);

        const res2 = await helper.post(orgUrl, {'name': 'test'}, helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.objectContaining(helper.toOrg(orgId, 'test')));
    });

    it('with view access should be updated by staff', async () => {
        const orgId = helper.newId('Org')
        const orgUrl = helper.joinUrl('orgs', orgId);
        await helper.postOrg(orgId, helper.regularMemberUserToken, 'View');
        helper.cleanup(orgUrl);

        const res2 = await helper.post(orgUrl, {'name': 'test'}, helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.objectContaining(helper.toOrg(orgId, 'test')));
    });

    it('with edit access should be updated by staff', async () => {
        const orgId = helper.newId('Org')
        const orgUrl = helper.joinUrl('orgs', orgId);
        await helper.postOrg(orgId, helper.regularMemberUserToken, 'Edit');
        helper.cleanup(orgUrl);

        const res2 = await helper.post(orgUrl, {'name': 'test'}, helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.objectContaining(helper.toOrg(orgId, 'test')));
    });

    it('should be deleted by staff', async () => {
        const orgId = helper.newId('Org')
        const orgUrl = helper.joinUrl('orgs', orgId);
        const res = await helper.postOrg(orgId, helper.regularMemberUserToken);
        helper.cleanup(orgUrl);

        const json = await res.json();
        expect(json).toEqual(expect.objectContaining(helper.toOrg(orgId)));

        await helper.del(orgUrl, helper.adminToken);
        const res2 = await helper.get('orgs/', helper.adminToken);
        const json2 = await res2.json();

        expect(json2).toEqual(expect.not.arrayContaining([ helper.toOrg(orgId) ]));
    });

    it('with none access should be deleted by staff', async () => {
        const orgId = helper.newId('Org')
        const orgUrl = helper.joinUrl('orgs', orgId);
        const res = await helper.postOrg(orgId, helper.regularMemberUserToken, 'None');
        helper.cleanup(orgUrl);

        const json = await res.json();
        expect(json).toEqual(expect.objectContaining(helper.toOrg(orgId)));

        await helper.del(orgUrl, helper.adminToken);
        const res2 = await helper.get('orgs/', helper.adminToken);
        const json2 = await res2.json();

        expect(json2).toEqual(expect.not.arrayContaining([ helper.toOrg(orgId) ]));
    });

    it('with view access should be deleted by staff', async () => {
        const orgId = helper.newId('Org')
        const orgUrl = helper.joinUrl('orgs', orgId);
        const res = await helper.postOrg(orgId, helper.regularMemberUserToken, 'View');
        helper.cleanup(orgUrl);

        const json = await res.json();
        expect(json).toEqual(expect.objectContaining(helper.toOrg(orgId)));

        await helper.del(orgUrl, helper.adminToken);
        const res2 = await helper.get('orgs/', helper.adminToken);
        const json2 = await res2.json();

        expect(json2).toEqual(expect.not.arrayContaining([ helper.toOrg(orgId) ]));
    });

    it('with edit access should be deleted by staff', async () => {
        const orgId = helper.newId('Org')
        const orgUrl = helper.joinUrl('orgs', orgId);
        const res = await helper.postOrg(orgId, helper.regularMemberUserToken, 'Edit');
        helper.cleanup(orgUrl);

        const json = await res.json();
        expect(json).toEqual(expect.objectContaining(helper.toOrg(orgId)));

        await helper.del(orgUrl, helper.adminToken);
        const res2 = await helper.get('orgs/', helper.adminToken);
        const json2 = await res2.json();

        expect(json2).toEqual(expect.not.arrayContaining([ helper.toOrg(orgId) ]));
    });

    it('should list public and belonging orgs for authenticated member', async () => {
        const res = await helper.get('orgs/', helper.regularMemberUserToken);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([ helper.toOrg('OCL', 'Open Concept Lab'),
            helper.toOrg(helper.privateOrg), helper.toOrg(helper.viewOrg), helper.toOrg(helper.editOrg) ]));
        expect(json).toEqual(expect.not.arrayContaining([ helper.toOrg(helper.privateAdminOrg) ]));
    });

    it.skip('with query params should list should public and belonging orgs for authenticated member', async () => {
        const res = await helper.get('orgs/?q=*', helper.regularMemberUserToken);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([ helper.toOrg('OCL', 'Open Concept Lab'),
            helper.toOrg(helper.privateOrg), helper.toOrg(helper.viewOrg), helper.toOrg(helper.editOrg) ]));
        expect(json).toEqual(expect.not.arrayContaining([ helper.toOrg(helper.privateAdminOrg) ]));
    });

    it('should be updated by authenticated member', async () => {
        const orgId = helper.newId('Org');
        const orgUrl = helper.joinUrl('orgs', orgId);
        await helper.postOrg(orgId, helper.regularMemberUserToken);
        helper.cleanup(orgUrl);

        const res = await helper.post(orgUrl, {'name': 'test'}, helper.regularMemberUserToken);
        const json = await res.json();

        expect(json).toEqual(expect.objectContaining({ id: orgId, name: 'test', url: orgUrl }));
    });

    it('with none access should be updated by authenticated member', async () => {
        const orgId = helper.newId('Org');
        const orgUrl = helper.joinUrl('orgs', orgId);
        await helper.postOrg(orgId, helper.regularMemberUserToken, 'None');
        helper.cleanup(orgUrl);

        const res = await helper.post(orgUrl, {'name': 'test'}, helper.regularMemberUserToken);
        const json = await res.json();

        expect(json).toEqual(expect.objectContaining({ id: orgId, name: 'test', url: orgUrl }));
    });


    it('with view access should be updated by authenticated member', async () => {
        const orgId = helper.newId('Org');
        const orgUrl = helper.joinUrl('orgs', orgId);
        await helper.postOrg(orgId, helper.regularMemberUserToken, 'View');
        helper.cleanup(orgUrl);

        const res = await helper.post(orgUrl, {'name': 'test'}, helper.regularMemberUserToken);
        const json = await res.json();

        expect(json).toEqual(expect.objectContaining({ id: orgId, name: 'test', url: orgUrl }));
    });

    it('with edit access should be updated by authenticated member', async () => {
        const orgId = helper.newId('Org');
        const orgUrl = helper.joinUrl('orgs', orgId);
        await helper.postOrg(orgId, helper.regularMemberUserToken, 'Edit');
        helper.cleanup(orgUrl);

        const res = await helper.post(orgUrl, {'name': 'test'}, helper.regularMemberUserToken);
        const json = await res.json();

        expect(json).toEqual(expect.objectContaining({ id: orgId, name: 'test', url: orgUrl }));
    });

    it('should not be deleted by authenticated member', async () => {
        const orgId = helper.newId('Org')
        const orgUrl = helper.joinUrl('orgs', orgId);
        const res = await helper.postOrg(orgId, helper.regularMemberUserToken);
        helper.cleanup(orgUrl);

        const json = await res.json();
        expect(json).toEqual(expect.objectContaining(helper.toOrg(orgId)));

        const res2 = await helper.del(orgUrl, helper.regularMemberUserToken);
        expect(res2.status).toBe(403);

        const res3 = await helper.get('orgs/', helper.adminToken);
        const json3 = await res3.json();

        expect(json3).toEqual(expect.arrayContaining([ helper.toOrg(orgId) ]));
    });

    it('with none access should not be deleted by authenticated member', async () => {
        const orgId = helper.newId('Org')
        const orgUrl = helper.joinUrl('orgs', orgId);
        const res = await helper.postOrg(orgId, helper.regularMemberUserToken, 'None');
        helper.cleanup(orgUrl);

        const json = await res.json();
        expect(json).toEqual(expect.objectContaining(helper.toOrg(orgId)));

        const res2 = await helper.del(orgUrl, helper.regularMemberUserToken);
        expect(res2.status).toBe(403);

        const res3 = await helper.get('orgs/', helper.adminToken);
        const json3 = await res3.json();

        expect(json3).toEqual(expect.arrayContaining([ helper.toOrg(orgId) ]));
    });

    it('with view access should not be deleted by authenticated member', async () => {
        const orgId = helper.newId('Org')
        const orgUrl = helper.joinUrl('orgs', orgId);
        const res = await helper.postOrg(orgId, helper.regularMemberUserToken, 'View');
        helper.cleanup(orgUrl);

        const json = await res.json();
        expect(json).toEqual(expect.objectContaining(helper.toOrg(orgId)));

        const res2 = await helper.del(orgUrl, helper.regularMemberUserToken);
        expect(res2.status).toBe(403);

        const res3 = await helper.get('orgs/', helper.adminToken);
        const json3 = await res3.json();

        expect(json3).toEqual(expect.arrayContaining([ helper.toOrg(orgId) ]));
    });

    it('with edit access should not be deleted by authenticated member', async () => {
        const orgId = helper.newId('Org')
        const orgUrl = helper.joinUrl('orgs', orgId);
        const res = await helper.postOrg(orgId, helper.regularMemberUserToken, 'Edit');
        helper.cleanup(orgUrl);

        const json = await res.json();
        expect(json).toEqual(expect.objectContaining(helper.toOrg(orgId)));

        const res2 = await helper.del(orgUrl, helper.regularMemberUserToken);
        expect(res2.status).toBe(403);

        const res3 = await helper.get('orgs/', helper.adminToken);
        const json3 = await res3.json();

        expect(json3).toEqual(expect.arrayContaining([ helper.toOrg(orgId) ]));
    });


    it('should list public orgs for authenticated nonmember', async () => {
        const res = await helper.get('orgs/', helper.regularNonMemberUserToken);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([ helper.toOrg('OCL', 'Open Concept Lab'),
            helper.toOrg(helper.editOrg), helper.toOrg(helper.viewOrg)]));
        expect(json).toEqual(expect.not.arrayContaining([ helper.toOrg(helper.privateAdminOrg),
            helper.toOrg(helper.privateOrg) ]));
    });

    it('should not be updated by authenticated nonmember', async () => {
        const org = helper.newId('Org');
        const res = await helper.post('orgs/OCL/', {'name': org}, helper.regularNonMemberUserToken);
        expect(res.status).toBe(403);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg('OCL', 'Open Concept Lab') ]));
    });

    it('with none access should not be updated by authenticated nonmember', async () => {
        const org = helper.newId('Org');
        const res = await helper.post(helper.privateOrgUrl, {'name': org}, helper.regularNonMemberUserToken);
        expect(res.status).toBe(403);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg(helper.privateOrg) ]));
    });

    it('with view access should not be updated by authenticated nonmember', async () => {
        const org = helper.newId('Org');
        const res = await helper.post(helper.viewOrgUrl, {'name': org}, helper.regularNonMemberUserToken);
        expect(res.status).toBe(403);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg(helper.viewOrg) ]));
    });

    it('with edit access should be updated by authenticated nonmember', async () => {
        const orgId = helper.newId('Org')
        const orgUrl = helper.joinUrl('orgs', orgId);
        await helper.postOrg(orgId, helper.regularMemberUserToken, 'Edit');
        helper.cleanup(orgUrl);

        const org = helper.newId('Org');
        const res = await helper.post(orgUrl, {'name': org}, helper.regularNonMemberUserToken);
        expect(res.status).toBe(200);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg(orgId, org) ]));
    });

    it('should not be deleted by authenticated nonmember', async () => {
        const res = await helper.del('orgs/OCL/', helper.regularNonMemberUserToken);
        expect(res.status).toBe(403);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg('OCL', 'Open Concept Lab') ]));
    });

    it('with none access should not be deleted by authenticated nonmember', async () => {
        const res = await helper.del(helper.privateOrgUrl, helper.regularNonMemberUserToken);
        expect(res.status).toBe(403);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg(helper.privateOrg) ]));
    });

    it('with view access should not be deleted by authenticated nonmember', async () => {
        const res = await helper.del(helper.viewOrgUrl, helper.regularNonMemberUserToken);
        expect(res.status).toBe(403);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg(helper.viewOrg) ]));
    });

    it('with edit access should not be deleted by authenticated nonmember', async () => {
        const res = await helper.del(helper.editOrgUrl, helper.regularNonMemberUserToken);
        expect(res.status).toBe(403);

        const res2 = await helper.get('orgs/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.arrayContaining([ helper.toOrg(helper.editOrg) ]));
    });
});


