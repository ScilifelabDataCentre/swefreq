#!/usr/bin/env perl

use strict;
use warnings;

use DBI;
use Data::Dumper;
use IO::File;
use JSON;

sub get_file {
    my ($fname) = @_;

    local $/;
    my $fh = IO::File->new( $fname, "r" ) or die($!);
    my $text = <$fh>;
    $fh->close();

    return $text;
}

my $json_text = get_file('metadata-example.json');
my $data      = decode_json($json_text);

my $dbuser = '';
my $dbpass = '';

my $dbh = DBI->connect( 'DBI:mysql:database=swefreq;host=swefreq-db-dev',
    $dbuser, $dbpass, { 'RaiseError' => 1 } );

# Insert study
if ( -f $data->{'study'}{'description'} ) {
    $data->{'study'}{'description'} =
      get_file( $data->{'study'}{'description'} );
}
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

    # Insert dataset
    $dbh->do(
        'INSERT IGNORE INTO dataset '
          . '(study_pk,short_name,full_name,avg_seq_depth,'
          . 'seq_type,seq_tech,seq_center,dataset_size,mongodb_collection) '
          . 'SELECT study_pk,?,?,?,?,?,?,?,"exac" '
          . 'FROM study WHERE title = ? AND pi_email = ?',
        undef,
        @{$dataset}{
            'short-name', 'full-name',  'avg-seq-depth', 'seq-type',
            'seq-tech',   'seq-center', 'dataset-size'
        },
        @{ $data->{'study'} }{ 'title', 'pi-email' }
    );

    # Insert dataset_version
    my $version = $dataset->{'version'};
    if ( -f $version->{'description'} ) {
        $version->{'description'} = get_file( $version->{'description'} );
    }
    if ( -f $version->{'terms'} ) {
        $version->{'terms'} = get_file( $version->{'terms'} );
    }
    $dbh->do(
        'INSERT IGNORE INTO dataset_version '
          . '(dataset_pk,version,description,terms,var_call_ref,'
          . 'available_from,ref_doi) '
          . 'SELECT dataset_pk,?,?,?,?,?,? '
          . 'FROM dataset WHERE short_name = ?',
        undef,
        @{$version}{
            'version',        'description',
            'terms',          'var-call-ref',
            'available-from', 'ref-doi'
        },
        $dataset->{'short-name'}
    );

    # Insert collection and sample_set
    foreach my $sample_set ( @{ $dataset->{'sample-sets'} } ) {
        $dbh->do(
            'INSERT IGNORE INTO collection '
              . '(name,ethnicity) '
              . 'VALUE (?,?)',
            undef,
            @{$sample_set}{ 'collection', 'ethnicity' }
        );
        $dbh->do(
            'INSERT IGNORE INTO sample_set '
              . '(dataset_pk,collection_pk,sample_size,phenotype) '
              . 'SELECT d.dataset_pk,c.collection_pk,?,? '
              . 'FROM collection AS c '
              . 'JOIN dataset AS d '
              . 'WHERE c.name = ? AND d.short_name = ?',
            undef,
            @{$sample_set}{ 'sample-size', 'phenotype', 'collection' },
            $dataset->{'short-name'}
        );
    }

    # Insert logotype if present
    if ( defined( $dataset->{'logotype-mimitype'} )
        && -f $dataset->{'logotype'} )
    {
        $dataset->{'logotype'} = get_file( $dataset->{'logotype'} );
        $dbh->do(
            'INSERT IGNORE INTO dataset_logo '
              . '(dataset_pk,data,mimetype) '
              . 'SELECT dataset_pk,?,? '
              . 'FROM dataset WHERE short_name = ?',
            undef,
            @{$dataset}{ 'logotype', 'logotype-mimetype', 'short-name' }
        );
    }
}
