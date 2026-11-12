// Story: Dratewka the shoemaker, sulphur bombs and the dragon of Krakow. Three chapters of
// ten stages; every fifth stage is a boss. In the last chapter sheep stuffed with sulphur
// roam the stages: caught, a sheep is carried like an extra bomb, and only a sheep let go at
// the dragon can hurt it.
#ifndef CAMPAIGN_H
#define CAMPAIGN_H

#include "controls.h"

#define CHAPTERS       3
#define CHAPTER_LEN    10
#define STAGE_COUNT    30

#define GOAL_EXIT      0
#define GOAL_ENEMIES   1
#define GOAL_KEYS      2
#define GOAL_SURVIVE   3
#define GOAL_BOSS      4

#define SCROLL_NONE    0
#define SCROLL_WIDE    1
#define SCROLL_TALL    2

#define SURVIVE_STEPS  5
#define SHEEP_CAP      3
#define SHEEP_FUSE     420     // frames a lit sheep runs before it goes off on its own
#define SHEEP_RESPAWN  300
#define SHEEP_STAMINA  180     // frames a sheep can flee before it must stop for breath
#define SHEEP_REST     90
#define DRAGON_HP      3       // sheep it takes
#define LIVES          3

struct StageDef
{
    int chapter, goal, density, dwarves, bats, skeletons, boss, scroll, boss_hp, sheep;
};

StageDef stage;
int camp_stage = 1;
int camp_lives = LIVES;
int camp_tries = 0;
bool camp_coop = false;
int[ 2 ] camp_bombs, camp_len, camp_sheep;     // what each hero carries between stages
int sheep_respawn = 0;

int chapter_of( int n ) { return ( n - 1 ) / CHAPTER_LEN + 1; }

void stage_def( int n, StageDef* s )
{
    int ch = chapter_of( n ), i = ( n - 1 ) % CHAPTER_LEN + 1;
    s->chapter = ch;
    s->boss = BOSS_NONE;
    if( i == CHAPTER_LEN )
    {
        if( ch == 1 ) s->boss = BOSS_UTOPIEC; else if( ch == 2 ) s->boss = BOSS_JAGA; else s->boss = BOSS_DRAGON;
    }
    else if( i == 5 )
    {
        if( ch == 3 ) s->boss = BOSS_JAGA; else s->boss = BOSS_UTOPIEC;
    }
    bool foes = s->boss == BOSS_NONE;
    s->goal = pick( foes, ( n - 1 ) % 4, GOAL_BOSS );
    s->density = 30 + 5 * ( n % 3 );
    s->dwarves = pick( foes, imin( 6, 2 + n / 5 ), 0 );
    s->bats = pick( foes && ch >= 2, imin( 5, 1 + ( n - 11 ) / 5 ), 0 );
    s->skeletons = pick( foes && ch >= 3, imin( 3, 1 + ( n - 21 ) / 4 ), 0 );
    s->scroll = pick( n % 3 == 0, SCROLL_WIDE, pick( n % 3 == 1, SCROLL_TALL, SCROLL_NONE ) );
    s->boss_hp = 0;
    if( s->boss == BOSS_DRAGON ) s->boss_hp = DRAGON_HP;
    else if( s->boss != BOSS_NONE ) s->boss_hp = 3 + ch - 1 - pick( i == 5, 1, 0 );
    // sheep only in the last chapter: one to catch on a stage, two at the dragon
    s->sheep = 0;
    if( ch == 3 ) s->sheep = pick( s->boss == BOSS_DRAGON, 2, 1 );
}

// ---------------------------------------------------------------------------
//   cells far from the heroes' corner, in random order
// ---------------------------------------------------------------------------

int[ MAP_CELLS ] far_list;
int far_n = 0;

