__author__ = 'misternando'

class NonrelRouter(object):

    def db_for_read(self, model, **hints):
        if hasattr(model, 'db_for_read'):
            return getattr(model, 'db_for_read')()
        return False

    def db_for_write(self, model, **hints):
        if hasattr(model, 'db_for_write'):
            return getattr(model, 'db_for_write')()
        return False

    def allow_relation(self, obj1, obj2, **hints):
        if hasattr(obj1, 'allow_relation'):
            return getattr(obj1, 'allow_relation')(obj2, **hints)
        return False

    def allow_syncdb(self, db, model):
        if hasattr(model, 'allow_syncdb'):
            return getattr(model, 'allow_syncdb')(db)
        return False

