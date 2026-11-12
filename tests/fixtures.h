// Situations the tests and simulations build on the real game state.
#ifndef FIXTURES_H
#define FIXTURES_H

void reset_events() { for( int e = 0; e < EV_COUNT; e++ ) events[ e ] = 0; }

// an arena with only its border walls, nobody on it and the zone switched off
void blank_arena( int w, int h )
{
    camp_mode = false;
    set_arena( w, h );
    clear_round();
    for( int i = 0; i < MAP_CELLS; i++ ) { map[ i ] = T_WALL; hidden[ i ] = ITEM_NONE; blast_cover[ i ] = 0; }
    for( int r = 1; r < h - 1; r++ )
      for( int c = 1; c < w - 1; c++ ) map[ cell( c, r ) ] = T_EMPTY;
    player_count = 0;
    for( int i = 0; i < MAX_PLAYERS; i++ ) { human_slot[ i ] = false; players[ i ].alive = false; }
    reset_shrink();
    shrink_at = FOREVER;
    reset_events();
    camp_keys = 0; camp_done = false; camp_lives = LIVES; camp_state = CAMP_PLAY;
}

// the arena's border and pillars, without crates
void pillar_arena( int w, int h )
{
    blank_arena( w, h );
    block_density = 0;
    init_map();
}

void story_arena( int w, int h )
{
    blank_arena( w, h );
    camp_mode = true;
}

// a player that stands still: human, but nobody presses anything
Player* put_player( int id, int c, int r )
{
    new_player( id, c, r );
    players[ id ].human = true;
    if( id >= player_count ) player_count = id + 1;
    return &players[ id ];
}

Player* put_bot( int id, int c, int r )
{
    Player* p = put_player( id, c, r );
    p->human = false;
    return p;
}

Player* put_hero( int id, int c, int r )
{
    Player* p = put_player( id, c, r );
    p->team = 1;
    return p;
}

void put_boss( int kind, int c, int r, int hp )
{
    boss.kind = kind; boss.c = c; boss.r = r; boss.x = gpx( c ); boss.y = gpy( r );
    boss.dx = 0; boss.dy = 0; boss.hp = hp; boss.max_hp = hp;
    boss.t = 1; boss.inv = 0; boss.warn = false; boss.roar = 0;
}

void walk( Player* p, int dc, int dr, int frames )
{
    for( int i = 0; i < frames; i++ ) move_player( p, dc, dr );
}

// one battle frame as update_battle runs it, starting at the top of a console frame so the
// bots get their whole cycle budget
void step_battle()
{
    end_frame();
    frame++;
    reset_events();
    update_bombs();
    update_blasts();
    update_invul_and_deaths();
    update_shrink();
    update_players();
}

void step_story()
{
    end_frame();
    frame++;
    reset_events();
    update_campaign();
}

int bombs_owned_by( int id )
{
    int n = 0;
    for( int i = 0; i < bomb_count; i++ ) if( bombs[ i ].owner == id ) n++;
    return n;
}

int alive_sheep()
{
    int n = 0;
    for( int i = 0; i < MAX_SHEEP; i++ ) if( sheep[ i ].alive ) n++;
    return n;
}

// a hero bot presses B while the dragon lives (the bots in src/ never let a sheep go)
void heroes_let_sheep_go()
{
    if( !dragon_alive() ) return;
    for( int i = 0; i < MAX_SHEEP; i++ ) if( sheep[ i ].alive && sheep[ i ].state == SHEEP_LIT ) return;
    for( int i = 0; i < player_count; i++ )
    {
        Player* p = &players[ i ];
        if( p->alive && p->team == 1 && !p->human && p->sheep > 0 ) { launch_sheep( p ); return; }
    }
}

#endif
