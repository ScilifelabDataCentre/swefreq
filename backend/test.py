import unittest
from unittest import TestCase
import requests
import peewee
import db


class RequestTests(TestCase):
    HOST = 'http://localhost:4000'

    def newSession(self):
        if hasattr(self, '_session'):
            self.destroySession()
        self._session = requests.Session()

    def destroySession(self):
        self._session.close()
        del self._session

    @property
    def session(self):
        if hasattr(self, '_session'):
            return self._session
        return requests

    @property
    def cookies(self):
        if hasattr(self, '_session'):
            return self._session.cookies
        return {}

    def getUrl(self, path):
        return "{}{}".format(self.HOST, path)

    def get(self, path, *args, **kwargs):
        return self.session.get(self.getUrl(path), *args, **kwargs)

    def post(self, path, *args, **kwargs):
        return self.session.post(self.getUrl(path), *args, **kwargs)

    def assertHTTPCode(self, path, code=200, method='get', *args, **kwargs):
        m = getattr(self, method.lower())
        r = m(path, *args, **kwargs)
        self.assertEqual(r.status_code, code)

    def login_user(self,user):
        self.assertHTTPCode('/developer/login?user={}&email={}'.format(user,user), 200)


class TestEndpoints(RequestTests):
    def test_datasets(self):
        self.assertHTTPCode('/api/datasets')

    def test_one_dataset(self):
        self.assertHTTPCode('/api/datasets/Dataset%201')

    def test_dataset_logo(self):
        self.assertHTTPCode('/api/datasets/Dataset%201/logo', 404)

    def test_dataset_collection(self):
        self.assertHTTPCode('/api/datasets/Dataset%201/collection')

    def test_get_versions(self):
        self.assertHTTPCode('/api/datasets/Dataset%201/versions')

    def test_get_one_version(self):
        self.assertHTTPCode('/api/datasets/Dataset%201/versions/Version%201-1')

    def test_get_users_current(self):
        self.assertHTTPCode('/api/datasets/Dataset%201/users_current', 403)

    def test_get_users_pending(self):
        self.assertHTTPCode('/api/datasets/Dataset%201/users_pending', 403)

    def test_create_temporary_link(self):
        self.assertHTTPCode('/api/datasets/Dataset%201/temporary_link', 403)

    def test_list_files(self):
        self.assertHTTPCode('/api/datasets/Dataset%201/files', 403)

    def test_request_access(self):
        self.assertHTTPCode('/api/datasets/Dataset%201/users/email0/request', 403)

    def test_user_me(self):
        self.assertHTTPCode('/api/users/me')

    def test_user_datasets(self):
        self.assertHTTPCode('/api/users/datasets', 403)


class TestRequestAccess(RequestTests):
    USER='e1'

    def setUp(self):
        self.newSession()
        if db.database.is_closed():
            db.database.connect()

    def tearDown(self):
        self.destroySession()
        try:
            u = db.User.select(db.User).where(db.User.email==self.USER).get()
            try:
                u.dataset_access.get().delete_instance()
            except peewee.PeeweeException:
                pass
            try:
                for l in u.access_logs:
                    l.delete_instance()
            except peewee.PeeweeException:
                pass
            try:
                u.delete_instance()
            except peewee.PeeweeException:
                pass
        except db.User.DoesNotExist:
            pass

        if not db.database.is_closed():
            db.database.close()


    def test_login(self):
        self.login_user(self.USER)

        count = db.User.select().where(db.User.email==self.USER).count()
        self.assertEqual(count, 0)

        self.assertIn('email', self.cookies)
        self.assertIn('user', self.cookies)

    def test_request_access_with_get(self):
        self.login_user(self.USER)
        self.assertHTTPCode('/api/datasets/Dataset 1/users/{}/request'.format(self.USER), 405)

    def test_request_access_without_xsrf(self):
        self.login_user(self.USER)
        r = self.post('/api/datasets/Dataset 1/users/{}/request'.format(self.USER),
                data = {
                        "affiliation": 'none',
                        "country": "Sweden",
                        "newsletter": 0,
                    }
                )
        self.assertEqual(r.status_code, 403)

    def test_get_xsrf_token(self):
        self.get('/api/datasets')
        self.assertIn('_xsrf', self.cookies)

    def test_request_access_with_wrong_xsrf_1(self):
        self.login_user(self.USER)
        r = self.post('/api/datasets/Dataset 1/users/{}/request'.format(self.USER),
                data = {
                        "affiliation": 'none',
                        "country": "Sweden",
                        "newsletter": 0,
                        "_xsrf": 'Fnurken',
                    }
                )
        self.assertEqual(r.status_code, 403)

    def test_request_access_with_wrong_xsrf_2(self):
        self.login_user(self.USER)

        self.assertIn('_xsrf', self.cookies)
        self.assertIn('user', self.cookies)
        self.assertIn('email', self.cookies)

        r = self.post('/api/datasets/Dataset 1/users/{}/request'.format(self.USER),
                data = {
                        "affiliation": 'none',
                        "country": "Sweden",
                        "newsletter": 0,
                        "_xsrf": 'Fnurken',
                    }
                )
        self.assertEqual(r.status_code, 403)

    def test_request_access_correctly(self):
        self.login_user(self.USER)

        count = db.User.select().where(db.User.email==self.USER).count()
        self.assertEqual(count, 0)

        r = self.post('/api/datasets/Dataset 1/users/{}/request'.format(self.USER),
                data = {
                        "affiliation": 'none',
                        "country": "Sweden",
                        "newsletter": 0,
                        "_xsrf": self.cookies['_xsrf'],
                    }
                )
        self.assertEqual(r.status_code, 200)

        count = db.User.select().where(db.User.email==self.USER).count()
        self.assertEqual(count, 1)

        r = self.get('/api/users/datasets')
        self.assertEqual(r.status_code, 200)
        try:
            json = r.json()
        except ValueError:
            self.fail("Can't parse JSON Data")

        self.assertIn('data', json)
        self.assertEqual(json['data'][0]['access'], False)


