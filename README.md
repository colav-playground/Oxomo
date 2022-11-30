[![Python build package](https://github.com/colav/Oxomo/actions/workflows/python-package.yml/badge.svg)](https://github.com/colav/Oxomo/actions/workflows/python-package.yml)
<center><img src="https://raw.githubusercontent.com/colav/colav.github.io/master/img/Logo.png"/></center>

# Oxomo
Colav OAI-PMH Harvesting / Goddess of the night, the astrology and the calendar.

# Description
Package to download metadata records for repositories using OAI-PMH.
Supports:
* Download XML records using OAI-PMH protocol.
* Download XML records in multiple XML schemas.
* Parallel execution, to download multiple repositories at the same time.
* Rate-Limit to avoid DDoS and 429 errors, this is supported asynchronous in the parallel execution, which means that every repo can have a different rate limit.
* Allows parse the XML as dictionary without losing information thanks to the package xmltodict, allowing at the same time, saving the records in MongoDB.
* Command line tool oxomo_run.
* CheckPoint to save the state of the execution. This feature is available suing to different algorithms, selective or not. Which means that we can create a checkpoint using (from/until) in the verb ListIdentifiers. This is because not all endpoints has support for this.

# Installation

## MongoDB
This package requires a MongoDB engine to save the results.
Please read https://www.mongodb.com/docs/manual/administration/install-community/

## Package
`pip install oxomo`

# Usage

Create a config file ex: config.py <br>
Read the comments in the next one for more information.
```python
endpoints = {}
endpoints["dspace_udea"] = {}
endpoints["dspace_udea"]["enabled"] = True #if this endpoint is enabled
endpoints["dspace_udea"]["url"] = "http://bibliotecadigital.udea.edu.co/oai/request"
endpoints["dspace_udea"]["metadataPrefix"] = "dim"  #xml format, check if the list in the repository using
endpoints["dspace_udea"]["rate_limit"] = {"calls": 10000, "secs": 1}
endpoints["dspace_udea"]["checkpoint"] = {}
endpoints["dspace_udea"]["checkpoint"]["enabled"] = True
# uses selective harvesting to create the checkpoint.
# check http://www.openarchives.org/OAI/openarchivesprotocol.html#SelectiveHarvesting
endpoints["dspace_udea"]["checkpoint"]["selective"] = True
endpoints["dspace_udea"]["checkpoint"]["days"] = 30  # if selective, time step

endpoints["dspace_uext"] = {}
endpoints["dspace_uext"]["enabled"] = True
endpoints["dspace_uext"]["url"] = "http://bdigital.uexternado.edu.co/oai/request"
endpoints["dspace_uext"]["metadataPrefix"] = "dim"
endpoints["dspace_uext"]["rate_limit"] = {
    "calls": 1000, "secs": 1}  # calls per second
endpoints["dspace_uext"]["checkpoint"] = {}
endpoints["dspace_uext"]["checkpoint"]["enabled"] = True
endpoints["dspace_uext"]["checkpoint"]["selective"] = True
endpoints["dspace_uext"]["checkpoint"]["days"] = 30

```

We suggest to use selective checkpoint if supported by the repository, it is more efficient.

To execute it run:
```bash
oxomo_run --config config.py
```

By default:
* it will run in parallel with 2 threads because there is 2 endpoints, if there is more endpoints it will try to use the maximum number of threads available. Please use `--max_thread` parameter to control the parallel execution.
* it will  try to connect to local MongoDB instance without credentials.
* The database with the results is oxomo.

The collections produced are:
```
dspace_udea_identifiers
dspace_udea_identity
dspace_udea_invalid
dspace_udea_errors
dspace_udea_records
```
where:
* dspace_udea_identifiers: is the list of identifiers for the checkpoints, additional useful information can be found here such as deleted records and setSpec for every record id
* dspace_udea_identity: information of the repository using the verb [Identify](http://www.openarchives.org/OAI/openarchivesprotocol.html#Identify)
* dspace_udea_invalid: records that are not marked as deleted by the repository but it is returning id doesn´t exists or some other [OAI-PMH error](http://www.openarchives.org/OAI/openarchivesprotocol.html#ErrorConditions)
* dspace_udea_errors: if there is and error in the request such as [500](https://developer.mozilla.org/es/docs/Web/HTTP/Status/500) or [429](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429) the error is saved in this collection.
* dspace_udea_records: all the records correctly downloaded.

Please check oxomo_run for more options.

# License
BSD-3-Clause License

# Links
http://colav.udea.edu.co/



