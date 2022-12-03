from oxomoc.checkpoint import OxomocCheckPoint
from oxomoc.ckpselective import OxomocCheckPointSelective
from pymongo import MongoClient
from oaipmh.client import Client
from joblib import Parallel, delayed
import psutil
import xmltodict
from ratelimit import limits, sleep_and_retry
import sys


class OxomocHarvester:
    """
    Class for harvesting data from OAI-PHM protocol
    """

    def __init__(self, endpoints: dict, mongo_db="oxomoc", mongodb_uri="mongodb://localhost:27017/", force_http_get=True):
        """
        Harvester constructor

        Parameters:
        ----------
        endpoints:dict
            dictionary with parameters for endpoints such as url, name, rate-limit, etc..
        mongo_db:str
            MongoDB name, default value "oxomoc"
        mongodb_uri:str
            MongoDB connection string uri
        """
        self.endpoints = endpoints
        self.mongo_db = mongo_db
        self.mongodb_uri = mongodb_uri
        self.client = MongoClient(mongodb_uri)
        self.force_http_get = force_http_get
        self.check_limit = {}
        self.checkpoint = {}
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
            self.checkpoint[endpoint].update_record(
                self.mongo_db, endpoint, keys={"_id": identifier})
            print("=== ERROR ===")
            print(e)
            print(identifier)
            return

        record = xmltodict.parse(raw_record)
        record["_id"] = identifier
        try:
            if "error" in record["OAI-PMH"].keys():
                self.client[self.mongo_db][f"{endpoint}_invalid"].insert_one(
                    record)
            else:
                self.client[self.mongo_db][f"{endpoint}_records"].insert_one(
                    record)
            self.checkpoint[endpoint].update_record(
                self.mongo_db, endpoint, keys={"_id": identifier})
        except Exception as e:
            print("=== ERROR: ", e, endpoint, file=sys.stderr)
        # performing "atomic" operation here(to be sure it was inserted)
        finally:
            rcount = self.client[self.mongo_db][f"{endpoint}_records"].count_documents({"_id": identifier})
            icount = self.client[self.mongo_db][f"{endpoint}_invalid"].count_documents({"_id": identifier})
            if rcount != 0 or icount != 0:
                self.checkpoint[endpoint].update_record(
                    self.mongo_db, endpoint, keys={"_id": identifier})

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
            self.process_record(
                client, identifier["_id"], metadataPrefix, endpoint)
            if count % 1000 == 0:
                print(
                    f"=== INFO: Downloaded {count} of {size} ({(count/size)*100:.2f}%) for {endpoint}")
            count += 1

    def process_endpoint(self, endpoint: str):
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
        selective = self.endpoints[endpoint]["checkpoint"]["selective"]
        checkpoint = self.endpoints[endpoint]["checkpoint"]["enabled"]

        if selective:
            self.checkpoint[endpoint] = OxomocCheckPointSelective(
                self.mongodb_uri)
        else:
            self.checkpoint[endpoint] = OxomocCheckPoint(self.mongodb_uri)
        if checkpoint:
            if selective:
                days = self.endpoints[endpoint]["checkpoint"]["days"]
                self.checkpoint[endpoint].create(
                    url, self.mongo_db, endpoint, metadataPrefix,days)
            else:
                self.checkpoint[endpoint].create(
                    url, self.mongo_db, endpoint, metadataPrefix)

        print(f"\n=== Processing {endpoint} from {url} ")
        if self.checkpoint[endpoint].exists_records(self.mongo_db, endpoint):
            client = Client(url, force_http_get=self.force_http_get)
            record_ids = self.checkpoint[endpoint].get_records_regs(
                self.mongo_db, endpoint)
            self.process_records(client, record_ids, metadataPrefix, endpoint)
        else:
            print(
                f"=== Error: records checkpoint for {endpoint} not found, create it first with ...")
            print(f"=== Error: Skipping records from {url} in {endpoint}")

    def run(self, jobs: int = None):
        """
        Method to start the harvesting of the data in the multiples endpoints in parallel.
        You have to create the checkpoint first, before call this method.

        Parameters:
        ----------
        jobs:int
            number of jobs for parallel execution, if the value is None, it will
            take the number of threads available in the cpu.
        """
        endpoints_names = self.endpoints.keys()
        if jobs is None:
            jobs = psutil.cpu_count()
        if jobs > len(endpoints_names):
            jobs = len(endpoints_names)
        endpoints = []
        for endpoint in endpoints_names:
            if self.endpoints[endpoint]["enabled"]:
                endpoints.append(endpoint)
            else:
                print(f"=== INFO: repository {endpoint} is disabled, skipped!")
        Parallel(n_jobs=jobs, backend='threading', verbose=10)(delayed(self.process_endpoint)(
            endpoint) for endpoint in endpoints)
