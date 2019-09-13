import * as faker from 'faker';
import {authenticate, authenticateAdmin, newUser, del} from "./utils";
import { container as containerFixture } from "./fixtures";
import api from "./api";

const sortCriteria = (container1, container2) => {
    if (container1.id < container2.id) return -1;
    else if(container1.id > container2.id) return 1;
    else return 0;
};

const cleanupAnyPublicContainers = async (adminToken, containerType) => {
    const containers = await api[containerType].list('/');
    for(let i in containers) await del(containers[i].url, adminToken);
};

const delay = seconds => new Promise(resolve => setTimeout(resolve, seconds*1000));

describe.each([
    'sources',
    'collections',
])('View Authorization Tests: %s', container => {
    let adminToken;
    let user1InOrg1;
    let user2InOrg1;
    let user3NotInOrg1;
    let org1;
    let privateContainerOwnedByUser1;
    let privateContainerOwnedByOrg1;
    let publicContainerOwnedByUser1;
    let publicContainerOwnedByOrg1;

    beforeAll(async () => {
        adminToken = await authenticateAdmin();
        // in case an afterAll is not executed, public containers would not be deleted
        // and would interfere with the public access tests since they are not namespaced
        await cleanupAnyPublicContainers(adminToken, container);

        // making this as random as possible since we can't delete users
        const generateRandomName = () => faker.name.firstName() + faker.name.lastName();
        const username1 = generateRandomName();
        const username2 = generateRandomName();
        const username3 = generateRandomName();
        const orgId1 = generateRandomName();

        user1InOrg1 = await newUser(username1, username1, adminToken);
        user2InOrg1 = await newUser(username2, username2, adminToken);
        user3NotInOrg1 = await newUser(username3, username3, adminToken);
        user1InOrg1.token = await authenticate(username1, username1);
        user2InOrg1.token = await authenticate(username2, username2);
        user3NotInOrg1.token = await authenticate(username3, username3);

        org1 = await (await api.organizations.new(orgId1, adminToken)).json();
        await api.organizations.addNewMember(org1.members_url, user1InOrg1.username, adminToken);
        await api.organizations.addNewMember(org1.members_url, user2InOrg1.username, adminToken);

        privateContainerOwnedByUser1 = await api[container].new(user1InOrg1.url, containerFixture(), user1InOrg1.token);
        privateContainerOwnedByOrg1 = await api[container].new(org1.url, containerFixture(), user1InOrg1.token);
        publicContainerOwnedByUser1 = await api[container].new(user1InOrg1.url, containerFixture('View'), user1InOrg1.token);
        publicContainerOwnedByOrg1 = await api[container].new(org1.url, containerFixture('View'), user1InOrg1.token);

        await delay(2); // index updates take a second sometimes
    });

    afterAll(async () => {
        const items = [
            publicContainerOwnedByOrg1,
            publicContainerOwnedByUser1,
            privateContainerOwnedByOrg1,
            privateContainerOwnedByUser1,
            org1,
            user3NotInOrg1,
            user2InOrg1,
            user1InOrg1,
        ];
        for(let i in items) await del(items[i].url, adminToken);
    });

    describe('logged in user', () => {
        test(`can view own ${container}`, async () => {
            const results = (await api[container].list(`${user1InOrg1.url}`, user1InOrg1.token)).sort(sortCriteria);
            const expected = [publicContainerOwnedByUser1, privateContainerOwnedByUser1].sort(sortCriteria);
            expect(results).toEqual(expected);
        });

        test(`can view their orgs ${container}`, async () => {
            const results = (await api[container].list(`${org1.url}`, user2InOrg1.token)).sort(sortCriteria);
            const expected = [publicContainerOwnedByOrg1, privateContainerOwnedByOrg1].sort(sortCriteria);
            expect(results).toEqual(expected);
        });

        test(`can view another users public ${container}`, async () => {
            const results = (await api[container].list(`${user1InOrg1.url}`, user2InOrg1.token)).sort(sortCriteria);
            const expected = [publicContainerOwnedByUser1].sort(sortCriteria);
            expect(results).toEqual(expected);
        });

        test(`can view another orgs public ${container}`, async () => {
            const results = (await api[container].list(`${org1.url}`, user3NotInOrg1.token)).sort(sortCriteria);
            const expected = [publicContainerOwnedByOrg1].sort(sortCriteria);
            expect(results).toEqual(expected);
        });

        test(`cannot view another users private ${container}`, async () => {
            const results = await api[container].list(`${user1InOrg1.url}`, user2InOrg1.token);
            expect(results).not.toContain(privateContainerOwnedByUser1);
        });

        test(`cannot view another orgs private ${container}`, async () => {
            const results = await api[container].list(`${org1.url}`, user3NotInOrg1.token);
            expect(results).not.toContain(privateContainerOwnedByOrg1);
        });
    });

    describe('not logged in user', () => {
        test(`can view another users public ${container}`, async () => {
            const results = (await api[container].list(`${user1InOrg1.url}`)).sort(sortCriteria);
            const expected = [publicContainerOwnedByUser1].sort(sortCriteria);
            expect(results).toEqual(expected);
        });

        test(`can view another orgs public ${container}`, async () => {
            const results = (await api[container].list(`${org1.url}`)).sort(sortCriteria);
            const expected = [publicContainerOwnedByOrg1].sort(sortCriteria);
            expect(results).toEqual(expected);
        });

        test(`cannot view another users private ${container}`, async () => {
            const results = await api[container].list(`${user1InOrg1.url}`, user2InOrg1.token);
            expect(results).not.toContain(privateContainerOwnedByUser1);
        });

        test(`cannot view another orgs private ${container}`, async () => {
            const results = await api[container].list(`${org1.url}`);
            expect(results).not.toContain(privateContainerOwnedByOrg1);
        });
    });

    describe(`view all public ${container}`, () => {
        test('logged in user', async () => {
            const expected = [publicContainerOwnedByUser1, publicContainerOwnedByOrg1].sort(sortCriteria);

            let results = (await api[container].list('/', user1InOrg1.token)).sort(sortCriteria);
            expect(results).toEqual(expected);

            results = (await api[container].list('/', user2InOrg1.token)).sort(sortCriteria);
            expect(results).toEqual(expected);

            results = (await api[container].list('/', user3NotInOrg1.token)).sort(sortCriteria);
            expect(results).toEqual(expected);
        });

        test('not logged in user', async () => {
            const expected = [publicContainerOwnedByUser1, publicContainerOwnedByOrg1].sort(sortCriteria);
            const results = (await api[container].list('/')).sort(sortCriteria);
            expect(results).toEqual(expected);
        });
    });

    describe('query param tests', () => {
        test('using query params does not reset the queryset', async () => {
            const expected = [publicContainerOwnedByUser1, publicContainerOwnedByOrg1].sort(sortCriteria);
            const results = (await api[container].list('/', undefined, undefined, '&customValidationSchema=OpenMRS')).sort(sortCriteria);
            expect(results).toEqual(expected);
        });
    });
});