void far_cells( int want_tile, int min_dist )
{
    far_n = 0;
    for( int r = 1; r < H - 1; r++ )
      for( int c = 1; c < W - 1; c++ )
        if( mget( c, r ) == want_tile && iabs( c - start_c[ 0 ] ) + iabs( r - start_r[ 0 ] ) >= min_dist )
        { far_list[ far_n ] = cell( c, r ); far_n++; }
    for( int i = far_n - 1; i > 0; i-- )
    {
        int j = rnd( i + 1 );
        int t = far_list[ i ]; far_list[ i ] = far_list[ j ]; far_list[ j ] = t;
    }
}

// a free cell outside every blast, bomb, monster and hero, far from the heroes, or -1
int pop_far_free()
{
    while( far_n > 0 )
    {
        far_n--;
        int k = far_list[ far_n ];
        int c = k % MAP_STRIDE, r = k / MAP_STRIDE;
        if( mget( c, r ) == T_EMPTY && !is_bomb( c, r ) && !is_blast( c, r ) ) return k;
    }
    return -1;
}

// items the goal needs, under crates when there are enough of them, else on the floor
void hide_items( int kind, int n )
{
    far_cells( T_BLOCK, ( W + H ) / 4 );
    int i = 0;
    while( i < n && far_n > 0 )
    {
        far_n--;
        if( hidden[ far_list[ far_n ] ] != ITEM_NONE ) continue;
        hidden[ far_list[ far_n ] ] = kind;
        i++;
    }
    if( i == n ) return;
    far_cells( T_EMPTY, ( W + H ) / 4 );
    for( ; i < n; i++ )
    {
        int k = pop_far_free();
        if( k >= 0 ) add_item( k % MAP_STRIDE, k / MAP_STRIDE, kind );
    }
}

void hero_got_quest( int kind )
{
    if( kind == ITEM_KEY ) camp_keys++;
    else if( kind == ITEM_EXIT ) camp_done = true;
}

void spawn_monster( int kind, int k )
{
    if( monster_count >= MAX_MONSTERS || k < 0 ) return;
    Monster* m = &monsters[ monster_count ];
    m->kind = kind; m->c = k % MAP_STRIDE; m->r = k / MAP_STRIDE;
    m->x = gpx( m->c ); m->y = gpy( m->r ); m->dx = 0; m->dy = 0;
    monster_count++;
}

// ---------------------------------------------------------------------------
//   sheep
// ---------------------------------------------------------------------------

bool spawn_sheep( int k )
{
    if( k < 0 ) return false;
    for( int i = 0; i < MAX_SHEEP; i++ )
    {
        Sheep* s = &sheep[ i ];
        if( s->alive ) continue;
        s->alive = true; s->state = SHEEP_GRAZE;
        s->c = k % MAP_STRIDE; s->r = k / MAP_STRIDE; s->x = gpx( s->c ); s->y = gpy( s->r );
        s->dx = 0; s->dy = 0; s->t = 60; s->run = 0; s->owner = OWNER_NONE;
        return true;
    }
    return false;
}

void spawn_sheep_far()
{
    far_cells( T_EMPTY, ( W + H ) / 3 );
    spawn_sheep( pop_far_free() );
}

// a sheep in a blast goes off: sulphur is sulphur (a closing wall only crushes it)
void sheep_goes_off( Sheep* s )
{
    s->alive = false;
    add_bomb( s->c, s->r, 1, 3, s->owner, true );
}

void kill_sheep_at( int c, int r )
{
    for( int i = 0; i < MAX_SHEEP; i++ )
      if( sheep[ i ].alive && sheep[ i ].c == c && sheep[ i ].r == r ) sheep[ i ].alive = false;
}

bool dragon_alive() { return boss.kind == BOSS_DRAGON && boss.hp > 0; }

bool boss_covers( int c, int r )
{
    return c >= boss.c && c <= boss.c + 1 && r >= boss.r && r <= boss.r + 1;
}

