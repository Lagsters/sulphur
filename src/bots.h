// Bots, ported from BlasTIC: a danger map, a timed escape planner that knows chain
// reactions, bombs only where the bot can still get away, traps, items and wandering.
// The console has 250 000 cycles a frame, so a bot plans its next step only when it reaches
// the middle of a cell (or its way is cut), and only a few bots plan in one frame.
#ifndef BOTS_H
#define BOTS_H

#include "players.h"

#define BOT_STEP          16      // frames to cross one cell
#define BOT_PICKUP_RANGE  10
#define BOT_PLANS         2       // bots planning in one frame
#define BOT_SAFE_CHECKS   6       // bomb-safety checks one search may spend
#define FOREVER           1000000
// cycles of the frame (250 000) bots may use before planning stops; fleeing may run longer.
// Drawing takes up to ~90 000 (measured in the dragon fight) and the music ~10 000.
#define BOT_THINK_CYCLES  80000
#define BOT_FLEE_CYCLES   105000
// bats look for a hero at most once a frame, and only early in it
int bat_searches_left = 1;

bool out_of_time( int limit ) { return get_cycle_counter() > limit; }

int bot_plans_left = BOT_PLANS;

// ---------------------------------------------------------------------------
//   danger: cells burning now, every bomb's blast lines and the blinking zone step;
//   for a hero bot also monsters (and the cells next to them) and the dragon's line
// ---------------------------------------------------------------------------

int[ MAP_CELLS ] danger_mark;
int danger_stamp = 0;
int[ MAP_CELLS ] hero_danger_mark;
int hero_danger_stamp = 0;

void mark_line( int* marks, int stamp, int c, int r, int len )
{
    marks[ cell( c, r ) ] = stamp;
    for( int d = 0; d < 4; d++ )
      for( int i = 1; i <= len; i++ )
      {
          int nc = c + DIR_X[ d ] * i, nr = r + DIR_Y[ d ] * i;
          int t = mget( nc, nr );
          if( t == T_WALL ) break;
          marks[ cell( nc, nr ) ] = stamp;
          if( t == T_BLOCK ) break;
      }
}

void compute_danger()
{
    danger_stamp++;
    for( int i = 0; i < blast_count; i++ ) danger_mark[ cell( blasts[ i ].c, blasts[ i ].r ) ] = danger_stamp;
    if( shrink_closing() >= 0 )
      for( int i = 0; i < step_count; i++ ) danger_mark[ cell( step_c[ i ], step_r[ i ] ) ] = danger_stamp;
    for( int i = 0; i < bomb_count; i++ ) mark_line( danger_mark, danger_stamp, bombs[ i ].c, bombs[ i ].r, bombs[ i ].len );
    if( !camp_mode ) return;
    hero_danger_stamp++;
    for( int i = 0; i < monster_count; i++ )
    {
        Monster* m = &monsters[ i ];
        hero_danger_mark[ cell( m->c, m->r ) ] = hero_danger_stamp;
        for( int d = 0; d < 4; d++ )
          hero_danger_mark[ cell( clampi( m->c + DIR_X[ d ], 0, W - 1 ), clampi( m->r + DIR_Y[ d ], 0, H - 1 ) ) ] = hero_danger_stamp;
    }
    if( boss.kind != BOSS_NONE && boss.hp > 0 )
    {
        for( int dc = 0; dc < 2; dc++ ) for( int dr = 0; dr < 2; dr++ )
          hero_danger_mark[ cell( boss.c + dc, boss.r + dr ) ] = hero_danger_stamp;
        if( boss.warn )
        {
            if( boss.warn_row ) { for( int c = 1; c < W - 1; c++ ) hero_danger_mark[ cell( c, boss.warn_r ) ] = hero_danger_stamp; }
            else { for( int r = 1; r < H - 1; r++ ) hero_danger_mark[ cell( boss.warn_c, r ) ] = hero_danger_stamp; }
        }
    }
}

bool dangerous_k( Player* p, int k )
{
    if( danger_mark[ k ] == danger_stamp ) return true;
    return camp_mode && p->team == 1 && hero_danger_mark[ k ] == hero_danger_stamp;
}

bool dangerous( Player* p, int c, int r ) { return dangerous_k( p, cell( c, r ) ); }

// by cell index: the searches visit every cell, and a call per check costs more than the check
bool walkable_k( int k ) { return map[ k ] == T_EMPTY && bomb_cover[ k ] == 0; }

