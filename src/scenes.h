// Story scenes: short films between the chapters (docs/STORY.md). The shots, actors and lines
// are tables in gen/scene_text.h (tools/scenes/script.py); the art is the scenes group
// (tools/scenes/make.py). A shot is a backdrop with a slow pan, actors moving along lines, arcs
// or circles, a caption typed in the top bar and lines typed in the bottom bar, cut with a fade.
// Pad: A finishes the line being typed or goes on; Start ends the scene.
#ifndef SCENES_H
#define SCENES_H

#include "state.h"
#include "text.h"
#include "sound.h"
#include "gen/core.h"
#include "gen/scenes.h"

#define SCENE_WROCLAW  0      // before chapter 1
#define SCENE_SLEZA    1      // before chapter 2
#define SCENE_KRAKOW   2      // before chapter 3
#define SCENE_ENDING   3      // after the dragon

#include "gen/scene_text.h"

// actor modes and flags (tools/scenes/script.py)
#define ACT_STILL      0
#define ACT_WALK       1
#define ACT_LOOP       2
#define ACT_ONCE       3
#define ACT_BUST       4
#define ACT_FLIP       1
#define ACT_ADD        2
#define ACT_SCREEN     4
#define ACT_ORBIT      8

#define SCENE_FADE     15     // frames of a fade in or out
#define SCENE_TYPE     2      // frames a letter of a line
#define SCENE_CAP_TYPE 3      // frames a letter of a caption
#define SCENE_READ     100    // frames to read a typed line, plus one a letter
#define SCENE_TOP      40     // the backdrop between the bars
#define SCENE_BOTTOM   320
#define SCENE_MAX_LINES 8

bool scene_ready = false;
int scene_shot, scene_end_shot, scene_t;
int scene_line, scene_line_t;
int scene_leave;              // frames left of the fade out; 0 while the shot plays
bool scene_quit;
int[ SCENE_MAX_LINES ] scene_line_start;
// the line on screen: its speaker, and whether its letters are still coming
int scene_speaker;
bool scene_typing;
int scene_ax, scene_ay;       // where scene_actor_at put the actor

int* scene_str( int id ) { return &scene_chars[ scene_str_at[ 2 * id + lang ] ]; }

int scene_len( int* s )
{
    int n = 0;
    while( s[ n ] ) n++;
    return n;
}

void scene_rect( int x, int y, int w, int h, int color )
{
    select_texture( core_tex[ CORE_WHITE ] );
    select_region( core_reg[ CORE_WHITE ] );
    set_multiply_color( color );
    set_drawing_scale( w / 16.0, h / 16.0 );
    draw_region_zoomed_at( x, y );
    set_multiply_color( color_white );
}

void scene_begin_shot( int s )
{
    scene_shot = s;
    scene_t = 0;
    scene_line = 0;
    scene_line_t = 0;
    scene_leave = 0;
    for( int i = 0; i < SCENE_MAX_LINES; i++ ) scene_line_start[ i ] = -1;
    if( shot_song[ s ] >= 0 ) music_play( shot_song[ s ] );
}

void scene_start( int id )
{
    if( !scene_ready )
    {
        define_scenes_regions();
        scene_ready = true;
    }
    scene_end_shot = scene_first[ id + 1 ];
    scene_quit = false;
    scene_begin_shot( scene_first[ id ] );
}

// the actor's own clock: frames from the shot's start, or from the start of its line; -1 while
// that line has not come yet
int scene_actor_time( int a )
{
    int l = actor_on_line[ a ];
    if( l < 0 ) return scene_t;
    if( scene_line_start[ l ] < 0 ) return -1;
    return scene_t - scene_line_start[ l ];
}

// progress through the actor's move in thousandths
int scene_actor_k( int a, int t )
{
    int t0 = actor_t0[ a ], t1 = actor_t1[ a ];
    if( t1 <= t0 ) return 1000;
    return clampi( ( t - t0 ) * 1000 / ( t1 - t0 ), 0, 1000 );
}

