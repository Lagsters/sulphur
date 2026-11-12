// The arena: walls, crates, start corners and the closing zone.
#ifndef ARENA_H
#define ARENA_H

#include "state.h"

int[ 4 ] DIR_X = { 0, 0, -1, 1 };
int[ 4 ] DIR_Y = { -1, 1, 0, 0 };

int mget( int c, int r )
{
    if( c < 0 || r < 0 || c >= W || r >= H ) return T_WALL;
    return map[ cell( c, r ) ];
}

void mset( int c, int r, int v )
{
    if( c < 0 || r < 0 || c >= W || r >= H ) return;
    map[ cell( c, r ) ] = v;
}

int gpx( int c ) { return ( c - 1 ) * TILE; }
int gpy( int r ) { return r * TILE; }
// floor division: a hitbox poking left of column 1 (x < 0) is in the wall column 0
int floor_div( int v, int d ) { if( v >= 0 ) return v / d; return -( ( -v + d - 1 ) / d ); }
int gcol( int x ) { return floor_div( x, TILE ) + 1; }
int grow( int y ) { return floor_div( y, TILE ); }

// the arena and its four start corners; the campaign uses wider or taller ones
void set_arena( int w, int h )
{
    W = w; H = h;
    start_c[ 0 ] = 1;     start_r[ 0 ] = 1;
    start_c[ 1 ] = W - 2; start_r[ 1 ] = 1;
    start_c[ 2 ] = 1;     start_r[ 2 ] = H - 2;
    start_c[ 3 ] = W - 2; start_r[ 3 ] = H - 2;
}

bool near_start( int c, int r )
{
    for( int i = 0; i < 4; i++ )
      if( iabs( c - start_c[ i ] ) + iabs( r - start_r[ i ] ) <= 1 ) return true;
    return false;
}

// pillars on even cells counted from both edges, so the map is mirrored left-right and
// top-bottom (counting from one edge only made the right corners win more often)
bool is_pillar( int c, int r )
{
    bool row = ( r < H / 2 - 1 && r % 2 == 0 ) || ( r > H / 2 && ( H - 1 - r ) % 2 == 0 );
    bool col = ( c < W / 2 && c % 2 == 0 ) || ( c >= W / 2 && ( W - 1 - c ) % 2 == 0 );
    return row && col;
}

void init_map()
{
    for( int i = 0; i < MAP_CELLS; i++ ) { map[ i ] = T_WALL; hidden[ i ] = ITEM_NONE; blast_cover[ i ] = 0; bomb_cover[ i ] = 0; }
    for( int r = 0; r < H; r++ )
      for( int c = 0; c < W; c++ )
      {
          int t = T_EMPTY;
          if( r == 0 || r == H - 1 || c == 0 || c == W - 1 || is_pillar( c, r ) ) t = T_WALL;
          else if( rnd( 100 ) < block_density && !near_start( c, r ) ) t = T_BLOCK;
          map[ cell( c, r ) ] = t;
      }
}

// a random but fixed order of the four directions, the tie-break of one bot for a round
void shuffle_dirs( int* order )
{
    for( int i = 0; i < 4; i++ ) order[ i ] = i;
    for( int i = 3; i > 0; i-- )
    {
        int j = rnd( i + 1 );
        int t = order[ i ]; order[ i ] = order[ j ]; order[ j ] = t;
    }
}

// ---------------------------------------------------------------------------
//   closing zone: every SHRINK_CYCLE frames after SHRINK_DELAY one step of the
//   outline blinks for SHRINK_WARN frames, then turns to wall all at once
// ---------------------------------------------------------------------------

int zone_x0, zone_y0, zone_x1, zone_y1;
int zone_cycle, zone_steps, shrink_at, round_frames;
int zone_done_at;           // frame the zone stopped at its middle strip, -1 while it moves

void reset_shrink()
{
    zone_cycle = SHRINK_CYCLE;
    zone_steps = 0;
    zone_x0 = 1; zone_y0 = 1; zone_x1 = W - 2; zone_y1 = H - 2;
    shrink_at = SHRINK_DELAY + SHRINK_CYCLE - 1;
    round_frames = 0;
    zone_done_at = -1;
}

// a box only ZONE_MIN_H tall loses its two side columns per step, a taller one its outline
bool zone_thin( int y0, int y1 ) { return y1 - y0 + 1 <= ZONE_MIN_H; }

int[ 400 ] step_c, step_r;
int step_count;

// open cells of the step with this box
void collect_step( int x0, int y0, int x1, int y1 )
{
    step_count = 0;
    for( int r = y0; r <= y1; r++ )
    {
        if( mget( x0, r ) != T_WALL ) { step_c[ step_count ] = x0; step_r[ step_count ] = r; step_count++; }
        if( x1 > x0 && mget( x1, r ) != T_WALL ) { step_c[ step_count ] = x1; step_r[ step_count ] = r; step_count++; }
    }
    if( zone_thin( y0, y1 ) ) return;
    for( int c = x0 + 1; c <= x1 - 1; c++ )
    {
        if( mget( c, y0 ) != T_WALL ) { step_c[ step_count ] = c; step_r[ step_count ] = y0; step_count++; }
        if( y1 > y0 && mget( c, y1 ) != T_WALL ) { step_c[ step_count ] = c; step_r[ step_count ] = y1; step_count++; }
    }
}

void advance_zone()
{
    bool sides = zone_thin( zone_y0, zone_y1 );
    zone_x0++; zone_x1--;
    if( !sides ) { zone_y0++; zone_y1--; }
}

// the next step with open cells into step_c/step_r, skipping steps without any; false once
// only the middle strip is left (it never closes, so the last step never kills everyone)
bool next_step_cells()
{
    while( !( zone_thin( zone_y0, zone_y1 ) && zone_x1 - zone_x0 + 1 <= ZONE_MIN_W ) )
    {
        collect_step( zone_x0, zone_y0, zone_x1, zone_y1 );
        if( step_count > 0 ) return true;
        advance_zone();
    }
    return false;
}

// frames left before the blinking step closes, or -1 when nothing blinks; its cells are
// left in step_c/step_r
int shrink_closing()
{
    int left = shrink_at - round_frames;
    if( left > SHRINK_WARN ) return -1;
    if( !next_step_cells() ) return -1;
    return left;
}

#endif
