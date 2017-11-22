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

if ( -f $data->{'study'}{'description'} ) {
    local $/;
    my $fh = IO::File->new( $data->{'study'}{'description'}, "r" ) or die($!);
    $data->{'study'}{'description'} = <$fh>;
    $fh->close();
}

my $dbh = DBI->connect( 'DBI:mysql:database=swefreq;host=swefreq-db-dev',
    'swefreq', undef, { 'RaiseError' => 1 } );

$dbh->do(
    'INSERT IGNORE INTO study '
      . '(pi_name,pi_email,contact_name,contact_email,'
      . 'title,description,publication_date,ref_doi) '
      . 'VALUE (?,?,?,?,?,?,?,?)',
    undef,
    @{ $data->{'study'} }{
        'pi-name',          'pi-email',
        'contact-name',     'contact-email',
        'title',            'description',
        'publication-date', 'ref-doi'
    }
);

foreach my $dataset ( @{ $data->{'study'}{'datasets'} } ) {
    $dbh->do(
        'INSERT IGNORE INTO dataset '
          . '(study_pk,short_name,full_name,avg_seq_depth,'
          . 'seq_type,seq_tech,seq_center,dataset_size,mongodb_collection '
          . 'SELECT study_pk,?,?,?,?,?,?,?,"exac" '
          . 'FROM study WHERE title = ? AND pi_email = ?',
        undef,
        @{$dataset}{
            'short-name', 'full-name',  'avg-seq-depth', 'seq-type',
            'seq-tech',   'seq-center', 'dataset-size'
        },
        @{ $data->{'study'} }{ 'title', 'pi-email' }
    );
}
