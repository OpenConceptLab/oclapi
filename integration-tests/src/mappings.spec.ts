import { TestHelper } from './testHelper';

describe('Mapping', () => {
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

    async function shouldListMappings(from: string, who?: string) {
        const res = await helper.get(helper.joinUrl(from, 'mappings'), who);
        const json = await res.json();

        expect(json).toEqual([]);
    }

    async function shouldRetrieveMapping(from: string, id: string, who?: string) {
        const res = await helper.get(helper.joinUrl(from, 'mappings', id), who);
        const json = await res.json();

        expect(res.status).toBe(200);
        expect(json.id).toEqual(id);
    }

    it('should list mappings from viewable source for anonymous', async () => {
        await shouldListMappings(helper.viewSourceUrl);
    });

    it('should list mappings from editable source for anonymous', async () => {
        await shouldListMappings(helper.editSourceUrl);
    });

    it('should not list mappings from private source for anonymous', async () => {
        const res = await helper.get(helper.joinUrl(helper.privateSourceUrl, 'mappings'));
        expect(res.status).toBe(401)
    });

    it('should list mappings from public source for nonmember', async () => {
        await shouldListMappings(helper.viewSourceUrl, helper.regularNonMemberUserToken);
    });

    it('should list mappings from editable source for nonmember', async () => {
        await shouldListMappings(helper.editSourceUrl, helper.regularNonMemberUserToken);
    });

    it('should not list mappings from private source for nonmember', async () => {
        const res = await helper.get(helper.joinUrl(helper.privateSourceUrl, 'mappings'), helper.regularNonMemberUserToken);
        expect(res.status).toBe(403)
    });

    it('should list mappings from public source for member', async () => {
        await shouldListMappings(helper.viewSourceUrl, helper.regularMemberUserToken);
    });

    it('should list mappings from editable source for member', async () => {
        await shouldListMappings(helper.editSourceUrl, helper.regularMemberUserToken);
    });

    it('should not list mappings from private source for member', async () => {
        await shouldListMappings(helper.privateSourceUrl, helper.regularMemberUserToken);
    });

    it('should list mappings from public source for staff', async () => {
        await shouldListMappings(helper.viewSourceUrl, helper.adminToken);
    });

    it('should list mappings from editable source for staff', async () => {
        await shouldListMappings(helper.editSourceUrl, helper.adminToken);
    });

    it('should not list mappings from private source for staff', async () => {
        await shouldListMappings(helper.privateSourceUrl, helper.adminToken);
    });

    it('should list mappings from viewable collection for anonymous', async () => {
        await shouldListMappings(helper.viewCollectionUrl);
    });

    it('should list mappings from editable collection for anonymous', async () => {
        await shouldListMappings(helper.editCollectionUrl);
    });

    it('should not list mappings from private collection for anonymous', async () => {
        const res = await helper.get(helper.joinUrl(helper.privateCollectionUrl, 'mappings'));
        expect(res.status).toBe(401)
    });

    it('should list mappings from public collection for nonmember', async () => {
        await shouldListMappings(helper.viewCollectionUrl, helper.regularNonMemberUserToken);
    });

    it('should list mappings from editable collection for nonmember', async () => {
        await shouldListMappings(helper.editCollectionUrl, helper.regularNonMemberUserToken);
    });

    it('should not list mappings from private collection for nonmember', async () => {
        const res = await helper.get(helper.joinUrl(helper.privateCollectionUrl, 'mappings'), helper.regularNonMemberUserToken);
        expect(res.status).toBe(403)
    });

    it('should list mappings from public collection for member', async () => {
        await shouldListMappings(helper.viewCollectionUrl, helper.regularMemberUserToken);
    });

    it('should list mappings from editable collection for member', async () => {
        await shouldListMappings(helper.editCollectionUrl, helper.regularMemberUserToken);
    });

    it('should not list mappings from private collection for member', async () => {
        await shouldListMappings(helper.privateCollectionUrl, helper.regularMemberUserToken);
    });

    it('should list mappings from public collection for staff', async () => {
        await shouldListMappings(helper.viewCollectionUrl, helper.adminToken);
    });

    it('should list mappings from editable collection for staff', async () => {
        await shouldListMappings(helper.editCollectionUrl, helper.adminToken);
    });

    it('should not list mappings from private collection for staff', async () => {
        await shouldListMappings(helper.privateCollectionUrl, helper.adminToken);
    });

    it('should retrieve private mapping if mapping owner', async () => {
        const res = await helper.postMapping(helper.privateUserOwnedSourceUrl, helper.privateUserOwnedConcept1Url, helper.privateUserOwnedConcept2Url, helper.regularNonMemberUserToken);
        const json = await res.json();
        await shouldRetrieveMapping(helper.privateUserOwnedSourceUrl, json.id, helper.regularNonMemberUserToken)
    });

    it('should retrieve private mapping if org member', async () => {
        const res = await helper.postMapping(helper.privateOrg1OwnedSourceUrl, helper.privateOrg1OwnedConcept1Url, helper.privateOrg1OwnedConcept2Url, helper.regularMemberUserToken);
        const json = await res.json();
        await shouldRetrieveMapping(helper.privateOrg1OwnedSourceUrl, json.id, helper.regularMemberUser2Token)
    });
});


