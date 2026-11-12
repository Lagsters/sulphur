// Logic tests on the console: exact situations built on the game modules, results on the card.
//   python tools/build.py tests/logic.c t_logic   (tools/check.py builds and runs it)
#include "video.h"
#include "input.h"
#include "audio.h"
#include "time.h"
#include "math.h"
#include "misc.h"
#include "string.h"
#include "memcard.h"

#include "../src/campaign.h"
#include "../src/save.h"
#include "harness.h"
#include "fixtures.h"

// ---------------------------------------------------------------------------
//   map
// ---------------------------------------------------------------------------

bool walls_mirror( int w, int h )
{
    blank_arena( w, h );
    block_density = 0;
    init_map();
    for( int r = 0; r < h; r++ )
      for( int c = 0; c < w; c++ )
      {
          bool wall = mget( c, r ) == T_WALL;
          if( wall != ( mget( w - 1 - c, r ) == T_WALL ) ) return false;
          if( wall != ( mget( c, h - 1 - r ) == T_WALL ) ) return false;
      }
    return true;
}

// with every free cell asked to take a crate, the start corners and their neighbours stay open
bool corners_free( int w, int h )
{
    blank_arena( w, h );
    block_density = 100;
    init_map();
    if( mget( 5, 3 ) != T_BLOCK ) return false;
    for( int i = 0; i < 4; i++ )
      for( int d = 0; d < 4; d++ )
      {
          int c = start_c[ i ] + DIR_X[ d ], r = start_r[ i ] + DIR_Y[ d ];
          if( c <= 0 || r <= 0 || c >= w - 1 || r >= h - 1 ) continue;
          if( mget( c, r ) != T_EMPTY ) return false;
      }
    for( int i = 0; i < 4; i++ ) if( mget( start_c[ i ], start_r[ i ] ) != T_EMPTY ) return false;
    return true;
}

void map_tests()
{
    test( "the 32x18 battle arena's walls mirror left-right and top-bottom" );
    expect( walls_mirror( 32, 18 ), "a wall without its mirror" );
    test( "the 62x18 wide stage's walls mirror left-right and top-bottom" );
    expect( walls_mirror( 62, 18 ), "a wall without its mirror" );
    test( "the 32x34 tall stage's walls mirror left-right and top-bottom" );
    expect( walls_mirror( 32, 34 ), "a wall without its mirror" );

    test( "the battle arena has a border wall and no pillars in the middle strip" );
    pillar_arena( 32, 18 );
    bool border = true;
    for( int c = 0; c < 32; c++ ) if( mget( c, 0 ) != T_WALL || mget( c, 17 ) != T_WALL ) border = false;
    for( int r = 0; r < 18; r++ ) if( mget( 0, r ) != T_WALL || mget( 31, r ) != T_WALL ) border = false;
    expect( border, "border" );
    for( int r = 8; r <= 9; r++ ) for( int c = 1; c <= 30; c++ ) expect( mget( c, r ) == T_EMPTY, "a wall in the two middle rows" );
    expect( mget( 2, 2 ) == T_WALL && mget( 29, 15 ) == T_WALL, "pillars at (2,2) and (29,15)" );

    test( "the start corners of the battle arena are free of crates" );
    expect( corners_free( 32, 18 ), "a crate or wall at a start corner" );
    test( "the start corners of the wide and tall stages are free of crates" );
    expect( corners_free( 62, 18 ), "wide stage" );
    expect( corners_free( 32, 34 ), "tall stage" );
}

// ---------------------------------------------------------------------------
//   bombs and blasts
// ---------------------------------------------------------------------------

