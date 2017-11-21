#!/usr/bin/env perl

use strict;
use warnings;

use DBI;
use Data::Dumper;
use IO::File;
use JSON;

my $json_text;
{
    local $/;
    my $json_file = 'metadata-example.json';
    my $fh = IO::File->new( $json_file, "r" ) or die($!);
    $json_text = <$fh>;
    $fh->close();
}

print "$json_text";
my $data = decode_json($json_text);

print Dumper($data);
exit;

my $dsn = 'DBI:mysql:database=swefreq;host=swefreq-db-dev';
my $dbh = DBI->connect( $dsn, 'swefreq' );