// position at time t into scene_ax, scene_ay; true when it faces left
bool scene_actor_at( int a, int t )
{
    bool left = ( actor_flags[ a ] & ACT_FLIP ) != 0;
    if( ( actor_flags[ a ] & ACT_ORBIT ) != 0 )
    {
        // x1, y1: radii; t1: frames a turn; t0: phase in degrees
        float angle = ( ( t * 360 ) / actor_t1[ a ] + actor_t0[ a ] ) * 0.0174533;
        float s = sin( angle );
        scene_ax = actor_x0[ a ] + (int)( actor_x1[ a ] * cos( angle ) );
        scene_ay = actor_y0[ a ] + (int)( actor_y1[ a ] * s );
        return s > 0;
    }
    int k = scene_actor_k( a, t );
    scene_ax = actor_x0[ a ] + ( actor_x1[ a ] - actor_x0[ a ] ) * k / 1000;
    scene_ay = actor_y0[ a ] + ( actor_y1[ a ] - actor_y0[ a ] ) * k / 1000;
    // an arc: a parabola `arc` pixels high at the middle of the move
    scene_ay -= actor_arc[ a ] * 4 * k / 1000 * ( 1000 - k ) / 1000;
    return left;
}

int scene_lerp_color( int c0, int c1, int k )
{
    if( c0 == c1 ) return c0;
    int r = get_color_red( c0 ) + ( get_color_red( c1 ) - get_color_red( c0 ) ) * k / 1000;
    int g = get_color_green( c0 ) + ( get_color_green( c1 ) - get_color_green( c0 ) ) * k / 1000;
    int b = get_color_blue( c0 ) + ( get_color_blue( c1 ) - get_color_blue( c0 ) ) * k / 1000;
    return make_color_rgba( r, g, b, get_color_alpha( c0 ) );
}

int scene_actor_frame( int a, int t, bool moving, int x )
{
    int mode = actor_mode[ a ];
    int f0 = actor_f0[ a ];
    if( mode == ACT_WALK )
    {
        if( !moving ) return actor_idle[ a ];
        // eight frames a gait cycle, picked by the ground covered, so the feet do not slide
        return f0 + ( iabs( x - actor_x0[ a ] ) * 8 / actor_stride[ a ] ) % 8;
    }
    if( mode == ACT_LOOP ) return f0 + ( ( t - actor_show[ a ] ) / actor_rate[ a ] ) % actor_n[ a ];
    if( mode == ACT_ONCE ) return f0 + imin( actor_n[ a ] - 1, ( t - actor_show[ a ] ) / actor_rate[ a ] );
    if( mode == ACT_BUST )
    {
        if( scene_typing && scene_speaker == actor_talker[ a ] && ( scene_t / 5 ) % 2 == 0 ) return f0 + 1;
        if( ( scene_t + a * 37 ) % 170 < 7 ) return f0 + 2;
    }
    return f0;
}