void blast_tests()
{
    test( "a blast stops at a wall" );
    blank_arena( 32, 18 );
    mset( 7, 5, T_WALL );
    add_bomb( 5, 5, 1, 3, OWNER_NONE, false );
    update_bombs();
    expect( is_blast( 5, 5 ) && is_blast( 6, 5 ), "the bomb's cell and the next one burn" );
    expect( !is_blast( 7, 5 ), "the wall burns" );
    expect( mget( 7, 5 ) == T_WALL, "the wall broke" );
    expect( !is_blast( 8, 5 ), "the blast went through the wall" );

    test( "a blast breaks the first crate in its way and stops there" );
    blank_arena( 32, 18 );
    mset( 5, 7, T_BLOCK ); mset( 5, 8, T_BLOCK );
    add_bomb( 5, 5, 1, 3, OWNER_NONE, false );
    update_bombs();
    expect( is_blast( 5, 7 ), "the first crate's cell burns" );
    expect( mget( 5, 7 ) == T_EMPTY, "the first crate is still there" );
    expect( !is_blast( 5, 8 ), "the blast went past the first crate" );
    expect( mget( 5, 8 ) == T_BLOCK, "the second crate broke" );

    test( "a blast reaches exactly the bomb's length" );
    blank_arena( 32, 18 );
    add_bomb( 10, 8, 1, 4, OWNER_NONE, false );
    update_bombs();
    expect( is_blast( 14, 8 ) && is_blast( 6, 8 ) && is_blast( 10, 4 ) && is_blast( 10, 12 ), "length 4 not reached" );
    expect( !is_blast( 15, 8 ) && !is_blast( 5, 8 ) && !is_blast( 10, 3 ) && !is_blast( 10, 13 ), "longer than 4" );

    test( "a blast burns out after BLAST_TIME frames" );
    for( int i = 0; i < BLAST_TIME - 1; i++ ) update_blasts();
    expect( is_blast( 10, 8 ), "gone too early" );
    update_blasts();
    expect_eq( blast_count, 0, "blasts left" );
    expect( !is_blast( 10, 8 ), "the cell still burns" );

    test( "bombs in a blast go off in the same tick as a chain" );
    blank_arena( 32, 18 );
    for( int i = 0; i < 3; i++ ) { put_player( i, 2 + i * 3, 2 ); players[ i ].bombs = 1; }
    add_bomb( 5, 10, 1, 2, 0, false );
    add_bomb( 7, 10, 100, 2, 1, false );
    add_bomb( 9, 10, 100, 2, 2, false );
    reset_events();
    update_bombs();
    expect_eq( bomb_count, 0, "bombs left after one tick" );
    expect( is_blast( 11, 10 ), "the last bomb of the chain did not burn its cells" );
    expect_eq( events[ EV_BOOM ], 3, "explosions" );

    test( "every owner gets his bomb back after a chain" );
    for( int i = 0; i < 3; i++ ) expect_eq( players[ i ].bombs, 0, "bombs of an owner" );

    test( "a bomb behind a wall does not join the chain" );
    blank_arena( 32, 18 );
    mset( 6, 12, T_WALL );
    add_bomb( 5, 12, 1, 2, OWNER_NONE, false );
    add_bomb( 7, 12, 100, 2, OWNER_NONE, false );
    update_bombs();
    expect_eq( bomb_count, 1, "bombs left" );
    expect( is_bomb( 7, 12 ) && bombs[ 0 ].t == 99, "the bomb behind the wall went off" );

    test( "a laid bomb counts for its owner until it goes off" );
    blank_arena( 32, 18 );
    Player* p = put_player( 0, 5, 5 );
    expect( place_bomb( p ), "the first bomb was refused" );
    expect_eq( p->bombs, 1, "bombs ticking" );
    expect( bomb_count == 1 && bombs[ 0 ].c == 5 && bombs[ 0 ].r == 5 && bombs[ 0 ].owner == 0, "bomb on the player's cell" );
    expect_eq( bombs[ 0 ].t, BOMB_TIMER, "timer" );
    expect_eq( bombs[ 0 ].len, BLAST_LEN, "length" );
    for( int i = 0; i < BOMB_TIMER - 1; i++ ) update_bombs();
    expect_eq( bomb_count, 1, "the bomb went off before BOMB_TIMER" );
    update_bombs();
    expect_eq( bomb_count, 0, "the bomb did not go off at BOMB_TIMER" );
    expect_eq( p->bombs, 0, "the bomb did not come back" );

    test( "a player with one bomb cannot lay a second one" );
    blank_arena( 32, 18 );
    p = put_player( 0, 5, 5 );
    place_bomb( p );
    walk( p, 1, 0, 16 );
    expect( !place_bomb( p ), "a second bomb was laid" );
    expect_eq( bomb_count, 1, "bombs" );

    test( "a cell with a bomb takes no second one" );
    blank_arena( 32, 18 );
    p = put_player( 0, 5, 5 );
    p->stat_bombs = 3;
    place_bomb( p );
    expect( !place_bomb( p ), "a second bomb on the same cell" );
    expect_eq( p->bombs, 1, "bombs counted" );
}

// ---------------------------------------------------------------------------
//   items
// ---------------------------------------------------------------------------

