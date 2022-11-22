from oxomo.checkpoint import OxomoCheckPoint
from oxomo.ckpselective import OxomoCheckPointSelective
from pymongo import MongoClient
from oaipmh.client import Client
from joblib import Parallel, delayed
import psutil
import xmltodict
from ratelimit import limits, sleep_and_retry
import sys


class OxomoHarvester:
    """
    Class for harvesting data from OAI-PHM protocol
    """

    def __init__(self, endpoints: dict, mongo_db="oxomo", mongodb_uri="mongodb://localhost:27017/", force_http_get=True, selective=True):
        """
        Harvester constructor

        Parameters:
        ----------
        endpoints:dict
            dictionary with dspace endpoint url and university name
        mongodb_uri:str
            MongoDB connection string uri
        """
        if selective:
            self.ckp = OxomoCheckPointSelective(mongodb_uri)
        else:
            self.ckp = OxomoCheckPoint(mongodb_uri)
        self.endpoints = endpoints
        self.mongo_db = mongo_db
        self.client = MongoClient(mongodb_uri)
        self.force_http_get = force_http_get
        self.check_limit = {}
        for endpoint in self.endpoints.keys():
            if "rate_limit" in self.endpoints[endpoint].keys():
                calls = self.endpoints[endpoint]["rate_limit"]["calls"]
                secs = self.endpoints[endpoint]["rate_limit"]["secs"]

                @sleep_and_retry
                @limits(calls=calls, period=secs)
                def check_limit():
                    pass
                self.check_limit[endpoint] = check_limit
            else:
                def check_limit():
                    pass
                self.check_limit[endpoint] = check_limit

    def process_record(self, client: Client, identifier: str, metadataPrefix: str, endpoint: str):
        """
        This method perform the request for the given record id and save it in the mongo
        collection and updates the checkpoint collection when it was inserted.

        Parameters:
        ---------
        client: oaipmh.client
            oaipmh client instance 
        identifier:str
            record id
        metadataPrefix:str
            metadata type for xml schema ex: dim, xoai, mods, oai_dc (default: oai_dc)
        endpoint:str
            name of the endpoint to process and the MongoDb collection name
        """
        self.check_limit[endpoint]()

        try:
            raw_record = client.makeRequest(
                **{'verb': 'GetRecord', 'identifier': identifier, 'metadataPrefix': metadataPrefix})
        except Exception as e:
            record = {}
            record["identifier"] = identifier
            record["instance"] = str(type(e))
            record["item_type"] = "record"
            record["msg"] = str(e)
            self.client[self.mongo_db][f"{endpoint}_errors"].insert_one(record)
            self.ckp.update_record(self.mongo_db, endpoint, keys={"_id": identifier})
            print("=== ERROR ===")
            print(e)
            print(identifier)
            return

        record = xmltodict.parse(raw_record)
        record["_id"] = identifier
        try:
            if "error" in record["OAI-PMH"].keys():
                self.client[self.mongo_db][f"{endpoint}_invalid"].insert_one(record)
            else:
                self.client[self.mongo_db][f"{endpoint}_records"].insert_one(record)
            self.ckp.update_record(self.mongo_db, endpoint, keys={"_id": identifier})
        except Exception as e:
            print("=== ERROR: ", e, endpoint, file=sys.stderr)
        finally:  # performing atomic operation here(to be sure it was inserted)
            if self.client[self.mongo_db][f"{endpoint}_records"].count_documents({"_id": identifier}) != 0 or self.client[self.mongo_db][f"{endpoint}_invalid"].count_documents({"_id": identifier}) != 0:
                self.ckp.update_record(self.mongo_db, endpoint, keys={"_id": identifier})

    def process_records(self, client: Client, identifiers: list, metadataPrefix: str, endpoint: str):
        """
        This method makes a loop over the record to perform the request.
        Also reports the progress in stdout every 1000 records.

        Parameters:
        ---------
        client: oaipmh.client
            oaipmh client instance 
        identifiers:list
            record ids
        metadataPrefix:str
            metadata type for xml schema ex: dim, xoai, mods, oai_dc (default: oai_dc)
        endpoint:str
            name of the endpoint to process and the MongoDb collection name
        """
        count = 0
        size = len(identifiers)
        for identifier in identifiers:
            self.process_record(client, identifier["_id"], metadataPrefix, endpoint)
            if count % 1000 == 0:
                print(
                    f"=== INFO: Downloaded {count} of {size} ({(count/size)*100:.2f}%) for {endpoint}")
            count += 1

    def process_endpoint(self, endpoint: str, checkpoint: bool):
        """
        Method to parse endpoint config, handle checkpoint and process records.

        Parameters:
        ---------
        endpoint:str
            name of the endpoint to process and the MongoDb collection name
        checkpoint:bool
            Bool to enable checkpointing
        """
        url = self.endpoints[endpoint]["url"]
        metadataPrefix = self.endpoints[endpoint]["metadataPrefix"]
        if checkpoint:
            self.ckp.create(url, self.mongo_db, endpoint, metadataPrefix)

        print(f"\n=== Processing {endpoint} from {url} ")
        if self.ckp.exists_records(self.mongo_db, endpoint):
            client = Client(url, force_http_get=self.force_http_get)
            record_ids = self.ckp.get_records_regs(self.mongo_db, endpoint)
            self.process_records(client, record_ids, metadataPrefix, endpoint)
        else:
            print(
                f"*** Error: records checkpoint for {endpoint} not found, create it first with ...")
            print(f"*** Omitting records {url} {endpoint}")

    def run(self, checkpoint: bool = False, jobs: int = None):
        """
        Method to start the harvesting of the data in the multiples endpoints in parallel.
        You have to create the checkpoint first, before call this method.

        Parameters:
        ----------
        jobs:int
            number of jobs for parallel execution, if the value is None, it will
            take the number of threads available in the cpu.
        """
        if jobs is None:
            jobs = psutil.cpu_count()
        if jobs > len(self.endpoints.keys()):
            jobs = len(self.endpoints.keys())
        Parallel(n_jobs=jobs, backend='threading', verbose=10)(delayed(self.process_endpoint)(
            endpoint, checkpoint) for endpoint in self.endpoints.keys())
