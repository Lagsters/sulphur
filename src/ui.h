// Screens around the arena: title and menu, the world map between stages, pause, and the
// messages at the end of a stage, a round and a match; the attract demo.
#ifndef UI_H
#define UI_H

#include "render.h"
#include "save.h"
#include "sound.h"
#include "scenes.h"

#define ST_TITLE   0
#define ST_MAP     1
#define ST_STAGE   2
#define ST_SCENE   3
#define ST_BATTLE  4

#define TITLE_IDLE     1800    // frames on the menu before the battle demo starts
#define DEMO_LENGTH    3600
#define MAP_AUTO       420
#define GOAL_BANNER    150
#define HINT_TIME      200

int state = ST_TITLE;
int state_t = 0;
bool paused = false;
int paused_at = -1;     // the frame Start opened the pause: the same press must not close it
int pause_sel = 0;
int menu_sel = 0;
int next_stage_after_scene = 0;     // 0: back to the title
int hint = -1, hint_t = 0;
bool sheep_hint_shown = false;
int immune_hint_wait = 0;

void enter( int s ) { state = s; state_t = 0; paused = false; }

void pause_game() { paused = true; pause_sel = 0; paused_at = frame; ui_sound( UI_CONFIRM ); }

bool pad_connected( int n ) { select_gamepad( n ); return gamepad_is_connected(); }

// buttons of the first gamepad as they go down this frame
bool p1_pressed_a() { select_gamepad( 0 ); return gamepad_button_a() == 1; }
bool p1_pressed_b() { select_gamepad( 0 ); return gamepad_button_b() == 1; }
bool p1_pressed_start() { select_gamepad( 0 ); return gamepad_button_start() == 1; }
bool p1_pressed_up() { select_gamepad( 0 ); return gamepad_up() == 1; }
bool p1_pressed_down() { select_gamepad( 0 ); return gamepad_down() == 1; }
bool any_button() { return p1_pressed_a() || p1_pressed_b() || p1_pressed_start(); }

// darkens the screen: a fade in at the start of a state, and behind menus
void dim( int alpha ) { if( alpha > 0 ) fill_rect( 0, 0, 640, 360, alpha << 24 ); }

void fade_in() { if( state_t < 20 ) dim( 255 - state_t * 12 ); }

void panel( int x, int y, int w, int h )
{
    fill_rect( x - 2, y - 2, w + 4, h + 4, 0xFF1A3A5A );
    fill_rect( x, y, w, h, 0xE0100804 );
    fill_rect( x, y, w, 1, 0xFF40B0E0 );
}

// ---------------------------------------------------------------------------
//   title
// ---------------------------------------------------------------------------

#define MENU_STORY      0
#define MENU_STORY2     1
#define MENU_CONTINUE   2
#define MENU_CONTINUE2  3
#define MENU_NEW        4
#define MENU_BATTLE     5
#define MENU_LANG       6

int[ 8 ] menu_items;
int menu_count = 0;

void build_menu()
{
    menu_count = 0;
    bool two = pad_connected( 1 );
    if( saved_stage > 1 )
    {
        menu_items[ menu_count ] = MENU_CONTINUE; menu_count++;
        if( two ) { menu_items[ menu_count ] = MENU_CONTINUE2; menu_count++; }
        menu_items[ menu_count ] = MENU_NEW; menu_count++;
    }
    else
    {
        menu_items[ menu_count ] = MENU_STORY; menu_count++;
        if( two ) { menu_items[ menu_count ] = MENU_STORY2; menu_count++; }
    }
    menu_items[ menu_count ] = MENU_BATTLE; menu_count++;
    menu_items[ menu_count ] = MENU_LANG; menu_count++;
    if( menu_sel >= menu_count ) menu_sel = 0;
}

int menu_label( int item )
{
    if( item == MENU_STORY ) return STR_MENU_STORY;
    if( item == MENU_STORY2 ) return STR_MENU_STORY2;
    if( item == MENU_CONTINUE ) return STR_MENU_CONTINUE;
    if( item == MENU_CONTINUE2 ) return STR_MENU_CONTINUE2;
    if( item == MENU_NEW ) return STR_MENU_NEW;
    if( item == MENU_BATTLE ) return STR_MENU_BATTLE;
    return STR_MENU_LANG;
}