// a lit sheep can only be let go at the dragon: elsewhere it is saved for it
bool launch_sheep( Player* p )
{
    if( !camp_mode || p->sheep <= 0 || !dragon_alive() ) return false;
    for( int i = 0; i < MAX_SHEEP; i++ )
    {
        Sheep* s = &sheep[ i ];
        if( s->alive ) continue;
        s->alive = true; s->state = SHEEP_LIT;
        s->c = p->c; s->r = p->r; s->x = gpx( p->c ); s->y = gpy( p->r );
        s->dx = 0; s->dy = 0; s->t = SHEEP_FUSE; s->run = 0; s->owner = p->id;
        p->sheep--;
        raise_event( EV_FIRE );
        return true;
    }
    return false;
}

int nearest_hero_dist( int c, int r )
{
    int best = FOREVER;
    for( int i = 0; i < player_count; i++ )
      if( players[ i ].alive && players[ i ].team == 1 )
        best = imin( best, iabs( players[ i ].c - c ) + iabs( players[ i ].r - r ) );
    return best;
}

bool sheep_open( int c, int r )
{
    if( !bot_passable( c, r ) || is_blast( c, r ) || danger_mark[ cell( c, r ) ] == danger_stamp ) return false;
    if( boss.kind != BOSS_NONE && boss.hp > 0 && boss_covers( c, r ) ) return false;
    for( int i = 0; i < MAX_SHEEP; i++ )
      if( sheep[ i ].alive && sheep[ i ].c == c && sheep[ i ].r == r ) return false;
    return true;
}

// a grazing sheep picks its next cell: away from the nearest hero when one comes close, else
// a slow wander with pauses to graze (that is when it can be caught)
void sheep_choose( Sheep* s )
{
    int here = nearest_hero_dist( s->c, s->r );
    s->dx = 0; s->dy = 0;
    if( s->t > 0 ) return;
    // a sheep runs faster than a man, but not for long: then it stands and pants
    if( s->run > SHEEP_STAMINA ) { s->run = 0; s->t = SHEEP_REST; return; }
    if( here <= 4 )
    {
        int best = -1, best_d = here;
        int first = rnd( 4 );
        for( int i = 0; i < 4; i++ )
        {
            int d = ( first + i ) % 4;
            int nc = s->c + DIR_X[ d ], nr = s->r + DIR_Y[ d ];
            if( !sheep_open( nc, nr ) ) continue;
            int dist = nearest_hero_dist( nc, nr );
            if( dist > best_d ) { best = d; best_d = dist; }
        }
        if( best >= 0 ) { s->dx = DIR_X[ best ]; s->dy = DIR_Y[ best ]; }
        return;
    }
    if( rnd( 100 ) < 35 ) { s->t = 60 + rnd( 90 ); return; }
    int first = rnd( 4 );
    for( int i = 0; i < 4; i++ )
    {
        int d = ( first + i ) % 4;
        if( sheep_open( s->c + DIR_X[ d ], s->r + DIR_Y[ d ] ) ) { s->dx = DIR_X[ d ]; s->dy = DIR_Y[ d ]; return; }
    }
}

bool goal_beside_dragon( Player* p, int c, int r )
{
    for( int d = 0; d < 4; d++ ) if( boss_covers( c + DIR_X[ d ], r + DIR_Y[ d ] ) ) return true;
    return false;
}

void boss_hit( int damage );

Player sheep_walker;

