endpoints = {}

endpoints["dspace_udea"] = {}
endpoints["dspace_udea"]["enabled"] = True
endpoints["dspace_udea"]["url"] = "http://bibliotecadigital.udea.edu.co/oai/request"
endpoints["dspace_udea"]["metadataPrefix"] = "dim"
endpoints["dspace_udea"]["rate_limit"] = {"calls": 10000, "secs": 1}
# selective harvesting is handled by the checkpoint
# if false and it doesn´t exists, records will not be downloaded
endpoints["dspace_udea"]["checkpoint"] = {}
endpoints["dspace_udea"]["checkpoint"]["enabled"] = True
# uses selective harvesting to create the checkpoint.
endpoints["dspace_udea"]["checkpoint"]["selective"] = True
endpoints["dspace_udea"]["checkpoint"]["days"] = 30  # if selective, time step

endpoints["dspace_udem"] = {}
endpoints["dspace_udem"]["enabled"] = True
endpoints["dspace_udem"]["url"] = "http://repository.udem.edu.co/oai/request"
endpoints["dspace_udem"]["metadataPrefix"] = "dim"
endpoints["dspace_udem"]["rate_limit"] = {"calls": 1000, "secs": 1}
endpoints["dspace_udem"]["checkpoint"] = {}
endpoints["dspace_udem"]["checkpoint"]["enabled"] = True
endpoints["dspace_udem"]["checkpoint"]["selective"] = True
endpoints["dspace_udem"]["checkpoint"]["days"] = 30

# pure doen't supoor selective ListIdentifiers (from/until) we have to use normal incremental checkpoint here
endpoints["pure_udem"] = {}
endpoints["pure_udem"]["enabled"] = True
endpoints["pure_udem"]["url"] = "http://investigaciones-pure.udem.edu.co/ws/oai"
endpoints["pure_udem"]["metadataPrefix"] = "mods"
endpoints["pure_udem"]["rate_limit"] = {"calls": 100, "secs": 1}
endpoints["pure_udem"]["checkpoint"] = {}
endpoints["pure_udem"]["checkpoint"]["enabled"] = True
endpoints["pure_udem"]["checkpoint"]["selective"] = False
endpoints["pure_udem"]["checkpoint"]["days"] = 30

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

# this is not working :C
endpoints["dspace_unaula"] = {}
endpoints["dspace_unaula"]["enabled"] = False
endpoints["dspace_unaula"]["url"] = "http://repositorio.unaula.edu.co:8080/server/oai/request"
endpoints["dspace_unaula"]["metadataPrefix"] = "dim"
endpoints["dspace_unaula"]["rate_limit"] = {
    "calls": 1000, "secs": 1}  # calls per second
endpoints["dspace_unaula"]["checkpoint"] = {}
endpoints["dspace_unaula"]["checkpoint"]["enabled"] = True
endpoints["dspace_unaula"]["checkpoint"]["selective"] = True
endpoints["dspace_unaula"]["checkpoint"]["days"] = 30

endpoints["zenodo"] = {}
endpoints["zenodo"]["enabled"] = False
endpoints["zenodo"]["url"] = "https://zenodo.org/oai2d"
endpoints["zenodo"]["metadataPrefix"] = "oai_datacite"
endpoints["zenodo"]["rate_limit"] = {"calls": 2, "secs": 1}  # calls per second
endpoints["zenodo"]["checkpoint"] = {}
endpoints["zenodo"]["checkpoint"]["enabled"] = True
endpoints["zenodo"]["checkpoint"]["selective"] = True
endpoints["zenodo"]["checkpoint"]["days"] = 30

endpoints["redalyc"] = {}
endpoints["redalyc"]["enabled"] = False
endpoints["redalyc"]["url"] = "http://148.215.1.70/redalyc/oai"
endpoints["redalyc"]["metadataPrefix"] = "mods"
endpoints["redalyc"]["rate_limit"] = {
    "calls": 100, "secs": 1}  # calls per second
endpoints["redalyc"]["checkpoint"] = {}
endpoints["redalyc"]["checkpoint"]["enabled"] = True
endpoints["redalyc"]["checkpoint"]["selective"] = True
endpoints["redalyc"]["checkpoint"]["days"] = 30
