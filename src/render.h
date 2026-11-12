// Drawing the arena and the HUD with the game and story art (tools/catalog.py). Logic units map
// to screen pixels at 20/16; the 32x18 battle grid fills the 640x360 screen exactly, its top wall
// row under the HUD.
#ifndef RENDER_H
#define RENDER_H

#include "campaign.h"
#include "gen/core.h"
#include "gen/game.h"
#include "gen/story.h"
#include "gen/strings.h"
#include "text.h"

#define HUD_H          20
#define THEME_TOWN     0
#define THEME_FOREST   1
#define THEME_CASTLE   2

int theme = THEME_TOWN;

int sx( int x ) { return TILE_PX + ( ( x - cam_x ) * TILE_PX ) / TILE; }
int sy( int y ) { return ( ( y - cam_y ) * TILE_PX ) / TILE; }

// ---------------------------------------------------------------------------
//   sprites: one texture selected at a time, regions drawn without scaling
// ---------------------------------------------------------------------------

void use_texture( int t ) { select_texture( t ); }

void game_spr( int id, int f, int x, int y )
{
    use_texture( game_tex[ id ] );
    select_region( game_reg[ id ] + f );
    draw_region_at( x, y );
}

void story_spr( int id, int f, int x, int y )
{
    use_texture( story_tex[ id ] );
    select_region( story_reg[ id ] + f );
    draw_region_at( x, y );
}

void fill_rect( int x, int y, int w, int h, int color )
{
    use_texture( core_tex[ CORE_WHITE ] );
    select_region( core_reg[ CORE_WHITE ] );
    set_multiply_color( color );
    set_drawing_scale( w / 16.0, h / 16.0 );
    draw_region_zoomed_at( x, y );
    set_multiply_color( color_white );
}

// the sprites by theme, look and direction, named once so a missing one fails the build
int[ 3 ] spr_floor, spr_pillar, spr_wall, spr_crate;
int[ 7 ][ 4 ] spr_hero;
int[ 7 ] spr_hero_die, spr_head;
int[ 4 ] spr_dwarf, spr_sheep;
int[ 6 ] spr_item;

