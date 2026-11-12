// Music and sound effects.
//
// Music: a 12-voice tracker on channels 0..11 (voice v on channel v) playing the songs of the
// module assets/music/songs/sulphur.xm, which tools/audio/xm2vircon.py converts into per-voice
// commands at frame times (src/gen/music.h): note on, key-off, volume and the row's effect.
// One tracker tick is one frame (150 BPM). Every frame a voice follows its instrument's volume
// envelope (held at the sustain point until key-off, then fading out), runs the row's effect
// (volume slide, vibrato, portamento, note cut) and sets the channel's volume and speed; the
// speed is the pitch, since the console plays samples at any speed without interpolation.
// A song loops from its loop point; notes still sounding run on across the seam. A new song
// fades in over half a second while the voices of the old one fade out under it.
//
// Effects: channels 12..14 for the game's events (state.h events[]), 15 for the UI.
//
// tools/audio/refengine.py mirrors this code statement by statement to render reference audio:
// change both together.
#ifndef SOUND_H
#define SOUND_H

#include "audio.h"
#include "math.h"
#include "state.h"
#include "gen/music.h"
#include "gen/sfx.h"

#define SONG_NONE      -1
#define SONG_TITLE     0      // title and menu
#define SONG_BATTLE    1
#define SONG_WROCLAW   2      // chapter 1 stages
#define SONG_SLEZA     3      // chapter 2 stages
#define SONG_KRAKOW    4      // chapter 3 stages
#define SONG_BOSS      5      // utopiec and Baba Jaga
#define SONG_DRAGON    6
#define SONG_CALM      7      // story scenes: a still moment
#define SONG_TENSION   8      // story scenes: a threat
#define SONG_JOY       9      // story scenes: the feast, the ending
#define SONG_COUNT     10

// a short UI sound: menu move and confirm, and the blip of a typed letter in a scene
#define UI_MOVE        0
#define UI_CONFIRM     1
#define UI_TYPE        2

#define MUS_VOICES     12
#define SFX_FIRST      12     // channels 12..14: effects of game events
#define SFX_CHANNELS   3
#define SFX_UI         15
#define SFX_UI_FIRST   11     // the UI sounds follow the 11 event effects in the sfx group
#define MUS_NEVER      0x7FFFFFFF

// commands (xm2vircon.py)
#define CMD_NOTE       0
#define CMD_OFF        1
#define CMD_VOL        2
#define CMD_FX         3
#define FX_NONE        0
#define FX_VSLIDE      1
#define FX_VIBRATO     2
#define FX_TONE        3
#define FX_UP          4
#define FX_DOWN        5
#define FX_CUT         6

int mus_song = SONG_NONE;
int mus_time = 0;
float mus_fade = 1.0;         // fade-in of a song that replaced another
float mus_duck = 1.0;         // the music dips under big explosions
float mus_master = 0.0;

int[ MUS_VOICES ] mus_ptr;    // next command (index into mus_events / 2)
int[ MUS_VOICES ] mus_end;
int[ MUS_VOICES ] mus_next;   // frame of the next command, MUS_NEVER after the last
bool[ MUS_VOICES ] mus_on;
bool[ MUS_VOICES ] mus_released;
bool[ MUS_VOICES ] mus_old;   // still sounding a note of the song before: fading out
bool[ MUS_VOICES ] mus_shifted;
int[ MUS_VOICES ] mus_note;
int[ MUS_VOICES ] mus_vol;    // 0..64
int[ MUS_VOICES ] mus_envp;   // envelope position (index into mus_env)
int[ MUS_VOICES ] mus_envend;
int[ MUS_VOICES ] mus_envsus;
int[ MUS_VOICES ] mus_fx;
int[ MUS_VOICES ] mus_p1;
int[ MUS_VOICES ] mus_p2;
int[ MUS_VOICES ] mus_tick;
int[ MUS_VOICES ] mus_vib_pos;
float[ MUS_VOICES ] mus_base; // speed of the note
float[ MUS_VOICES ] mus_pitch;// portamento, in 1/64 semitones
float[ MUS_VOICES ] mus_vib;  // vibrato, in 1/64 semitones
float[ MUS_VOICES ] mus_kfade;// fadeout after key-off, 1..0
float[ MUS_VOICES ] mus_fadeout;
float[ MUS_VOICES ] mus_oldgain;