bool bot_passable( int c, int r )
{
    if( c < 0 || r < 0 || c >= W || r >= H ) return false;
    return walkable_k( cell( c, r ) );
}

// a step in direction d is this many cells in the map arrays; the searches never leave the
// arena, whose border is wall
int[ 4 ] DIR_K = { -MAP_STRIDE, MAP_STRIDE, -1, 1 };

bool step_ok( Player* p, int dx, int dy )
{
    int nc = p->c + dx, nr = p->r + dy;
    return bot_passable( nc, nr ) && !dangerous( p, nc, nr );
}

// ---------------------------------------------------------------------------
//   fire times: frames until each cell starts burning and until it stops; a bomb hit by
//   an earlier blast goes off at that moment (chain reactions); one extra bomb may be added
// ---------------------------------------------------------------------------

int[ MAP_CELLS ] ft_from, ft_to, ft_mark;
int ft_stamp = 0;
int[ MAX_BOMB_LIST + 1 ] fb_c, fb_r, fb_len, fb_t;
int fb_n = 0;

bool ft_has( int k ) { return ft_mark[ k ] == ft_stamp; }

void ft_burn( int k, int s )
{
    if( !ft_has( k ) ) { ft_mark[ k ] = ft_stamp; ft_from[ k ] = s; ft_to[ k ] = s + BLAST_TIME; return; }
    if( s < ft_from[ k ] ) ft_from[ k ] = s;
    if( s + BLAST_TIME > ft_to[ k ] ) ft_to[ k ] = s + BLAST_TIME;
}

int[ 32 ] line_cells;
int line_n = 0;

void bomb_cells( int c, int r, int len )
{
    line_n = 0;
    line_cells[ line_n ] = cell( c, r ); line_n++;
    for( int d = 0; d < 4; d++ )
      for( int i = 1; i <= len; i++ )
      {
          int nc = c + DIR_X[ d ] * i, nr = r + DIR_Y[ d ] * i;
          int t = mget( nc, nr );
          if( t == T_WALL ) break;
          line_cells[ line_n ] = cell( nc, nr ); line_n++;
          if( t == T_BLOCK ) break;
      }
}

void fire_times( bool extra, int ec, int er, int elen )
{
    ft_stamp++;
    fb_n = 0;
    for( int i = 0; i < bomb_count; i++ )
    {
        fb_c[ fb_n ] = bombs[ i ].c; fb_r[ fb_n ] = bombs[ i ].r; fb_len[ fb_n ] = bombs[ i ].len; fb_t[ fb_n ] = bombs[ i ].t;
        fb_n++;
    }
    if( extra ) { fb_c[ fb_n ] = ec; fb_r[ fb_n ] = er; fb_len[ fb_n ] = elen; fb_t[ fb_n ] = BOMB_TIMER; fb_n++; }
    for( int i = 0; i < blast_count; i++ )
    {
        int k = cell( blasts[ i ].c, blasts[ i ].r );
        if( !ft_has( k ) ) { ft_mark[ k ] = ft_stamp; ft_from[ k ] = 0; ft_to[ k ] = blasts[ i ].t; }
        else { ft_from[ k ] = 0; ft_to[ k ] = imax( ft_to[ k ], blasts[ i ].t ); }
    }
    int left = shrink_closing();
    if( left >= 0 )
      for( int i = 0; i < step_count; i++ )
      {
          int k = cell( step_c[ i ], step_r[ i ] );
          if( !ft_has( k ) ) { ft_mark[ k ] = ft_stamp; ft_from[ k ] = left; }
          else ft_from[ k ] = imin( ft_from[ k ], left );
          ft_to[ k ] = FOREVER;
      }
    for( int i = 0; i < fb_n; i++ )
    {
        int k = cell( fb_c[ i ], fb_r[ i ] );
        if( ft_has( k ) && ft_from[ k ] < fb_t[ i ] ) fb_t[ i ] = ft_from[ k ];
    }
    bool changed = true;
    while( changed )
    {
        changed = false;
        for( int i = 0; i < fb_n; i++ )
        {
            int t = fb_t[ i ];
            bomb_cells( fb_c[ i ], fb_r[ i ], fb_len[ i ] );
            for( int j = 0; j < line_n; j++ )
            {
                int k = line_cells[ j ];
                if( !ft_has( k ) || t < ft_from[ k ] || ft_to[ k ] < t + BLAST_TIME ) { ft_burn( k, t ); changed = true; }
                for( int o = 0; o < fb_n; o++ )
                  if( cell( fb_c[ o ], fb_r[ o ] ) == k && fb_t[ o ] > t ) { fb_t[ o ] = t; changed = true; }
            }
        }
    }
}