void init_sprites()
{
    define_core_regions();
    define_game_regions();
    define_story_regions();
    spr_floor[ 0 ] = GAME_FLOOR_TOWN;   spr_floor[ 1 ] = GAME_FLOOR_FOREST;   spr_floor[ 2 ] = GAME_FLOOR_CASTLE;
    spr_pillar[ 0 ] = GAME_PILLAR_TOWN; spr_pillar[ 1 ] = GAME_PILLAR_FOREST; spr_pillar[ 2 ] = GAME_PILLAR_CASTLE;
    spr_wall[ 0 ] = GAME_WALL_TOWN;     spr_wall[ 1 ] = GAME_WALL_FOREST;     spr_wall[ 2 ] = GAME_WALL_CASTLE;
    spr_crate[ 0 ] = GAME_CRATE_TOWN;   spr_crate[ 1 ] = GAME_CRATE_FOREST;   spr_crate[ 2 ] = GAME_CRATE_CASTLE;
    spr_hero[ 0 ][ 0 ] = GAME_HERO_DRATEWKA_DOWN; spr_hero[ 0 ][ 1 ] = GAME_HERO_DRATEWKA_UP; spr_hero[ 0 ][ 2 ] = GAME_HERO_DRATEWKA_LEFT; spr_hero[ 0 ][ 3 ] = GAME_HERO_DRATEWKA_RIGHT;
    spr_hero[ 1 ][ 0 ] = GAME_HERO_WANDA_DOWN;    spr_hero[ 1 ][ 1 ] = GAME_HERO_WANDA_UP;    spr_hero[ 1 ][ 2 ] = GAME_HERO_WANDA_LEFT;    spr_hero[ 1 ][ 3 ] = GAME_HERO_WANDA_RIGHT;
    spr_hero[ 2 ][ 0 ] = GAME_HERO_WHITE_DOWN;    spr_hero[ 2 ][ 1 ] = GAME_HERO_WHITE_UP;    spr_hero[ 2 ][ 2 ] = GAME_HERO_WHITE_LEFT;    spr_hero[ 2 ][ 3 ] = GAME_HERO_WHITE_RIGHT;
    spr_hero[ 3 ][ 0 ] = GAME_HERO_GREEN_DOWN;    spr_hero[ 3 ][ 1 ] = GAME_HERO_GREEN_UP;    spr_hero[ 3 ][ 2 ] = GAME_HERO_GREEN_LEFT;    spr_hero[ 3 ][ 3 ] = GAME_HERO_GREEN_RIGHT;
    spr_hero[ 4 ][ 0 ] = GAME_HERO_BLUE_DOWN;     spr_hero[ 4 ][ 1 ] = GAME_HERO_BLUE_UP;     spr_hero[ 4 ][ 2 ] = GAME_HERO_BLUE_LEFT;     spr_hero[ 4 ][ 3 ] = GAME_HERO_BLUE_RIGHT;
    spr_hero[ 5 ][ 0 ] = GAME_HERO_RED_DOWN;      spr_hero[ 5 ][ 1 ] = GAME_HERO_RED_UP;      spr_hero[ 5 ][ 2 ] = GAME_HERO_RED_LEFT;      spr_hero[ 5 ][ 3 ] = GAME_HERO_RED_RIGHT;
    spr_hero[ 6 ][ 0 ] = GAME_HERO_SKELETON_DOWN; spr_hero[ 6 ][ 1 ] = GAME_HERO_SKELETON_UP; spr_hero[ 6 ][ 2 ] = GAME_HERO_SKELETON_LEFT; spr_hero[ 6 ][ 3 ] = GAME_HERO_SKELETON_RIGHT;
    spr_hero_die[ 0 ] = GAME_HERO_DRATEWKA_DIE; spr_hero_die[ 1 ] = GAME_HERO_WANDA_DIE; spr_hero_die[ 2 ] = GAME_HERO_WHITE_DIE;
    spr_hero_die[ 3 ] = GAME_HERO_GREEN_DIE; spr_hero_die[ 4 ] = GAME_HERO_BLUE_DIE; spr_hero_die[ 5 ] = GAME_HERO_RED_DIE; spr_hero_die[ 6 ] = GAME_HERO_SKELETON_DIE;
    spr_head[ 0 ] = GAME_ICON_HEAD_DRATEWKA; spr_head[ 1 ] = GAME_ICON_HEAD_WANDA; spr_head[ 2 ] = GAME_ICON_HEAD_WHITE;
    spr_head[ 3 ] = GAME_ICON_HEAD_GREEN; spr_head[ 4 ] = GAME_ICON_HEAD_BLUE; spr_head[ 5 ] = GAME_ICON_HEAD_RED; spr_head[ 6 ] = GAME_ICON_HEAD_SKELETON;
    spr_dwarf[ 0 ] = GAME_DWARF_DOWN; spr_dwarf[ 1 ] = GAME_DWARF_UP; spr_dwarf[ 2 ] = GAME_DWARF_LEFT; spr_dwarf[ 3 ] = GAME_DWARF_RIGHT;
    spr_sheep[ 0 ] = GAME_SHEEP_DOWN; spr_sheep[ 1 ] = GAME_SHEEP_UP; spr_sheep[ 2 ] = GAME_SHEEP_LEFT; spr_sheep[ 3 ] = GAME_SHEEP_RIGHT;
    spr_item[ ITEM_BOMB ] = GAME_ITEM_BOMB; spr_item[ ITEM_RANGE ] = GAME_ITEM_RANGE; spr_item[ ITEM_SHIELD ] = GAME_ITEM_SHIELD;
    spr_item[ ITEM_KEY ] = GAME_ITEM_KEY; spr_item[ ITEM_EXIT ] = GAME_ITEM_EXIT;
}