int[ SFX_CHANNELS ] sfx_started;
int sfx_clock = 0;
// its own generator: the game's rand() is seeded per stage and must replay the same
int sfx_seed = 12345;

// effect of each event (state.h EV_*): the sfx group lists them in the same order
int[ EV_COUNT ] sfx_of_event = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 };

void sound_init()
{
    for( int i = 0; i < MUS_SAMPLES; i++ )
      if( mus_loop_end[ i ] > 0 )
      {
          select_sound( SND_BASE_MUSIC + i );
          set_sound_loop( true );
          set_sound_loop_start( mus_loop_start[ i ] );
          set_sound_loop_end( mus_loop_end[ i ] );
      }
    for( int v = 0; v < MUS_VOICES; v++ )
    {
        mus_on[ v ] = false;
        mus_old[ v ] = false;
        mus_next[ v ] = MUS_NEVER;
    }
    for( int c = 0; c < SFX_CHANNELS; c++ ) sfx_started[ c ] = -1000;
}

// points every voice at the song's first command, or at the first one of the loop
void mus_rewind( bool from_loop )
{
    int base = mus_song * MUS_VOICES;
    for( int v = 0; v < MUS_VOICES; v++ )
    {
        int first = mus_first[ base + v ];
        mus_end[ v ] = first + mus_count[ base + v ];
        mus_ptr[ v ] = first;
        if( from_loop ) mus_ptr[ v ] = first + mus_loop_ptr[ base + v ];
        if( mus_ptr[ v ] < mus_end[ v ] ) mus_next[ v ] = mus_events[ mus_ptr[ v ] * 2 ] & 0xFFFF;
        else mus_next[ v ] = MUS_NEVER;
    }
}

// the notes sounding now fade out under whatever plays next
void mus_release_all()
{
    for( int v = 0; v < MUS_VOICES; v++ )
      if( mus_on[ v ] && !mus_old[ v ] )
      {
          mus_oldgain[ v ] = mus_master;
          mus_old[ v ] = true;
      }
}

// starts a song (looping); the same song again keeps playing; crossfades from the last one
void music_play( int song )
{
    if( song == mus_song ) return;
    bool was_playing = mus_song != SONG_NONE;
    mus_release_all();
    mus_song = song;
    mus_time = 0;
    if( was_playing ) mus_fade = 0.0;
    else mus_fade = 1.0;
    mus_rewind( false );
}

void music_stop()
{
    mus_release_all();
    mus_song = SONG_NONE;
    for( int v = 0; v < MUS_VOICES; v++ ) mus_next[ v ] = MUS_NEVER;
}

// the voice's volume before the song's: envelope, fadeout and note volume
float mus_level( int v )
{
    return mus_env[ mus_envp[ v ] ] * mus_kfade[ v ] * mus_vol[ v ] * MUS_VOL_SCALE;
}

void mus_start( int v, int w1 )
{
    int smp = w1 & 255;
    int ins = ( w1 >> 22 ) & 31;
    mus_note[ v ] = ( w1 >> 8 ) & 127;
    mus_vol[ v ] = ( w1 >> 15 ) & 127;
    mus_base[ v ] = mus_semi[ mus_note[ v ] ] * mus_sample_speed[ smp ];
    mus_pitch[ v ] = 0.0;
    mus_vib[ v ] = 0.0;
    mus_vib_pos[ v ] = 0;
    mus_shifted[ v ] = false;
    mus_envp[ v ] = mus_env_first[ ins ];
    mus_envend[ v ] = mus_env_first[ ins ] + mus_env_len[ ins ] - 1;
    mus_envsus[ v ] = mus_env_first[ ins ] + mus_env_sus[ ins ];
    if( mus_env_sus[ ins ] < 0 ) mus_envsus[ v ] = -1;
    mus_kfade[ v ] = 1.0;
    mus_fadeout[ v ] = mus_ins_fadeout[ ins ];
    mus_released[ v ] = false;
    mus_on[ v ] = true;
    mus_old[ v ] = false;
    // a sound can only be given to a stopped channel; stop_channel also selects it
    stop_channel( v );
    set_channel_speed( mus_base[ v ] );
    set_channel_volume( mus_level( v ) * mus_master );
    play_sound_in_channel( SND_BASE_MUSIC + smp, v );
}

