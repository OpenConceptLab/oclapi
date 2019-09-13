import fetch from 'node-fetch';

export const config = {
    serverUrl: process.env.npm_config_url ? process.env.npm_config_url : process.env.npm_package_config_url,
    adminUser: process.env.npm_config_adminUser ? process.env.npm_config_adminUser : process.env.npm_package_config_adminUser,
    adminPassword: process.env.npm_config_adminPassword ? process.env.npm_config_adminPassword : process.env.npm_package_config_adminPassword
};

export const initHeaders = function(token, headers={}) {
    headers['Content-type'] = 'application/json';
    if (token != null) {
        headers['Authorization'] = 'Token ' + token;
    }
    return headers;
};

export const joinUrl = function (url, part) {
    url = url.endsWith('/') ? url : url + '/';
    part = part.startsWith('/') ? part.substring(1) : part;
    return url + part;
};

export const newUser = async function(username, password, adminToken) {
    const user = await post('users/', {username: username, password: password, name: username, email: username + '@openconceptlab.org'}, adminToken);
    await put('users/' + username + '/reactivate/', {username: username, password: password, name: username, email: username + '@openconceptlab.org'}, adminToken);
    return await user.json();
};

export const post = async function(url, body, token=null) {
    return fetch(joinUrl(config.serverUrl, url), {
        method: 'post',
        headers: initHeaders(await token),
        body: JSON.stringify(body)
    });
};

export const put = async function(url, body, token=null) {
    return fetch(joinUrl(config.serverUrl, url), {
        method: 'put',
        headers: initHeaders(await token),
        body: JSON.stringify(body)
    });
};

export const del = async function(url, token=null) {
    return fetch(joinUrl(config.serverUrl, url), {
        method: 'delete',
        headers: initHeaders(await token)
    });
};

export const get = async function(url, token=null) {
    return fetch(joinUrl(config.serverUrl, url + '?limit=100'), {
        method: 'get',
        headers: initHeaders(await token)
    });;
};

export const authenticate = async function(username, password) {
    const user = {username: username, password: password};
    const response = await post('users/login/', user);
    const json = await response.json();
    return json.token;
};

export const authenticateAdmin = async function() {
    return authenticate(config.adminUser, config.adminPassword);
};