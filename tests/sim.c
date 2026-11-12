// Bot simulation on the console, invariants checked every frame.
//   input (card words 0..): mode (0 battle, 1 story), seed, then
//     battle: rounds, frame limit per round
//     story:  first stage, frame limit per try, last stage, tries per stage
//   output (CARD_STATS+): 0 rounds or tries done; battle 1..4 wins per corner, 5 draws,
//     6 rounds at the frame limit, 7 frames in all, 8 longest round; story 1 clears, 2 tries
//     lost, 3 tries at the frame limit, 4 frames of the cleared tries; 10..17 deaths by cause
//     (own blast, another player's blast, zone, boss fire, monster, boss touch, sheep blast,
//     skeleton blast); 20 console frames used, 21 game frames (more console frames: game frames
//     that overran the cycle budget, without any drawing); 100 invariant violations, then 4 words each: round, frame, code, player
#include "video.h"
#include "input.h"
#include "audio.h"
#include "time.h"
#include "math.h"
#include "misc.h"
#include "string.h"
#include "memcard.h"

#include "../src/campaign.h"
#include "harness.h"
#include "fixtures.h"

#define V_IN_WALL      1
#define V_BOMB_ON_TILE 2
#define V_BOMB_COUNT   3
#define V_RANGE        4
#define V_TWO_BOMBS    5
#define V_LIST_FULL    6
#define V_COVER        7
#define V_DRAGON       8
#define V_BODY         9
#define MAX_RECORDS    40

int[ 64 ] stats;
int[ 4 * MAX_RECORDS ] records;
int violations = 0;
int sim_round = 0, round_frame = 0;
int[ 16 ] reported;               // per code: players already reported this round (bits)
bool[ MAX_PLAYERS ] was_alive;
int[ MAP_CELLS ] cover_count;

void write_stats()
{
    card_write_data( stats, CARD_STATS, 64 );
    number_text[ 0 ] = violations;
    card_write_data( number_text, CARD_STATS + 100, 1 );
    card_write_data( records, CARD_STATS + 101, 4 * MAX_RECORDS );
}

void violation( int code, int who )
{
    int bit = 1 << ( who + 2 );
    if( ( reported[ code ] & bit ) != 0 ) return;
    reported[ code ] = reported[ code ] | bit;
    if( violations < MAX_RECORDS )
    {
        int k = 4 * violations;
        records[ k ] = sim_round; records[ k + 1 ] = round_frame; records[ k + 2 ] = code; records[ k + 3 ] = who;
    }
    violations++;
}

bool fixed_wall( int c, int r ) { return c <= 0 || r <= 0 || c >= W - 1 || r >= H - 1 || is_pillar( c, r ); }

bool body_blocked( int c, int r )
{
    int t = mget( c, r );
    return t == T_BLOCK || ( t == T_WALL && fixed_wall( c, r ) );
}

void check_invariants()
{
    for( int i = 0; i < player_count; i++ )
    {
        Player* p = &players[ i ];
        if( p->bombs != bombs_owned_by( i ) ) violation( V_BOMB_COUNT, i );
        if( p->bombs < 0 || p->bombs > p->stat_bombs || p->stat_bombs < 1 || p->stat_bombs > BOMB_CAP
            || p->stat_len < BLAST_LEN || p->stat_len > LEN_CAP || p->sheep < 0 || p->sheep > SHEEP_CAP ) violation( V_RANGE, i );
        if( !p->alive ) continue;
        if( mget( p->c, p->r ) != T_EMPTY ) violation( V_IN_WALL, i );
        int x0 = gcol( p->x + 1 ), x1 = gcol( p->x + TILE - 2 ), y0 = grow( p->y + 1 ), y1 = grow( p->y + TILE - 2 );
        if( body_blocked( x0, y0 ) || body_blocked( x1, y0 ) || body_blocked( x0, y1 ) || body_blocked( x1, y1 ) ) violation( V_BODY, i );
    }
    for( int i = 0; i < bomb_count; i++ )
    {
        if( mget( bombs[ i ].c, bombs[ i ].r ) != T_EMPTY ) violation( V_BOMB_ON_TILE, bombs[ i ].owner );
        for( int j = i + 1; j < bomb_count; j++ )
          if( bombs[ j ].c == bombs[ i ].c && bombs[ j ].r == bombs[ i ].r ) violation( V_TWO_BOMBS, bombs[ i ].owner );
    }
    if( bomb_count >= MAX_BOMB_LIST || blast_count >= MAX_BLASTS || item_count >= MAX_ITEMS ) violation( V_LIST_FULL, -1 );
    if( round_frame % 16 != 0 ) return;
    for( int i = 0; i < MAP_CELLS; i++ ) cover_count[ i ] = 0;
    for( int i = 0; i < blast_count; i++ ) cover_count[ cell( blasts[ i ].c, blasts[ i ].r ) ]++;
    for( int i = 0; i < MAP_CELLS; i++ ) if( cover_count[ i ] != blast_cover[ i ] ) { violation( V_COVER, -1 ); return; }
}

