// Sulphur: the sulphur legend, an arena game for Vircon32 (a fork of BlasTIC for TIC-80).
#include "video.h"
#include "input.h"
#include "audio.h"
#include "time.h"
#include "math.h"
#include "misc.h"
#include "string.h"
#include "memcard.h"

#include "render.h"

void main()
{
    init_render();
    srand( get_time() + 1 );
    for( int i = 0; i < MAX_PLAYERS; i++ ) human_slot[ i ] = false;
    demo = true;
    start_match();
    while( true )
    {
        frame++;
        for( int e = 0; e < EV_COUNT; e++ ) events[ e ] = 0;
        if( over_timer > 0 )
        {
            over_timer--;
            if( over_timer == 0 ) { if( match_winner() >= 0 ) start_match(); else start_battle_round(); }
        }
        else if( update_battle() ) over_timer = 120;
        draw_arena_dev();
        end_frame();
    }
}