void update_sheep()
{
    for( int i = 0; i < MAX_SHEEP; i++ )
    {
        Sheep* s = &sheep[ i ];
        if( !s->alive ) continue;
        if( is_blast( s->c, s->r ) ) { sheep_goes_off( s ); continue; }
        bool centred = s->x == gpx( s->c ) && s->y == gpy( s->r );
        if( s->state == SHEEP_GRAZE )
        {
            if( s->t > 0 ) s->t--;
            // a hero walking onto it catches it
            for( int k = 0; k < player_count; k++ )
            {
                Player* p = &players[ k ];
                if( p->alive && p->team == 1 && p->c == s->c && p->r == s->r && p->sheep < SHEEP_CAP )
                {
                    p->sheep++;
                    s->alive = false;
                    raise_event( EV_SHEEP_GOT );
                }
            }
            if( !s->alive ) continue;
            if( centred ) sheep_choose( s );
            // a frightened sheep runs twice as fast as a man
            bool fleeing = nearest_hero_dist( s->c, s->r ) <= 4 && ( s->dx != 0 || s->dy != 0 );
            if( fleeing ) s->run++; else if( s->run > 0 ) s->run--;
            int speed = pick( fleeing, 2, 1 );
            for( int k = 0; k < speed; k++ )
            {
                if( k > 0 && s->x == gpx( s->c ) && s->y == gpy( s->r ) ) break;
                s->x += s->dx; s->y += s->dy;
            }
        }
        else
        {
            s->t--;
            if( dragon_alive() && goal_beside_dragon( &sheep_walker, s->c, s->r ) )
            {
                // the dragon swallows it, and it goes off inside
                s->alive = false;
                for( int dc = 0; dc < 2; dc++ ) for( int dr = 0; dr < 2; dr++ ) add_blast( boss.c + dc, boss.r + dr, s->owner, true );
                raise_event( EV_SHEEP_BOOM );
                boss_hit( 1 );
                continue;
            }
            if( s->t <= 0 || !dragon_alive() ) { sheep_goes_off( s ); continue; }
            if( centred && walker_searches_left > 0 && !out_of_time( BOT_FLEE_CYCLES ) )
            {
                walker_searches_left--;
                sheep_walker.c = s->c; sheep_walker.r = s->r; sheep_walker.team = 1;
                for( int k = 0; k < 4; k++ ) sheep_walker.bot_order[ k ] = k;
                int d = path_dir( &sheep_walker, &open_any, &goal_beside_dragon );
                s->dx = 0; s->dy = 0;
                if( d >= 0 ) { s->dx = DIR_X[ d ]; s->dy = DIR_Y[ d ]; }
            }
            // without a fresh search it keeps its way, but never into a crate or a bomb
            if( centred && !bot_passable( s->c + s->dx, s->r + s->dy ) ) { s->dx = 0; s->dy = 0; }
            for( int k = 0; k < 2; k++ )
            {
                if( k > 0 && s->x == gpx( s->c ) && s->y == gpy( s->r ) ) break;
                s->x += s->dx; s->y += s->dy;
            }
        }
        s->c = gcol( s->x + TILE / 2 ); s->r = grow( s->y + TILE / 2 );
    }
    // the dragon fight must never stall: a new sheep comes when nobody has one
    if( !dragon_alive() ) return;
    bool any = false;
    for( int i = 0; i < MAX_SHEEP; i++ ) if( sheep[ i ].alive ) any = true;
    for( int i = 0; i < player_count; i++ ) if( players[ i ].alive && players[ i ].team == 1 && players[ i ].sheep > 0 ) any = true;
    if( any ) { sheep_respawn = SHEEP_RESPAWN; return; }
    sheep_respawn--;
    if( sheep_respawn <= 0 ) { spawn_sheep_far(); sheep_respawn = SHEEP_RESPAWN; }
}

// ---------------------------------------------------------------------------
//   monsters: dwarves wander, bats fly after the nearest hero; a blast kills them
// ---------------------------------------------------------------------------

bool goal_hero( Player* p, int c, int r )
{
    for( int i = 0; i < player_count; i++ )
      if( players[ i ].alive && players[ i ].team == 1 && players[ i ].c == c && players[ i ].r == r ) return true;
    return false;
}

Player monster_walker;