class TestAdminAccess(RequestTests):
    def setUp(self):
        self.newSession()

    def tearDown(self):
        self.destroySession()

    def test_login_admin(self):
        self.login_user('admin12')

        self.assertIn('email', self.cookies)
        self.assertIn('user', self.cookies)

    def test_admin_list_users(self):
        self.login_user('admin12')

        self.assertHTTPCode('/api/datasets/Dataset%201/users_current', 200)
        self.assertHTTPCode('/api/datasets/Dataset%201/users_pending', 200)

        self.assertHTTPCode('/api/datasets/Dataset%202/users_current', 200)
        self.assertHTTPCode('/api/datasets/Dataset%202/users_pending', 200)

    def test_admin_list_users_only_own_project_1(self):
        self.login_user('admin1')

        self.assertHTTPCode('/api/datasets/Dataset%201/users_current', 200)
        self.assertHTTPCode('/api/datasets/Dataset%201/users_pending', 200)

        self.assertHTTPCode('/api/datasets/Dataset%202/users_current', 403)
        self.assertHTTPCode('/api/datasets/Dataset%202/users_pending', 403)

    def test_admin_list_users_only_own_project_2(self):
        self.login_user('admin2')

        self.assertHTTPCode('/api/datasets/Dataset%201/users_current', 403)
        self.assertHTTPCode('/api/datasets/Dataset%201/users_pending', 403)

        self.assertHTTPCode('/api/datasets/Dataset%202/users_current', 200)
        self.assertHTTPCode('/api/datasets/Dataset%202/users_pending', 200)

    def test_admin_list_users_get_data(self):
        self.login_user('admin1')

        u = self.get('/api/datasets/Dataset%201/users_pending')
        try:
            json = u.json()
        except ValueError:
            self.fail("Can't parse JSON Data")

        self.assertIn('data', json)
        user = json['data'][0]

        self.assertIn('email', user)
        self.assertIn('user', user)
        self.assertIn('hasAccess', user)
        self.assertEqual(user['hasAccess'], 0)

    def test_admin_is_admin(self):
        self.login_user('admin1')

        r = self.get('/api/users/datasets')
        self.assertEqual(r.status_code, 200)
        try:
            json = r.json()
        except ValueError:
            self.fail("Can't parse JSON Data")

        self.assertIn('data', json)
        self.assertEqual(json['data'][0]['access'], True)
        self.assertEqual(json['data'][0]['isAdmin'], True)