// 0 down, 1 up, 2 left, 3 right
int dir_index( int dx, int dy )
{
    if( dy < 0 ) return 1;
    if( dx < 0 ) return 2;
    if( dx > 0 ) return 3;
    return 0;
}

// ---------------------------------------------------------------------------
//   the arena
// ---------------------------------------------------------------------------

bool outer_wall( int c, int r ) { return r == 0 || c == 0 || r == H - 1 || c == W - 1; }

void draw_map()
{
    int c0 = imax( 0, cam_x / TILE ), r0 = imax( 0, cam_y / TILE );
    int c1 = imin( W - 1, c0 + 32 ), r1 = imin( H - 1, r0 + 18 );
    int floor = spr_floor[ theme ], pillar = spr_pillar[ theme ], wall = spr_wall[ theme ], crate = spr_crate[ theme ];
    for( int r = r0; r <= r1; r++ )
    {
        int y = sy( gpy( r ) );
        for( int c = c0; c <= c1; c++ )
        {
            int x = sx( gpx( c ) );
            int t = map[ cell( c, r ) ];
            if( t == T_WALL )
            {
                if( outer_wall( c, r ) ) game_spr( wall, 0, x, y );
                else if( is_pillar( c, r ) ) game_spr( pillar, 0, x, y );
                else game_spr( GAME_ZONE, 0, x, y );
                continue;
            }
            game_spr( floor, ( c * 7 + r * 13 + ( c * r ) % 5 ) % 4, x, y );
            if( t == T_BLOCK ) game_spr( crate, 0, x, y );
        }
    }
    // the next closing step blinks, faster as it nears
    int left = shrink_closing();
    if( left >= 0 )
    {
        int period = 24 - ( 20 * ( SHRINK_WARN - left ) ) / SHRINK_WARN;
        if( round_frames % period < period / 2 )
          for( int i = 0; i < step_count; i++ ) game_spr( GAME_ZONE_WARN, 0, sx( gpx( step_c[ i ] ) ), sy( gpy( step_r[ i ] ) ) );
    }
    // crates hiding a quest item sparkle now and then, so the search is no lottery
    if( camp_mode && frame % 50 < 12 )
      for( int r = r0; r <= r1; r++ )
        for( int c = c0; c <= c1; c++ )
          if( hidden[ cell( c, r ) ] != ITEM_NONE && map[ cell( c, r ) ] == T_BLOCK )
            game_spr( GAME_SPARKLE, ( frame % 50 ) / 3 % 4, sx( gpx( c ) ) + 14, sy( gpy( r ) ) + 5 );
}

void draw_items()
{
    int bob = ( frame / 12 ) % 2;
    for( int i = 0; i < item_count; i++ )
    {
        Item* it = &items[ i ];
        int x = sx( gpx( it->c ) ), y = sy( gpy( it->r ) );
        if( it->kind == ITEM_EXIT ) game_spr( GAME_ITEM_EXIT, ( frame / 20 ) % 2, x, y );
        else game_spr( spr_item[ it->kind ], 0, x, y - bob );
    }
}

void draw_bombs()
{
    for( int i = 0; i < bomb_count; i++ )
    {
        Bomb* b = &bombs[ i ];
        int x = sx( gpx( b->c ) ) + TILE_PX / 2, y = sy( gpy( b->r ) ) + TILE_PX / 2;
        // it beats faster as it burns down
        int speed = pick( b->t < 40, 3, 8 );
        if( b->t < 40 && frame % 6 < 3 ) set_multiply_color( 0xFFC0E0FF );
        game_spr( GAME_BOMB, ( frame / speed ) % 4, x, y );
        set_multiply_color( color_white );
        game_spr( GAME_SPARK, ( frame / 2 ) % 4, x + 4, y - 9 );
    }
}