void item_tests()
{
    test( "walking onto a bomb item adds a bomb and takes the item" );
    blank_arena( 32, 18 );
    Player* p = put_player( 0, 5, 5 );
    add_item( 6, 5, ITEM_BOMB );
    walk( p, 1, 0, 16 );
    expect_eq( p->c, 6, "column" );
    expect_eq( p->stat_bombs, MAX_BOMBS + 1, "bombs" );
    expect_eq( item_count, 0, "items left" );

    test( "walking onto a range item adds one to the blast length" );
    add_item( 7, 5, ITEM_RANGE );
    walk( p, 1, 0, 16 );
    expect_eq( p->stat_len, BLAST_LEN + 1, "length" );

    test( "walking onto a shield item gives a shield" );
    add_item( 8, 5, ITEM_SHIELD );
    walk( p, 1, 0, 16 );
    expect( p->shield, "no shield" );
    expect_eq( item_count, 0, "items left" );

    test( "bombs stop at BOMB_CAP and range at LEN_CAP" );
    p->stat_bombs = BOMB_CAP; p->stat_len = LEN_CAP;
    add_item( 9, 5, ITEM_BOMB ); add_item( 10, 5, ITEM_RANGE );
    walk( p, 1, 0, 32 );
    expect_eq( p->c, 10, "column" );
    expect_eq( p->stat_bombs, BOMB_CAP, "bombs" );
    expect_eq( p->stat_len, LEN_CAP, "length" );
    expect_eq( item_count, 0, "items left" );

    test( "a blast burns bonus items but not keys or the exit" );
    blank_arena( 32, 18 );
    add_item( 6, 5, ITEM_BOMB ); add_item( 7, 5, ITEM_KEY ); add_item( 5, 6, ITEM_EXIT ); add_item( 5, 4, ITEM_SHIELD );
    add_bomb( 5, 5, 1, 3, OWNER_NONE, false );
    update_bombs();
    expect_eq( item_count, 2, "items left" );
    expect( item_kind_at( 7, 5 ) == ITEM_KEY && item_kind_at( 5, 6 ) == ITEM_EXIT, "a quest item burnt" );

    test( "a broken crate gives up the quest item hidden under it" );
    blank_arena( 32, 18 );
    mset( 5, 7, T_BLOCK );
    hidden[ cell( 5, 7 ) ] = ITEM_EXIT;
    add_bomb( 5, 5, 1, 2, OWNER_NONE, false );
    update_bombs();
    expect_eq( item_kind_at( 5, 7 ), ITEM_EXIT, "item on the crate's cell" );
    expect_eq( hidden[ cell( 5, 7 ) ], ITEM_NONE, "still hidden" );

    test( "a battle player does not pick up quest items" );
    blank_arena( 32, 18 );
    p = put_player( 2, 5, 5 );
    add_item( 6, 5, ITEM_KEY );
    walk( p, 1, 0, 16 );
    expect_eq( item_count, 1, "items left" );
}

// ---------------------------------------------------------------------------
//   walking
// ---------------------------------------------------------------------------

void walk_tests()
{
    test( "a player walks one unit a frame, a cell in 16 frames" );
    blank_arena( 32, 18 );
    Player* p = put_player( 0, 5, 5 );
    int x0 = p->x;
    walk( p, 1, 0, 1 );
    expect_eq( p->x, x0 + 1, "x after one frame" );
    walk( p, 1, 0, 15 );
    expect_eq( p->x, x0 + TILE, "x after 16 frames" );
    expect_eq( p->c, 6, "column" );

    test( "walls and crates stop a walking player" );
    blank_arena( 32, 18 );
    p = put_player( 0, 1, 1 );
    // the hitbox is a unit smaller than the cell on each side: the body may overlap a wall by 1
    walk( p, 0, -1, 10 );
    expect_eq( p->y, gpy( 1 ) - 1, "walked into the top wall" );
    walk( p, -1, 0, 10 );
    expect_eq( p->x, gpx( 1 ) - 1, "walked into the left wall" );
    mset( 2, 1, T_BLOCK );
    walk( p, 1, 0, 10 );
    expect_eq( p->x, gpx( 1 ) + 1, "walked into a crate" );

    test( "the corner assist slides a player off the axis into a corridor" );
    blank_arena( 32, 18 );
    mset( 4, 4, T_WALL ); mset( 4, 6, T_WALL );
    p = put_player( 0, 3, 5 );
    p->y = gpy( 5 ) - 4;
    walk( p, 1, 0, 40 );
    expect_eq( p->y, gpy( 5 ), "not lined up with the corridor" );
    expect( p->c >= 5, "did not get through the corridor" );

    test( "the corner assist slides the other way too" );
    blank_arena( 32, 18 );
    mset( 4, 4, T_WALL ); mset( 4, 6, T_WALL );
    p = put_player( 0, 3, 5 );
    p->y = gpy( 5 ) + 5;
    walk( p, 1, 0, 40 );
    expect_eq( p->y, gpy( 5 ), "not lined up with the corridor" );
    expect( p->c >= 5, "did not get through the corridor" );

    test( "a player walks off his own bomb" );
    blank_arena( 32, 18 );
    p = put_player( 0, 5, 5 );
    place_bomb( p );
    walk( p, 1, 0, 16 );
    expect_eq( p->x, gpx( 6 ), "stuck on his own bomb" );

    test( "a player cannot walk back onto his own bomb once off it" );
    walk( p, -1, 0, 8 );
    expect_eq( p->x, gpx( 6 ) - 1, "walked back into his bomb" );

    test( "a player cannot walk into another player's bomb" );
    put_player( 1, 20, 10 );
    add_bomb( 7, 5, 100, 2, 1, false );
    walk( p, 1, 0, 8 );
    expect_eq( p->x, gpx( 6 ) + 1, "walked into a bomb" );
}

// ---------------------------------------------------------------------------
//   hurting
// ---------------------------------------------------------------------------

