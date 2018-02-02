import handlers
import pymongo
import settings
import tornado.web

class Query(handlers.UnsafeHandler):
    def make_error_response(self):
        ret_str = ""

        checks = {
                'dataset': lambda x: "" if x == 'SweGen' else "dataset has to be SweGen\n",
                'ref': lambda x: "" if x == 'hg19' else "ref has to be hg19\n",
                'pos': lambda x: "" if x.isdigit() else "pos has to be digit\n",
        }

        for arg in ['chrom', 'pos', 'dataset', 'referenceAllele', 'allele', 'ref']:
            try:
                val = self.get_argument(arg)
                if arg in checks:
                    ret_str += checks[arg](val)
            except tornado.web.MissingArgumentError:
                ret_str += arg + " is missing\n"
                if arg in checks:
                    ret_str += checks[arg]("")

        return ret_str

    def get(self):
        the_errors = self.make_error_response()
        if the_errors:
            self.set_status(400)
            self.set_header('Content-Type', 'text/plain')
            self.write(the_errors)
            return

        sChr      = self.get_argument('chrom', '').upper()
        iPos      = self.get_argument('pos', '')
        dataset   = self.get_argument('dataset', '')
        referenceAllele = self.get_argument('referenceAllele', '').upper()
        allele = self.get_argument('allele', '').upper()
        reference = self.get_argument('ref', '')

        exists = lookupAllele(sChr, int(iPos), referenceAllele, allele, reference, dataset)

        if self.get_argument('format', '') == 'text':
            self.set_header('Content-Type', 'text/plain')
            self.write(str(exists))
        else:
            self.write({
                'response': {
                    'exists': exists,
                    'observed': 0,
                    'externalUrl': "%s://%s" % ('https', self.request.host),
                    },
                'query': {
                    'chromosome': sChr,
                    'position': int(iPos),
                    'referenceAllele': referenceAllele,
                    'allele': allele,
                    'dataset': dataset,
                    'reference': reference
                    },
                'beacon': 'swefreq-beacon'
                })

class Info(handlers.UnsafeHandler):
    def get(self):
        query_uri = "%s://%s/query?" % ('https', self.request.host)
        self.write({
            'id': 'swefreq-beacon',
            'name': 'Swefreq Beacon',
            'organization': 'SciLifeLab',
            'api': '0.3',
            #'description': u'Swefreq beacon from NBIS',
            'datasets': [
                {
                    'id': 'SweGen',
                    # 'description': 'Description',
                    # 'size': { 'variants': 1234, 'samples': 12 },
                    # 'data_uses': [] # Data use limitations
                    'reference': 'hg19'
                },
            ],
            'homepage':  "%s://%s" % ('https', self.request.host),
            #'email': u'swefreq-beacon@nbis.se',
            #'auth': 'None', # u'oauth2'
            'queries': [
                query_uri + 'dataset=SweGen&ref=hg19&chrom=1&pos=55500975&referenceAllele=C&allele=T',
                query_uri + 'dataset=SweGen&ref=hg19&chrom=1&pos=55505551&referenceAllele=A&allele=ACTG&format=text',
                query_uri + 'dataset=SweGen&ref=hg19&chrom=2&pos=41936&referenceAllele=AG&allele=A'
                ] #
            })

def lookupAllele(chrom, pos, referenceAllele, allele, reference, dataset):
    """CHeck if an allele is present in the database
    Args:
        chrom: The chromosome, format matches [1-22XY]
        pos: Coordinate within a chromosome. Position is a number and is 0-based
        allele: Any string of nucleotides A,C,T,G
        alternate: Any string of nucleotides A,C,T,G
        reference: The human reference build that was used (currently unused)
        dataset: Dataset to look in (currently used to select Mongo database)
    Returns:
        The string 'true' if the allele was found, otherwise the string 'false'
    """
    client = pymongo.MongoClient(host=settings.mongo_host, port=settings.mongo_port)

    # The name of the dataset in the database is exac as required by the
    # exac browser we are using.
    if dataset == 'SweGen':
        dataset = 'exac'

    mdb = client[dataset]
    mdb.authenticate(settings.mongo_user, settings.mongo_password)

    # Beacon is 0-based, our database is 1-based in coords.
    pos += 1
    res = mdb.variants.find({'chrom': chrom, 'pos': pos})
    for r in res:
        if r['alt'] == allele and r['ref'] == referenceAllele:
            return True

    return False
