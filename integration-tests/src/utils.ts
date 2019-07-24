import fetch from 'node-fetch';

export const config = {
    serverUrl: process.env.npm_config_url ? process.env.npm_config_url : process.env.npm_package_config_url,
    adminUser: process.env.npm_config_adminUser ? process.env.npm_config_adminUser : process.env.npm_package_config_adminUser,
    adminPassword: process.env.npm_config_adminPassword ? process.env.npm_config_adminPassword : process.env.npm_package_config_adminPassword
};

export const post = async function(url, body) {
    const response = fetch(config.serverUrl + 'users/login/', {
        method: 'post',
        headers: {
            "Content-type": "application/json"
        },
        body: JSON.stringify(body)
    });
    return response;
};