void hurt_tests()
{
    test( "a blast on a player's cell kills him" );
    blank_arena( 32, 18 );
    Player* p = put_player( 0, 5, 5 );
    add_blast( 6, 5, OWNER_NONE, false );
    expect( !blast_hurts( p ), "a blast on the next cell hurts" );
    add_blast( 5, 5, OWNER_NONE, false );
    expect( blast_hurts( p ), "the blast on his cell does not hurt" );
    blast_hit( p );
    expect( !p->alive, "alive" );
    expect_eq( p->death_t, DEATH_TIME, "death animation" );

    test( "a shield takes the first hit and gives a short invulnerability" );
    blank_arena( 32, 18 );
    p = put_player( 0, 5, 5 );
    p->shield = true;
    blast_hit( p );
    expect( p->alive && !p->shield, "shield not used up, or died" );
    expect_eq( p->invul, SHIELD_INVUL, "invulnerability" );
    blast_hit( p );
    expect( p->alive, "died while invulnerable" );

    test( "after the invulnerability the next hit kills" );
    for( int i = 0; i < SHIELD_INVUL; i++ ) update_invul_and_deaths();
    expect_eq( p->invul, 0, "invulnerability left" );
    blast_hit( p );
    expect( !p->alive, "survived without a shield" );

    test( "in battle another player's blast kills" );
    blank_arena( 32, 18 );
    p = put_player( 0, 5, 5 );
    put_player( 1, 9, 9 );
    add_blast( 5, 5, 1, false );
    expect( blast_hurts( p ), "spared" );

    test( "in the story a fellow hero's blast spares a hero" );
    story_arena( 32, 18 );
    p = put_hero( 0, 5, 5 );
    put_hero( 1, 9, 9 );
    add_blast( 5, 5, 1, false );
    expect( !blast_hurts( p ), "hurt by a fellow hero" );

    test( "in the story a hero's own blast kills him" );
    add_blast( 5, 5, 0, false );
    expect( blast_hurts( p ), "spared by his own blast" );

    test( "in the story a skeleton's or a boss's blast kills a hero" );
    story_arena( 32, 18 );
    p = put_hero( 0, 5, 5 );
    Player* s = put_player( 1, 9, 9 );
    s->team = 2;
    add_blast( 5, 5, 1, false );
    expect( blast_hurts( p ), "spared by a skeleton" );
    story_arena( 32, 18 );
    p = put_hero( 0, 5, 5 );
    add_blast( 5, 5, OWNER_BOSS, false );
    expect( blast_hurts( p ), "spared by the boss" );
}

// ---------------------------------------------------------------------------
//   the closing zone
// ---------------------------------------------------------------------------

int open_cells()
{
    int n = 0;
    for( int r = 1; r < H - 1; r++ ) for( int c = 1; c < W - 1; c++ ) if( mget( c, r ) == T_EMPTY ) n++;
    return n;
}

// after k steps the open cells are exactly the box the zone left
bool zone_box_after( int k )
{
    int ky = imin( k, 7 );
    int x0 = 1 + k, x1 = 30 - k, y0 = 1 + ky, y1 = 16 - ky;
    for( int r = 1; r < H - 1; r++ )
      for( int c = 1; c < W - 1; c++ )
      {
          bool inside = c >= x0 && c <= x1 && r >= y0 && r <= y1;
          if( inside != ( mget( c, r ) == T_EMPTY ) ) return false;
      }
    return true;
}

void zone_tests()
{
    test( "no cell closes before the first zone step" );
    blank_arena( 32, 18 );
    reset_shrink();
    int open = open_cells();
    expect_eq( shrink_at, SHRINK_DELAY + SHRINK_CYCLE - 1, "first step at" );
    for( int i = 0; i < shrink_at - 1; i++ ) update_shrink();
    expect_eq( open_cells(), open, "open cells" );
    expect_eq( zone_steps, 0, "steps" );

    test( "the step blinks SHRINK_WARN frames before it closes" );
    expect( shrink_closing() >= 0, "not blinking one frame before" );
    blank_arena( 32, 18 );
    reset_shrink();
    round_frames = shrink_at - SHRINK_WARN - 1;
    expect_eq( shrink_closing(), -1, "blinks too early" );
    round_frames++;
    expect_eq( shrink_closing(), SHRINK_WARN, "frames left when the blinking starts" );
    expect_eq( step_count, 2 * 30 + 2 * 14, "cells of the first step" );

    test( "the first zone step closes the whole outline at once" );
    blank_arena( 32, 18 );
    reset_shrink();
    int first = shrink_at;
    for( int i = 0; i < first; i++ ) update_shrink();
    expect_eq( zone_steps, 1, "steps" );
    expect( zone_box_after( 1 ), "the open cells are not the inner box" );

    test( "the zone steps again every SHRINK_CYCLE frames" );
    for( int i = 0; i < SHRINK_CYCLE - 1; i++ ) update_shrink();
    expect_eq( zone_steps, 1, "stepped early" );
    update_shrink();
    expect_eq( zone_steps, 2, "did not step" );
    expect( zone_box_after( 2 ), "the open cells are not the inner box" );

    test( "the zone closes rings down to two rows, then side columns, and stops at the 4x2 middle" );
    bool order = true;
    for( int k = 3; k <= 13; k++ )
    {
        for( int i = 0; i < SHRINK_CYCLE; i++ ) update_shrink();
        if( zone_steps != k || !zone_box_after( k ) ) order = false;
    }
    expect( order, "a step closed something else than the next ring or side columns" );
    for( int i = 0; i < 20 * SHRINK_CYCLE; i++ ) update_shrink();
    expect_eq( zone_steps, 13, "steps" );
    expect_eq( open_cells(), 8, "open cells left" );
    expect( zone_box_after( 13 ), "the strip left is not cells 14..17 of rows 8..9" );

    test( "a closing step crushes players and items and takes back bombs" );
    blank_arena( 32, 18 );
    reset_shrink();
    Player* p = put_player( 0, 1, 1 );
    Player* q = put_player( 1, 10, 10 );
    add_bomb( 30, 5, 1000, 2, 1, false );
    q->bombs = 1;
    add_item( 5, 16, ITEM_BOMB );
    first = shrink_at;
    for( int i = 0; i < first; i++ ) update_shrink();
    expect( !p->alive, "the player on the outline survived" );
    expect( q->alive, "the player inside died" );
    expect_eq( bomb_count, 0, "bombs left on the closed cells" );
    expect_eq( q->bombs, 0, "the owner did not get his bomb back" );
    expect_eq( item_count, 0, "items left on the closed cells" );
}

