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


describe('Signup', () => {
    const helper = new TestHelper();
    const signUpUrl = 'users/signup/';
    const loginUrl = 'users/login/';

    it('allows user to create account', async () => {
        const username = helper.newId('user');
        const user = {
            username,
            name: "test_name",
            password: "test_password",
            email: `${username}test@openconceptlab.org`,
            email_verify_success_url: "https://example.org",
            email_verify_failure_url: "https://example.org",
        };
        const res = await helper.post(signUpUrl, user);

        expect(res.status).toBe(201);
        const json = await res.json();
        expect(json.username).toBe(user.username);
    });

    it('requires email confirmation', async () => {
        const username = helper.newId('user');
        const user = {
            username,
            name: "test_name",
            password: "test_password",
            email: `${username}test@openconceptlab.org`,
            email_verify_success_url: "https://example.org",
            email_verify_failure_url: "https://example.org",
        };
        await helper.post(signUpUrl, user);

        const loginResponse = await helper.post(loginUrl, {username: user.username, password: user.password});
        const json = await loginResponse.json();
        expect(json.detail).toContain("A verification email has been sent to the address on record.")
    });
});