void start_battle( bool as_demo );
void begin_stage_or_scene( int n, bool coop );

void title_frame()
{
    if( state_t == 1 ) { music_play( SONG_TITLE ); build_menu(); }
    story_spr( STORY_TITLE_BG, 0, 0, 0 );
    story_spr( STORY_LOGO, 0, 320, 92 );
    text_draw_centered( 320, 152, tr( STR_SUBTITLE ), 0xFF60D0F0 );
    int top = 196, row = 26;
    panel( 200, top - 10, 240, menu_count * row + 14 );
    for( int i = 0; i < menu_count; i++ )
    {
        int y = top + i * row;
        int* label = tr( menu_label( menu_items[ i ] ) );
        if( i == menu_sel )
        {
            fill_rect( 206, y - 3, 228, 24, 0x6040A0E0 );
            game_spr( GAME_BOMB, ( frame / 8 ) % 4, 222, y + 9 );
        }
        text_draw_centered( 320, y, label, pick( i == menu_sel, color_white, 0xFFA0B0B8 ) );
        if( menu_items[ i ] == MENU_CONTINUE && saved_stage > 1 )
        {
            int w = text_width( label );
            text_number( 320 + w / 2 + 10, y, saved_stage, 0xFF40D0FF );
        }
    }
    text_draw_centered( 320, 334, tr( STR_CONTROLS ), 0xFF808890 );
    fade_in();
    if( p1_pressed_up() ) { menu_sel = ( menu_sel + menu_count - 1 ) % menu_count; state_t = 30; ui_sound( UI_MOVE ); }
    if( p1_pressed_down() ) { menu_sel = ( menu_sel + 1 ) % menu_count; state_t = 30; ui_sound( UI_MOVE ); }
    if( p1_pressed_a() || p1_pressed_start() )
    {
        int item = menu_items[ menu_sel ];
        ui_sound( UI_CONFIRM );
        if( item == MENU_LANG ) { lang = 1 - lang; write_save(); return; }
        if( item == MENU_BATTLE ) { start_battle( false ); return; }
        if( item == MENU_NEW ) { saved_stage = 0; write_save(); menu_sel = 0; build_menu(); return; }
        bool coop = item == MENU_STORY2 || item == MENU_CONTINUE2;
        sheep_hint_shown = false;
        int from = pick( item == MENU_CONTINUE || item == MENU_CONTINUE2, saved_stage, 1 );
        start_campaign( coop, from );
        begin_stage_or_scene( from, coop );
        return;
    }
    if( state_t > TITLE_IDLE ) start_battle( true );
}

// ---------------------------------------------------------------------------
//   the world map between stages: the chapter's ten stages as a winding road
// ---------------------------------------------------------------------------

int map_stage = 1;

int node_x( int i ) { int col = i % 5; if( ( i / 5 ) % 2 == 1 ) col = 4 - col; return 160 + col * 80; }
int node_y( int i ) { return 176 + ( i / 5 ) * 64; }

int chapter_string( int ch ) { if( ch == 1 ) return STR_CH1; if( ch == 2 ) return STR_CH2; return STR_CH3; }

int[ 3 ] chapter_map;
int[ 3 ] chapter_song;

void show_map( int n ) { map_stage = n; enter( ST_MAP ); }