void update_monsters()
{
    for( int i = monster_count - 1; i >= 0; i-- )
    {
        Monster* m = &monsters[ i ];
        if( is_blast( m->c, m->r ) )
        {
            for( int k = i; k < monster_count - 1; k++ ) monsters[ k ] = monsters[ k + 1 ];
            monster_count--;
            continue;
        }
        // a dwarf crosses a cell in 24 frames, a bat in 16
        int units = 0;
        if( m->kind == MON_BAT ) units = 1; else if( frame % 3 == 0 ) units = 2;
        for( int u = 0; u < units; u++ )
        {
            if( m->x == gpx( m->c ) && m->y == gpy( m->r ) )
            {
                if( m->kind == MON_BAT )
                {
                    // a bat looks for the nearest hero when the frame has time; else it flies on
                    if( walker_searches_left > 0 && !out_of_time( BOT_THINK_CYCLES ) )
                    {
                        walker_searches_left--;
                        monster_walker.c = m->c; monster_walker.r = m->r; monster_walker.team = 2;
                        for( int k = 0; k < 4; k++ ) monster_walker.bot_order[ k ] = k;
                        int d = path_dir( &monster_walker, &open_any, &goal_hero );
                        m->dx = 0; m->dy = 0;
                        if( d >= 0 ) { m->dx = DIR_X[ d ]; m->dy = DIR_Y[ d ]; }
                    }
                }
                else if( rnd( 100 ) < 15 || !bot_passable( m->c + m->dx, m->r + m->dy ) || ( m->dx == 0 && m->dy == 0 ) )
                {
                    int d = rnd( 4 );
                    m->dx = DIR_X[ d ]; m->dy = DIR_Y[ d ];
                }
                if( !bot_passable( m->c + m->dx, m->r + m->dy ) ) { m->dx = 0; m->dy = 0; }
            }
            m->x += m->dx; m->y += m->dy;
            m->c = gcol( m->x + TILE / 2 ); m->r = grow( m->y + TILE / 2 );
        }
    }
}

// ---------------------------------------------------------------------------
//   bosses
// ---------------------------------------------------------------------------

bool boss_free( int c, int r )
{
    for( int dc = 0; dc < 2; dc++ ) for( int dr = 0; dr < 2; dr++ )
    {
        if( !bot_passable( c + dc, r + dr ) ) return false;
        for( int i = 0; i < player_count; i++ )
          if( players[ i ].alive && players[ i ].team == 1 && players[ i ].c == c + dc && players[ i ].r == r + dr ) return false;
    }
    return true;
}

Player* dratewka() { return &players[ 0 ]; }

void boss_teleport()
{
    Player* a = dratewka();
    far_cells( T_EMPTY, 0 );
    while( far_n > 0 )
    {
        far_n--;
        int k = far_list[ far_n ];
        int c = k % MAP_STRIDE, r = k / MAP_STRIDE;
        if( boss_free( c, r ) && iabs( c - a->c ) + iabs( r - a->r ) >= 6 )
        { boss.c = c; boss.r = r; boss.x = gpx( c ); boss.y = gpy( r ); return; }
    }
}

void boss_hit( int damage )
{
    boss.hp = boss.hp - damage;
    boss.inv = 60;
    raise_event( EV_BOSS_HIT );
}

// the dragon's breath: a row or column through Dratewka, warned a second before it burns
void dragon_breath()
{
    if( !boss.warn )
    {
        Player* a = dratewka();
        boss.warn = true; boss.warn_row = rnd( 2 ) == 0;
        boss.warn_c = a->c; boss.warn_r = a->r; boss.warn_t = 60;
        raise_event( EV_ROAR );
        return;
    }
    boss.warn_t--;
    if( boss.warn_t > 0 ) return;
    boss.roar = 40;
    raise_event( EV_FIRE );
    int n = pick( boss.warn_row, W - 2, H - 2 );
    for( int k = 1; k <= n; k++ )
    {
        int c = pick( boss.warn_row, k, boss.warn_c ), r = pick( boss.warn_row, boss.warn_r, k );
        if( mget( c, r ) == T_EMPTY && !boss_covers( c, r ) ) add_blast( c, r, OWNER_BOSS, false );
    }
    boss.warn = false;
}