// ---------------------------------------------------------------------------
//   bots
// ---------------------------------------------------------------------------

int bombs_laid = 0;
void run_battle( int frames )
{
    for( int i = 0; i < frames; i++ ) { step_battle(); bombs_laid += events[ EV_BOMB ]; }
}

void bot_tests()
{
    test( "every bot gets the four directions in a shuffled order" );
    bool all = true;
    for( int i = 0; i < 4; i++ )
    {
        new_player( i, 1, 1 );
        int seen = 0;
        for( int k = 0; k < 4; k++ ) seen = seen | ( 1 << players[ i ].bot_order[ k ] );
        if( seen != 15 ) all = false;
    }
    expect( all, "a direction missing" );

    test( "a bot on its own bomb in the corner gets out of the blast" );
    pillar_arena( 32, 18 );
    Player* b = put_bot( 0, 1, 1 );
    place_bomb( b );
    run_battle( BOMB_TIMER + BLAST_TIME + 10 );
    expect( b->alive, "died" );
    expect_eq( b->bombs, 0, "bomb not back" );

    test( "a bot next to its own bomb leaves the blast line" );
    pillar_arena( 32, 18 );
    b = put_bot( 0, 6, 5 );
    add_bomb( 5, 5, BOMB_TIMER, 3, 0, false );
    b->bombs = 1;
    run_battle( BOMB_TIMER + BLAST_TIME + 10 );
    expect( b->alive, "died" );

    test( "a bot in a dead end does not lay a bomb it cannot escape" );
    pillar_arena( 32, 18 );
    mset( 2, 1, T_BLOCK ); mset( 1, 3, T_BLOCK );
    b = put_bot( 0, 1, 1 );
    bombs_laid = 0;
    run_battle( 300 );
    expect_eq( bombs_laid, 0, "bombs laid" );
    expect( b->alive, "died" );

    test( "a bot lays a bomb by a crate when it can get away, and survives it" );
    pillar_arena( 32, 18 );
    mset( 2, 1, T_BLOCK );
    b = put_bot( 0, 1, 1 );
    bombs_laid = 0;
    run_battle( 300 );
    expect( bombs_laid >= 1, "no bomb laid" );
    expect( mget( 2, 1 ) == T_EMPTY, "the crate is still there" );
    expect( b->alive, "died" );

    test( "a bot bombs an enemy standing in its blast line and survives" );
    pillar_arena( 32, 18 );
    b = put_bot( 0, 1, 1 );
    Player* prey = put_player( 1, 3, 1 );
    run_battle( 200 );
    expect( !prey->alive, "the enemy survived" );
    expect( b->alive, "the bot died" );

    test( "a bot leaves the blinking zone step before it closes" );
    pillar_arena( 32, 18 );
    b = put_bot( 0, 1, 1 );
    reset_shrink();
    round_frames = shrink_at - SHRINK_WARN;
    run_battle( SHRINK_WARN + 10 );
    expect_eq( zone_steps, 1, "steps" );
    expect( b->alive, "crushed" );
}

// ---------------------------------------------------------------------------
//   the story: stages
// ---------------------------------------------------------------------------

int boss_of( int n ) { StageDef s; stage_def( n, &s ); return s.boss; }