void map_frame()
{
    chapter_map[ 0 ] = STORY_MAP_1; chapter_map[ 1 ] = STORY_MAP_2; chapter_map[ 2 ] = STORY_MAP_3;
    int ch = chapter_of( map_stage );
    StageDef def;
    stage_def( map_stage, &def );
    if( state_t == 1 ) music_play( chapter_song[ ch - 1 ] );
    story_spr( chapter_map[ ch - 1 ], 0, 0, 0 );
    int first = ( ch - 1 ) * CHAPTER_LEN + 1, here = map_stage - first;
    // a dotted road between the stages; the walked part gilded
    for( int i = 0; i < CHAPTER_LEN - 1; i++ )
      for( int d = 1; d < 8; d++ )
      {
          int x = node_x( i ) + ( ( node_x( i + 1 ) - node_x( i ) ) * d ) / 8;
          int y = node_y( i ) + ( ( node_y( i + 1 ) - node_y( i ) ) * d ) / 8;
          fill_rect( x - 1, y - 1, 3, 3, pick( i < here, 0xFF40C0F0, 0xC0303030 ) );
      }
    for( int i = 0; i < CHAPTER_LEN; i++ )
    {
        StageDef s;
        stage_def( first + i, &s );
        int f = pick( i < here, 1, pick( s.boss != BOSS_NONE, 2, 0 ) );
        story_spr( STORY_MAP_NODE, f, node_x( i ), node_y( i ) );
    }
    // Dratewka walks from the last stage to this one
    int from = imax( 0, here - 1 );
    int k = imin( 60, state_t );
    int x = node_x( from ) + ( ( node_x( here ) - node_x( from ) ) * k ) / 60;
    int y = node_y( from ) + ( ( node_y( here ) - node_y( from ) ) * k ) / 60 - 6;
    int dir = pick( node_x( here ) < node_x( from ), 2, pick( node_x( here ) > node_x( from ), 3, 1 ) );
    game_spr( GAME_SHADOW, 0, x, y - 1 );
    game_spr( spr_hero[ 0 ][ dir ], pick( k < 60, ( state_t / 3 ) % 8, 0 ), x, y );
    panel( 120, 34, 400, 66 );
    text_draw_big( 320, 40, tr( chapter_string( ch ) ), color_white, 2 );
    // "STAGE 2-7: FIND THREE KEYS"
    int* label = tr( STR_STAGE );
    int* num = stage_label( map_stage );
    int* goal = tr( goal_string_for( &def ) );
    int gap = 10;
    int w = text_width( label ) + gap + text_width( num ) + 2 * gap + text_width( goal );
    int lx = 320 - w / 2;
    text_draw( lx, 74, label, 0xFF60D0F0 );
    lx += text_width( label ) + gap;
    text_draw( lx, 74, num, 0xFF60D0F0 );
    lx += text_width( num ) + 2 * gap;
    text_draw( lx, 74, goal, color_white );
    if( state_t > 60 && state_t % 40 < 28 ) text_draw_centered( 320, 326, tr( STR_PRESS_A ), color_white );
    fade_in();
    if( state_t > MAP_AUTO || ( state_t > 30 && ( p1_pressed_a() || p1_pressed_start() ) ) )
    {
        start_stage( map_stage );
        enter( ST_STAGE );
    }
}

// ---------------------------------------------------------------------------
//   the story stages
// ---------------------------------------------------------------------------

int end_timer = 0;

void stage_music()
{
    if( stage.boss == BOSS_DRAGON ) music_play( SONG_DRAGON );
    else if( stage.boss != BOSS_NONE ) music_play( SONG_BOSS );
    else music_play( chapter_song[ stage.chapter - 1 ] );
}

void show_hint( int s ) { hint = s; hint_t = HINT_TIME; }

void scene_for_chapter( int ch )
{
    if( ch == 1 ) scene_start( SCENE_WROCLAW );
    else if( ch == 2 ) scene_start( SCENE_SLEZA );
    else scene_start( SCENE_KRAKOW );
}

// a stage, or first the scene that opens its chapter; the progress is saved here
void begin_stage_or_scene( int n, bool coop )
{
    saved_stage = n;
    write_save();
    if( chapter_start( n ) )
    {
        for( int i = 0; i < 2; i++ ) { camp_bombs[ i ] = MAX_BOMBS; camp_len[ i ] = BLAST_LEN; }
        next_stage_after_scene = n;
        scene_for_chapter( chapter_of( n ) );
        enter( ST_SCENE );
        return;
    }
    show_map( n );
}

void pause_menu();