void update_boss()
{
    if( boss.kind == BOSS_NONE || boss.hp <= 0 ) return;
    boss.t++;
    if( boss.inv > 0 ) boss.inv--;
    if( boss.roar > 0 ) boss.roar--;
    // sulphur hurts the utopiec and Baba Jaga; the dragon only fears sheep (update_sheep)
    if( boss.kind != BOSS_DRAGON && boss.inv == 0 )
    {
        bool hit = false;
        for( int i = 0; i < blast_count && !hit; i++ )
          if( blasts[ i ].owner != OWNER_BOSS && boss_covers( blasts[ i ].c, blasts[ i ].r ) ) hit = true;
        if( hit ) boss_hit( 1 );
    }
    if( boss.kind == BOSS_UTOPIEC )
    {
        if( boss.t % 3 != 0 ) return;
        Player* a = dratewka();
        if( boss.x == gpx( boss.c ) && boss.y == gpy( boss.r ) )
        {
            boss.dx = 0; boss.dy = 0;
            for( int d = 0; d < 4; d++ )
            {
                int nc = boss.c + DIR_X[ d ], nr = boss.r + DIR_Y[ d ];
                if( boss_free( nc, nr ) && iabs( nc - a->c ) + iabs( nr - a->r ) < iabs( boss.c - a->c ) + iabs( boss.r - a->r ) )
                { boss.dx = DIR_X[ d ]; boss.dy = DIR_Y[ d ]; }
            }
        }
        boss.x += boss.dx * 2; boss.y += boss.dy * 2;
        boss.c = gcol( boss.x + TILE / 2 ); boss.r = grow( boss.y + TILE / 2 );
    }
    else if( boss.kind == BOSS_JAGA )
    {
        if( boss.t % 150 != 0 ) return;
        boss_teleport();
        add_bomb( boss.c, boss.r, BOMB_TIMER, 3, OWNER_BOSS, false );
    }
    else if( boss.warn || boss.t % 120 == 0 ) dragon_breath();
}

// ---------------------------------------------------------------------------
//   stages
// ---------------------------------------------------------------------------

#define CAMP_PLAY      0
#define CAMP_CLEAR     1
#define CAMP_LOST      2
#define CAMP_GAMEOVER  3
int camp_state = CAMP_PLAY;

void stage_size( int scroll )
{
    if( scroll == SCROLL_WIDE ) set_arena( 62, 18 );
    else if( scroll == SCROLL_TALL ) set_arena( 32, 34 );
    else set_arena( ARENA_W, ARENA_H );
}

void add_hero( int id, int c, int r )
{
    new_player( id, c, r );
    Player* p = &players[ id ];
    p->team = 1;
    p->human = id == 0 || camp_coop;
    p->stat_bombs = camp_bombs[ id ]; p->stat_len = camp_len[ id ]; p->sheep = camp_sheep[ id ];
    p->look = id;
}

void start_stage( int n )
{
    stage_def( n, &stage );
    camp_mode = true;
    camp_stage = n;
    camp_keys = 0; camp_done = false;
    camp_state = CAMP_PLAY;
    srand( n * 7919 + camp_tries + 1 );
    stage_size( stage.scroll );
    block_density = stage.density;
    clear_round();
    init_map();
    player_count = 1;
    add_hero( 0, start_c[ 0 ], start_r[ 0 ] );
    if( stage.chapter >= 2 ) { add_hero( 1, start_c[ 0 ], start_r[ 0 ] + 1 ); player_count = 2; }
    for( int i = 0; i < stage.skeletons; i++ )
    {
        int corner = pick( i == 0, 3, pick( stage.scroll == SCROLL_TALL, 2, 1 ) );
        int id = player_count;
        new_player( id, start_c[ corner ], start_r[ corner ] );
        players[ id ].team = 2; players[ id ].human = false; players[ id ].look = 9;
        player_count++;
    }
    far_cells( T_EMPTY, 8 );
    for( int i = 0; i < stage.dwarves; i++ ) spawn_monster( MON_DWARF, pop_far_free() );
    for( int i = 0; i < stage.bats; i++ ) spawn_monster( MON_BAT, pop_far_free() );
    if( stage.goal == GOAL_EXIT ) hide_items( ITEM_EXIT, 1 );
    else if( stage.goal == GOAL_KEYS ) hide_items( ITEM_KEY, 3 );
    if( stage.boss != BOSS_NONE )
    {
        int c = W / 2 - 1, r = H / 2 - 1;
        for( int dc = 0; dc < 2; dc++ ) for( int dr = 0; dr < 2; dr++ ) mset( c + dc, r + dr, T_EMPTY );
        boss.kind = stage.boss; boss.c = c; boss.r = r; boss.x = gpx( c ); boss.y = gpy( r );
        boss.dx = 0; boss.dy = 0; boss.hp = stage.boss_hp; boss.max_hp = stage.boss_hp;
        boss.t = 0; boss.inv = 0; boss.warn = false; boss.roar = 0;
    }
    for( int i = 0; i < stage.sheep; i++ ) spawn_sheep_far();
    sheep_respawn = SHEEP_RESPAWN;
    reset_shrink();
    // survive: the walls start after 10 s and step on as soon as each 5 s blink is over
    if( stage.goal == GOAL_SURVIVE ) { shrink_at = 600; zone_cycle = SHRINK_WARN; }
    else shrink_at = FOREVER;
}

