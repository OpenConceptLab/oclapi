import {put, get, post} from "./utils"
import {VerboseContainer} from "./types";

const common = {
    container: {
        list: type =>
                async (ownerUrl: string, token: string=null, verbose: boolean=true, otherQueryParams: string=''): Promise<VerboseContainer[]> =>
                    (await get(`${ownerUrl}${type}/?verbose=${verbose}${otherQueryParams}`, token)).json(),
        new: type =>
                async (ownerUrl: string, body:object, token:string): Promise<VerboseContainer[]> =>
                    (await post(`${ownerUrl}${type}/`, body, token)).json(),
    },
};

const api = {
    organizations: {
        new: async (orgId: string, token: string, publicAccess: boolean= true): Promise<Response> => publicAccess ?
            post('orgs/', {id: orgId, name: orgId}, token) :
            post('orgs/', {id: orgId, name: orgId, public_access: 'None'}, token),
        addNewMember: async (membersUrl, user, token) => put(`${membersUrl}${user}/`, undefined, token),
    },
    collections: {
        list: common.container.list('collections'),
        new: common.container.new('collections'),
    },
    sources: {
        list: common.container.list('sources'),
        new: common.container.new('sources'),
    },
};

export default api;