// the row's effect on the ticks after its first
void mus_effect( int v )
{
    int fx = mus_fx[ v ];
    mus_tick[ v ]++;
    if( fx == FX_VSLIDE )
    {
        mus_vol[ v ] = clampi( mus_vol[ v ] + mus_p1[ v ] - mus_p2[ v ], 0, 64 );
    }
    else if( fx == FX_VIBRATO )
    {
        mus_vib_pos[ v ] = ( mus_vib_pos[ v ] + mus_p1[ v ] ) & 63;
        mus_vib[ v ] = mus_sine[ mus_vib_pos[ v ] ] * mus_p2[ v ] * 8.0;
    }
    else if( fx == FX_TONE )
    {
        float target = ( mus_p2[ v ] - mus_note[ v ] ) * 64.0;
        float step = mus_p1[ v ] * 4.0;
        if( mus_pitch[ v ] < target )
        {
            mus_pitch[ v ] = mus_pitch[ v ] + step;
            if( mus_pitch[ v ] > target ) mus_pitch[ v ] = target;
        }
        else
        {
            mus_pitch[ v ] = mus_pitch[ v ] - step;
            if( mus_pitch[ v ] < target ) mus_pitch[ v ] = target;
        }
    }
    else if( fx == FX_UP ) mus_pitch[ v ] = mus_pitch[ v ] + mus_p1[ v ] * 4.0;
    else if( fx == FX_DOWN ) mus_pitch[ v ] = mus_pitch[ v ] - mus_p1[ v ] * 4.0;
    else if( fx == FX_CUT )
    {
        if( mus_tick[ v ] == mus_p1[ v ] ) mus_vol[ v ] = 0;
    }
}

// advances the music by one frame
void music_update()
{
    if( mus_fade < 1.0 )
    {
        mus_fade += 0.0333333;
        if( mus_fade > 1.0 ) mus_fade = 1.0;
    }
    if( mus_duck < 1.0 )
    {
        mus_duck += 0.0125;
        if( mus_duck > 1.0 ) mus_duck = 1.0;
    }
    if( mus_song != SONG_NONE ) mus_master = mus_song_gain[ mus_song ] * mus_fade * mus_duck;

    for( int v = 0; v < MUS_VOICES; v++ )
    {
        // this frame's commands; a new note or a new row effect skips the effect tick
        int fresh = 0;
        while( mus_time == mus_next[ v ] )
        {
            int at = mus_ptr[ v ] * 2;
            int w1 = mus_events[ at + 1 ];
            int kind = ( mus_events[ at ] >> 16 ) & 3;
            if( kind == CMD_NOTE )
            {
                mus_start( v, w1 );
                fresh = 1;
            }
            else if( kind == CMD_OFF ) mus_released[ v ] = true;
            else if( kind == CMD_VOL ) mus_vol[ v ] = w1;
            else
            {
                if( mus_fx[ v ] == FX_VIBRATO ) mus_vib[ v ] = 0.0;
                mus_fx[ v ] = w1 & 15;
                mus_p1[ v ] = ( w1 >> 4 ) & 255;
                mus_p2[ v ] = ( w1 >> 12 ) & 255;
                mus_tick[ v ] = 0;
                if( fresh == 0 ) fresh = 2;
            }
            mus_ptr[ v ]++;
            if( mus_ptr[ v ] < mus_end[ v ] ) mus_next[ v ] = mus_events[ at + 2 ] & 0xFFFF;
            else mus_next[ v ] = MUS_NEVER;
        }
        if( !mus_on[ v ] || fresh == 1 ) continue;
        if( fresh == 0 && !mus_old[ v ] ) mus_effect( v );

        // the envelope: held at its sustain point until key-off, then on to its end
        if( mus_released[ v ] )
        {
            if( mus_envp[ v ] < mus_envend[ v ] ) mus_envp[ v ]++;
            mus_kfade[ v ] = mus_kfade[ v ] - mus_fadeout[ v ];
            if( mus_kfade[ v ] < 0.0 ) mus_kfade[ v ] = 0.0;
            if( ( mus_envp[ v ] == mus_envend[ v ] && mus_env[ mus_envp[ v ] ] < 0.002 ) || mus_kfade[ v ] <= 0.0 )
            {
                stop_channel( v );
                mus_on[ v ] = false;
                continue;
            }
        }
        else if( mus_envp[ v ] != mus_envsus[ v ] && mus_envp[ v ] < mus_envend[ v ] ) mus_envp[ v ]++;

        select_channel( v );
        if( mus_old[ v ] )
        {
            mus_oldgain[ v ] = mus_oldgain[ v ] * 0.92;
            if( mus_oldgain[ v ] < 0.0005 )
            {
                stop_channel( v );
                mus_on[ v ] = false;
                continue;
            }
            set_channel_volume( mus_level( v ) * mus_oldgain[ v ] * mus_duck );
        }
        else set_channel_volume( mus_level( v ) * mus_master );

        float shift = mus_pitch[ v ] + mus_vib[ v ];
        if( shift != 0.0 )
        {
            set_channel_speed( mus_base[ v ] * pow( 2.0, shift * 0.00130208333 ) );
            mus_shifted[ v ] = true;
        }
        else if( mus_shifted[ v ] )
        {
            set_channel_speed( mus_base[ v ] );
            mus_shifted[ v ] = false;
        }
    }

    if( mus_song != SONG_NONE )
    {
        mus_time++;
        if( mus_time >= mus_length[ mus_song ] )
        {
            mus_time = mus_loop[ mus_song ];
            mus_rewind( true );
        }
    }
}