void draw_blasts()
{
    set_blending_mode( blending_add );
    for( int i = 0; i < blast_count; i++ )
    {
        Blast* b = &blasts[ i ];
        int f = ( ( BLAST_TIME - b->t ) * 8 ) / BLAST_TIME;
        int x = sx( gpx( b->c ) ) + TILE_PX / 2, y = sy( gpy( b->r ) ) + TILE_PX / 2;
        game_spr( pick( b->sheep, GAME_FIRE_SHEEP, GAME_FIRE ), imin( 7, f ), x, y );
    }
    set_blending_mode( blending_alpha );
}

// ---------------------------------------------------------------------------
//   figures, sorted by the row of their feet so nearer ones stand in front
// ---------------------------------------------------------------------------

#define FIG_PLAYER  0
#define FIG_MONSTER 1
#define FIG_SHEEP   2
#define FIG_BOSS    3
#define MAX_FIGS    32

int[ MAX_FIGS ] fig_kind, fig_index, fig_y;
int fig_count = 0;
int[ MAX_PLAYERS ] last_walk;

void add_fig( int kind, int index, int y )
{
    if( fig_count >= MAX_FIGS ) return;
    int i = fig_count;
    while( i > 0 && fig_y[ i - 1 ] > y )
    {
        fig_kind[ i ] = fig_kind[ i - 1 ]; fig_index[ i ] = fig_index[ i - 1 ]; fig_y[ i ] = fig_y[ i - 1 ];
        i--;
    }
    fig_kind[ i ] = kind; fig_index[ i ] = index; fig_y[ i ] = y;
    fig_count++;
}

void draw_shadow( int x, int y ) { game_spr( GAME_SHADOW, 0, x, y ); }

void draw_player( Player* p )
{
    int x = sx( p->x ) + TILE_PX / 2, y = sy( p->y ) + TILE_PX - 2;
    if( !p->alive )
    {
        int f = ( ( DEATH_TIME - p->death_t ) * 6 ) / DEATH_TIME;
        game_spr( spr_hero_die[ p->look ], imin( 5, f ), x, y );
        return;
    }
    if( p->invul > 0 && frame % 8 < 4 ) return;
    bool walking = p->walk_anim != last_walk[ p->id ];
    last_walk[ p->id ] = p->walk_anim;
    int f = pick( walking, ( p->walk_anim / 3 ) % 8, 0 );
    draw_shadow( x, y - 1 );
    game_spr( spr_hero[ p->look ][ dir_index( p->dir_x, p->dir_y ) ], f, x, y );
    if( p->shield )
    {
        // sparks of sulphur light circle a shielded player
        set_blending_mode( blending_add );
        game_spr( GAME_SPARK, ( frame / 3 ) % 4, x - 9, y - 26 + ( frame / 4 ) % 3 );
        game_spr( GAME_SPARK, ( frame / 3 + 2 ) % 4, x + 9, y - 10 - ( frame / 4 ) % 3 );
        set_blending_mode( blending_alpha );
    }
}

void draw_monster( Monster* m )
{
    int x = sx( m->x ) + TILE_PX / 2, y = sy( m->y ) + TILE_PX - 2;
    draw_shadow( x, y - 1 );
    if( m->kind == MON_BAT ) { game_spr( GAME_BAT, ( frame / 4 ) % 6, x, y - 14 ); return; }
    int f = pick( m->dx != 0 || m->dy != 0, ( frame / 6 ) % 4, 0 );
    game_spr( spr_dwarf[ dir_index( m->dx, m->dy ) ], f, x, y );
}

void draw_sheep( Sheep* s )
{
    int x = sx( s->x ) + TILE_PX / 2, y = sy( s->y ) + TILE_PX - 2;
    draw_shadow( x, y - 1 );
    bool moving = s->dx != 0 || s->dy != 0;
    if( !moving && s->state == SHEEP_GRAZE ) game_spr( GAME_SHEEP_GRAZE, ( frame / 10 ) % 4, x, y );
    else game_spr( spr_sheep[ dir_index( s->dx, s->dy ) ], ( frame / 3 ) % 6, x, y );
    if( s->state == SHEEP_LIT )
    {
        game_spr( GAME_SPARK, ( frame / 2 ) % 4, x, y - 20 );
        game_spr( GAME_SPARK, ( frame / 2 + 1 ) % 4, x + 2, y - 23 );
    }
}