void start_campaign( bool coop, int from_stage )
{
    camp_coop = coop;
    camp_lives = LIVES;
    camp_tries = 0;
    for( int i = 0; i < 2; i++ ) { camp_bombs[ i ] = MAX_BOMBS; camp_len[ i ] = BLAST_LEN; camp_sheep[ i ] = 0; }
    start_stage( from_stage );
}

bool chapter_start( int n ) { return n == 1 || chapter_of( n ) != chapter_of( n - 1 ); }

bool stage_goal_met()
{
    if( stage.goal == GOAL_EXIT ) return camp_done;
    if( stage.goal == GOAL_KEYS ) return camp_keys >= 3;
    if( stage.goal == GOAL_SURVIVE ) return zone_steps >= SURVIVE_STEPS;
    if( stage.goal == GOAL_BOSS ) return boss.hp <= 0;
    for( int i = 0; i < player_count; i++ ) if( players[ i ].alive && players[ i ].team == 2 ) return false;
    return monster_count == 0;
}

int enemies_left()
{
    int n = monster_count;
    for( int i = 0; i < player_count; i++ ) if( players[ i ].alive && players[ i ].team == 2 ) n++;
    return n;
}

// the camera follows the heroes along the stage's one scrolling axis
void update_camera()
{
    int x = 0, y = 0, n = 0;
    for( int i = 0; i < player_count; i++ )
      if( players[ i ].team == 1 && players[ i ].alive ) { x += players[ i ].x; y += players[ i ].y; n++; }
    if( n == 0 ) return;
    cam_x = clampi( x / n - 232, 0, imax( 0, ( W - 2 ) * TILE - 30 * TILE ) );
    cam_y = clampi( y / n - 120, 0, imax( 0, ( H - 2 ) * TILE - 16 * TILE ) );
}

void update_campaign()
{
    update_bombs();
    update_blasts();
    update_invul_and_deaths();
    update_shrink();
    update_players();
    update_monsters();
    update_boss();
    update_sheep();
    int heroes = 0;
    for( int i = 0; i < player_count; i++ )
    {
        Player* p = &players[ i ];
        if( !p->alive || p->team != 1 ) continue;
        collect_item( p );   // an item can appear under a hero who stands still
        for( int k = 0; k < monster_count; k++ ) if( monsters[ k ].c == p->c && monsters[ k ].r == p->r ) blast_hit( p );
        if( boss.kind != BOSS_NONE && boss.hp > 0 && boss_covers( p->c, p->r ) ) blast_hit( p );
        if( p->alive ) heroes++;
    }
    update_camera();
    if( heroes == 0 )
    {
        camp_lives--;
        camp_state = pick( camp_lives > 0, CAMP_LOST, CAMP_GAMEOVER );
    }
    else if( stage_goal_met() )
    {
        for( int i = 0; i < player_count; i++ )
        {
            Player* p = &players[ i ];
            if( p->team != 1 ) continue;
            camp_bombs[ p->id ] = p->stat_bombs; camp_len[ p->id ] = p->stat_len; camp_sheep[ p->id ] = p->sheep;
        }
        camp_state = CAMP_CLEAR;
    }
}

#endif