void stage_hints()
{
    // the first sheep caught before the dragon: tell what it is for
    if( events[ EV_SHEEP_GOT ] > 0 && !sheep_hint_shown )
    {
        sheep_hint_shown = true;
        show_hint( pick( dragon_alive(), STR_SHEEP_USE, STR_SHEEP_GOT ) );
    }
    if( immune_hint_wait > 0 ) immune_hint_wait--;
    if( dragon_alive() && immune_hint_wait == 0 )
      for( int i = 0; i < blast_count; i++ )
        if( !blasts[ i ].sheep && blasts[ i ].owner >= 0 && boss_covers( blasts[ i ].c, blasts[ i ].r ) )
        {
            show_hint( STR_DRAGON_IMMUNE );
            immune_hint_wait = 900;
            break;
        }
    if( state_t == GOAL_BANNER && stage.boss == BOSS_DRAGON ) show_hint( STR_SHEEP_USE );
}

void stage_frame()
{
    if( state_t == 1 ) { theme = stage.chapter - 1; stage_music(); hint = -1; immune_hint_wait = 0; end_timer = 0; }
    if( !paused && camp_state == CAMP_PLAY )
    {
        update_campaign();
        stage_hints();
        if( p1_pressed_start() ) pause_game();
    }
    else if( !paused )
    {
        // the stage is over: keep the fire burning out under the message
        update_bombs(); update_blasts(); update_invul_and_deaths();
    }
    draw_world();
    draw_campaign_hud();
    if( state_t < GOAL_BANNER && camp_state == CAMP_PLAY )
    {
        panel( 150, 140, 340, 44 );
        text_draw_centered( 320, 152, tr( goal_string() ), color_white );
    }
    if( hint >= 0 && hint_t > 0 && camp_state == CAMP_PLAY )
    {
        if( !paused ) hint_t--;
        int w = text_width( tr( hint ) );
        panel( 320 - w / 2 - 12, 316, w + 24, 32 );
        text_draw_centered( 320, 322, tr( hint ), 0xFF60E0FF );
    }
    if( paused ) { pause_menu(); return; }
    if( camp_state == CAMP_PLAY ) { fade_in(); return; }
    end_timer++;
    int msg = pick( camp_state == CAMP_CLEAR, STR_STAGE_CLEAR, pick( camp_state == CAMP_LOST, STR_OUCH, STR_GAME_OVER ) );
    int wave = 0;
    if( camp_state == CAMP_CLEAR ) wave = ( ( end_timer / 4 ) % 7 ) - 3;
    text_draw_big( 320, 140 + iabs( wave ), tr( msg ), pick( camp_state == CAMP_CLEAR, 0xFF40E0FF, 0xFF6060FF ), 3 );
    if( camp_state == CAMP_LOST )
    {
        int* s = tr( STR_LIVES_LEFT );
        int w = text_width( s );
        text_draw( 320 - w / 2 - 8, 200, s, color_white );
        text_number( 320 + w / 2 + 2, 200, camp_lives, 0xFF40E0FF );
    }
    if( end_timer < 150 && !( end_timer > 50 && any_button() ) ) return;
    if( camp_state == CAMP_CLEAR )
    {
        camp_tries = 0;
        if( camp_stage == STAGE_COUNT )
        {
            saved_stage = 0; write_save();
            next_stage_after_scene = 0;
            scene_start( SCENE_ENDING );
            enter( ST_SCENE );
            return;
        }
        begin_stage_or_scene( camp_stage + 1, camp_coop );
    }
    else if( camp_state == CAMP_LOST ) { camp_tries++; start_stage( camp_stage ); enter( ST_STAGE ); }
    else enter( ST_TITLE );
}

// ---------------------------------------------------------------------------
//   pause
// ---------------------------------------------------------------------------

