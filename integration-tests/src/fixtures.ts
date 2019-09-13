import * as faker from 'faker';

export const container = (publicAccess = 'None', customValidationSchema='OpenMRS') => {
    return {
        type: "Collection",
        uuid: faker.random.uuid(),
        id: faker.random.number(),
        external_id: "",
        short_code: faker.company.bsNoun(),
        name: faker.company.companyName(),
        full_name: faker.company.companyName(),
        collection_type: "Core Dataset",
        public_access: publicAccess,
        supported_locales: "en,es",
        website: "",
        description: "",
        extras: {},
        custom_validation_schema: customValidationSchema,
    }
};
