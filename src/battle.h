// Battle: four players, the closing arena, rounds and the match.
#ifndef BATTLE_H
#define BATTLE_H

#include "bots.h"

int[ MAX_PLAYERS ] score;
int round_winner = -1;      // -1 draw
int over_timer = 0;
bool demo = false;          // the title's attract mode: everybody is a bot

void kill_sheep_at( int c, int r );

// a cell of the closing step turns to wall: whatever stands on it is crushed
void shrink_cell( int c, int r )
{
    mset( c, r, T_WALL );
    for( int i = monster_count - 1; i >= 0; i-- )
      if( monsters[ i ].c == c && monsters[ i ].r == r )
      {
          for( int k = i; k < monster_count - 1; k++ ) monsters[ k ] = monsters[ k + 1 ];
          monster_count--;
      }
    for( int i = item_count - 1; i >= 0; i-- ) if( items[ i ].c == c && items[ i ].r == r ) remove_item( i );
    for( int i = 0; i < player_count; i++ )
      if( players[ i ].alive && players[ i ].c == c && players[ i ].r == r ) kill_player( &players[ i ] );
    for( int i = bomb_count - 1; i >= 0; i-- )
      if( bombs[ i ].c == c && bombs[ i ].r == r )
      {
          if( bombs[ i ].owner >= 0 ) players[ bombs[ i ].owner ].bombs = imax( 0, players[ bombs[ i ].owner ].bombs - 1 );
          remove_bomb( i );
      }
    kill_sheep_at( c, r );
}

void update_shrink()
{
    round_frames++;
    if( round_frames < shrink_at ) return;
    if( !next_step_cells() ) return;
    for( int i = 0; i < step_count; i++ ) shrink_cell( step_c[ i ], step_r[ i ] );
    raise_event( EV_ZONE );
    zone_steps++;
    advance_zone();
    shrink_at = round_frames + zone_cycle;
}

void clear_round()
{
    bomb_count = 0; blast_count = 0; item_count = 0; monster_count = 0;
    boss.kind = BOSS_NONE;
    for( int i = 0; i < MAX_SHEEP; i++ ) sheep[ i ].alive = false;
    cam_x = 0; cam_y = 0;
}

void start_battle_round()
{
    camp_mode = false;
    set_arena( ARENA_W, ARENA_H );
    block_density = 40;
    clear_round();
    init_map();
    player_count = 4;
    for( int i = 0; i < 4; i++ )
    {
        new_player( i, start_c[ i ], start_r[ i ] );
        players[ i ].human = human_slot[ i ] && !demo;
    }
    reset_shrink();
    round_winner = -1;
    over_timer = 0;
}

void start_match()
{
    for( int i = 0; i < MAX_PLAYERS; i++ ) score[ i ] = 0;
    start_battle_round();
}

int match_winner()
{
    for( int i = 0; i < 4; i++ ) if( score[ i ] >= MATCH_WINS ) return i;
    return -1;
}

void update_human( Player* p );

void update_players()
{
    bot_plans_left = BOT_PLANS;
    compute_danger();
    // bots take turns at being first, so the planning budget is shared fairly
    for( int k = 0; k < player_count; k++ )
    {
        Player* p = &players[ ( k + frame ) % player_count ];
        if( !p->alive ) continue;
        if( p->human ) update_human( p ); else update_bot( p );
    }
}

// one frame of a battle round; true when the round has just ended
bool update_battle()
{
    update_bombs();
    update_blasts();
    update_invul_and_deaths();
    update_shrink();
    update_players();
    int last;
    if( count_alive( &last ) <= 1 )
    {
        round_winner = last;
        if( last >= 0 ) score[ last ]++;
        return true;
    }
    return false;
}

#endif
