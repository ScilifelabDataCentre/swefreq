#!/usr/bin/env python3
"""
Swefreq data importer.
"""

from data_importer.dbsnp_importer import DbSNPImporter

if __name__ == '__main__':

    import os
    import argparse
    import logging

    parser = argparse.ArgumentParser( description = __doc__ ,
             formatter_class = argparse.ArgumentDefaultsHelpFormatter )

    parser.add_argument("--batch_size", type=int, default=5000,
                        help = ("Where batch insertion is possible, use this number of"
                                " inserts per batch."))
    parser.add_argument("--limit_chrom", default=None,
                        help = "Limit chromosome to insert into the database.")
    parser.add_argument("--data_dir", default=os.path.join(os.path.dirname(__file__),
                                                           "downloaded_files"),
                        help = "Default directory to download and look for files.")

    # Reference versions
    parser.add_argument("--add_reference", action="store_true",
                        help = "Insert new reference set.")

    parser.add_argument("--gencode_version", default=19, type=int,
                        help = "Gencode version to download and use.")
    parser.add_argument("--ensembl_version", default="homo_sapiens_core_75_37",
                        help = "Ensembl database to connect to.")
    parser.add_argument("--dbnsfp_version", default="2.9.3",
                        help = "dbNSFP version to download and use.")
    parser.add_argument("--dbsnp_version", default="b150",
                        help = "dbSNP version to download and use.")
    parser.add_argument("--dbsnp_reference", default="GRCh37p13",
                        help = "Which reference the dbSNP should be aligned to.")

    # Actions
    parser.add_argument("--add_dbsnp", action="store_true",
                        help = "Adds a new dbSNP version to the database.")

    # Logging and verbosity
    parser.add_argument("--disable_progress", action="store_true",
                        help="Do not show progress bars.")
    parser.add_argument("-v", "--verbose", action = "count", default = 3,
                        help="Increase output Verbosity.")
    parser.add_argument("-q", "--quiet", action = "count", default = 0,
                        help="Decrease output Verbosity.")

    args = parser.parse_args()

    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level = (5-args.verbose+args.quiet)*10, datefmt="%H:%M:%S")

    if args.add_dbsnp:
        logging.info("Adding new dbSNP version")
        logging.info("  - dbSNP version:   {}".format(args.dbsnp_version))
        logging.info("  - dbSNP reference: {}".format(args.dbsnp_reference))

        importer = DbSNPImporter(args)
        importer.prepare_data()
        if not args.disable_progress:
            importer.count_entries()
        importer.start_import()

    if args.add_reference:
        logging.info("Adding a new reference set using these sources:")
        logging.info("  - Gencode: {}".format(args.gencode_version))
        logging.info("  - Ensembl: {}".format(args.ensembl_version))
        logging.info("  - dbNSFP:  {}".format(args.dbnsfp_version))
        logging.info("  - dbSNP:   {}".format(args.dbsnp_version))
