from joblib import Parallel, delayed
from oaipmh.client import Client
from pymongo import MongoClient
from datetime import datetime, timedelta
import xmltodict
import psutil


class OxomocCheckPointSelective:
    """
    Class to handle checkpoints for Colav OAI-PMH using selective strategy by dates.
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

    def create(self, base_url: str, mongo_db: str, mongo_collection: str, metadataPrefix='oai_dc', force_http_get=True, days=30, max_tries=4):  # noqa: E501
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
            identity = client.identify()
        except BaseException as err:
            print(f"=== ERROR: Unexpected {err}, {type(err)}")
            print(f"=== ERROR: CheckPoint can not be created for {base_url}")
            return
        if metadataPrefix not in [i[0] for i in client.listMetadataFormats()]:
            print(
                f"=== ERROR: metadataPrefix {metadataPrefix}, not supported for {base_url}")
            print(
                f"=== ERROR: CheckPoint can not be created for {mongo_collection} omitting..")
            return

        print(
            f"=== Creating CheckPoint for {mongo_collection} from  {base_url} with metadataPrefix {metadataPrefix}")

        info = {}
        info["repository_name"] = identity.repositoryName()
        info["admin_emails"] = identity.adminEmails()
        info["base_url"] = identity.baseURL()
        info["protocol_version"] = identity.protocolVersion()
        info["earliest_datestamp"] = identity.earliestDatestamp()
        info["granularity"] = identity.granularity()

        self.client[mongo_db][f"{mongo_collection}_identity"].drop()
        self.client[mongo_db][f"{mongo_collection}_identity"].insert_one(info)

        delta = 60 * 60 * 24
        col_identifiers = self.client[mongo_db][f"{mongo_collection}_identifiers"]
        ckp = col_identifiers.find_one({}, sort=[('final_date', -1)])
        if ckp is not None:
            if "final_date" in ckp.keys():
                init_date = ckp["final_date"]
            else:
                init_date = identity.earliestDatestamp()
        else:
            init_date = identity.earliestDatestamp()
        end_date = init_date + timedelta(days=days)
        end_date = end_date.replace(hour=0, minute=0, second=0)
        if end_date > datetime.today():
            end_date = datetime.today().replace(microsecond=0)
        while init_date < datetime.today():
            print("=== INFO:", init_date, "----", end_date, mongo_collection)
            params = {"verb": "ListIdentifiers", "metadataPrefix": metadataPrefix,
                      "from": init_date.isoformat(), "until": end_date.isoformat()}
            for i in range(max_tries):
                try:
                    ids = client.makeRequest(**params)
                    break
                except BaseException as err:
                    print(f"=== ERROR: Unexpected {err}, {type(err)}")
                    print(
                        f"=== ERROR: CheckPoint try {i} of {max_tries} for {base_url}")
                    if i == (max_tries - 1):
                        print(
                            f"=== ERROR: CheckPoint can not be created for {base_url} with params {params}")
                        return

            ids = xmltodict.parse(ids)
            identifiers = []
            total = 0
            if "error" in ids['OAI-PMH'].keys():
                if ids['OAI-PMH']["error"]['@code'] == 'noRecordsMatch':
                    # records not found in the period of time
                    # setting next time range
                    col_identifiers.insert_one(
                        {"_id": end_date, "initial_date": init_date, "final_date": end_date, "identifiers":[]})
                    init_date = end_date + timedelta(seconds=delta)
                    end_date = init_date + timedelta(days=days)
                    if end_date > datetime.today():
                        end_date = datetime.today().replace(microsecond=0)
                    continue
                else:
                    print("=== ERROR:", ids['OAI-PMH']["error"]
                          ['@code'], mongo_collection, base_url, params),
                    print(init_date, "----", end_date,
                          "ERROR creating checkpoint!!!", mongo_collection)
                    break
            if ids['OAI-PMH']['ListIdentifiers'] is None:
                pass
            else:
                identifiers = ids['OAI-PMH']['ListIdentifiers']["header"]
                # if there is only one register is returning a dict, instead list
                if type(identifiers) is not list:
                    identifiers = [identifiers]
                resumptionToken = "resumptionToken" in ids['OAI-PMH']['ListIdentifiers'].keys(
                )
                if not resumptionToken:
                    total = len(identifiers)
                while resumptionToken:
                    params = {}
                    params['verb'] = 'ListIdentifiers'
                    total = eval(ids['OAI-PMH']['ListIdentifiers']['resumptionToken']
                                 ['@completeListSize'])  # this is int for dspace
                    if type(total) is not int:
                        # this is for zenodo, maybe other implementations?
                        total = total["value"]
                    if '#text' in ids['OAI-PMH']['ListIdentifiers']['resumptionToken'].keys():
                        params['resumptionToken'] = ids['OAI-PMH']['ListIdentifiers']['resumptionToken']['#text']
                    else:
                        break
                    ids = client.makeRequest(**params)
                    ids = xmltodict.parse(ids)
                    _ids = ids['OAI-PMH']['ListIdentifiers']["header"]
                    # if there is only one register is returning a dict, instead list
                    if type(_ids) is not list:
                        _ids = [_ids]
                    identifiers += _ids
                    resumptionToken = "resumptionToken" in ids['OAI-PMH']['ListIdentifiers'].keys(
                    )
                    print("=== INFO:", init_date, "----", end_date, mongo_collection,
                          f"Pagination {len(identifiers)} of {total}", flush=True)
                for i in identifiers:
                    i["downloaded"] = False
            if len(identifiers) != 0:
                col_identifiers.insert_one({"_id": end_date, "final_date": end_date, 'identifiers': identifiers, 'ranges': {
                                           "init_date": init_date, 'final_date': end_date, "n_records": total}})
            else:
                col_identifiers.insert_one(
                    {"_id": end_date, "init_date": init_date, "final_date": end_date, "identifiers":[]})
            init_date = end_date + timedelta(seconds=delta)
            end_date = init_date + timedelta(days=days)
            if end_date > datetime.today():
                end_date = datetime.today().replace(microsecond=0)

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
        self.client[mongo_db][f"{mongo_collection}_identifiers"].update_many({}, {"$set": {
            "identifiers.$[idx].downloaded": True}},
            upsert=True,
            array_filters=[{'idx.identifier': keys["_id"]}])

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
        pipeline = [
            {"$match": {}},
            {"$project": {"_id": 0, "identifiers": 1}},
            {"$unwind": "$identifiers"},
            {"$match": {"$and": [{"identifiers.@status": {"$ne": "deleted"}},
                                 {"identifiers.downloaded": False}]}},
            {"$group": {"_id": "$identifiers.identifier"}},
            {"$project": {"_id": 1}},
        ]
        ckp_col = self.client[mongo_db][f"{mongo_collection}_identifiers"]
        ckpdata = list(ckp_col.aggregate(pipeline))
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

        Parallel(n_jobs=jobs, backend="threading", verbose=10)(delayed(self.create)(
            endpoints[endpoint]["url"], mongo_db,
            endpoint, endpoints[endpoint]["metadataPrefix"]) for endpoint in endpoints.keys())