// ---------------------------------------------------------------------------
//   searches; each returns the direction of the first step (0..3) or -1, and leaves the
//   end of the path in path_end and its length in path_len
// ---------------------------------------------------------------------------

int[ MAP_CELLS ] bq, bpar, bdep, bseen;
int bstamp = 0;
// the escape search runs inside the goal tests of the others, so it has arrays of its own
int[ MAP_CELLS ] eq, epar, edep, eseen;
int estamp = 0;
int path_end = 0, path_len = 0;

int first_dir( int* parent, int start, int k )
{
    while( parent[ k ] != start ) k = parent[ k ];
    int dc = k % MAP_STRIDE - start % MAP_STRIDE, dr = k / MAP_STRIDE - start / MAP_STRIDE;
    for( int d = 0; d < 4; d++ ) if( DIR_X[ d ] == dc && DIR_Y[ d ] == dr ) return d;
    return -1;
}

bool burning( int k, int a ) { return ft_has( k ) && ft_from[ k ] <= a + BOT_STEP / 2 && ft_to[ k ] > a; }
bool safe_end( int k, int a ) { return !ft_has( k ) || ft_to[ k ] <= a; }

// shortest way from (sc,sr) that never steps into a cell while it burns and ends on a cell
// that is not burning when the bot gets there; uses the last fire_times()
int escape_dir( int* order, int sc, int sr, int blocked )
{
    estamp++;
    int start = cell( sc, sr );
    int head = 0, tail = 0;
    eq[ tail ] = start; tail++; eseen[ start ] = estamp; edep[ start ] = 0;
    while( head < tail )
    {
        int k = eq[ head ]; head++;
        int d0 = edep[ k ];
        if( d0 > 0 && safe_end( k, d0 * BOT_STEP ) )
        {
            path_end = k; path_len = d0;
            return first_dir( epar, start, k );
        }
        for( int i = 0; i < 4; i++ )
        {
            int nk = k + DIR_K[ order[ i ] ];
            if( eseen[ nk ] == estamp || nk == blocked || !walkable_k( nk ) || burning( nk, ( d0 + 1 ) * BOT_STEP ) ) continue;
            eseen[ nk ] = estamp; epar[ nk ] = k; edep[ nk ] = d0 + 1;
            eq[ tail ] = nk; tail++;
        }
    }
    return -1;
}

#define OPEN_ANY   0      // every walkable cell
#define OPEN_SAFE  1      // walkable and out of danger for this player

// breadth-first search over the open cells to the nearest cell (not the start) accepted by
// is_goal
int path_dir( Player* p, int open, bool( Player*, int, int )* is_goal )
{
    bstamp++;
    int start = cell( p->c, p->r );
    int head = 0, tail = 0;
    bq[ tail ] = start; tail++; bseen[ start ] = bstamp; bdep[ start ] = 0;
    while( head < tail )
    {
        if( out_of_time( BOT_FLEE_CYCLES ) ) return -1;
        int k = bq[ head ]; head++;
        if( k != start && is_goal( p, k % MAP_STRIDE, k / MAP_STRIDE ) )
        {
            path_end = k; path_len = bdep[ k ];
            return first_dir( bpar, start, k );
        }
        for( int i = 0; i < 4; i++ )
        {
            int nk = k + DIR_K[ p->bot_order[ i ] ];
            if( bseen[ nk ] == bstamp || !walkable_k( nk ) ) continue;
            if( open == OPEN_SAFE && dangerous_k( p, nk ) ) continue;
            bseen[ nk ] = bstamp; bpar[ nk ] = k; bdep[ nk ] = bdep[ k ] + 1;
            bq[ tail ] = nk; tail++;
        }
    }
    return -1;
}

// ---------------------------------------------------------------------------
//   what a bot wants
// ---------------------------------------------------------------------------