void pause_menu()
{
    dim( 150 );
    bool fresh = frame == paused_at;
    panel( 220, 130, 200, 100 );
    text_draw_big( 320, 140, tr( STR_PAUSE ), color_white, 2 );
    text_draw_centered( 320, 180, tr( STR_RESUME ), pick( pause_sel == 0, color_white, 0xFF8090A0 ) );
    text_draw_centered( 320, 204, tr( STR_QUIT ), pick( pause_sel == 1, color_white, 0xFF8090A0 ) );
    if( fresh ) return;
    if( p1_pressed_up() || p1_pressed_down() ) { pause_sel = 1 - pause_sel; ui_sound( UI_MOVE ); }
    if( p1_pressed_start() || p1_pressed_b() ) { paused = false; return; }
    if( p1_pressed_a() )
    {
        ui_sound( UI_CONFIRM );
        if( pause_sel == 0 ) paused = false;
        else enter( ST_TITLE );
    }
}

// ---------------------------------------------------------------------------
//   battle: rounds until someone wins three; the demo plays it with four bots
// ---------------------------------------------------------------------------

#define ROUND_OVER_TIME 210
int round_over = 0;
bool match_over = false;

void start_battle( bool as_demo )
{
    demo = as_demo;
    for( int i = 0; i < MAX_PLAYERS; i++ ) human_slot[ i ] = false;
    if( !demo ) { human_slot[ 0 ] = true; human_slot[ 1 ] = pad_connected( 1 ); }
    srand( get_time() + get_frame_counter() + 1 );
    start_match();
    round_over = 0; match_over = false;
    theme = THEME_TOWN;
    enter( ST_BATTLE );
}

void battle_frame()
{
    if( state_t == 1 ) music_play( SONG_BATTLE );
    if( demo && ( any_button() || state_t > DEMO_LENGTH ) ) { enter( ST_TITLE ); return; }
    if( !paused && round_over == 0 )
    {
        if( update_battle() ) round_over = ROUND_OVER_TIME;
        if( !demo && p1_pressed_start() ) pause_game();
    }
    else if( !paused )
    {
        update_bombs(); update_blasts(); update_invul_and_deaths();
    }
    draw_world();
    draw_battle_hud();
    if( demo && state_t % 60 < 40 ) text_draw_big( 320, 160, tr( STR_DEMO ), color_white, 2 );
    if( paused ) { pause_menu(); return; }
    fade_in();
    if( round_over == 0 ) return;
    round_over--;
    int w = match_winner();
    if( round_winner >= 0 )
    {
        int[ 4 ] who = { 80, 49 + round_winner, 32, 0 };    // "P1 "
        int* s = tr( pick( w >= 0, STR_WINS_MATCH, STR_WINS ) );
        int width = text_width( who ) + text_width( s );
        panel( 320 - width / 2 - 20, 134, width + 40, 70 );
        text_draw( 320 - width / 2, 146, who, color_white );
        text_draw( 320 - width / 2 + text_width( who ), 146, s, color_white );
        text_draw_centered( 320, 174, tr( pick( players[ round_winner ].human, STR_PLAYER, STR_BOT ) ), 0xFF80C0E0 );
    }
    else
    {
        panel( 240, 134, 160, 50 );
        text_draw_big( 320, 144, tr( STR_DRAW ), color_white, 2 );
    }
    if( round_over > 0 ) return;
    if( w >= 0 ) start_match(); else start_battle_round();
}

// ---------------------------------------------------------------------------
//   scenes
// ---------------------------------------------------------------------------

void scene_state_frame()
{
    if( !scene_frame() ) return;
    if( next_stage_after_scene > 0 ) show_map( next_stage_after_scene );
    else enter( ST_TITLE );
}

void ui_init()
{
    chapter_song[ 0 ] = SONG_WROCLAW; chapter_song[ 1 ] = SONG_SLEZA; chapter_song[ 2 ] = SONG_KRAKOW;
}

void ui_frame()
{
    // the clocks of banners and hints stop while the game is paused
    if( !paused ) state_t++;
    if( state == ST_TITLE ) title_frame();
    else if( state == ST_MAP ) map_frame();
    else if( state == ST_STAGE ) stage_frame();
    else if( state == ST_SCENE ) scene_state_frame();
    else battle_frame();
}

#endif
