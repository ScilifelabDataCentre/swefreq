import tornado.template as template
import tornado.gen
import logging
import applicationTemplate
import auth
import json
import secrets
import torndb as database
import pymongo
import smtplib
import email.mime.multipart
from email.MIMEText import MIMEText


db = database.Connection(host = secrets.mysqlHost,
                         database = secrets.mysqlSchema,
                         user = secrets.mysqlUser,
                         password = secrets.mysqlPasswd)

class query(auth.UnsafeHandler):
    def make_error_response(self):
        ret_str = ""

        checks = {
                'dataset': lambda x: "" if x == 'SweGen' else "dataset has to be SweGen\n",
                'ref': lambda x: "" if x == 'hg19' else "ref has to be hg19\n",
                'pos': lambda x: "" if x.isdigit() else "pos has to be digit\n",
        }

        for arg in ['chrom', 'pos', 'dataset', 'allele', 'ref']:
            try:
                val = self.get_argument(arg)
                if checks.has_key(arg):
                    ret_str += checks[arg](val)
            except:
                ret_str += arg + " is missing\n"
                if checks.has_key(arg):
                    ret_str += checks[arg]("")

        dataset = self.get_argument('dataset', 'MISSING')

        return ret_str

    def get(self, *args, **kwargs):
        the_errors = self.make_error_response()
        if len(the_errors) > 0:
            self.set_status(400);
            self.set_header('Content-Type', 'text/plain');
            self.write(the_errors);
            return

        sChr = self.get_argument('chrom', '')
        iPos = self.get_argument('pos', '')
        dataset = self.get_argument('dataset', '')
        allele = self.get_argument('allele', '')
        reference = self.get_argument('ref', '')

        exists = lookupAllele(sChr.upper(), int(iPos), allele.upper(), reference, dataset)
        if self.get_argument('format', '') == 'text':
            self.set_header('Content-Type', 'text/plain')
            self.write(str(exists))
        else:
            self.write({
                'response': {
                    'exists': exists,
                    'observed': 0,
                    },
                'query': {
                    'chromosome': sChr,
                    'position': iPos,
                    'allele': allele,
                    'dataset': dataset,
                    'reference': reference
                    },
                'beacon': 'nbis-beacon'
                })

class info(auth.UnsafeHandler):
    def get(self, *args, **kwargs):
        query_uri = "%s://%s/query?" % (self.request.protocol, self.request.host)
        self.write({
            'id': u'nbis-beacon',
            'name': u'NBIS Beacon',
            'organization': u'NBIS',
            'api': u'0.2',
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
            'homepage':  "%s://%s" % (self.request.protocol, self.request.host),
            #'email': u'swefreq-beacon@nbis.se',
            #'auth': 'None', # u'oauth2'
            'queries': [
                query_uri + 'dataset=SweGen&ref=hg19&chrom=1&pos=55500976&dataset=exac&allele=C',
                query_uri + 'dataset=SweGen&ref=hg19&chrom=1&pos=55505553&allele=ICTG&format=text',
                query_uri + 'dataset=SweGen&ref=hg19&chrom=2&pos=41938&allele=D1'
                ] #
            })

def lookupAllele(chrom, pos, allele, reference, dataset):
    """CHeck if an allele is present in the database
    Args:
        chrom: The chromosome, format matches [1-22XY]
        pos: Coordinate within a chromosome. Position is a number and is 1-based
        allele: Any string of nucleotides A,C,T,G or D, I for deletion and insertion, respectively.
        reference: The human reference build that was used (currently unused)
        dataset: Dataset to look in (currently used to select Mongo database)
    Returns:
        The string 'true' if the allele was found, otherwise the string 'false'
    """
    client = pymongo.MongoClient(host=secrets.mongodbhost, port=secrets.mongodbport)

    # The name of the dataset in the database is exac as required by the
    # exac browser we are using.
    if dataset == 'SweGen':
        dataset = 'exac'

    mdb = client[dataset]

    if allele[0] == 'D' or allele[0] == 'I':
        pos -= 1

    res = mdb.variants.find({'chrom': chrom, 'pos': pos})
    if not res:
        return False

    for r in res:
        # Just a (point) mutation
        if allele[0] != 'D' and allele[0] != 'I':
            if r['alt'] == allele:
                return True

        # Insertion. Inserted sequence is from second position and onwards and
        # should match allele
        if allele[0] == 'I':
            if r['alt'][1:] == allele[1:]:
                return True

        # Deletion. Just check that the length of the ref is one more than the
        # length of the deletion.
        if allele[0] == 'D':
            if int(allele[1:])+1 == len(r['ref']):
                return True

    return False

class home(auth.UnsafeHandler):
    def get(self, *args, **kwargs):
        t = template.Template(applicationTemplate.indexHead)
        self.write(t.generate())

        is_admin = False

        if self.get_current_token() != None:
            t = template.Template(applicationTemplate.indexHtml)
            is_admin = self.is_admin()
        elif self.get_current_user() != None:
            t = template.Template(applicationTemplate.indexNoAccess)
        else:
            t = template.Template(applicationTemplate.notAuthorizedHtml)

        self.write(t.generate(user_name=self.get_current_user(),
                              email=self.get_current_email(),
                              is_admin=is_admin,
                              ExAC=secrets.ExAC_server))

