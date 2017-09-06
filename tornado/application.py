import email.mime.multipart
from email.mime.text import MIMEText
import json
import logging
import peewee
import smtplib
import tornado.web

import db
import handlers
import settings


class Home(handlers.UnsafeHandler):
    def get(self, *args, **kwargs):
        name = None
        email = None
        if self.current_user:
            name = self.current_user.name
            email = self.current_user.email

        self.render('index.html', user_name=name, email=email)


def build_dataset_structure(dataset_version, user=None, dataset=None):
    if dataset is None:
        dataset = dataset_version.dataset.get()
    r = {}
    for key in ['short_name', 'full_name', 'browser_uri',
            'beacon_uri', 'avg_seq_depth', 'seq_type', 'seq_tech',
            'seq_center', 'dataset_size']:
        r[key] = getattr(dataset, key)

    r['version'] = {}
    for key in ['version', 'description', 'terms', 'var_call_ref', 'available_from']:
        r['version'][key] = getattr(dataset_version, key)
    r['version']['available_from'] = r['version']['available_from'].strftime('%Y-%m-%d %H:%M')

    r['has_image']  = dataset.has_image()
    r['is_admin']   = False
    r['has_access'] = False

    if user:
        if user.has_access(dataset):
            r['has_access'] = True
        if user.is_admin(dataset):
            r['is_admin'] = True

    return r

class ListDatasets(handlers.UnsafeHandler):
    def get(self):
        # List all datasets available to the current user, latest is_current
        # earliear than now OR versions that are available in the future that
        # the user is admin of.
        user = self.get_current_user()

        ret = []
        for version in db.DatasetVersionCurrent.select():
            ret.append( build_dataset_structure(version, user) )

        self.finish({'data':ret})


class GetDataset(handlers.UnsafeHandler):
    def get(self, dataset, *args, **kwargs):
        user = self.get_current_user()

        dataset = db.get_dataset(dataset)
        current_version = dataset.current_version.get()

        ret = build_dataset_structure(current_version, user, dataset)

        self.finish(ret)


class GetUser(handlers.UnsafeHandler):
    def get(self, *args, **kwargs):
        user = self.current_user

        ret = { 'user': None, 'email': None }
        if user:
            ret = { 'user': user.name, 'email': user.email }

        self.finish(json.dumps(ret))


class CountryList(handlers.UnsafeHandler):
    def get(self, *args, **kwargs):
        self.write({'countries': [{'name': c} for c in self.country_list()]})

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


class RequestAccess(handlers.SafeHandler):
    def get(self, dataset, *args, **kwargs):
        user = self.current_user
        name = user.name
        email = user.email

        logging.info("Request: " + name + ' ' + email)
        self.finish(json.dumps({'user':name, 'email':email}))

    def post(self, dataset, *args, **kwargs):
        dataset = db.get_dataset(dataset)

        userName    = self.get_argument("userName", default='',strip=False)
        email       = self.get_argument("email", default='', strip=False)
        affiliation = self.get_argument("affiliation", strip=False)
        country     = self.get_argument("country", strip=False)
        newsletter  = self.get_argument("newsletter", strip=False)

        # This is the only chance for XSRF in the application
        # avoid it by checking that the email sent by google is the same as
        # supplied by the form post
        user = self.current_user
        if user.email != email:
            return

        user.affiliation = affiliation
        user.country = country
        logging.info("Inserting into database: {}, {}".format(user.name, user.email))

        try:
            with db.database.atomic():
                user.save() # Save to database
                db.DatasetAccess.create(
                        user             = user,
                        dataset          = dataset,
                        wants_newsletter = newsletter
                    )
                db.UserLog.create(
                        user = user,
                        dataset = dataset,
                        action = 'access_requested'
                    )
        except Exception as e:
            logging.error(e)


class LogEvent(handlers.SafeHandler):
    def get(self, dataset, sEvent):
        user = self.current_user

        ok_events = ['download','consent']
        if sEvent in ok_events:
            db.UserLog.create(
                    user = user,
                    dataset = db.get_dataset(dataset),
                    action = sEvent
                )
        else:
            raise tornado.web.HTTPError(400, reason="Can't log that")

class ApproveUser(handlers.AdminHandler):
    def get(self, dataset, sEmail):
        with db.database.atomic():
            dataset = db.get_dataset(dataset)

            user = db.User.select().where(db.User.email == sEmail).get()

            da = db.DatasetAccess.select().where(
                        db.DatasetAccess.user == user,
                        db.DatasetAccess.dataset == dataset
                ).get()
            da.has_access = True
            da.save()

            db.UserLog.create(
                    user = user,
                    dataset = dataset,
                    action = 'access_granted'
                )

        msg = email.mime.multipart.MIMEMultipart()
        msg['to'] = sEmail
        msg['from'] = settings.from_address
        msg['subject'] = 'Swefreq account created'
        msg.add_header('reply-to', settings.reply_to_address)
        body = "Your Swefreq account has been activated."
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(settings.mail_server)
        server.sendmail(msg['from'], [msg['to']], msg.as_string())


class RevokeUser(handlers.AdminHandler):
    def get(self, dataset, sEmail):
        if self.current_user.email == sEmail:
            # Don't let the admin delete hens own account
            return

        with db.database.atomic():
            dataset = db.get_dataset(dataset)
            user = db.User.select().where(db.User.email == sEmail).get()

            da = db.DatasetAccess.select(
                    ).join(
                        db.User
                    ).where(
                        db.User.email == sEmail,
                        db.DatasetAccess.dataset == dataset
                    ).get()
            da.delete_instance()

            db.UserLog.create(
                    user = user,
                    dataset = dataset,
                    action = 'access_revoked'
                )


class DatasetUsers(handlers.SafeHandler):
    def get(self, dataset, *args, **kwargs):
        dataset = db.get_dataset(dataset)
        query = db.User.select(
                db.User, db.DatasetAccess.wants_newsletter, db.DatasetAccess.has_access
            ).join(
                db.DatasetAccess
            ).switch(
                db.User
            ).join(
                db.UserLog,
                peewee.JOIN.LEFT_OUTER,
                on=(   (db.User.user        == db.UserLog.user)
                     & (db.UserLog.action   == 'download')
                     & (db.UserLog.dataset  == db.DatasetAccess.dataset)
                )
            ).where(
                db.DatasetAccess.dataset    == dataset,
            ).annotate(db.UserLog)

        json_response = []
        for user in query:
            json_response.append({
                    'user':          user.name,
                    'email':         user.email,
                    'affiliation':   user.affiliation,
                    'country':       user.country,
                    'downloadCount': user.count,
                    'newsletter':    user.dataset_access.wants_newsletter,
                    'has_access':    user.dataset_access.has_access
                })

        self.finish(json.dumps(json_response))

class ServeLogo(handlers.UnsafeHandler):
    def get(self, dataset, *args, **kwargs):
        try:
            logo_entry = db.DatasetLogo.select(
                    db.DatasetLogo
                ).join(
                    db.Dataset
                ).where(
                    db.Dataset.short_name == dataset
                ).get()
        except:
            self.send_error(status_code=404)
            return

        self.set_header("Content-Type", logo_entry.mimetype)
        self.write(logo_entry.data)
        self.finish()
