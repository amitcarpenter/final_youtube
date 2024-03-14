from pymongo import MongoClient

atlas_connection_string = "mongodb+srv://amitcarpenter:amitcarpenter@bms.oboxpe2.mongodb.net/?retryWrites=true&w=majority"
# atlas_connection_string = "mongodb://127.0.0.1"
client = MongoClient(atlas_connection_string)
db = client.test

collection = db.emails
collection_youtube = db.videos
collection_order = db.orders
collection_ips = db.ips