void start_round_checks()
{
    for( int i = 0; i < 16; i++ ) reported[ i ] = 0;
    round_frame = 0;
}

void remember_alive() { for( int i = 0; i < player_count; i++ ) was_alive[ i ] = players[ i ].alive; }

bool monster_on( int c, int r )
{
    for( int i = 0; i < monster_count; i++ ) if( monsters[ i ].c == c && monsters[ i ].r == r ) return true;
    return false;
}

// 0 own blast, 1 another player's, 2 zone, 3 boss fire, 4 monster, 5 boss touch, 6 sheep, 7 skeleton
int death_cause( Player* p )
{
    if( mget( p->c, p->r ) == T_WALL ) return 2;
    if( camp_mode && monster_on( p->c, p->r ) ) return 4;
    if( camp_mode && boss.kind != BOSS_NONE && boss.hp > 0 && boss_covers( p->c, p->r ) ) return 5;
    int cause = 1;
    for( int i = 0; i < blast_count; i++ )
    {
        Blast* b = &blasts[ i ];
        if( b->c != p->c || b->r != p->r ) continue;
        if( b->owner == p->id ) return 0;
        if( b->owner == OWNER_BOSS ) cause = 3;
        else if( b->owner == OWNER_NONE ) cause = 6;
        else if( camp_mode && players[ b->owner ].team == 2 ) cause = 7;
    }
    return cause;
}

void count_deaths( bool heroes_only )
{
    for( int i = 0; i < player_count; i++ )
    {
        Player* p = &players[ i ];
        if( !was_alive[ i ] || p->alive || ( heroes_only && p->team != 1 ) ) continue;
        stats[ 10 + death_cause( p ) ]++;
    }
}

// ---------------------------------------------------------------------------

void battle_round( int cap )
{
    demo = true;
    for( int i = 0; i < MAX_PLAYERS; i++ ) human_slot[ i ] = false;
    start_battle_round();
    start_round_checks();
    int f0 = get_frame_counter();
    bool over = false;
    while( !over && round_frame < cap )
    {
        end_frame();
        frame++;
        round_frame++;
        reset_events();
        remember_alive();
        over = update_battle();
        count_deaths( false );
        check_invariants();
    }
    if( !over ) stats[ 6 ]++;
    else if( round_winner >= 0 ) stats[ 1 + round_winner ]++;
    else stats[ 5 ]++;
    stats[ 20 ] += get_frame_counter() - f0;
    stats[ 21 ] += round_frame;
    stats[ 7 ] += round_frame;
    stats[ 8 ] = imax( stats[ 8 ], round_frame );
    stats[ 0 ]++;
}

void story_try( int n, int t, int cap )
{
    camp_coop = false;
    camp_lives = 99;
    camp_tries = t;
    for( int i = 0; i < 2; i++ ) { camp_bombs[ i ] = MAX_BOMBS; camp_len[ i ] = BLAST_LEN; camp_sheep[ i ] = 0; }
    start_stage( n );
    for( int i = 0; i < player_count; i++ ) if( players[ i ].team == 1 ) players[ i ].human = false;
    start_round_checks();
    int f0 = get_frame_counter();
    while( camp_state == CAMP_PLAY && round_frame < cap )
    {
        end_frame();
        frame++;
        round_frame++;
        reset_events();
        remember_alive();
        int hp = boss.hp;
        heroes_let_sheep_go();
        update_campaign();
        if( boss.kind == BOSS_DRAGON && boss.hp < hp && events[ EV_SHEEP_BOOM ] == 0 ) violation( V_DRAGON, -1 );
        count_deaths( true );
        check_invariants();
    }
    stats[ 20 ] += get_frame_counter() - f0;
    stats[ 21 ] += round_frame;
    if( camp_state == CAMP_CLEAR ) { stats[ 1 ]++; stats[ 4 ] += round_frame; }
    else if( camp_state == CAMP_PLAY ) stats[ 3 ]++;
    else stats[ 2 ]++;
    stats[ 0 ]++;
}

void main()
{
    read_input();
    srand( card_input[ 1 ] );
    for( int i = 0; i < 64; i++ ) stats[ i ] = 0;
    write_stats();
    if( card_input[ 0 ] == 0 )
    {
        start_match();
        for( sim_round = 1; sim_round <= card_input[ 2 ]; sim_round++ ) { battle_round( card_input[ 3 ] ); write_stats(); }
    }
    else
    {
        for( int n = card_input[ 2 ]; n <= card_input[ 4 ]; n++ )
          for( int t = 0; t < card_input[ 5 ]; t++ ) { sim_round = n * 100 + t; story_try( n, t, card_input[ 3 ] ); write_stats(); }
    }
    exit();
}
