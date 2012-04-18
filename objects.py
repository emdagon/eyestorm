
from bson import ObjectId

import tornado
import asyncmongo

from eyestorm import options


# Dev purposes (will be removed)
from pprint import pprint


def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance


@singleton
class Db(object):
    """System-wide (singleton) asyncmongo client instance"""


    def __init__(self):
        self._config = options.db
        self._connection = asyncmongo.Client(**self._config)
        print("Mongo connection created")

    def get_config(self):
        return self._config

    def get_connection(self):
        return self._connection



class MongoHelper():


    def __init__(self, collection):
        self._collection = collection

    def set_criteria(self, criteria):
        if isinstance(criteria, ObjectId):
            self._criteria = {'_id': criteria}
        else:
            self._criteria = criteria

    def __getattr__(self, name):
        def method(field, value=None, callback=None):
            self._collection.update(spec=self._criteria,
                                    document={"$%s" % name: {field: value}},
                                    callback=callback)
        return method



class Persistable(object):
    """`Abstract` class that represent a mongo collection object.

    Provides the `db` attribute pointing to Db instance

    """


    def __init__(self):
        self._db = None

    @property
    def db(self):
        self._initialize_db()
        return self._db

    def _initialize_db(self):
        if self._db is None:
            self._db = Db().get_connection()

    def _set_collection(self, collection):
        self._initialize_db()
        self._collection_name = collection
        self._collection = getattr(self._db, collection)
        self.operate = MongoHelper(self._collection)

    def get_collection_name(self):
        return self._collection_name

    def sleep(self):
        self._collection = None
        self._db = None

    def wakeup(self):
        self._set_collection(self._collection_name)



class Entity(Persistable):


    _private_attributes = ['_db', '_attributes', '_callback', '_collection',
                           '_collection_name', '_error', '_exists',
                           '_private_attributes', 'operate']

    def __init__(self, collection=None):
        super(Entity, self).__init__()
        self._private_attributes = []
        self._attributes = {}
        self._collection = None
        self._callback = None
        self._error = None
        self._exists = False
        if collection:
            self._set_collection(collection)

    def __getattr__(self, name):
        if name in Entity._private_attributes + \
                        object.__getattribute__(self, '_private_attributes'):
            return object.__getattribute__(self, name)
        elif name in self._attributes:
            return self._attributes[name]
        return None

    def __setattr__(self, name, value):
        if name in Entity._private_attributes + \
                        object.__getattribute__(self, '_private_attributes'):
            self.__dict__[name] = value
        else:
            self._attributes[name] = value

    def __delattr__(self, name):
        if name in self._attributes[name]:
            del self._attributes[name]

    def _return(self):
        if callable(self._callback):
            self._callback(entity=self, error=self._error)


    def response_dict(self):
        attributes = self._attributes.copy()
        if '_id' in attributes:
            attributes['_id'] = str(attributes['_id'])
        return attributes

    def response_json(self):
        return tornado.escape.json_encode(self.response_dict())

    def set_attributes(self, attributes, exists=False):
        self._exists = exists
        self._attributes = attributes.copy()

    def update_attributes(self, attributes):
        self._attributes.update(attributes)

    def update_attribute(self, attribute, value):
        self._attributes[attribute] = value

    def get_attributes(self):
        return self._attributes

    def exists(self):
        return (self._exists and '_id' in self._attributes)


    def load(self, _id=None, attributes=None, callback=None,
             **kwargs):
        self._callback = callback
        if _id != None:
            self._id = ObjectId(_id)
            self.operate.set_criteria(self._id)
            self._collection.find_one({'_id': self._id},
                                        callback=self._on_load, **kwargs)
        elif isinstance(attributes, dict):
            self.operate.set_criteria(attributes)
            self._collection.find_one(attributes,
                                        callback=self._on_load, **kwargs)

    def _on_load(self, result, error):
        if result:
            self._attributes = result
            self._exists = True
            self.operate.set_criteria(self._id)
        else:
            self._error = error
        self._return()


    def save(self, callback=None, force_update=False):
        self._callback = callback
        if self.exists() or force_update:
            self._update()
        else:
            self._insert()

    def _insert(self):
        if not '_id' in self._attributes:
            self._attributes['_id'] = ObjectId()
        self._collection.insert(self._attributes, callback=self._on_insert)

    def _on_insert(self, result, error):
        if result:
            self._exists = True
        self._error = error
        self._return()

    def _update(self):
        self._collection.update({'_id': self._attributes['_id']},
                                self._attributes, callback=self._on_update)

    def _on_update(self, result, error):
        if result:
            self._exists = True
        self._error = error
        self._return()

    def update(self, callback):
        if self.exists():
            document = self._attributes.copy()
            del document['_id']
            self._collection.update({'_id': self._attributes['_id']},
                                    {'$set': document},
                                    callback=callback)
        else:
            self.save(callback)


    def delete(self, _id=None, criteria=None, callback=None):
        self._callback = callback
        if _id:
            self._collection.remove(ObjectId(_id), callback=self._on_delete)
        elif criteria:
            self._collection.remove(criteria, callback=self._on_delete)
        elif self.exists():
            self._collection.remove(self._attributes['_id'],
                                    callback=self._on_delete)
        else:
            return False

    def _on_delete(self, result, error):
        if not error:
            self._exists = False
        self._error = error
        self._return()