class TestUserManagement(RequestTests):

    def setUp(self):
        self.newSession()

    def tearDown(self):
        self.destroySession()

        if hasattr(self, '_email'):
            al = (db.UserAccessLog.select()
                    .join(db.User)
                    .where(
                        (   (db.UserAccessLog.action == 'access_granted')
                          | (db.UserAccessLog.action == 'access_revoked'))
                        & (db.User.email == self._email)
                ))
            for a in al:
                a.delete_instance()

    def test_admin_approve_user(self):
        self.login_user('admin1')

        r = self.get('/api/datasets/Dataset%201/users_pending')
        email = r.json()['data'][0]['email']
        self._email = email

        self.assertHTTPCode('/api/datasets/Dataset%201/users/{}/approve'.format(email), 405)
        self.assertHTTPCode('/api/datasets/Dataset%201/users/{}/approve'.format(email), 403, 'POST')
        self.assertHTTPCode('/api/datasets/Dataset%201/users/{}/approve'.format(email), 403, 'POST',
                data = {'_xsrf': "The wrong thing"} )

        self.assertHTTPCode('/api/datasets/Dataset%201/users/{}/approve'.format(email), 200, 'POST',
                data = {'_xsrf': self.cookies['_xsrf']} )


        r = self.get('/api/datasets/Dataset%201/users_current')
        l = [u for u in r.json()['data'] if u['email'] == email]

        self.assertEqual(len(l), 1)

    def test_recently_approved_user_can_list_files(self):
        self.login_user('admin1')

        u = self.get('/api/datasets/Dataset%201/users_pending').json()['data'][0]
        self._email = u['email']

        self.newSession()
        self.login_user(u['email'])
        self.assertHTTPCode('/api/datasets/Dataset%201/files', 403)

        self.newSession()
        self.login_user('admin1')
        self.assertHTTPCode('/api/datasets/Dataset%201/users/{}/approve'.format(u['email']), 200, 'POST',
                data = {'_xsrf': self.cookies['_xsrf']} )

        self.newSession()
        self.login_user(u['email'])
        self.assertHTTPCode('/api/datasets/Dataset%201/files', 200)

        # The dataset should be listed on the dataset page as well
        r = self.get('/api/users/datasets')
        self.assertEqual(r.status_code, 200)
        try:
            json = r.json()
        except ValueError:
            self.fail("Can't parse JSON Data")

        self.assertIn('data', json)
        self.assertEqual(json['data'][0]['access'], True)

    def test_recently_revoked_user_cant_list_files(self):
        self.login_user('admin1')

        u = self.get('/api/datasets/Dataset%201/users_current').json()['data'][0]
        self._email = u['email']

        self.newSession()
        self.login_user(u['email'])
        self.assertHTTPCode('/api/datasets/Dataset%201/files', 200)

        self.newSession()
        self.login_user('admin1')
        self.assertHTTPCode('/api/datasets/Dataset%201/users/{}/revoke'.format(u['email']), 200, 'POST',
                data = {'_xsrf': self.cookies['_xsrf']} )

        self.newSession()
        self.login_user(u['email'])
        self.assertHTTPCode('/api/datasets/Dataset%201/files', 403)

    def test_full_user_roundabout(self):
        email = 'unlisted'
        self._email = email

        ## Request access
        self.assertHTTPCode('/api/datasets/Dataset%201/files', 403)
        self.login_user(email)
        self.assertHTTPCode('/api/datasets/Dataset%201/files', 403)
        self.assertHTTPCode('/api/datasets/Dataset 1/users/{}/request'.format(email), 200, 'POST',
                data = {
                        "affiliation": 'none',
                        "country": "Sweden",
                        "newsletter": 0,
                        "_xsrf": self.cookies['_xsrf'],
                    }
                )
        self.assertHTTPCode('/api/datasets/Dataset%201/files', 403)

        ## Approve user
        self.newSession()
        self.login_user('admin1')

        # User is in pending queue
        users = self.get('/api/datasets/Dataset%201/users_pending').json()['data']
        u = [ x for x in users if x['email'] == email ]
        self.assertEqual(len(u), 1)

        self.assertHTTPCode('/api/datasets/Dataset%201/users/{}/approve'.format(email), 200, 'POST',
                data = {'_xsrf': self.cookies['_xsrf']} )

        # User is in approved queue
        users = self.get('/api/datasets/Dataset%201/users_current').json()['data']
        u = [ x for x in users if x['email'] == email ]
        self.assertEqual(len(u), 1)

        # User can log in and do stuff
        self.newSession()
        self.login_user(email)
        self.assertHTTPCode('/api/datasets/Dataset%201/files', 200)

        # Revoke user
        self.newSession()
        self.login_user('admin1')
        self.assertHTTPCode('/api/datasets/Dataset%201/users/{}/revoke'.format(email), 200, 'POST',
                data = {'_xsrf': self.cookies['_xsrf']} )

        # User is not in approved queue
        users = self.get('/api/datasets/Dataset%201/users_current').json()['data']
        u = [ x for x in users if x['email'] == email ]
        self.assertEqual(len(u), 0)

        # User can log in but cant do stuff
        self.newSession()
        self.login_user(email)
        self.assertHTTPCode('/api/datasets/Dataset%201/files', 403)


class TestLoggedInUser(RequestTests):
    def setUp(self):
        if not hasattr(self, '_email'):
            self.newSession()
            self.login_user('admin1')
            u = self.get('/api/datasets/Dataset%201/users_current').json()['data'][0]
            self._email = u['email']

        self.newSession()
        self.login_user(self._email)

    def tearDown(self):
        self.destroySession()

    def testLoggedInFiles(self):
        self.assertHTTPCode('/api/datasets/Dataset 1/files', 200)

    def testLoggedInTempLinkGet(self):
        self.assertHTTPCode('/api/datasets/Dataset 1/temporary_link', 405)

    def testLoggedInTempLinkPost(self):
        self.assertHTTPCode('/api/datasets/Dataset 1/temporary_link', 403, 'POST')

    def testLoggedInTempLinkPostXSRF1(self):
        self.assertHTTPCode('/api/datasets/Dataset 1/temporary_link', 403, 'POST',
                data = { '_xsrf': "INCORRECT"})

    def testLoggedInTempLinkPostXSRF2(self):
        self.assertHTTPCode('/api/datasets/Dataset 1/temporary_link', 200, 'POST',
                data = {'_xsrf': self.cookies['_xsrf']} )


if __name__ == '__main__':
    unittest.main()
