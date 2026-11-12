// Frame cost of the heaviest scenes, through the game's own screens (src/ui.h) with all drawing.
//   input (card words 0..): mode (0 battle demo with four bots, 1 dragon fight with hero bots),
//     frames to run
//   output (CARD_STATS+): 0 frames run, 1 worst frame in cycles, 2 average, 3 frames over the
//     250 000-cycle budget, 4 the frame (counted from the start) of the worst one, 5 the console
//     frame counter at the first frame, 6 cycles of the first frame (setting the scene up, not
//     counted in 1..4)
// The runner's SKIPLOG shows the same overruns as skipped frames.
#include "video.h"
#include "input.h"
#include "audio.h"
#include "time.h"
#include "math.h"
#include "misc.h"
#include "string.h"
#include "memcard.h"

#include "../src/ui.h"
#include "harness.h"
#include "fixtures.h"

#define FRAME_CYCLES 250000

int[ 8 ] perf_stats;

void start_dragon()
{
    start_campaign( false, STAGE_COUNT );
    camp_lives = 99;
    enter( ST_STAGE );
}

// the heroes are bots: the stage restarts itself after a lost life (src/ui.h)
void heroes_are_bots()
{
    for( int i = 0; i < player_count; i++ ) if( players[ i ].team == 1 ) players[ i ].human = false;
    camp_lives = 99;
}

void main()
{
    read_input();
    init_strings();
    init_sprites();
    text_init();
    sound_init();
    ui_init();
    srand( 5 );
    bool dragon = card_input[ 0 ] == 1;
    if( dragon ) start_dragon(); else start_battle( true );
    int worst = 0, over = 0, worst_at = 0, sum = 0;
    perf_stats[ 5 ] = get_frame_counter();
    for( int f = 1; f <= card_input[ 1 ]; f++ )
    {
        int f0 = get_frame_counter();
        frame++;
        clear_screen( color_black );
        if( dragon )
        {
            if( state != ST_STAGE ) start_dragon();
            heroes_are_bots();
            heroes_let_sheep_go();
        }
        else if( state != ST_BATTLE ) start_battle( true );
        ui_frame();
        sound_frame();
        for( int e = 0; e < EV_COUNT; e++ ) events[ e ] = 0;
        int used = ( get_frame_counter() - f0 ) * FRAME_CYCLES + get_cycle_counter();
        if( f == 1 ) perf_stats[ 6 ] = used;
        else
        {
            if( used > worst ) { worst = used; worst_at = f; }
            if( used > FRAME_CYCLES ) over++;
            sum += used / 100;
        }
        perf_stats[ 0 ] = f; perf_stats[ 1 ] = worst; perf_stats[ 2 ] = ( sum / imax( 1, f - 1 ) ) * 100;
        perf_stats[ 3 ] = over; perf_stats[ 4 ] = worst_at;
        if( f % 60 == 0 ) card_write_data( perf_stats, CARD_STATS, 8 );
        end_frame();
    }
    card_write_data( perf_stats, CARD_STATS, 8 );
    exit();
}