void stage_tests()
{
    StageDef s;
    test( "every fifth stage and only those is a boss fight" );
    for( int n = 1; n <= STAGE_COUNT; n++ )
    {
        stage_def( n, &s );
        expect( ( s.boss != BOSS_NONE ) == ( n % 5 == 0 ), "boss on a wrong stage" );
        expect( ( s.goal == GOAL_BOSS ) == ( n % 5 == 0 ), "boss goal on a wrong stage" );
        expect( s.boss != BOSS_NONE || ( s.goal >= GOAL_EXIT && s.goal <= GOAL_SURVIVE ), "a stage without a goal" );
    }

    test( "utopiec ends chapter 1, Baba Jaga chapter 2 and the dragon chapter 3" );
    expect_eq( boss_of( 10 ), BOSS_UTOPIEC, "stage 10" );
    expect_eq( boss_of( 20 ), BOSS_JAGA, "stage 20" );
    expect_eq( boss_of( 30 ), BOSS_DRAGON, "stage 30" );
    expect_eq( boss_of( 5 ), BOSS_UTOPIEC, "stage 5" );
    expect_eq( boss_of( 15 ), BOSS_UTOPIEC, "stage 15" );
    expect_eq( boss_of( 25 ), BOSS_JAGA, "stage 25" );

    test( "stages 1-10, 11-20 and 21-30 are chapters 1, 2 and 3" );
    for( int n = 1; n <= STAGE_COUNT; n++ ) { stage_def( n, &s ); expect_eq( s.chapter, ( n - 1 ) / 10 + 1, "chapter" ); }

    test( "sheep come only in chapter 3, two of them at the dragon" );
    for( int n = 1; n <= STAGE_COUNT; n++ )
    {
        stage_def( n, &s );
        if( n <= 20 ) expect_eq( s.sheep, 0, "sheep before chapter 3" );
        else expect( s.sheep >= 1, "a chapter 3 stage without a sheep" );
    }
    stage_def( 30, &s );
    expect_eq( s.sheep, 2, "sheep at the dragon" );

    test( "the dragon takes DRAGON_HP sheep and every boss has hit points" );
    expect_eq( s.boss_hp, DRAGON_HP, "dragon hp" );
    expect_eq( DRAGON_HP, 3, "DRAGON_HP" );
    for( int n = 5; n <= STAGE_COUNT; n += 5 ) { stage_def( n, &s ); expect( s.boss_hp > 0, "a boss without hp" ); }

    test( "bats come from chapter 2 on and skeletons only in chapter 3" );
    for( int n = 1; n <= STAGE_COUNT; n++ )
    {
        stage_def( n, &s );
        if( n <= 10 ) expect_eq( s.bats, 0, "bats in chapter 1" );
        if( n <= 20 ) expect_eq( s.skeletons, 0, "skeletons before chapter 3" );
        if( n > 20 && n % 5 != 0 ) expect( s.skeletons >= 1, "chapter 3 stage without skeletons" );
    }

    test( "chapter 1 stages have only Dratewka" );
    start_campaign( false, 1 );
    expect_eq( player_count, 1, "players" );
    expect( players[ 0 ].team == 1 && players[ 0 ].human, "Dratewka is not a human hero" );

    test( "Wanda joins from chapter 2 as a bot ally, or as player 2 in a 2P story" );
    start_campaign( false, 11 );
    expect( player_count >= 2 && players[ 1 ].team == 1 && !players[ 1 ].human, "no bot Wanda" );
    start_campaign( true, 11 );
    expect( players[ 1 ].human, "Wanda is not human in 2P" );

    test( "an exit stage hides one exit and a keys stage three keys" );
    for( int n = 1; n <= 3; n += 2 )
    {
        start_campaign( false, n );
        int want = pick( stage.goal == GOAL_KEYS, ITEM_KEY, ITEM_EXIT );
        int found = 0;
        for( int i = 0; i < MAP_CELLS; i++ ) if( hidden[ i ] == want ) found++;
        for( int i = 0; i < item_count; i++ ) if( items[ i ].kind == want ) found++;
        expect_eq( found, pick( want == ITEM_KEY, 3, 1 ), "quest items" );
    }

    test( "monsters start at least 8 cells from the heroes" );
    bool far = true;
    for( int n = 1; n <= STAGE_COUNT; n++ )
    {
        start_campaign( false, n );
        for( int i = 0; i < monster_count; i++ )
          if( iabs( monsters[ i ].c - start_c[ 0 ] ) + iabs( monsters[ i ].r - start_r[ 0 ] ) < 8 ) far = false;
    }
    expect( far, "a monster too close" );

    test( "stage 30 puts a 3-hp dragon in the middle and two sheep on the map" );
    start_campaign( false, 30 );
    expect_eq( boss.kind, BOSS_DRAGON, "boss" );
    expect_eq( boss.hp, 3, "hp" );
    expect_eq( alive_sheep(), 2, "sheep" );
    for( int dc = 0; dc < 2; dc++ ) for( int dr = 0; dr < 2; dr++ ) expect( mget( boss.c + dc, boss.r + dr ) == T_EMPTY, "the dragon stands in a wall" );
}

// ---------------------------------------------------------------------------
//   the story: sheep and bosses
// ---------------------------------------------------------------------------

Player* dragon_arena()
{
    story_arena( 32, 18 );
    Player* p = put_hero( 0, 3, 8 );
    put_boss( BOSS_DRAGON, 15, 8, DRAGON_HP );
    return p;
}

void sheep_frame()
{
    end_frame();
    frame++;
    reset_events();
    compute_danger();
    update_bombs();
    update_blasts();
    update_sheep();
}

