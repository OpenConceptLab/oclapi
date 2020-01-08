import { TestHelper } from './testHelper';

describe('Source', () => {
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

    it('global search should list only public sources for anonymous', async () => {
        const res = await helper.get(helper.joinUrl('sources'));
        const json = await res.json();

        expect(json).toEqual(expect.arrayContaining([
            helper.toSource(helper.viewOrg, helper.viewSource), helper.toSource(helper.viewOrg, helper.editSource)]));

        expect(json).toEqual(expect.not.arrayContaining([ helper.toSource(helper.viewOrg, helper.privateSource) ]));
    });

    it('global search should list all sources for staff', async () => {
        const res = await helper.get('sources', helper.adminToken);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([helper.toSource(helper.viewOrg, helper.viewSource),
            helper.toSource(helper.viewOrg, helper.editSource), helper.toSource(helper.viewOrg, helper.privateSource)
        ]));
    });

    it('global search should list public and belonging sources for authenticated member', async () => {
        const res = await helper.get('sources', helper.regularMemberUserToken);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([
            helper.toSource(helper.viewOrg, helper.viewSource), helper.toSource(helper.viewOrg, helper.editSource),
            helper.toSource(helper.viewOrg, helper.privateSource) ]));
    });

    it('should list public and belonging sources for authenticated member', async () => {
        const res = await helper.get(helper.joinUrl(helper.viewOrgUrl, 'sources'), helper.regularMemberUserToken);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([
            helper.toSource(helper.viewOrg, helper.viewSource), helper.toSource(helper.viewOrg, helper.editSource),
            helper.toSource(helper.viewOrg, helper.privateSource) ]));
    });

    it('global search should list public and belonging sources for authenticated nonmember', async () => {
        const res = await helper.get('sources', helper.regularNonMemberUserToken);

        expect(res.status).toBe(200);
        const json = await res.json();

        expect(json).toEqual(expect.arrayContaining([
            helper.toSource(helper.viewOrg, helper.viewSource), helper.toSource(helper.viewOrg, helper.editSource)]));

        expect(json).toEqual(expect.not.arrayContaining([ helper.toSource(helper.viewOrg, helper.privateSource) ]));
    });

    it('should list only public sources for anonymous', async () => {
        const res = await helper.get(helper.joinUrl(helper.viewOrgUrl, 'sources'));
        const json = await res.json();

        expect(json).toEqual(expect.arrayContaining([
            helper.toSource(helper.viewOrg, helper.viewSource), helper.toSource(helper.viewOrg, helper.editSource)]));

        expect(json).toEqual(expect.not.arrayContaining([ helper.toSource(helper.viewOrg, helper.privateSource) ]));
    });

    it('should list all sources for staff', async () => {
        const res = await helper.get(helper.joinUrl(helper.viewOrgUrl, 'sources'), helper.adminToken);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([helper.toSource(helper.viewOrg, helper.viewSource),
            helper.toSource(helper.viewOrg, helper.editSource), helper.toSource(helper.viewOrg, helper.privateSource)
        ]));
    });

    it('should list only public sources for authenticated nonmember', async () => {
        const res = await helper.get(helper.joinUrl(helper.viewOrgUrl, 'sources'), helper.regularNonMemberUserToken);
        const json = await res.json();

        expect(json).toEqual(expect.arrayContaining([
            helper.toSource(helper.viewOrg, helper.viewSource), helper.toSource(helper.viewOrg, helper.editSource)]));

        expect(json).toEqual(expect.not.arrayContaining([ helper.toSource(helper.viewOrg, helper.privateSource) ]));
    });

    it('should list public and belonging sources in all orgs for authenticated member', async () => {
        const res = await helper.get(helper.joinUrl(helper.regularMemberUserUrl, 'orgs', 'sources'), helper.regularMemberUserToken);
        const res2 = await helper.get(helper.joinUrl('user', 'orgs', 'sources'), helper.regularMemberUserToken);

        expect(res.status).toBe(200);
        expect(res2.status).toBe(200);

        const json = await res.json();
        const json2 = await res2.json();

        expect(json).toEqual(expect.arrayContaining([
            helper.toSource(helper.viewOrg, helper.viewSource),
            helper.toSource(helper.viewOrg, helper.editSource),
            helper.toSource(helper.viewOrg, helper.privateSource),

            helper.toSource(helper.editOrg, helper.privateEditOrgOwnedSource),
        ]));
        expect(json).toEqual(json2);
    });

    it('should list all sources belonging to an authenticated user', async () => {
        const res = await helper.get(helper.joinUrl(helper.regularNonMemberUserUrl, 'sources'), helper.regularNonMemberUserToken);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([
            helper.toUserSource(helper.regularNonMemberUser, helper.privateUserOwnedSource),
            helper.toUserSource(helper.regularNonMemberUser, helper.viewUserOwnedSource) ]));
    });

    it('should list only public sources for anonymous user', async () => {
        const res = await helper.get(helper.joinUrl(helper.regularNonMemberUserUrl, 'sources'));

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json).toEqual(expect.arrayContaining([
            helper.toUserSource(helper.regularNonMemberUser, helper.viewUserOwnedSource),
        ]));
        expect(json).toEqual(expect.not.arrayContaining([
            helper.toUserSource(helper.regularNonMemberUser, helper.privateUserOwnedSource),
        ]));
    });

    it('should not be created by anonymous', async () => {
        const sourceId = helper.newId('Source');
        const res = await helper.postSource('OCL', sourceId, null);
        expect(res.status).toBe(403);

        const res2 = await helper.get('orgs/OCL/sources/', helper.adminToken);
        const json = await res2.json();

        expect(json).toEqual(expect.not.arrayContaining([ helper.toSource('OCL', sourceId) ]));
    });

    const updateSourceTestHelper = async(updateToken: string, publicAccess?: string, success?: boolean) => {
        const sourceId = helper.newId('Source')
        const sourceUrl = helper.joinUrl(helper.viewOrgUrl, 'sources', sourceId);
        await helper.postSource(helper.viewOrg, sourceId, helper.regularMemberUserToken, publicAccess);
        helper.cleanup(sourceUrl);

        const res2 = await helper.put(sourceUrl, {'name': 'test'}, updateToken);
        if (success == null || success) {
            expect(res2.status).toBe(200);
            const json = await res2.json();
            expect(json).toEqual(expect.objectContaining(helper.toSource(helper.viewOrg, sourceId, 'test')));
        } else {
            expect([403, 401]).toContain(res2.status);
            const json = await res2.json();
            expect(json).toEqual(expect.not.objectContaining(helper.toSource(helper.viewOrg, sourceId, 'test')));
        }
    };

    it('with none access should not be updated by anonymous', async () => {
        await updateSourceTestHelper(null, 'None', false);
    });

    it('with view access should not be updated by anonymous', async () => {
        await updateSourceTestHelper(null, 'View', false);
    });

    it('with edit access should not be updated by anonymous', async () => {
        await updateSourceTestHelper(null, 'Edit', false);
    });

    it('should be updated by staff', async () => {
        await updateSourceTestHelper(helper.adminToken);
    });

    it('with none access should be updated by staff', async () => {
        await updateSourceTestHelper(helper.adminToken, 'None');
    });

    it('with view access should be updated by staff', async () => {
        await updateSourceTestHelper(helper.adminToken, 'View');
    });

    it('with edit access should be updated by staff', async () => {
        await updateSourceTestHelper(helper.adminToken, 'Edit');
    });

    it('should be updated by authenticated member', async () => {
        await updateSourceTestHelper(helper.regularMemberUserToken);
    });

    it('with none access should be updated by authenticated member', async () => {
        await updateSourceTestHelper(helper.regularMemberUserToken, 'None');
    });

    it('with view access should be updated by authenticated member', async () => {
        await updateSourceTestHelper(helper.regularMemberUserToken, 'View');
    });

    it('with edit access should be updated by authenticated member', async () => {
        await updateSourceTestHelper(helper.regularMemberUserToken, 'Edit');
    });

    it('should not be updated by authenticated nonmember', async () => {
        await updateSourceTestHelper(helper.regularNonMemberUserToken, null, false);
    });

    it('with none access should not be updated by authenticated nonmember', async () => {
        await updateSourceTestHelper(helper.regularNonMemberUserToken, 'None', false);
    });

    it('with view access should not be updated by authenticated nonmember', async () => {
        await updateSourceTestHelper(helper.regularNonMemberUserToken, 'View', false);
    });

    it('with edit access should be updated by authenticated nonmember', async () => {
        await updateSourceTestHelper(helper.regularNonMemberUserToken, 'Edit');
    });

    const deleteSourceTestHelper = async (updateToken: string, publicAccess?: string, success?: boolean) => {
        const sourceId = helper.newId('Source');
        const sourceUrl = helper.joinUrl(helper.viewOrgUrl, 'sources', sourceId);
        const res = await helper.postSource(helper.viewOrg, sourceId, helper.regularMemberUserToken, publicAccess);
        helper.cleanup(sourceUrl);

        const json = await res.json();
        expect(json).toEqual(expect.objectContaining(helper.toSource(helper.viewOrg, sourceId)));

        const res2 = await helper.del(sourceUrl, updateToken);
        if (success == null || success) {
            expect(res2.status).toBe(204);
        } else {
            expect([403, 401]).toContain(res2.status);
        }

        const res3 = await helper.get(helper.joinUrl(helper.viewOrgUrl, 'sources'), helper.adminToken);
        const json3 = await res3.json();
        if (success == null || success) {
            expect(json3).toEqual(expect.not.arrayContaining([helper.toSource(helper.viewOrg, sourceId)]));
        } else {
            expect(json3).toEqual(expect.arrayContaining([helper.toSource(helper.viewOrg, sourceId)]));
        }
    };

    it('with none access should not be deleted by anonymous', async () => {
        await deleteSourceTestHelper(null, 'None', false);
    });

    it('with view access should not be deleted by anonymous', async () => {
        await deleteSourceTestHelper(null, 'View', false);
    });

    it('with edit access should not be deleted by anonymous', async () => {
        await deleteSourceTestHelper(null, 'Edit', false);
    });

    it('should be deleted by staff', async () => {
        await deleteSourceTestHelper(helper.adminToken);
    });

    it('with none access should be deleted by staff', async () => {
        await deleteSourceTestHelper(helper.adminToken, 'None');
    });

    it('with view access should be deleted by staff', async () => {
        await deleteSourceTestHelper(helper.adminToken, 'View');
    });

    it('with edit access should be deleted by staff', async () => {
        await deleteSourceTestHelper(helper.adminToken, 'Edit');
    });

    it('should be deleted by authenticated member', async () => {
        await deleteSourceTestHelper(helper.regularMemberUserToken);
    });

    it('with none access should not be deleted by authenticated member', async () => {
        await deleteSourceTestHelper(helper.regularMemberUserToken, 'None');
    });

    it('with view access should not be deleted by authenticated member', async () => {
        await deleteSourceTestHelper(helper.regularMemberUserToken, 'View');
    });

    it('with edit access should not be deleted by authenticated member', async () => {
        await deleteSourceTestHelper(helper.regularMemberUserToken, 'Edit');
    });

    it('should not be deleted by authenticated nonmember', async () => {
        await deleteSourceTestHelper(helper.regularNonMemberUserToken, null, false);
    });

    it('with none access should not be deleted by authenticated nonmember', async () => {
        await deleteSourceTestHelper(helper.regularNonMemberUserToken, 'None', false);
    });

    it('with view access should not be deleted by authenticated nonmember', async () => {
        await deleteSourceTestHelper(helper.regularNonMemberUserToken, 'View', false);
    });

    it('with edit access should be deleted by authenticated nonmember', async () => {
        await deleteSourceTestHelper(helper.regularNonMemberUserToken, 'Edit');
    });

    it('should not delete concept from previous source version after edit', async() => {
        //Given
        const sourceId = helper.newId('Source');
        const sourceUrl = helper.joinUrl(helper.viewOrgUrl, 'sources', sourceId);
        await helper.postSource(helper.viewOrg, sourceId, helper.regularMemberUserToken);
        helper.cleanup(sourceUrl);

        const conceptId = helper.newId('Concept');
        const conceptUrl = helper.joinUrl(sourceUrl, 'concepts', conceptId);
        let res = await helper.postConcept(sourceUrl, conceptId, helper.regularMemberUserToken);
        let json;

        res = await helper.post(helper.joinUrl(sourceUrl, 'versions'), { 'id': 'v1' }, helper.regularMemberUserToken);

        await helper.retry(async () =>{
            res = await helper.get(helper.joinUrl(sourceUrl, 'v1', 'concepts'), helper.regularMemberUserToken);
            json = await res.json();
            expect(json.length).toEqual(1);
        });

        //When
        res = await helper.put(conceptUrl, {'external_id': 'new value'}, helper.regularMemberUserToken);

        //Then
        await helper.retry(async () => {
            res = await helper.get(helper.joinUrl(sourceUrl, 'v1', 'concepts'), helper.regularMemberUserToken);
            json = await res.json();
            expect(json).toEqual([expect.objectContaining({'external_id': null})]);
            res = await helper.get(helper.joinUrl(sourceUrl, 'concepts'), helper.regularMemberUserToken);
            json = await res.json();
            expect(json).toEqual([expect.objectContaining({'external_id': 'new value'})]);
        });
    });
});