class Collection(Persistable):


    def __init__(self, collection):
        super(Collection, self).__init__()
        self._data = []
        self.attributes = None
        self._indexes = {}
        self._set_collection(collection)

    def __getitem__(self, index):
        return self._data[index]

    def __len__(self):
        return len(self._data)


    def load(self, attributes=None, callback=None, **kwargs):
        self._callback = callback
        if not isinstance(attributes, dict):
            attributes = {}
        self.attributes = attributes
        self.operate.set_criteria(attributes)
        self._collection.find(attributes, callback=self._on_load, **kwargs)

    def _on_load(self, result, error):
        if not error:
            self._data = result
            self.operate.set_criteria(self.attributes)
        self._callback(collection=self, error=error)


    def insert(self, items, callback=None):
        self._callback = callback
        self._items = items
        self._collection.insert(items, callback=self._on_insert)

    def _on_insert(self, result, error):
        if not error:
            self.set_items(self._items)
        del self._items
        self._callback(self, error)


    def remove(self, attributes=None, callback=None, **kwargs):
        self._callback = callback
        if not isinstance(attributes, dict):
            attributes = {}
        self.attributes = attributes
        self._collection.remove(attributes, callback=self._on_remove, **kwargs)

    def _on_remove(self, result, error):
        self._error = error
        self._callback(result[0], error)


    def count(self, attributes=None, callback=None, **kwargs):
        def _callback(collection=None, error=None):
            callback(len(self._data))
        if len(self._data) > 0:
            _callback()
            return
        self.load(attributes, callback=_callback, **kwargs)


    def set_items(self, items):
        self._data = items

    def get_items(self):
        return self._data

    def get_response_dict(self):
        def stringfy(document):
            d = document.copy()
            d['_id'] = str(d['_id'])
            return d
        return map(stringfy, self._data)

    def get_attributes(self, attribute):
        return map(lambda d: d[attribute], self._data)


    def get_indexes(self, attribute):
        if not attribute in self._indexes:
            self._indexes[attribute] = {}
            for document in self._data:
                if attribute in document:
                    if not document[attribute] in self._indexes[attribute]:
                        self._indexes[attribute][document[attribute]] = []
                    self._indexes[attribute][document[attribute]].append(
                                                                    document)
        return self._indexes[attribute]

    def get_by_attribute(self, **attributes):
        result = []
        for key, value in attributes.items():
            indexes = self.get_indexes(key)
            if value in indexes:
                result = result + (indexes[value])
        return result


    def exists(self):
        return len(self._data) > 0


class Entities(Collection):


    def __getitem__(self, index):
        data = self._data[index]
        entity = Entity()
        entity._set_collection(self.get_collection_name())
        entity.set_attributes(data, True)
        return entity