// a living enemy of p on (c,r): another team's player, or for the heroes a monster or the boss
bool foe_at( Player* p, int c, int r )
{
    for( int i = 0; i < player_count; i++ )
    {
        Player* o = &players[ i ];
        if( o->alive && o->team != p->team && o->c == c && o->r == r ) return true;
    }
    if( p->team != 1 || !camp_mode ) return false;
    for( int i = 0; i < monster_count; i++ ) if( monsters[ i ].c == c && monsters[ i ].r == r ) return true;
    // the dragon only fears sheep: a bot does not waste its bombs on it
    return boss.kind != BOSS_NONE && boss.kind != BOSS_DRAGON && boss.hp > 0
           && c >= boss.c && c <= boss.c + 1 && r >= boss.r && r <= boss.r + 1;
}

// a living enemy stands in the blast line of a bomb laid on (c,r)
bool enemy_spot( Player* p, int c, int r )
{
    for( int d = 0; d < 4; d++ )
      for( int i = 1; i <= p->stat_len; i++ )
      {
          int nc = c + DIR_X[ d ] * i, nr = r + DIR_Y[ d ] * i;
          if( mget( nc, nr ) != T_EMPTY ) break;
          if( foe_at( p, nc, nr ) ) return true;
      }
    return false;
}

bool target_spot( Player* p, int c, int r )
{
    for( int d = 0; d < 4; d++ ) if( mget( c + DIR_X[ d ], r + DIR_Y[ d ] ) == T_BLOCK ) return true;
    return enemy_spot( p, c, r );
}

int safe_checks_left = 0;

// a bomb laid on (c,r) still leaves the bot a way out before it goes off
bool bomb_safe( Player* p, int c, int r )
{
    safe_checks_left--;
    if( out_of_time( BOT_THINK_CYCLES ) ) return false;
    fire_times( true, c, r, p->stat_len );
    return escape_dir( p->bot_order, c, r, -1 ) >= 0;
}

// a bomb laid on (c,r) is a trap when the bot can leave its blast but an enemy in it
// cannot, the bomb itself blocking that enemy's way
bool trap_spot( Player* p, int c, int r )
{
    if( !enemy_spot( p, c, r ) ) return false;
    if( !bomb_safe( p, c, r ) ) return false;
    int blocked = cell( c, r );
    for( int i = 0; i < player_count; i++ )
    {
        Player* o = &players[ i ];
        if( !o->alive || o->team == p->team || !ft_has( cell( o->c, o->r ) ) ) continue;
        if( escape_dir( o->bot_order, o->c, o->r, blocked ) < 0 ) return true;
    }
    return false;
}

bool goal_out_of_danger( Player* p, int c, int r ) { return !dangerous( p, c, r ); }

bool goal_item( Player* p, int c, int r )
{
    for( int i = 0; i < item_count; i++ )
      if( items[ i ].c == c && items[ i ].r == r && ( p->team == 1 || !quest_item( items[ i ].kind ) ) ) return true;
    return false;
}

bool goal_trap( Player* p, int c, int r )
{
    if( safe_checks_left <= 0 ) return false;
    return trap_spot( p, c, r );
}

bool goal_enemy( Player* p, int c, int r )
{
    if( safe_checks_left <= 0 || !enemy_spot( p, c, r ) ) return false;
    return bomb_safe( p, c, r );
}

bool goal_target( Player* p, int c, int r )
{
    if( safe_checks_left <= 0 || !target_spot( p, c, r ) ) return false;
    return bomb_safe( p, c, r );
}

int item_kind_at( int c, int r )
{
    for( int i = 0; i < item_count; i++ ) if( items[ i ].c == c && items[ i ].r == r ) return items[ i ].kind;
    return ITEM_NONE;
}

// first step towards an item within BOT_PICKUP_RANGE over cells not on fire; quest items are
// worth any walk, the stage cannot be won without them
int pickup_dir( Player* p )
{
    if( item_count == 0 ) return -1;
    int d = path_dir( p, OPEN_SAFE, &goal_item );
    if( d < 0 ) return -1;
    if( path_len <= BOT_PICKUP_RANGE || quest_item( item_kind_at( path_end % MAP_STRIDE, path_end / MAP_STRIDE ) ) ) return d;
    return -1;
}

int quest_goal = 0;
bool goal_cell( Player* p, int c, int r ) { return cell( c, r ) == quest_goal; }

