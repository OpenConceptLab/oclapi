from django.core.exceptions import ValidationError

__author__ = 'misternando'


class DictionaryItemMixin(object):

    @classmethod
    def create_initial_version(cls, obj, **kwargs):
        return None

    @classmethod
    def persist_new(cls, obj, **kwargs):
        errors = dict()
        user = kwargs.pop('owner', None)
        if not user:
            errors['owner'] = 'Concept owner cannot be null.'
        parent_resource = kwargs.pop('parent_resource', None)
        if not parent_resource:
            errors['parent'] = 'Concept parent cannot be null.'
        if errors:
            return errors
        obj.owner = user
        obj.parent = parent_resource
        try:
            obj.full_clean()
        except ValidationError as e:
            errors.update(e.message_dict)
        if errors:
            return errors

        parent_resource_version = kwargs.pop('parent_resource_version', None)
        if parent_resource_version is None:
            parent_resource_version = parent_resource.get_version_model().get_latest_version_of(parent_resource)
        child_list_attribute = kwargs.pop('child_list_attribute', 'concepts')

        initial_parent_children = getattr(parent_resource_version, child_list_attribute) or []
        initial_version = None
        errored_action = 'saving concept'
        persisted = False
        try:
            obj.save(**kwargs)

            # Create the initial version
            errored_action = 'creating initial version of dictionary item'
            initial_version = cls.create_initial_version(obj)

            # Associate the version with a version of the parent
            errored_action = 'associating dictionary item with parent resource'
            parent_children = getattr(parent_resource_version, child_list_attribute) or []
            child_id = initial_version.id if initial_version else obj.id
            parent_children.append(child_id)
            setattr(parent_resource_version, child_list_attribute, parent_children)
            parent_resource_version.save()

            # Save the initial version again to trigger the Solr update
            if initial_version is not None:
                initial_version.save()

            persisted = True
        finally:
            if not persisted:
                errors['non_field_errors'] = ['An error occurred while %s.' % errored_action]
                setattr(parent_resource_version, child_list_attribute, initial_parent_children)
                parent_resource_version.save()
                if initial_version:
                    initial_version.delete()
                obj.delete()
        return errors