void scene_draw_actor( int a, int cam, int dy )
{
    int t = scene_actor_time( a );
    if( t < 0 || t < actor_show[ a ] ) return;
    if( actor_hide[ a ] >= 0 && t >= actor_hide[ a ] ) return;
    bool left = scene_actor_at( a, t );
    int x = scene_ax, y = scene_ay;
    int target = actor_attach[ a ];
    if( target >= 0 )
    {
        left = scene_actor_at( target, scene_actor_time( target ) );
        x = scene_ax + actor_x0[ a ];
        y = scene_ay + actor_y0[ a ];
    }
    int k = scene_actor_k( a, t );
    bool moving = k > 0 && k < 1000 && actor_x1[ a ] != actor_x0[ a ] && target < 0;
    int spr = actor_spr[ a ];
    select_texture( scenes_tex[ spr ] );
    select_region( scenes_reg[ spr ] + scene_actor_frame( a, t, moving, x ) );
    set_multiply_color( scene_lerp_color( actor_c0[ a ], actor_c1[ a ], k ) );
    if( ( actor_flags[ a ] & ACT_SCREEN ) != 0 ) cam = 0;
    if( actor_mode[ a ] == ACT_BUST ) y += imax( 0, 14 - t ) * 4;     // rises into the close-up
    if( ( actor_flags[ a ] & ACT_ADD ) != 0 ) set_blending_mode( blending_add );
    int scale = actor_s0[ a ] + ( actor_s1[ a ] - actor_s0[ a ] ) * k / 1000;
    if( left || scale != 100 )
    {
        float s = scale / 100.0;
        if( left ) set_drawing_scale( -s, s );
        else set_drawing_scale( s, s );
        draw_region_zoomed_at( x - cam, y + dy );
    }
    else draw_region_at( x - cam, y + dy );
    set_blending_mode( blending_alpha );
    set_multiply_color( color_white );
}

void scene_draw_card()
{
    int gold = 0xFF40A0D8, dark = 0xFF205070;
    scene_rect( 110, 66, 420, 4, gold );
    scene_rect( 110, 290, 420, 4, gold );
    scene_rect( 110, 66, 4, 228, gold );
    scene_rect( 526, 66, 4, 228, gold );
    scene_rect( 118, 74, 404, 1, dark );
    scene_rect( 118, 285, 404, 1, dark );
    scene_rect( 118, 74, 1, 212, dark );
    scene_rect( 521, 74, 1, 212, dark );
}

// A or Start on any pad: true on the frame it goes down
bool scene_pressed( bool start )
{
    bool hit = false;
    for( int p = 0; p < 4; p++ )
    {
        select_gamepad( p );
        if( !gamepad_is_connected() ) continue;
        if( start && gamepad_button_start() == 1 ) hit = true;
        if( !start && gamepad_button_a() == 1 ) hit = true;
    }
    return hit;
}

// the line being said: types it, reads the pad, moves to the next; true when the shot is done
bool scene_update_lines( bool a )
{
    int s = scene_shot;
    int count = shot_lines[ s ];
    scene_typing = false;
    scene_speaker = -1;
    if( count == 0 ) return scene_t >= shot_len[ s ] || ( a && scene_t > 20 );
    if( scene_line >= count ) return true;
    if( scene_t < shot_lines_at[ s ] )
    {
        if( a ) scene_t = shot_lines_at[ s ];
        return false;
    }
    if( scene_line_start[ scene_line ] < 0 ) scene_line_start[ scene_line ] = scene_t;
    int li = shot_line0[ s ] + scene_line;
    int* text = scene_str( line_text[ li ] );
    int len = scene_len( text );
    int shown = scene_line_t / SCENE_TYPE;
    scene_speaker = line_who[ li ];
    scene_typing = shown < len;
    if( scene_typing && scene_line_t % ( 2 * SCENE_TYPE ) == 0 && text[ shown ] != ' ' ) ui_sound( UI_TYPE );
    scene_line_t++;
    bool next = scene_line_t > len * SCENE_TYPE + SCENE_READ + len;
    if( a )
    {
        if( scene_typing ) scene_line_t = len * SCENE_TYPE;
        else next = true;
    }
    if( next )
    {
        scene_line++;
        scene_line_t = 0;
        return scene_line >= count;
    }
    return false;
}

