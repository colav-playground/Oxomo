endpoints = {}

endpoints["dspace_udea"] = {}
endpoints["dspace_udea"]["url"] = "http://bibliotecadigital.udea.edu.co/oai/request"
endpoints["dspace_udea"]["metadataPrefix"] = "dim"
endpoints["dspace_udea"]["rate_limit"] = {"calls": 100, "secs": 1}
# selective harvesting is handled by the checkpoint
endpoints["dspace_udea"]["selective_checkpoint"] = {"days": 1}

endpoints["dspace_udem"] = {}
endpoints["dspace_udem"]["url"] = "http://repository.udem.edu.co/oai/request"
endpoints["dspace_udem"]["metadataPrefix"] = "dim"
endpoints["dspace_udem"]["rate_limit"] = {"calls": 100, "secs": 1}

endpoints["dspace_uext"] = {}
endpoints["dspace_uext"]["url"] = "http://bdigital.uexternado.edu.co/oai/request"
endpoints["dspace_uext"]["metadataPrefix"] = "dim"
endpoints["dspace_uext"]["rate_limit"] = {
    "calls": 1000, "secs": 1}  # calls per second

endpoints["dspace_unaula"] = {}
endpoints["dspace_unaula"]["url"] = "http://repository.unaula.edu.co:8080/oai/request"
endpoints["dspace_unaula"]["metadataPrefix"] = "dim"
endpoints["dspace_unaula"]["rate_limit"] = {
    "calls": 1000, "secs": 1}  # calls per second
