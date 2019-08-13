import { TestHelper } from './testHelper';

describe('Login', () => {
    const helper = new TestHelper();
    const loginUrl = 'users/login/';

    it('succeeds with correct credentials', async () => {
        const user = {username: TestHelper.config.adminUser, password: TestHelper.config.adminPassword};
        const res = await helper.post(loginUrl, user);

        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json.token).toBeDefined();
    });
    it('fails with invalid username', async () => {
        const user = {username:'someuser', password: 'somepassword'};
        const res = await helper.post(loginUrl, user);
        expect(res.status).toBe(401);
    });
    it('fails with invalid password', async () => {
        const user = {username:'admin', password: 'somepassword'};
        const res = await helper.post(loginUrl, user);
        expect(res.status).toBe(401);
    });
    it('fails with missing credentials', async () => {
        const user = {};
        const res = await helper.post(loginUrl, user);
        expect(res.status).toBe(400);
    });
    it('fails with missing username', async () => {
        const user = {password: 'Admin123'};
        const res = await helper.post(loginUrl, user);
        expect(res.status).toBe(400);
    });
    it('fails with missing password', async () => {
        const user = {username: 'admin'};
        const res = await helper.post(loginUrl, user);
        expect(res.status).toBe(400);
    });
    it('fails with username ignoring case', async () => {
        const user = {username: 'ADMIN', password: 'Admin123'};
        const res = await helper.post(loginUrl, user);
        expect(res.status).toBe(401);
    });
    it('fails with password ignoring case', async () => {
        const user = {username: 'admin', password: 'admin123'};
        const res = await helper.post(loginUrl, user);
        expect(res.status).toBe(401);
    });
});