void sheep_tests()
{
    test( "a hero walking onto a grazing sheep catches it" );
    story_arena( 32, 18 );
    mset( 1, 2, T_BLOCK );
    Player* p = put_hero( 0, 3, 1 );
    spawn_sheep( cell( 1, 1 ) );
    int got = 0;
    for( int i = 0; i < 48 && alive_sheep() > 0; i++ ) { move_player( p, -1, 0 ); sheep_frame(); got += events[ EV_SHEEP_GOT ]; }
    expect_eq( p->sheep, 1, "sheep carried" );
    expect_eq( alive_sheep(), 0, "sheep on the map" );
    expect_eq( got, 1, "catch events" );

    test( "a hero carrying SHEEP_CAP sheep or a skeleton cannot catch one" );
    story_arena( 32, 18 );
    p = put_hero( 0, 5, 5 );
    p->sheep = SHEEP_CAP;
    Player* sk = put_player( 1, 9, 9 );
    sk->team = 2;
    spawn_sheep( cell( 5, 5 ) );
    spawn_sheep( cell( 9, 9 ) );
    sheep_frame();
    expect_eq( p->sheep, SHEEP_CAP, "carried" );
    expect_eq( alive_sheep(), 2, "sheep on the map" );

    test( "a carried sheep is let go only in the story while the dragon lives" );
    story_arena( 32, 18 );
    p = put_hero( 0, 3, 8 );
    p->sheep = 1;
    expect( !launch_sheep( p ), "let go without a dragon" );
    put_boss( BOSS_UTOPIEC, 15, 8, 3 );
    expect( !launch_sheep( p ), "let go at the utopiec" );
    put_boss( BOSS_DRAGON, 15, 8, 0 );
    expect( !launch_sheep( p ), "let go at a dead dragon" );
    put_boss( BOSS_DRAGON, 15, 8, 3 );
    camp_mode = false;
    expect( !launch_sheep( p ), "let go in battle" );
    camp_mode = true;
    expect_eq( p->sheep, 1, "sheep carried" );
    expect( launch_sheep( p ), "not let go at a live dragon" );
    expect_eq( p->sheep, 0, "sheep carried after letting go" );
    expect( alive_sheep() == 1 && sheep[ 0 ].state == SHEEP_LIT && sheep[ 0 ].owner == 0, "no lit sheep" );

    test( "a let-go sheep runs to the dragon and takes one hit point" );
    p = dragon_arena();
    p->sheep = 1;
    launch_sheep( p );
    int t = 0;
    while( t < SHEEP_FUSE && boss.hp == DRAGON_HP ) { sheep_frame(); t++; }
    expect_eq( boss.hp, DRAGON_HP - 1, "dragon hp" );
    expect_eq( alive_sheep(), 0, "sheep left" );
    expect( is_blast( 15, 8 ) && is_blast( 16, 9 ), "no blast inside the dragon" );
    expect( t < 200, "the sheep took too long" );

    test( "sulphur bombs never hurt the dragon" );
    p = dragon_arena();
    p->bombs = 2;
    add_bomb( 14, 8, 1, 3, 0, false );
    add_bomb( 17, 9, 1, 3, 0, false );
    for( int i = 0; i < BLAST_TIME + 5; i++ )
    {
        sheep_frame();
        update_boss();
        if( i == 0 ) expect( is_blast( 15, 8 ) && is_blast( 16, 9 ), "the blasts did not reach the dragon" );
    }
    expect_eq( boss.hp, DRAGON_HP, "dragon hp" );

    test( "a grazing sheep caught in a blast goes off with a bigger blast" );
    story_arena( 32, 18 );
    spawn_sheep( cell( 10, 10 ) );
    add_blast( 10, 10, OWNER_NONE, false );
    sheep_frame();
    expect_eq( alive_sheep(), 0, "the sheep survived" );
    expect( is_bomb( 10, 10 ) && bombs[ bomb_at( 10, 10 ) ].sheep, "no sheep bomb" );
    sheep_frame();
    expect( is_blast( 13, 10 ) && is_blast( 10, 7 ), "the sheep's blast is shorter than 3" );

    test( "a lit sheep going off on its own gives its owner no extra bomb" );
    p = dragon_arena();
    place_bomb( p );
    p->sheep = 1;
    launch_sheep( p );
    sheep[ 0 ].c = 12; sheep[ 0 ].x = gpx( 12 );
    boss.hp = 0;
    sheep_frame();
    sheep_frame();
    expect_eq( bombs_owned_by( 0 ), 1, "his bombs on the map" );
    expect_eq( p->bombs, bombs_owned_by( 0 ), "his bomb counter" );

    test( "the dragon's breath burns the warned line a second later" );
    p = dragon_arena();
    boss.t = 119;
    update_boss();
    expect( boss.warn, "no warning" );
    for( int i = 0; i < 59; i++ ) update_boss();
    expect( !is_blast( p->c, p->r ), "burnt before the warning ended" );
    update_boss();
    expect( is_blast( p->c, p->r ), "the warned line did not burn" );
    expect( blast_hurts( p ), "the breath spares Dratewka" );

    test( "utopiec takes one hit from a blast and is briefly invulnerable" );
    story_arena( 32, 18 );
    put_hero( 0, 2, 2 );
    put_boss( BOSS_UTOPIEC, 15, 8, 3 );
    add_blast( 15, 8, 0, false );
    update_boss();
    expect_eq( boss.hp, 2, "hp after the blast" );
    expect( boss.inv > 0, "not invulnerable" );
    update_boss();
    expect_eq( boss.hp, 2, "hp a frame later" );

    test( "Baba Jaga takes one hit from a blast" );
    story_arena( 32, 18 );
    put_hero( 0, 2, 2 );
    put_boss( BOSS_JAGA, 15, 8, 3 );
    add_blast( 16, 9, 0, false );
    update_boss();
    expect_eq( boss.hp, 2, "hp" );

    test( "a boss is not hurt by its own blasts" );
    story_arena( 32, 18 );
    put_hero( 0, 2, 2 );
    put_boss( BOSS_JAGA, 15, 8, 3 );
    add_blast( 15, 8, OWNER_BOSS, false );
    update_boss();
    expect_eq( boss.hp, 3, "hp" );
}

