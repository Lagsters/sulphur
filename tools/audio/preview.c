// Audio preview: plays the start of every song, a crossfade, then every effect and UI sound,
// measuring the cycles sound_frame() takes. tools/audio/verify.py runs it headless with
// AUDIO_OUT and compares the console's audio with the reference engine (refengine.py), which
// it drives through the same schedule (SCHEDULE in verify.py: keep both in step).
//
//   python tools/build.py tools/audio/preview.c audio_preview
//
// Memory card (words): 0 = 1 when done; per song k at 16 + 4k: max cycles, total cycles,
// frames; the effects part at 16 + 4 * SONG_COUNT.
#include "video.h"
#include "input.h"
#include "audio.h"
#include "time.h"
#include "math.h"
#include "misc.h"
#include "string.h"
#include "memcard.h"

#include "../../src/sound.h"

#define SONG_FRAMES    1800   // 30 s of each song
#define XFADE_FRAMES   300
#define EFFECT_FRAMES  150

int[ 64 ] card;

// one frame of the game loop as main.c runs it, timed
void frame_with( int part )
{
    int t0 = get_cycle_counter();
    sound_frame();
    int spent = get_cycle_counter() - t0;
    int at = 16 + part * 4;
    if( spent > card[ at ] ) card[ at ] = spent;
    card[ at + 1 ] += spent;
    card[ at + 2 ]++;
    for( int e = 0; e < EV_COUNT; e++ ) events[ e ] = 0;
    clear_screen( make_color_rgb( 20, 20, 30 ) );
    end_frame();
}

void main()
{
    for( int i = 0; i < 64; i++ ) card[ i ] = 0;
    for( int e = 0; e < EV_COUNT; e++ ) events[ e ] = 0;
    sound_init();

    for( int s = 0; s < SONG_COUNT; s++ )
    {
        music_stop();
        music_play( s );
        for( int f = 0; f < SONG_FRAMES; f++ ) frame_with( s );
    }

    // a crossfade: battle, then the dragon replaces it
    music_play( SONG_BATTLE );
    for( int f = 0; f < XFADE_FRAMES; f++ ) frame_with( SONG_COUNT );
    music_play( SONG_DRAGON );
    for( int f = 0; f < XFADE_FRAMES; f++ ) frame_with( SONG_COUNT );
    music_stop();

    // every event effect alone, then a chain of two booms in one frame, then the UI sounds
    for( int e = 0; e < EV_COUNT; e++ )
    {
        events[ e ] = 1;
        for( int f = 0; f < EFFECT_FRAMES; f++ ) frame_with( SONG_COUNT + 1 );
    }
    events[ EV_BOOM ] = 2;
    for( int f = 0; f < EFFECT_FRAMES; f++ ) frame_with( SONG_COUNT + 1 );
    for( int u = 0; u < 3; u++ )
    {
        ui_sound( u );
        for( int f = 0; f < 40; f++ ) frame_with( SONG_COUNT + 1 );
    }

    card[ 0 ] = 1;
    card_write_data( card, 0, 64 );
    exit();
}
