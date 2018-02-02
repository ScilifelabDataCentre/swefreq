#!/usr/bin/env perl

use strict;
use warnings;

use Carp;
use DBI;
use Data::Dumper;
use Getopt::Long;
use IO::File;
use JSON;
use MIME::Types;

my $opt_config = 'settings.json';
my $opt_file   = 'metadata-example.json';
my $opt_help   = 0;

sub usage {
    print("Usage:\n");
    print("\t$0 [-c config-file] [-f data-file]\n");
    print("\t$0 -h\n");
}

sub get_file {
    my ($fname) = @_;

    local $/;
    my $fh = IO::File->new( $fname, "r" ) or croak("$!");
    my $text = <$fh>;
    $fh->close();

    return $text;
}

sub has_data {
    my ( $hash, $key ) = @_;

    return exists( $hash->{$key} ) && $hash->{$key} =~ /\S/;
}

sub validate_required {
    my ( $variable, $name, @keys ) = @_;

    my $error = 0;
    foreach my $key (@keys) {
        if ( !has_data( $variable, $key ) ) {
            ++$error;
            printf( STDERR "%s is missing required key %s\n",
                    $name, $key );
        }
    }

    return $error;
}

if ( !GetOptions( 'help|h'     => \$opt_help,
                  'config|c=s' => \$opt_config,
                  'file|f=s'   => \$opt_file ) )
{
    usage();
    die('Failed to parse command line options');
}
if ($opt_help) { usage(); exit 0; }

my $settings = decode_json( get_file($opt_config) );
my $study    = decode_json( get_file($opt_file) );

my $dbh = DBI->connect(sprintf( "DBI:mysql:database=%s;host=%s;port=%s",
                                $settings->{'mysqlSchema'},
                                $settings->{'mysqlHost'},
                                $settings->{'mysqlPort'} ),
                       $settings->{'mysqlUser'},
                       $settings->{'mysqlPasswd'},
                       { 'RaiseError' => 1 } );

# Insert study
die
  if validate_required(
    $study,
    'study',
    qw( title publication-date pi-name pi-email contact-name contact-email datasets )
  );

if ( has_data( $study, 'description' ) ) {
    if ( -f $study->{'description'} ) {
        $study->{'description'} = get_file( $study->{'description'} );
    }
}
else { delete( $study->{'description'} ); }

if ( !has_data( $study, 'ref-doi' ) ) {
    delete( $study->{'ref-doi'} );
}

$dbh->do( 'INSERT IGNORE INTO study ' .
            '(pi_name,pi_email,contact_name,contact_email,' .
            'title,description,publication_date,ref_doi) ' .
            'VALUE (?,?,?,?,?,?,?,?)',
          undef,
          @{$study}{
              'pi-name',          'pi-email',
              'contact-name',     'contact-email',
              'title',            'description',
              'publication-date', 'ref-doi' } );

foreach my $dataset ( @{ $study->{'datasets'} } ) {
    # Insert dataset
    die
      if validate_required( $dataset, 'dataset',
          qw( short-name full-name dataset-size version sample-sets ) );

    foreach
      my $opt_key (qw( avg-seq-depth seq-type seq-tech seq-center ))
    {
        if ( !has_data( $dataset, $opt_key ) ) {
            delete( $dataset->{$opt_key} );
        }
    }

    $dbh->do( 'INSERT IGNORE INTO dataset ' .
                '(study_pk,short_name,full_name,avg_seq_depth,' .
                'seq_type,seq_tech,seq_center,' .
                'dataset_size,mongodb_collection) ' .
                'SELECT study_pk,?,?,?,?,?,?,?,"non-existent" ' .
                'FROM study WHERE title = ? AND pi_email = ?',
              undef,
              @{$dataset}{
                  'short-name',    'full-name',
                  'avg-seq-depth', 'seq-type',
                  'seq-tech',      'seq-center',
                  'dataset-size' },
              @{$study}{ 'title', 'pi-email' } );

    # Insert dataset_version
    my $version = $dataset->{'version'};
    die
      if validate_required( $version, 'version',
                            qw( version description terms ) );

    foreach my $opt_key (qw( var-call-ref ref-doi available-from )) {
        if ( !has_data( $version, $opt_key ) ) {
            delete( $version->{$opt_key} );
        }
    }

    if ( -f $version->{'description'} ) {
        $version->{'description'} =
          get_file( $version->{'description'} );
    }

    if ( -f $version->{'terms'} ) {
        $version->{'terms'} = get_file( $version->{'terms'} );
    }

    $dbh->do( 'INSERT IGNORE INTO dataset_version ' .
                '(dataset_pk,version,description,terms,var_call_ref,' .
                'available_from,ref_doi) ' .
                'SELECT dataset_pk,?,?,?,?,?,? ' .
                'FROM dataset WHERE short_name = ?',
              undef,
              @{$version}{
                  'version',        'description',
                  'terms',          'var-call-ref',
                  'available-from', 'ref-doi' },
              $dataset->{'short-name'} );

    # Insert collection and sample_set
    foreach my $sample_set ( @{ $dataset->{'sample-sets'} } ) {
        die
          if validate_required( $sample_set, 'sample-set',
                               qw( collection sample-size phenotype ) );

        if ( !has_data( $sample_set, 'ethnicity' ) ) {
            delete( $sample_set->{'ethnicity'} );
        }

        $dbh->do( 'INSERT IGNORE INTO collection ' .
                    '(name,ethnicity) VALUE (?,?)',
                  undef,
                  @{$sample_set}{ 'collection', 'ethnicity' } );
        $dbh->do('INSERT IGNORE INTO sample_set ' .
                   '(dataset_pk,collection_pk,sample_size,phenotype) ' .
                   'SELECT d.dataset_pk,c.collection_pk,?,? ' .
                   'FROM collection AS c JOIN dataset AS d ' .
                   'WHERE c.name = ? AND d.short_name = ?',
                 undef,
                 @{$sample_set}{ 'sample-size', 'phenotype',
                     'collection' },
                 $dataset->{'short-name'} );
    }

    # Insert logotype if present
    if ( has_data( $dataset, 'logotype' ) && -f $dataset->{'logotype'} )
    {
        my $mt = MIME::Types->new();
        $dataset->{'logotype-mimetype'} =
          $mt->mimeTypeOf( $dataset->{'logotype'} )->type();
        $dataset->{'logotype'} = get_file( $dataset->{'logotype'} );

        $dbh->do( 'INSERT IGNORE INTO dataset_logo ' .
                    '(dataset_pk,data,mimetype) ' .
                    'SELECT dataset_pk,?,? ' .
                    'FROM dataset WHERE short_name = ?',
                  undef,
                  @{$dataset}{ 'logotype', 'logotype-mimetype',
                      'short-name' } );
    }
} ## end foreach my $dataset ( @{ $study...})
