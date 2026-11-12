// Sulphur bombs, their blasts and chain reactions, and the items crates drop.
#ifndef BOMBS_H
#define BOMBS_H

#include "arena.h"

bool quest_item( int kind ) { return kind == ITEM_EXIT || kind == ITEM_KEY; }

void add_item( int c, int r, int kind )
{
    if( item_count >= MAX_ITEMS ) return;
    items[ item_count ].c = c;
    items[ item_count ].r = r;
    items[ item_count ].kind = kind;
    item_count++;
}

void remove_item( int i )
{
    for( int k = i; k < item_count - 1; k++ ) items[ k ] = items[ k + 1 ];
    item_count--;
}

// a blast burns the bonus lying on its cell; exit and keys survive (a stage could not be
// finished without them)
void burn_items_at( int c, int r )
{
    for( int i = item_count - 1; i >= 0; i-- )
      if( items[ i ].c == c && items[ i ].r == r && !quest_item( items[ i ].kind ) ) remove_item( i );
}

void add_blast( int c, int r, int owner, bool sheep )
{
    if( blast_count >= MAX_BLASTS ) return;
    Blast* b = &blasts[ blast_count ];
    b->c = c; b->r = r; b->t = BLAST_TIME; b->owner = owner; b->sheep = sheep;
    blast_count++;
    blast_cover[ cell( c, r ) ]++;
    burn_items_at( c, r );
}

bool is_blast( int c, int r )
{
    if( c < 0 || r < 0 || c >= W || r >= H ) return false;
    return blast_cover[ cell( c, r ) ] > 0;
}

void drop_powerup( int c, int r )
{
    int quest = hidden[ cell( c, r ) ];
    if( quest != ITEM_NONE ) { add_item( c, r, quest ); hidden[ cell( c, r ) ] = ITEM_NONE; return; }
    if( rnd( 100 ) < POWERUP_CHANCE ) add_item( c, r, ITEM_BOMB + rnd( 3 ) );
}

int bomb_at( int c, int r )
{
    for( int i = 0; i < bomb_count; i++ )
      if( bombs[ i ].c == c && bombs[ i ].r == r ) return i;
    return -1;
}

bool is_bomb( int c, int r )
{
    if( c < 0 || r < 0 || c >= W || r >= H ) return false;
    return bomb_cover[ cell( c, r ) ] > 0;
}

void add_bomb( int c, int r, int t, int len, int owner, bool sheep )
{
    if( bomb_count >= MAX_BOMB_LIST ) return;
    Bomb* b = &bombs[ bomb_count ];
    b->c = c; b->r = r; b->t = t; b->len = len; b->owner = owner; b->sheep = sheep;
    bomb_count++;
    bomb_cover[ cell( c, r ) ]++;
}

void remove_bomb( int i )
{
    bomb_cover[ cell( bombs[ i ].c, bombs[ i ].r ) ]--;
    for( int k = i; k < bomb_count - 1; k++ ) bombs[ k ] = bombs[ k + 1 ];
    bomb_count--;
}

// cells covered by the bomb going off now are stamped in hit_stamp, so bombs on them follow
int[ MAP_CELLS ] hit_mark;
int hit_stamp = 0;

void explode( Bomb* b )
{
    raise_event( pick( b->sheep, EV_SHEEP_BOOM, EV_BOOM ) );
    add_blast( b->c, b->r, b->owner, b->sheep );
    hit_mark[ cell( b->c, b->r ) ] = hit_stamp;
    for( int d = 0; d < 4; d++ )
      for( int i = 1; i <= b->len; i++ )
      {
          int nc = b->c + DIR_X[ d ] * i, nr = b->r + DIR_Y[ d ] * i;
          int t = mget( nc, nr );
          if( t == T_WALL ) break;
          add_blast( nc, nr, b->owner, b->sheep );
          hit_mark[ cell( nc, nr ) ] = hit_stamp;
          if( t == T_BLOCK ) { mset( nc, nr, T_EMPTY ); drop_powerup( nc, nr ); break; }
      }
    // a sheep's blast belongs to its hero (no friendly fire) but was never one of his bombs
    if( b->owner >= 0 && !b->sheep ) players[ b->owner ].bombs = imax( 0, players[ b->owner ].bombs - 1 );
}

// bombs covered by a blast go off in the same tick, until no new ones are hit
Bomb[ MAX_BOMB_LIST ] going;
void update_bombs()
{
    int n = 0;
    for( int i = 0; i < bomb_count; i++ ) bombs[ i ].t--;
    for( int i = bomb_count - 1; i >= 0; i-- )
      if( bombs[ i ].t <= 0 ) { going[ n ] = bombs[ i ]; n++; remove_bomb( i ); }
    for( int k = 0; k < n; k++ )
    {
        hit_stamp++;
        explode( &going[ k ] );
        for( int i = bomb_count - 1; i >= 0; i-- )
          if( hit_mark[ cell( bombs[ i ].c, bombs[ i ].r ) ] == hit_stamp )
          {
              going[ n ] = bombs[ i ]; n++;
              remove_bomb( i );
          }
    }
}

void update_blasts()
{
    int keep = 0;
    for( int i = 0; i < blast_count; i++ )
    {
        Blast* b = &blasts[ i ];
        b->t--;
        if( b->t > 0 ) { blasts[ keep ] = *b; keep++; }
        else blast_cover[ cell( b->c, b->r ) ]--;
    }
    blast_count = keep;
}

#endif