// for a hero: towards the safe bomb spot nearest to a sparkling crate, so it digs its way to
// the quest item instead of blowing up the closest crates
int[ MAP_CELLS ] spot_cell, spot_dist;
int quest_dir( Player* p )
{
    int[ 16 ] qc, qr;
    int qn = 0;
    for( int r = 1; r < H - 1 && qn < 16; r++ )
      for( int c = 1; c < W - 1 && qn < 16; c++ )
        if( hidden[ cell( c, r ) ] != ITEM_NONE && mget( c, r ) == T_BLOCK ) { qc[ qn ] = c; qr[ qn ] = r; qn++; }
    if( qn == 0 ) return -1;
    // flood the reachable safe cells; spots keep the flood order, so ties go to the nearer one
    // (two equal spots on opposite sides would make the bot turn back and forth)
    bstamp++;
    int start = cell( p->c, p->r );
    int head = 0, tail = 0, spots = 0;
    bq[ tail ] = start; tail++; bseen[ start ] = bstamp;
    while( head < tail )
    {
        if( out_of_time( BOT_THINK_CYCLES ) ) break;
        int k = bq[ head ]; head++;
        int c = k % MAP_STRIDE, r = k / MAP_STRIDE;
        if( target_spot( p, c, r ) )
        {
            int best = FOREVER;
            for( int i = 0; i < qn; i++ ) best = imin( best, iabs( c - qc[ i ] ) + iabs( r - qr[ i ] ) );
            spot_cell[ spots ] = k; spot_dist[ spots ] = best; spots++;
        }
        for( int i = 0; i < 4; i++ )
        {
            int nk = k + DIR_K[ i ];
            if( bseen[ nk ] == bstamp || !walkable_k( nk ) || dangerous_k( p, nk ) ) continue;
            bseen[ nk ] = bstamp;
            bq[ tail ] = nk; tail++;
        }
    }
    for( int tries = 0; tries < 3 && spots > 0; tries++ )
    {
        int pick = 0;
        for( int i = 1; i < spots; i++ ) if( spot_dist[ i ] < spot_dist[ pick ] ) pick = i;
        int k = spot_cell[ pick ];
        spot_dist[ pick ] = FOREVER + 1;
        if( !bomb_safe( p, k % MAP_STRIDE, k / MAP_STRIDE ) ) continue;
        if( k == start ) return -1;
        quest_goal = k;
        return path_dir( p, OPEN_SAFE, &goal_cell );
    }
    return -1;
}

// a random direction onto a free cell outside danger, or standing still (4)
int safe_random_dir( Player* p )
{
    for( int k = 0; k < 8; k++ )
    {
        int d = rnd( 4 );
        if( step_ok( p, DIR_X[ d ], DIR_Y[ d ] ) ) return d;
    }
    return 4;
}

void set_bot_dir( Player* p, int d )
{
    if( d < 0 || d > 3 ) { p->bot_dir_x = 0; p->bot_dir_y = 0; return; }
    p->bot_dir_x = DIR_X[ d ]; p->bot_dir_y = DIR_Y[ d ];
}

// the zone has stopped long ago and the round goes nowhere: bombs without a way out
bool desperate() { return !camp_mode && zone_done_at >= 0 && round_frames - zone_done_at > DESPERATE_AFTER; }

bool try_bomb( Player* p )
{
    if( desperate() && enemy_spot( p, p->c, p->r ) ) return place_bomb( p );
    if( !target_spot( p, p->c, p->r ) ) return false;
    safe_checks_left = 1;
    if( !bomb_safe( p, p->c, p->r ) ) return false;
    return place_bomb( p );
}

// the decision BlasTIC made every frame: flee, bomb, pick up, hunt, or wander
bool dragon_alive();
bool launch_sheep( Player* p );
bool goal_grazing_sheep( Player* p, int c, int r )
{
    for( int i = 0; i < MAX_SHEEP; i++ )
      if( sheep[ i ].alive && sheep[ i ].state == SHEEP_GRAZE && sheep[ i ].c == c && sheep[ i ].r == r ) return true;
    return false;
}