// ---------------------------------------------------------------------------
//   effects
// ---------------------------------------------------------------------------

// a free effect channel, or the one whose effect started longest ago
int sfx_channel()
{
    int best = SFX_FIRST;
    int oldest = MUS_NEVER;
    for( int c = 0; c < SFX_CHANNELS; c++ )
    {
        if( get_channel_state( SFX_FIRST + c ) != channel_playing ) return SFX_FIRST + c;
        if( sfx_started[ c ] < oldest )
        {
            oldest = sfx_started[ c ];
            best = SFX_FIRST + c;
        }
    }
    return best;
}

void sfx_play( int effect, float volume, float speed, int channel )
{
    stop_channel( channel );
    set_channel_speed( speed );
    set_channel_volume( volume );
    play_sound_in_channel( SND_BASE_SFX + effect, channel );
}

// once a frame: plays the effects the game raised in events[] (state.h) and runs the music;
// an event raised several times in a frame plays at most twice (the second softer, lower)
void sound_frame()
{
    sfx_clock++;
    for( int e = 0; e < EV_COUNT; e++ )
    {
        int n = events[ e ];
        if( n <= 0 ) continue;
        int effect = sfx_of_event[ e ];
        // a slightly different pitch each time, so repeats do not sound like a machine gun
        sfx_seed = ( sfx_seed * 75 + 74 ) % 65537;
        float speed = 0.97 + ( sfx_seed & 63 ) * 0.001;
        int c = sfx_channel();
        sfx_started[ c - SFX_FIRST ] = sfx_clock;
        sfx_play( effect, sfx_level[ effect ] * SFX_GAIN, speed, c );
        if( n > 1 )
        {
            c = sfx_channel();
            sfx_started[ c - SFX_FIRST ] = sfx_clock;
            sfx_play( effect, sfx_level[ effect ] * SFX_GAIN * 0.6, speed * 0.92, c );
        }
        if( sfx_ducks[ effect ] ) mus_duck = 0.55;
    }
    music_update();
}

void ui_sound( int which )
{
    int effect = SFX_UI_FIRST + which;
    sfx_play( effect, sfx_level[ effect ] * SFX_GAIN, 1.0, SFX_UI );
}

#endif
