SweFreq - Swedish Frequency database
====================================

Installation
------------

The application has only been tested with python 2.7.10. It will most likely work with at least other 2.7 versions.

`virtualenv` is not a requirement but it will help you to install the application.

1. Download the repository from [github](https://github.com/NBISweden/swefreq)
2. Rename the file `settings_sample.json` into `settings.json` and edit all
   the values.
3. Install MySql. Only tested with 5.6, but should work with version 4 and above


4. If you have `virtualenv` and `pip` installed then you can do the following
   to install the required python packages. Locate the `requirements.txt` file
   in the `swefreq` repository.


    source /path/to/bin/activate             # activate your virtualenv
    pip install -r /path/to/requrements.txt  # install the required python packages


5. Create the MySql database, user and tables with the following command:


       mysql -u root -p < ./sql/swefreq.sql


   To experience the full site you need to manually add a dataset and a user
   to the database. Log into the mysql console and enter something like the
   following:


       USE swefreq;
       INSERT INTO dataset (dataset_pk, name) VALUES (1, "SweGen");
       INSERT INTO user (user_pk,name, email) VALUES (1, "test", "myemail@google.com");
       INSERT INTO dataset_access (dataset_pk, user_pk, is_admin, has_access) VALUES (1,1,1,1);


Start the server
----------------


    source /path/to/bin/activate                   # activate your virtualenv
    python /path/to/route.py