void bot_plan( Player* p )
{
    bool in_danger = dangerous( p, p->c, p->r );
    p->bot_planned = true;
    if( in_danger )
    {
        fire_times( false, 0, 0, 0 );
        int d = escape_dir( p->bot_order, p->c, p->r, -1 );
        // the timed escape knows only bombs: if it ends next to a monster or in dragon fire,
        // head for a cell outside all danger instead
        if( d < 0 || dangerous( p, path_end % MAP_STRIDE, path_end / MAP_STRIDE ) )
        {
            int e = path_dir( p, OPEN_ANY, &goal_out_of_danger );
            if( e >= 0 ) d = e;
        }
        if( d < 0 ) d = rnd( 4 );
        set_bot_dir( p, d );
        return;
    }
    // at the dragon a hero bot lets its sheep go, or hunts for one
    if( camp_mode && p->team == 1 && dragon_alive() )
    {
        if( p->sheep > 0 ) launch_sheep( p );
        int s = path_dir( p, OPEN_SAFE, &goal_grazing_sheep );
        if( s >= 0 ) { set_bot_dir( p, s ); return; }
    }
    if( try_bomb( p ) ) { set_bot_dir( p, 4 ); return; }
    int d = pickup_dir( p );
    if( d < 0 && p->bombs < p->stat_bombs )
    {
        // hunt: walk to a cell from which a bomb is safe to lay, enemies before blocks
        if( camp_mode && p->team == 1 ) { safe_checks_left = BOT_SAFE_CHECKS; d = quest_dir( p ); }
        if( d < 0 ) { safe_checks_left = BOT_SAFE_CHECKS; d = path_dir( p, OPEN_SAFE, &goal_trap ); }
        if( d < 0 ) { safe_checks_left = BOT_SAFE_CHECKS; d = path_dir( p, OPEN_SAFE, &goal_enemy ); }
        if( d < 0 ) { safe_checks_left = BOT_SAFE_CHECKS; d = path_dir( p, OPEN_SAFE, &goal_target ); }
    }
    if( d >= 0 ) { set_bot_dir( p, d ); p->bot_dir_timer = 0; return; }
    // nothing to hunt: wander in a safe direction, re-picked on a timer or when stuck
    if( p->bot_dir_timer <= 0 || !step_ok( p, p->bot_dir_x, p->bot_dir_y ) || ( p->bot_dir_x == 0 && p->bot_dir_y == 0 ) )
    {
        set_bot_dir( p, safe_random_dir( p ) );
        p->bot_dir_timer = 15 + rnd( 25 );
    }
}

// while moving, first line up with the current cell on the other axis, so a turn at a
// corner is not blocked by a wall corner
void bot_steer( Player* p, int* dc, int* dr )
{
    if( *dr != 0 && p->x != gpx( p->c ) ) { *dc = isign( gpx( p->c ) - p->x ); *dr = 0; return; }
    if( *dc != 0 && p->y != gpy( p->r ) ) { *dr = isign( gpy( p->r ) - p->y ); *dc = 0; }
}

void update_bot( Player* p )
{
    if( !p->alive ) return;
    p->bot_dir_timer--;
    bool centred = p->x == gpx( p->c ) && p->y == gpy( p->r );
    bool in_danger = dangerous( p, p->c, p->r );
    bool stuck = ( p->bot_dir_x != 0 || p->bot_dir_y != 0 ) && centred && !step_ok( p, p->bot_dir_x, p->bot_dir_y );
    bool wants = centred || stuck || ( in_danger && !p->bot_planned ) || p->bot_dir_timer < -60;
    // fleeing is planned while there is any time left; anything else only early in the frame
    int limit = pick( in_danger, BOT_FLEE_CYCLES, BOT_THINK_CYCLES );
    if( wants && bot_plans_left > 0 && !out_of_time( limit ) )
    {
        bot_plans_left--;
        bot_plan( p );
        p->bot_planned = in_danger;
        if( p->bot_dir_timer < -60 ) p->bot_dir_timer = 0;
    }
    else if( !in_danger && centred && !step_ok( p, p->bot_dir_x, p->bot_dir_y ) )
    {
        // no time to think this frame: rather wait than walk into fire
        p->bot_dir_x = 0; p->bot_dir_y = 0;
    }
    if( !in_danger ) p->bot_planned = false;
    int dc = p->bot_dir_x, dr = p->bot_dir_y;
    bot_steer( p, &dc, &dr );
    int ox = p->x, oy = p->y;
    if( dc != 0 || dr != 0 ) { p->dir_x = dc; p->dir_y = dr; }
    move_player( p, dc, dr );
    if( p->x != ox || p->y != oy ) p->walk_anim++;
    if( blast_hurts( p ) ) blast_hit( p );
}

#endif
