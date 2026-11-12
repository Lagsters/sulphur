// Test harness for programs that run on the console: results go to the memory card, which
// tools/check.py reads after the program halts.
//
// Card layout (32-bit words; the card file adds an 8-byte "V32-MEMC" header before word 0):
//   0..63          input parameters written by check.py (seed, rounds...)
//   RESULT+0       RESULT_MAGIC
//   RESULT+1       1 once the program has finished, 0 while it runs
//   RESULT+2..3    tests run, tests failed
//   RESULT+8..     the name of the test running now (0-terminated): the culprit of a hang
//   FAILS..        per failed test: its name, 0, what went wrong, 0
//   STATS..        free-form numbers of simulations and performance programs
#ifndef HARNESS_H
#define HARNESS_H

#define CARD_RESULT    1024
#define RESULT_MAGIC   1398096979
#define CARD_FAILS     2048
#define CARD_STATS     8192
#define NAME_MAX       120

int[ 64 ] card_input;
int[ 8 ] result_head;
int[ NAME_MAX ] test_name;
int[ 200 ] fail_note;
int[ 16 ] number_text;
bool in_test = false;
bool test_ok = true;
int tests_run = 0, tests_failed = 0;
int fail_at = CARD_FAILS;

void read_input() { card_read_data( card_input, 0, 64 ); }

void write_head( int done )
{
    result_head[ 0 ] = RESULT_MAGIC;
    result_head[ 1 ] = done;
    result_head[ 2 ] = tests_run;
    result_head[ 3 ] = tests_failed;
    card_write_data( result_head, CARD_RESULT, 4 );
}

void card_string( int* s, int at ) { card_write_data( s, at, strlen( s ) + 1 ); }

void close_test()
{
    if( !in_test ) return;
    in_test = false;
    tests_run++;
    if( !test_ok )
    {
        tests_failed++;
        card_string( test_name, fail_at );
        fail_at += strlen( test_name ) + 1;
        card_string( fail_note, fail_at );
        fail_at += strlen( fail_note ) + 1;
    }
    write_head( 0 );
}

// starts a test; its name says the behaviour it checks
void test( int* name )
{
    close_test();
    strncpy( test_name, name, NAME_MAX - 1 );
    test_name[ NAME_MAX - 1 ] = 0;
    card_string( test_name, CARD_RESULT + 8 );
    in_test = true;
    test_ok = true;
    fail_note[ 0 ] = 0;
}

// the first failed expectation of a test is the one reported
void expect( bool cond, int* what )
{
    if( cond || !test_ok ) return;
    test_ok = false;
    strncpy( fail_note, what, 150 );
    fail_note[ 150 ] = 0;
}

void expect_eq( int got, int want, int* what )
{
    if( got == want || !test_ok ) return;
    expect( false, what );
    strcat( fail_note, ": got " );
    itoa( got, number_text, 10 );
    strcat( fail_note, number_text );
    strcat( fail_note, ", want " );
    itoa( want, number_text, 10 );
    strcat( fail_note, number_text );
}

void finish_tests()
{
    close_test();
    write_head( 1 );
    exit();
}

// statistics of simulations and performance runs: STATS+i
void stat_put( int i, int v ) { number_text[ 0 ] = v; card_write_data( number_text, CARD_STATS + i, 1 ); }

#endif
