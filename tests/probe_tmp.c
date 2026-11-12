#include "video.h"
#include "input.h"
#include "audio.h"
#include "time.h"
#include "math.h"
#include "misc.h"
#include "string.h"
#include "memcard.h"
#include "../src/campaign.h"

int[ 8 ] out;
void note( int* s ) { card_write_data( s, 100, strlen( s ) + 1 ); }
void main()
{
    out[ 0 ] = get_frame_counter();
    note( "hello" );
    int f0 = get_frame_counter();
    for( int i = 0; i < 2000; i++ ) end_frame();
    out[ 1 ] = get_frame_counter() - f0;
    card_write_data( out, 0, 8 );
    exit();
}
