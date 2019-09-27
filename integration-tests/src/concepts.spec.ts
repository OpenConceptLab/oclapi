import { TestHelper } from './testHelper';

describe('Concept', () => {
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

    async function shouldListConcepts(from: string, who?: string) {
        const res = await helper.get(helper.joinUrl(from, 'concepts'), who);
        const json = await res.json();

        expect(json).toEqual([]);
    }

    it('should list concepts from viewable source for anonymous', async () => {
        await shouldListConcepts(helper.viewSourceUrl);
    });

    it('should list concepts from editable source for anonymous', async () => {
        await shouldListConcepts(helper.editSourceUrl);
    });

    it('should not list concepts from private source for anonymous', async () => {
        const res = await helper.get(helper.joinUrl(helper.privateSourceUrl, 'concepts'));
        expect(res.status).toBe(401)
    });

    it('should list concepts from public source for nonmember', async () => {
        await shouldListConcepts(helper.viewSourceUrl, helper.regularNonMemberUserToken);
    });

    it('should list concepts from editable source for nonmember', async () => {
        await shouldListConcepts(helper.editSourceUrl, helper.regularNonMemberUserToken);
    });

    it('should not list concepts from private source for nonmember', async () => {
        const res = await helper.get(helper.joinUrl(helper.privateSourceUrl, 'concepts'), helper.regularNonMemberUserToken);
        expect(res.status).toBe(403)
    });

    it('should list concepts from public source for member', async () => {
        await shouldListConcepts(helper.viewSourceUrl, helper.regularMemberUserToken);
    });

    it('should list concepts from editable source for member', async () => {
        await shouldListConcepts(helper.editSourceUrl, helper.regularMemberUserToken);
    });

    it('should not list concepts from private source for member', async () => {
        await shouldListConcepts(helper.privateSourceUrl, helper.regularMemberUserToken);
    });

    it('should list concepts from public source for staff', async () => {
        await shouldListConcepts(helper.viewSourceUrl, helper.adminToken);
    });

    it('should list concepts from editable source for staff', async () => {
        await shouldListConcepts(helper.editSourceUrl, helper.adminToken);
    });

    it('should not list concepts from private source for staff', async () => {
        await shouldListConcepts(helper.privateSourceUrl, helper.adminToken);
    });

    it('should list concepts from viewable collection for anonymous', async () => {
        await shouldListConcepts(helper.viewCollectionUrl);
    });

    it('should list concepts from editable collection for anonymous', async () => {
        await shouldListConcepts(helper.editCollectionUrl);
    });

    it('should not list concepts from private collection for anonymous', async () => {
        const res = await helper.get(helper.joinUrl(helper.privateCollectionUrl, 'concepts'));
        expect(res.status).toBe(401)
    });

    it('should list concepts from public collection for nonmember', async () => {
        await shouldListConcepts(helper.viewCollectionUrl, helper.regularNonMemberUserToken);
    });

    it('should list concepts from editable collection for nonmember', async () => {
        await shouldListConcepts(helper.editCollectionUrl, helper.regularNonMemberUserToken);
    });

    it('should not list concepts from private collection for nonmember', async () => {
        const res = await helper.get(helper.joinUrl(helper.privateCollectionUrl, 'concepts'), helper.regularNonMemberUserToken);
        expect(res.status).toBe(403)
    });

    it('should list concepts from public collection for member', async () => {
        await shouldListConcepts(helper.viewCollectionUrl, helper.regularMemberUserToken);
    });

    it('should list concepts from editable collection for member', async () => {
        await shouldListConcepts(helper.editCollectionUrl, helper.regularMemberUserToken);
    });

    it('should not list concepts from private collection for member', async () => {
        await shouldListConcepts(helper.privateCollectionUrl, helper.regularMemberUserToken);
    });

    it('should list concepts from public collection for staff', async () => {
        await shouldListConcepts(helper.viewCollectionUrl, helper.adminToken);
    });

    it('should list concepts from editable collection for staff', async () => {
        await shouldListConcepts(helper.editCollectionUrl, helper.adminToken);
    });

    it('should not list concepts from private collection for staff', async () => {
        await shouldListConcepts(helper.privateCollectionUrl, helper.adminToken);
    });

    it('should not be created in public source by anonymous', async () => {
        let conceptId = helper.newId('Concept');
        let response = await helper.postConcept(helper.viewSourceUrl, conceptId);
        expect(response.status).toBe(401);
    });

    it('should not be created in private source by anonymous', async () => {
        let conceptId = helper.newId('Concept');
        let response = await helper.postConcept(helper.privateSourceUrl, conceptId);
        expect(response.status).toBe(401);
    });

    it('should not be created in editable source by anonymous', async () => {
        let conceptId = helper.newId('Concept');
        let response = await helper.postConcept(helper.editSourceUrl, conceptId);
        expect(response.status).toBe(401);
    });

    it('should not be created in public source by nonmember', async () => {
        let conceptId = helper.newId('Concept');
        let response = await helper.postConcept(helper.viewSourceUrl, conceptId, helper.regularNonMemberUserToken);
        expect(response.status).toBe(403);
    });

    it('should not be created in private source by nonmember', async () => {
        let conceptId = helper.newId('Concept');
        let response = await helper.postConcept(helper.privateSourceUrl, conceptId, helper.regularNonMemberUserToken);
        expect(response.status).toBe(403);
    });

    it('should be created in editable source by nonmember', async () => {
        let conceptId = helper.newId('Concept');
        let response = await helper.postConcept(helper.editSourceUrl, conceptId, helper.regularNonMemberUserToken);
        expect(response.status).toBe(201);
    });
});