void draw_boss()
{
    int x = sx( boss.x ) + TILE_PX, y = sy( boss.y ) + 2 * TILE_PX - 2;
    if( boss.inv > 0 && frame % 6 < 3 ) set_multiply_color( 0xFF8080FF );
    if( boss.kind == BOSS_UTOPIEC ) story_spr( STORY_UTOPIEC_WALK, ( frame / 6 ) % 6, x, y );
    else if( boss.kind == BOSS_JAGA )
    {
        // she raises her pestle in the second before she vanishes
        if( boss.t % 150 > 110 ) story_spr( STORY_JAGA_CAST, ( frame / 5 ) % 4, x, y - 6 );
        else story_spr( STORY_JAGA, ( frame / 6 ) % 6, x, y - 6 + ( frame / 10 ) % 2 );
    }
    else if( boss.inv > 30 ) story_spr( STORY_DRAGON_HURT, ( frame / 4 ) % 2, x, y );
    else if( boss.roar > 0 || boss.warn ) story_spr( STORY_DRAGON_ROAR, ( frame / 5 ) % 4, x, y );
    else story_spr( STORY_DRAGON_IDLE, ( frame / 8 ) % 6, x, y );
    set_multiply_color( color_white );
}

void draw_figures()
{
    fig_count = 0;
    for( int i = 0; i < player_count; i++ )
      if( players[ i ].alive || players[ i ].death_t > 0 ) add_fig( FIG_PLAYER, i, players[ i ].y );
    for( int i = 0; i < monster_count; i++ ) add_fig( FIG_MONSTER, i, monsters[ i ].y );
    for( int i = 0; i < MAX_SHEEP; i++ ) if( sheep[ i ].alive ) add_fig( FIG_SHEEP, i, sheep[ i ].y );
    if( boss.kind != BOSS_NONE && boss.hp > 0 ) add_fig( FIG_BOSS, 0, boss.y + TILE );
    for( int i = 0; i < fig_count; i++ )
    {
        int k = fig_kind[ i ], n = fig_index[ i ];
        if( k == FIG_PLAYER ) draw_player( &players[ n ] );
        else if( k == FIG_MONSTER ) draw_monster( &monsters[ n ] );
        else if( k == FIG_SHEEP ) draw_sheep( &sheep[ n ] );
        else draw_boss();
    }
}

// the dragon's breath is warned a second ahead: its row or column glows
void draw_breath_warning()
{
    if( boss.kind != BOSS_DRAGON || boss.hp <= 0 || !boss.warn || frame % 8 >= 5 ) return;
    if( boss.warn_row )
    { for( int c = 1; c < W - 1; c++ ) if( mget( c, boss.warn_r ) == T_EMPTY ) game_spr( GAME_ZONE_WARN, 0, sx( gpx( c ) ), sy( gpy( boss.warn_r ) ) ); }
    else
    { for( int r = 1; r < H - 1; r++ ) if( mget( boss.warn_c, r ) == T_EMPTY ) game_spr( GAME_ZONE_WARN, 0, sx( gpx( boss.warn_c ) ), sy( gpy( r ) ) ); }
}

void draw_world()
{
    draw_map();
    draw_items();
    draw_breath_warning();
    draw_bombs();
    draw_figures();
    draw_blasts();
}

// ---------------------------------------------------------------------------
//   HUD
// ---------------------------------------------------------------------------

void draw_stat( int icon, int value, int x )
{
    game_spr( icon, 0, x, 2 );
    text_number( x + 17, 1, value, color_white );
}

void hud_bar() { fill_rect( 0, 0, 640, HUD_H, 0xE0000000 ); }