void scene_draw_texts()
{
    int s = scene_shot;
    int ty = ( SCENE_TOP - TEXT_H_PX ) / 2;
    if( shot_cap[ s ] >= 0 && scene_t >= 10 )
    {
        int* cap = scene_str( shot_cap[ s ] );
        text_draw_n( 320 - text_width( cap ) / 2, ty, cap, ( scene_t - 10 ) / SCENE_CAP_TYPE, 0xFFB0E0F0 );
    }
    for( int i = shot_label0[ s ]; i < shot_label0[ s ] + shot_labels[ s ]; i++ )
    {
        if( scene_t < label_t[ i ] ) continue;
        int* text = scene_str( label_text[ i ] );
        if( label_big[ i ] ) text_draw_big( label_x[ i ], label_y[ i ], text, label_color[ i ], 2 );
        else text_draw_centered( label_x[ i ], label_y[ i ], text, label_color[ i ] );
    }
    if( scene_speaker < 0 || scene_leave > 0 ) return;
    int li = shot_line0[ s ] + scene_line;
    int* name = scene_str( speaker_name[ scene_speaker ] );
    int y = SCENE_BOTTOM + ty;
    text_draw( 16, y, name, speaker_color[ scene_speaker ] );
    text_draw_n( 16 + text_width( name ) + 12, y, scene_str( line_text[ li ] ), scene_line_t / SCENE_TYPE, color_white );
}

// draws one frame of the playing scene and reads the pad; true once it has ended
bool scene_frame()
{
    int s = scene_shot;
    bool a = scene_pressed( false );
    if( scene_pressed( true ) && !scene_quit )
    {
        scene_quit = true;
        scene_leave = SCENE_FADE;
    }
    if( scene_leave == 0 && scene_update_lines( a ) ) scene_leave = SCENE_FADE;
    int len = imax( 1, shot_len[ s ] );
    int cam = shot_pan0[ s ] + ( shot_pan1[ s ] - shot_pan0[ s ] ) * imin( scene_t, len ) / len;
    int dy = 0;
    int shake = shot_shake[ s ];
    if( shake >= 0 && scene_t >= shake && scene_t < shake + 40 )
        dy = pick( scene_t % 4 < 2, 1, -1 ) * ( 40 - ( scene_t - shake ) ) / 8;

    clear_screen( color_black );
    int bd = shot_bd[ s ];
    if( bd >= 0 )
    {
        set_multiply_color( shot_dim[ s ] );
        select_texture( scenes_tex[ bd ] );
        select_region( scenes_reg[ bd ] );
        draw_region_at( -cam, SCENE_TOP + dy );
        select_texture( scenes_tex[ bd + 1 ] );
        select_region( scenes_reg[ bd + 1 ] );
        draw_region_at( 340 - cam, SCENE_TOP + dy );
        set_multiply_color( color_white );
    }
    if( shot_card[ s ] ) scene_draw_card();
    for( int i = shot_actor0[ s ]; i < shot_actor0[ s ] + shot_actors[ s ]; i++ ) scene_draw_actor( i, cam, dy );
    int flash = shot_flash[ s ];
    if( flash >= 0 && scene_t >= flash && scene_t < flash + 12 )
        scene_rect( 0, 0, 640, 360, make_color_rgba( 255, 255, 230, ( 12 - ( scene_t - flash ) ) * 20 ) );
    scene_rect( 0, 0, 640, SCENE_TOP, color_black );
    scene_rect( 0, SCENE_BOTTOM, 640, 360 - SCENE_BOTTOM, color_black );
    scene_draw_texts();

    int fade = 0;
    if( scene_t < SCENE_FADE ) fade = ( SCENE_FADE - scene_t ) * 255 / SCENE_FADE;
    if( scene_leave > 0 ) fade = ( SCENE_FADE - scene_leave ) * 255 / SCENE_FADE;
    if( fade > 0 ) scene_rect( 0, 0, 640, 360, make_color_rgba( 0, 0, 0, fade ) );

    scene_t++;
    if( scene_leave > 0 )
    {
        scene_leave--;
        if( scene_leave == 0 )
        {
            if( scene_quit || scene_shot + 1 >= scene_end_shot ) return true;
            scene_begin_shot( scene_shot + 1 );
        }
    }
    return false;
}

#endif