// ---------------------------------------------------------------------------
//   the story: goals
// ---------------------------------------------------------------------------

void goal_arena( int goal )
{
    story_arena( 32, 18 );
    stage_def( 1, &stage );
    stage.goal = goal;
}

void goal_tests()
{
    test( "walking onto the exit clears an exit stage" );
    goal_arena( GOAL_EXIT );
    Player* p = put_hero( 0, 5, 5 );
    add_item( 6, 5, ITEM_EXIT );
    step_story();
    expect_eq( camp_state, CAMP_PLAY, "cleared before the exit" );
    walk( p, 1, 0, 16 );
    step_story();
    expect_eq( camp_state, CAMP_CLEAR, "state" );

    test( "a skeleton does not take the exit" );
    goal_arena( GOAL_EXIT );
    put_hero( 0, 2, 2 );
    Player* sk = put_player( 1, 5, 5 );
    sk->team = 2;
    add_item( 6, 5, ITEM_EXIT );
    walk( sk, 1, 0, 16 );
    step_story();
    expect_eq( item_count, 1, "items" );
    expect_eq( camp_state, CAMP_PLAY, "state" );

    test( "two keys do not clear a keys stage, the third does" );
    goal_arena( GOAL_KEYS );
    p = put_hero( 0, 5, 5 );
    camp_keys = 2;
    add_item( 6, 5, ITEM_KEY );
    step_story();
    expect_eq( camp_state, CAMP_PLAY, "cleared with two keys" );
    walk( p, 1, 0, 16 );
    step_story();
    expect_eq( camp_keys, 3, "keys" );
    expect_eq( camp_state, CAMP_CLEAR, "state" );

    test( "a survive stage clears after the zone's fifth step" );
    goal_arena( GOAL_SURVIVE );
    put_hero( 0, 15, 8 );
    shrink_at = 600; zone_cycle = SHRINK_WARN;
    int t = 0;
    while( camp_state == CAMP_PLAY && t < 3000 ) { step_story(); t++; }
    expect_eq( camp_state, CAMP_CLEAR, "state" );
    expect_eq( round_frames, 600 + 4 * SHRINK_WARN, "cleared at frame" );

    test( "killing every monster and skeleton clears an enemies stage" );
    goal_arena( GOAL_ENEMIES );
    put_hero( 0, 2, 2 );
    sk = put_player( 1, 20, 10 );
    sk->team = 2;
    spawn_monster( MON_DWARF, cell( 10, 14 ) );
    step_story();
    expect_eq( camp_state, CAMP_PLAY, "cleared with enemies left" );
    add_blast( monsters[ 0 ].c, monsters[ 0 ].r, 0, false );
    step_story();
    expect_eq( monster_count, 0, "a blast did not kill the monster" );
    expect_eq( camp_state, CAMP_PLAY, "cleared with a skeleton left" );
    kill_player( sk );
    step_story();
    expect_eq( camp_state, CAMP_CLEAR, "state" );

    test( "a hero touching a monster dies and costs a life" );
    goal_arena( GOAL_ENEMIES );
    p = put_hero( 0, 5, 5 );
    spawn_monster( MON_DWARF, cell( 5, 5 ) );
    step_story();
    expect( !p->alive, "the hero survived" );
    expect_eq( camp_lives, LIVES - 1, "lives" );
    expect_eq( camp_state, CAMP_LOST, "state" );

    test( "defeating the boss clears a boss stage" );
    goal_arena( GOAL_BOSS );
    put_hero( 0, 2, 2 );
    put_boss( BOSS_JAGA, 15, 8, 1 );
    add_blast( 15, 8, 0, false );
    step_story();
    expect_eq( camp_state, CAMP_CLEAR, "state" );
}

// ---------------------------------------------------------------------------
//   the save on the memory card
// ---------------------------------------------------------------------------

void save_tests()
{
    test( "the story progress and the language survive on the memory card" );
    saved_stage = 7; lang = 1;
    write_save();
    saved_stage = 0; lang = 0;
    load_save();
    expect_eq( saved_stage, 7, "stage" );
    expect_eq( lang, 1, "language" );
    lang = 0;
}

void main()
{
    srand( 1 );
    write_head( 0 );
    map_tests();
    blast_tests();
    item_tests();
    walk_tests();
    hurt_tests();
    zone_tests();
    bot_tests();
    stage_tests();
    sheep_tests();
    goal_tests();
    save_tests();
    finish_tests();
}