// a player's head (greyed once dead), bombs, range and shield
void draw_player_stats( Player* p, int x )
{
    if( !p->alive ) set_multiply_color( 0xFF606060 );
    game_spr( spr_head[ p->look ], 0, x, 2 );
    set_multiply_color( color_white );
    draw_stat( GAME_ICON_BOMB, p->stat_bombs, x + 22 );
    draw_stat( GAME_ICON_RANGE, p->stat_len, x + 52 );
    if( p->shield ) game_spr( GAME_ICON_SHIELD, 0, x + 82, 2 );
}

void draw_battle_hud()
{
    hud_bar();
    for( int i = 0; i < 4; i++ )
    {
        int x = 6 + i * 150 + pick( i >= 2, 34, 0 );
        draw_player_stats( &players[ i ], x );
        for( int k = 0; k < MATCH_WINS; k++ )
          fill_rect( x + 102 + k * 8, 7, 6, 6, pick( score[ i ] > k, 0xFF20D0FF, 0xFF404040 ) );
    }
    int left = shrink_at - round_frames;
    if( left > 0 && !( left <= SHRINK_WARN && frame % 20 < 10 ) )
      text_number( 312, 1, left / 60 + 1, pick( left <= SHRINK_WARN, 0xFF4080FF, color_white ) );
}

int goal_string_for( StageDef* s )
{
    if( s->goal == GOAL_EXIT ) return STR_GOAL_EXIT;
    if( s->goal == GOAL_ENEMIES ) return STR_GOAL_ENEMIES;
    if( s->goal == GOAL_KEYS ) return STR_GOAL_KEYS;
    if( s->goal == GOAL_SURVIVE ) return STR_GOAL_SURVIVE;
    if( s->boss == BOSS_UTOPIEC ) return STR_GOAL_UTOPIEC;
    if( s->boss == BOSS_JAGA ) return STR_GOAL_JAGA;
    return STR_GOAL_DRAGON;
}

int goal_string() { return goal_string_for( &stage ); }

int[ 8 ] label_buf;

// "2-7": chapter and stage within it
int* stage_label( int n )
{
    label_buf[ 0 ] = 48 + chapter_of( n );
    label_buf[ 1 ] = 45;
    int s = ( n - 1 ) % CHAPTER_LEN + 1;
    if( s >= 10 ) { label_buf[ 2 ] = 49; label_buf[ 3 ] = 48 + s - 10; label_buf[ 4 ] = 0; }
    else { label_buf[ 2 ] = 48 + s; label_buf[ 3 ] = 0; }
    return label_buf;
}

void draw_campaign_hud()
{
    hud_bar();
    for( int k = 0; k < camp_lives; k++ ) game_spr( GAME_ICON_HEART, 0, 4 + k * 17, 2 );
    text_draw( 60, 1, stage_label( camp_stage ), color_white );
    int x = 110;
    for( int i = 0; i < player_count; i++ )
    {
        Player* p = &players[ i ];
        if( p->team != 1 ) continue;
        draw_player_stats( p, x );
        if( p->sheep > 0 ) draw_stat( GAME_ICON_SHEEP, p->sheep, x + 100 );
        x += 150;
    }
    if( stage.goal == GOAL_BOSS )
    {
        fill_rect( 456, 6, 176, 8, 0xFF202020 );
        fill_rect( 456, 6, ( 176 * imax( 0, boss.hp ) ) / imax( 1, boss.max_hp ), 8, 0xFF2020D0 );
        return;
    }
    int value = -1, label = STR_HUD_EXIT;
    if( stage.goal == GOAL_KEYS ) { label = STR_HUD_KEYS; value = camp_keys; }
    else if( stage.goal == GOAL_ENEMIES ) { label = STR_HUD_LEFT; value = enemies_left(); }
    else if( stage.goal == GOAL_SURVIVE ) { label = STR_HUD_HOLD; value = imax( 0, SURVIVE_STEPS - zone_steps ); }
    int* s = tr( label );
    int w = text_width( s );
    if( value >= 0 ) { text_draw( 600 - w, 1, s, color_white ); text_number( 610, 1, value, 0xFF40E0FF ); }
    else text_draw( 632 - w, 1, s, color_white );
}

#endif