class getUser(auth.UnsafeHandler):
    def get(self, *args, **kwargs):
        sUser = self.get_current_user()
        sEmail = self.get_current_email()

        tRes = db.query("""select full_user from swefreq.users where
                           email='%s' and full_user""" % sEmail)
        lTrusted = True if len(tRes)==1 else False

        tRes = db.query("""select full_user from swefreq.users where
                              email='%s'""" % sEmail)
        lDatabase = True if len(tRes) == 1 else False
        tRes = db.query("""select full_user from swefreq.users where
                              email='%s' and swefreq_admin""" % sEmail)
        lAdmin = True if len(tRes) == 1 else False

        logging.info("getUser: " + str(sUser) + ' ' + str(sEmail))
        self.finish(json.dumps({'user':sUser,
                                'email':sEmail,
                                'trusted':lTrusted,
                                'isInDatabase':lDatabase,
                                'admin':lAdmin}))

class country_list(auth.UnsafeHandler):
    def get(self, *args, **kwargs):
        self.write({'countries': map( lambda c: {'name': c}, self.country_list())})

    def country_list(self):
        return ["Afghanistan", "Albania", "Algeria", "American Samoa", "Andorra",
                "Angola", "Anguilla", "Antarctica", "Antigua and Barbuda",
                "Argentina", "Armenia", "Aruba", "Australia", "Austria",
                "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados",
                "Belarus", "Belgium", "Belize", "Benin", "Bermuda", "Bhutan",
                "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil",
                "British Indian Ocean Territory", "British Virgin Islands",
                "Brunei", "Bulgaria", "Burkina Faso", "Burundi", "Cambodia",
                "Cameroon", "Canada", "Cape Verde", "Cayman Islands",
                "Central African Republic", "Chad", "Chile", "China",
                "Christmas Island", "Cocos Islands", "Colombia", "Comoros",
                "Cook Islands", "Costa Rica", "Croatia", "Cuba", "Curacao",
                "Cyprus", "Czech Republic", "Democratic Republic of the Congo",
                "Denmark", "Djibouti", "Dominica", "Dominican Republic",
                "East Timor", "Ecuador", "Egypt", "El Salvador",
                "Equatorial Guinea", "Eritrea", "Estonia", "Ethiopia",
                "Falkland Islands", "Faroe Islands", "Fiji", "Finland", "France",
                "French Polynesia", "Gabon", "Gambia", "Georgia", "Germany",
                "Ghana", "Gibraltar", "Greece", "Greenland", "Grenada", "Guam",
                "Guatemala", "Guernsey", "Guinea", "Guinea-Bissau", "Guyana",
                "Haiti", "Honduras", "Hong Kong", "Hungary", "Iceland", "India",
                "Indonesia", "Iran", "Iraq", "Ireland", "Isle of Man", "Israel",
                "Italy", "Ivory Coast", "Jamaica", "Japan", "Jersey", "Jordan",
                "Kazakhstan", "Kenya", "Kiribati", "Kosovo", "Kuwait",
                "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia",
                "Libya", "Liechtenstein", "Lithuania", "Luxembourg", "Macau",
                "Macedonia", "Madagascar", "Malawi", "Malaysia", "Maldives",
                "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius",
                "Mayotte", "Mexico", "Micronesia", "Moldova", "Monaco",
                "Mongolia", "Montenegro", "Montserrat", "Morocco", "Mozambique",
                "Myanmar", "Namibia", "Nauru", "Nepal", "Netherlands",
                "Netherlands Antilles", "New Caledonia", "New Zealand",
                "Nicaragua", "Niger", "Nigeria", "Niue", "North Korea",
                "Northern Mariana Islands", "Norway", "Oman", "Pakistan", "Palau",
                "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru",
                "Philippines", "Pitcairn", "Poland", "Portugal", "Puerto Rico",
                "Qatar", "Republic of the Congo", "Reunion", "Romania", "Russia",
                "Rwanda", "Saint Barthelemy", "Saint Helena",
                "Saint Kitts and Nevis", "Saint Lucia", "Saint Martin",
                "Saint Pierre and Miquelon",
                "Saint Vincent and the Grenadines", "Samoa", "San Marino",
                "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia",
                "Seychelles", "Sierra Leone", "Singapore", "Sint Maarten",
                "Slovakia", "Slovenia", "Solomon Islands", "Somalia",
                "South Africa", "South Korea", "South Sudan", "Spain",
                "Sri Lanka", "Sudan", "Suriname", "Svalbard and Jan Mayen",
                "Swaziland", "Sweden", "Switzerland", "Syria", "Taiwan",
                "Tajikistan", "Tanzania", "Thailand", "Togo", "Tokelau", "Tonga",
                "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan",
                "Turks and Caicos Islands", "Tuvalu", "U.S. Virgin Islands",
                "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom",
                "United States", "Uruguay", "Uzbekistan", "Vanuatu", "Vatican",
                "Venezuela", "Vietnam", "Wallis and Futuna", "Western Sahara",
                "Yemen", "Zambia", "Zimbabwe" ];


