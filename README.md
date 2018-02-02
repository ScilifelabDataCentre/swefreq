SweFreq - Swedish Frequency database
====================================

Running on a production system
------------------------------

The application has only been tested with python 3.5.2. It will most likely work with at least other 3.5 versions.

`virtualenv` is not a requirement but it will help you to install the application.

1. Download the repository from [github](https://github.com/NBISweden/swefreq)

2. Credentials

   2.1 Make sure you have registered an Elixir AAI application with the Elixir.

   2.2 (legacy) Create Google OAuth 2.0 credentials with the [Google API
   Console](https://console.developers.google.com/) for enabling
   authentication.

3. Rename the file `settings_sample.json` into `settings.json` and edit all
   the values.

4. Install MySQL. Only tested with 5.6. Note, the schema is incompatible with the
   latest version of MariaDB.

5. If you have `virtualenv` and `pip` installed then you can do the following
   to install the required Python packages. Locate the `requirements.txt` file
   in the `swefreq` repository.

    source /path/to/bin/activate             # activate your virtualenv
    pip install -r /path/to/requrements.txt  # install the required Python packages

6. Create the MySQL database, user and tables with the following command:

       mysql -u root -p < ./sql/swefreq.sql

   To experience the full site you need to manually add a dataset and a user
   to the database. Log into the mysql console and enter something like the
   following, change the values to whatever fits your site (N.B.
   `myemail@google.com` is your google id):

       USE swefreq;
       INSERT INTO dataset (dataset_pk, name) VALUES (1, "Dataset");
       INSERT INTO user (user_pk,name, email) VALUES (1, "test", "myemail@google.com");
       INSERT INTO dataset_access (dataset_pk, user_pk, is_admin, has_access) VALUES (1,1,1,1);


### Start the server

    source /path/to/bin/activate                   # activate your virtualenv
    python /path/to/route.py


Quick development mode
----------------------

1. Install docker
2. Look at `test/travis_before_install.sh` to initiate the mysql docker image.
3. Copy `settings_sample.json` into `settings.json` and
    - Change mysqlSchema into `swefreq_test`.
    - Change mysqlPort to 3366
    - Update the credentials for elixir and google oauth.
        - Elixir/redirectUri: http://localhost:4000/elixir/login
        - redirectUri: http://localhost:4000/login
4. Run "Test 2. Load the swefreq schema" from `test/travis_script.sh`.
5. Run `make` in the root directory of the project.
6. Make a symbolic link from `backend/static` to `static`.
7. Run the server:
```bash
$ cd backend
$ python route.py --develop
```
