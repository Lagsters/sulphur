// Players: walking with the corner assist, bombs, items, death.
#ifndef PLAYERS_H
#define PLAYERS_H

#include "bombs.h"

void new_player( int id, int c, int r )
{
    Player* p = &players[ id ];
    p->c = c; p->r = r; p->x = gpx( c ); p->y = gpy( r );
    p->alive = true;
    p->stat_bombs = MAX_BOMBS; p->stat_len = BLAST_LEN;
    p->bombs = 0;
    p->shield = false;
    p->invul = 0;
    p->id = id;
    p->team = id;
    p->human = human_slot[ id ];
    p->pad = id;
    p->dir_x = 0; p->dir_y = 1;
    p->walk_anim = 0;
    p->death_t = 0;
    p->sheep = 0;
    p->bot_dir_x = 0; p->bot_dir_y = 0;
    shuffle_dirs( p->bot_order );
    p->bot_dir_timer = 0;
    p->bot_planned = false;
    p->look = 2 + id;
}

void hero_got_quest( int kind );

void collect_item( Player* p )
{
    for( int i = 0; i < item_count; i++ )
    {
        Item* it = &items[ i ];
        if( it->c != p->c || it->r != p->r ) continue;
        if( quest_item( it->kind ) && p->team != 1 ) continue;
        if( it->kind == ITEM_BOMB ) p->stat_bombs = imin( BOMB_CAP, p->stat_bombs + 1 );
        else if( it->kind == ITEM_RANGE ) p->stat_len = imin( LEN_CAP, p->stat_len + 1 );
        else if( it->kind == ITEM_SHIELD ) p->shield = true;
        else hero_got_quest( it->kind );
        remove_item( i );
        raise_event( EV_PICKUP );
        return;
    }
}

// cells where the hitbox at (x,y) lies; a player may stand in his own bomb until he leaves it
bool own_bomb_under( Player* p, int c, int r )
{
    int margin = 1;
    int x0 = gcol( p->x + margin ), x1 = gcol( p->x + TILE - margin - 1 );
    int y0 = grow( p->y + margin ), y1 = grow( p->y + TILE - margin - 1 );
    return c >= x0 && c <= x1 && r >= y0 && r <= y1;
}

bool blocked_at( Player* p, int x, int y )
{
    int margin = 1;
    int[ 4 ] cs, rs;
    cs[ 0 ] = gcol( x + margin );            rs[ 0 ] = grow( y + margin );
    cs[ 1 ] = gcol( x + TILE - margin - 1 ); rs[ 1 ] = grow( y + margin );
    cs[ 2 ] = gcol( x + margin );            rs[ 2 ] = grow( y + TILE - margin - 1 );
    cs[ 3 ] = gcol( x + TILE - margin - 1 ); rs[ 3 ] = grow( y + TILE - margin - 1 );
    for( int k = 0; k < 4; k++ )
    {
        int t = mget( cs[ k ], rs[ k ] );
        if( t == T_WALL || t == T_BLOCK ) return true;
        int b = bomb_at( cs[ k ], rs[ k ] );
        if( b >= 0 && !( bombs[ b ].owner == p->id && own_bomb_under( p, cs[ k ], rs[ k ] ) ) ) return true;
    }
    return false;
}

// corner assist: off the row (column) axis, slide toward the row whose next cell in the
// pressed direction is open, the nearer one first; it also centres the player while walking
int assist_y( Player* p, int nx )
{
    int pos = p->y;
    int a = pos - pos % TILE;
    if( pos == a ) return pos;
    int near = a, far = a + TILE;
    if( pos - a > TILE / 2 ) { near = a + TILE; far = a; }
    for( int k = 0; k < 2; k++ )
    {
        int t = pick( k == 0, near, far );
        if( !blocked_at( p, nx, t ) )
        {
            int s = pick( t > pos, SPEED, -SPEED );
            if( !blocked_at( p, p->x, pos + s ) ) return pos + s;
            return pos;
        }
    }
    return pos;
}

int assist_x( Player* p, int ny )
{
    int pos = p->x;
    int a = pos - pos % TILE;
    if( pos == a ) return pos;
    int near = a, far = a + TILE;
    if( pos - a > TILE / 2 ) { near = a + TILE; far = a; }
    for( int k = 0; k < 2; k++ )
    {
        int t = pick( k == 0, near, far );
        if( !blocked_at( p, t, ny ) )
        {
            int s = pick( t > pos, SPEED, -SPEED );
            if( !blocked_at( p, pos + s, p->y ) ) return pos + s;
            return pos;
        }
    }
    return pos;
}

void move_player( Player* p, int dc, int dr )
{
    int nx = p->x + dc * SPEED, ny = p->y + dr * SPEED;
    bool hx = !blocked_at( p, nx, p->y );
    bool hy = !blocked_at( p, p->x, ny );
    if( hx ) p->x = nx;
    if( hy ) p->y = ny;
    if( dc != 0 ) p->y = assist_y( p, nx );
    if( dr != 0 ) p->x = assist_x( p, ny );
    p->c = gcol( p->x + TILE / 2 );
    p->r = grow( p->y + TILE / 2 );
    collect_item( p );
}

bool place_bomb( Player* p )
{
    if( p->bombs >= p->stat_bombs ) return false;
    int bc = gcol( p->x + TILE / 2 ), br = grow( p->y + TILE / 2 );
    if( is_bomb( bc, br ) ) return false;
    add_bomb( bc, br, BOMB_TIMER, p->stat_len, p->id, false );
    p->bombs++;
    raise_event( EV_BOMB );
    return true;
}

void kill_player( Player* p )
{
    p->alive = false;
    p->death_t = DEATH_TIME;
    raise_event( EV_DEATH );
}

// a blast on p's cell hurts p, except in the campaign one made by a fellow hero's bomb
bool blast_hurts( Player* p )
{
    if( !is_blast( p->c, p->r ) ) return false;
    for( int i = 0; i < blast_count; i++ )
    {
        Blast* b = &blasts[ i ];
        if( b->c != p->c || b->r != p->r ) continue;
        int o = b->owner;
        if( camp_mode && o >= 0 && o != p->id && players[ o ].team == p->team ) continue;
        return true;
    }
    return false;
}

void blast_hit( Player* p )
{
    if( !p->alive || p->invul > 0 ) return;
    if( p->shield )
    {
        p->shield = false;
        p->invul = SHIELD_INVUL;
        raise_event( EV_SHIELD );
        return;
    }
    kill_player( p );
}

void update_invul_and_deaths()
{
    for( int i = 0; i < player_count; i++ )
    {
        if( players[ i ].invul > 0 ) players[ i ].invul--;
        if( players[ i ].death_t > 0 ) players[ i ].death_t--;
    }
}

int count_alive( int* last )
{
    int n = 0;
    *last = -1;
    for( int i = 0; i < player_count; i++ )
      if( players[ i ].alive ) { n++; *last = i; }
    return n;
}

#endif