class requestAccess(auth.UnsafeHandler):
    def get(self, *args, **kwargs):
        sUser = self.get_current_user()
        sEmail = self.get_current_email()
        logging.info("Request: " + sUser + ' ' + sEmail)
        self.finish(json.dumps({'user':sUser, 'email':sEmail}))

    def post(self, *args, **kwargs):
        userName = self.get_argument("userName", default='',strip=False)
        email = self.get_argument("email", default='', strip=False)
        affiliation = self.get_argument("affiliation", strip=False)
        country = self.get_argument("country", strip=False)
        newsletter = self.get_argument("newsletter", strip=False)

        # This is the only chance for XSRF in the application
        # avoid it by checking that the email sent by google is the same as
        # supplied by the form post
        sEmail = self.get_current_email()
        if sEmail != email:
            return

        sSql = """
        insert into swefreq.users (username, email, affiliation, full_user, country, newsletter)
        values ('%s', '%s', '%s', '%s', '%s', '%s')
        """ % (userName, email, affiliation, 0, country, newsletter)
        try:
            logging.error("Executing: " + sSql)
            db.execute(sSql)
        except:
            logging.error("Error inserting " + userName + ' ' + email)

class logEvent(auth.SafeHandler):
    def get(self, sEvent):
        sEmail=self.get_current_email()
        sSql = """insert into swefreq.user_log (email, action) values ('%s', '%s')
        """ % (sEmail, sEvent)
        db.execute(sSql)
        if sEvent == 'download':
            tRes = db.query("""select ifnull(download_count, 0) as download_count
                               from swefreq.users where email = '%s'""" % sEmail)
            db.execute("""update swefreq.users set download_count='%s'
                          where email='%s'""" % (int(tRes[0].download_count)+1, sEmail))

class approveUser(auth.SafeHandler):
    def get(self, sEmail):
        sLoggedInEmail = self.get_current_email()
        tRes = db.query("""select full_user from swefreq.users where
                              email='%s' and swefreq_admin""" % sLoggedInEmail)
        if len(tRes) == 0:
            return
        db.update("""update swefreq.users set full_user = '1'
        where email = '%s'""" % sEmail)

        msg = email.mime.multipart.MIMEMultipart()
        msg['to'] = sEmail
        msg['from'] = secrets.FROM_ADDRESS
        msg['subject'] = 'Swefreq account created'
        msg.add_header('reply-to', secrets.REPLY_TO_ADDRESS)
        body = "Your Swefreq account has been activated."
        msg.attach(MIMEText(body, 'plain'))


        server = smtplib.SMTP(secrets.MAIL_SERVER)
        server.sendmail(msg['from'], [msg['to']], msg.as_string())


class deleteUser(auth.SafeHandler):
    def get(self, sEmail):
        sLoggedInEmail = self.get_current_email()
        tRes = db.query("""select email from swefreq.users where
                              email='%s' and swefreq_admin""" % sLoggedInEmail)
        if len(tRes) == 0:
            return
        if sLoggedInEmail == sEmail:
            # Don't let the admin delete hens own account
            return
        db.execute("""update swefreq.users set full_user = '0'
                      where email = '%s'""" % sEmail)

class denyUser(auth.SafeHandler):
    def get(self, sEmail):
        sLoggedInEmail = self.get_current_email()
        tRes = db.query("""select email from swefreq.users where
                              email='%s' and swefreq_admin""" % sLoggedInEmail)
        if len(tRes) == 0:
            return
        if sLoggedInEmail == sEmail:
            # Don't let the admin delete hens own account
            return
        db.execute("""delete from swefreq.users where email = '%s'""" % sEmail)

class getOutstandingRequests(auth.SafeHandler):
    def get(self, *args, **kwargs):
        tRes = db.query("""select username, email, affiliation, country, create_date
        from swefreq.users where not full_user""")
        jRes = []
        for row in tRes:
            sDate = str(row.create_date).split(' ')[0]
            jRes.append({'user' : row.username,
                         'email' : row.email,
                         'affiliation' : row.affiliation,
                         'country' : row.country,
                         'applyDate' : sDate
            })
        self.finish(json.dumps(jRes))

class getApprovedUsers(auth.SafeHandler):
    def get(self, *args, **kwargs):
        tRes = db.query("""select username, email, affiliation, country,
        IFNULL(download_count, 0) as download_count, newsletter
        from swefreq.users where full_user""")
        jRes = []
        for row in tRes:
            jRes.append({'user' : row.username,
                         'email' : row.email,
                         'affiliation' : row.affiliation,
                         'country' : row.country,
                         'downloadCount' : row.download_count,
                         'newsletter': row.newsletter
            })
        self.finish(json.dumps(jRes))

class StaticFileHandler(tornado.web.StaticFileHandler):
    def get(self, path, include_body=True):
        if path.endswith('woff'):
            self.set_header('Content-Type','application/font-woff')
        super(StaticFileHandler, self).get(path, include_body)
