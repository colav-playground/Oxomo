from joblib import Parallel, delayed
from oaipmh.client import Client
from pymongo import MongoClient
import psutil


class OxomocCheckPoint:
    """
    Class to handle checkpoints for Colav OAI-PMH
    """

    def __init__(self, mongodb_uri="mongodb://localhost:27017/"):
        """
        CheckPoint constructor

        Parameters:
        ----------
        mongodb_uri:str
            MongoDB connection string uri
        """
        self.client = MongoClient(mongodb_uri)

    def create(self, base_url: str, mongo_db: str, mongo_collection: str, metadataPrefix='oai_dc', force_http_get=True):
        """
        Method to create the checkpoint, this allows to save all the ids for records and sets
        in order to know what was downloaded.
        All the checkpints are saved in the mongo collections

        Parameters:
        ----------
        base_url:str
            D-Space endpoint url
        mongo_db:str
            MongoDB database name
        mongo_collection:str
            MongoDB collection name
        metadataPrefix:str
            metadata type for xml schema ex: dim, xoai, mods, oai_dc (default: oai_dc)
        force_http_get:bool
            force to use get instead post for requests
        """

        client = Client(base_url, force_http_get=force_http_get)
        try:
            print(
                f"=== INFO: Checking identity for {mongo_collection} from  {base_url}")
            identity = client.identify()
        except BaseException as err:
            print(f"=== ERROR: Unexpected {err=}, {type(err)=}")
            print(f"=== ERROR: CheckPoint can not be created for {base_url}")
            return
        if metadataPrefix not in [i[0] for i in client.listMetadataFormats()]:
            print(
                f"=== ERROR: metadataPrefix {metadataPrefix}, not supported for {base_url}")
            print(
                f"=== ERROR: CheckPoint can not be created for {mongo_collection} omitting..")
            return

        print(
            f"=== INFO: Creating CheckPoint for {mongo_collection} from  {base_url}")
        info = {}
        info["repository_name"] = identity.repositoryName()
        info["admin_emails"] = identity.adminEmails()
        info["base_url"] = identity.baseURL()
        info["protocol_version"] = identity.protocolVersion()
        info["earliest_datestamp"] = identity.earliestDatestamp()
        info["granularity"] = identity.granularity()

        self.client[mongo_db][f"{mongo_collection}_identity"].drop()
        self.client[mongo_db][f"{mongo_collection}_identity"].insert_one(info)

        if self.exists_records(mongo_db, mongo_collection):
            print(
                f"=== Getting Records ids from {base_url}  for {mongo_collection}")
            print("=== Calling incremental checkpoints")
            old_ids = list(self.client[mongo_db]
                           [f"{mongo_collection}_identifiers"].find({}, {'_ids': 1}))
            old_ids = [i["_id"] for i in old_ids]
        else:
            old_ids = []
            print(
                f"=== Getting Records ids from {base_url}  for {mongo_collection}")

        ids = client.listIdentifiers(metadataPrefix=metadataPrefix)
        identifiers = []
        counter = 0
        for i in ids:
            _id = i.identifier()
            if _id not in old_ids:
                identifier = {}
                identifier["_id"] = _id
                identifier["datestamp"] = i.datestamp()
                identifier["deleted"] = i.isDeleted()
                identifier["setspec"] = i.setSpec()
                identifier["downloaded"] = False
                identifiers.append(identifier)
            counter += 1
            if counter % 1000 == 0:
                print(
                    f"=== INFO: CheckPoint: Processed {counter} records for {mongo_collection}")
        identifiers = list(
            {item['_id']: item for item in identifiers}.values())
        if len(identifiers) > 0:
            self.client[mongo_db][f"{mongo_collection}_identifiers"].insert_many(
                identifiers)
        print("=== INFO: Records CheckPoint total records found = {} for {}".format(
            len(identifiers), f"{mongo_collection}_identifiers"))

    def exists_records(self, mongo_db: str, mongo_collection: str):
        """
        Method to check if the checkpoints already exists for records.

        Parameters:
        ----------
        mongo_db:str
            MongoDB database name
        mongo_collection:str
            MongoDB collection name
        """
        ckp_rec = f"{mongo_collection}_identifiers"
        collections = self.client[mongo_db].list_collection_names()
        return ckp_rec in collections

    def drop(self, mongo_db: str, mongo_collection: str):
        """
        Method to delete all the checkpoints.

        Parameters:
        ----------
        mongo_db:str
            MongoDB database name
        mongo_collection:str
            MongoDB collection name
        """
        self.client[mongo_db][f"{mongo_collection}_identity"].drop()
        self.client[mongo_db][f"{mongo_collection}_identifiers"].drop()

    def update_record(self, mongo_db: str, mongo_collection: str, keys: dict):
        """
        Method to update the status of a record in the checkpoint

        Parameters:
        ----------
        mongo_db:str
            MongoDB database name
        mongo_collection:str
            MongoDB collection name
        keys:dict
            Dictionary with _id and other required values to perform the update.
        """
        self.client[mongo_db][f"{mongo_collection}_identifiers"].update_one(
            keys, {"$set": {"downloaded": 1}})

    def get_records_regs(self, mongo_db: str, mongo_collection: str):
        """
        Function to get registers from the records ckp collection that are not downloaded

        Parameters:
        ----------
        mongo_db:str
            MongoDB database name
        mongo_collection:str
            MongoDB collection name

        Returns:
        ----------
        list
            ids of records not downloaded.
        """
        ckp_col = self.client[mongo_db][f"{mongo_collection}_identifiers"]
        ckpdata = list(ckp_col.find(
            {"$and": [{"downloaded": False}, {"deleted": False}]}, {"downloaded": 0}))
        return ckpdata

    def run(self, endpoints: dict, mongo_db: str, jobs: int = None):
        """
        Method to create in parallel the checkpoints,
        every thread for endpoint

        Parameters:
        ----------
        endpoints: dict
            dictionary with the endpoints
        mongo_db: str
            database name
        jobs: int
            number of threads for the parallel execution,
            if None maximum allowed by the cpu.
        """
        if jobs is None:
            jobs = psutil.cpu_count()
        Parallel(n_jobs=jobs, backend='threading', verbose=10)(delayed(self.create)(
            endpoints[key]["url"], mongo_db, key, endpoints[key]["metadataPrefix"]) for key in endpoints.keys())
