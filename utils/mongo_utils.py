import pymongo
from typing import Optional, List, Dict

class MongoUtils:
    def __init__(self, uri: str = "mongodb://localhost:27017/", db_name: str = "mydatabase"):
        self.client = pymongo.MongoClient(uri)
        self.db = self.client[db_name]

    def insert_one(self, collection_name: str, document: Dict) -> str:
        collection = self.db[collection_name]
        result = collection.insert_one(document)
        return str(result.inserted_id)

    def find_one(self, collection_name: str, query: Dict) -> Optional[Dict]:
        collection = self.db[collection_name]
        return collection.find_one(query)

    def find_many(self, collection_name: str, query: Dict) -> List[Dict]:
        collection = self.db[collection_name]
        return list(collection.find(query))

    def update_one(self, collection_name: str, query: Dict, update: Dict) -> int:
        collection = self.db[collection_name]
        result = collection.update_one(query, {"$set": update})
        return result.modified_count

    def delete_one(self, collection_name: str, query: Dict) -> int:
        collection = self.db[collection_name]
        result = collection.delete_one(query)
        return result.deleted_count

    def close(self):
        self.client.close()

mongoUtils=MongoUtils()

if __name__=="__main__":
    mongoUtils.insert_one("test")