// Everything the game keeps between frames.
#ifndef STATE_H
#define STATE_H

#include "config.h"

struct Player
{
    int c, r, x, y;
    bool alive;
    int stat_bombs, stat_len;
    int bombs;              // own bombs ticking now
    bool shield;
    int invul;
    int id;                 // 0..MAX_PLAYERS-1
    int team;               // battle: own id; campaign: 1 heroes, 2 skeletons
    bool human;
    int pad;                // gamepad of a human
    int dir_x, dir_y;
    int walk_anim;
    int death_t;
    int sheep;              // sulphur sheep carried (campaign, late stages)
    // bot state
    int bot_dir_x, bot_dir_y;
    int[ 4 ] bot_order;     // fixed tie-break order of directions for this round
    int bot_dir_timer;
    int bot_plan_x, bot_plan_y;
    bool bot_planned;
    int look;               // which art (tools/catalog.py LOOKS): 0 Dratewka, 1 Wanda, 2-5 Battle, 6 skeleton
};

#define LOOK_SKELETON  6

struct Bomb
{
    int c, r, t, len;
    int owner;              // player index, OWNER_NONE or OWNER_BOSS
    bool sheep;             // a sulphur sheep going off: a bigger blast
};

struct Blast
{
    int c, r, t;
    int owner;
    bool sheep;
};

struct Item
{
    int c, r, kind;
};

#define MON_DWARF      0      // wanders, kills on touch
#define MON_BAT        1      // flies after the nearest hero
#define MAX_MONSTERS   16

struct Monster
{
    int kind, c, r, x, y, dx, dy;
};

#define BOSS_NONE      0
#define BOSS_UTOPIEC   1      // walks after Dratewka
#define BOSS_JAGA      2      // teleports and leaves her own bombs
#define BOSS_DRAGON    3      // breathes fire along a row or column; only sheep hurt it

struct Boss
{
    int kind, c, r, x, y, dx, dy;   // covers 2x2 cells from (c,r)
    int hp, max_hp, t, inv;
    bool warn;                      // the dragon's breath is coming: a row or a column
    bool warn_row;
    int warn_c, warn_r, warn_t;
    int roar;                       // frames of the dragon's open jaws, for the art
};

#define SHEEP_GRAZE    0      // wanders, runs from heroes and fire
#define SHEEP_LIT      1      // let go with a burning fuse: runs to the dragon
#define MAX_SHEEP      4

struct Sheep
{
    bool alive;
    int state, c, r, x, y, dx, dy;
    int t;                  // frames of grazing left, or of the fuse
    int run;                // frames it has been running from heroes; a tired sheep stops
    int owner;
};

int W = ARENA_W, H = ARENA_H;
int[ MAP_CELLS ] map;
int[ 4 ] start_c, start_r;
int block_density = 40;     // percent of free cells that get a crate

Player[ MAX_PLAYERS ] players;
int player_count = 0;
bool[ MAX_PLAYERS ] human_slot;

Bomb[ MAX_BOMB_LIST ] bombs;
int bomb_count = 0;
Blast[ MAX_BLASTS ] blasts;
int blast_count = 0;
// how many blasts and bombs lie on each cell, so the frequent "is there fire / a bomb" is one
// lookup (searches ask it for every cell they visit)
int[ MAP_CELLS ] blast_cover;
int[ MAP_CELLS ] bomb_cover;
Item[ MAX_ITEMS ] items;
int item_count = 0;
// a quest item hidden under the crate on this cell (campaign)
int[ MAP_CELLS ] hidden;

int frame = 0;
int lang = 0;               // 0 English, 1 Polish
bool camp_mode = false;     // Story; false is Battle
int cam_x = 0, cam_y = 0;   // camera in logic units

// the campaign stage being played (campaign.h has the rest)
int camp_keys = 0;
bool camp_done = false;
Monster[ MAX_MONSTERS ] monsters;
int monster_count = 0;
Boss boss;
Sheep[ MAX_SHEEP ] sheep;

// sound requests the game logic raises; the sound module plays them each frame
#define EV_BOMB        0
#define EV_BOOM        1
#define EV_PICKUP      2
#define EV_DEATH       3
#define EV_SHIELD      4
#define EV_SHEEP_GOT   5
#define EV_SHEEP_BOOM  6
#define EV_BOSS_HIT    7
#define EV_FIRE        8
#define EV_ZONE        9
#define EV_ROAR        10
#define EV_COUNT       11
int[ EV_COUNT ] events;

void raise_event( int e ) { events[ e ] = events[ e ] + 1; }

int cell( int c, int r ) { return r * MAP_STRIDE + c; }

// the dialect has no ?: operator; both values are computed
int pick( bool cond, int a, int b ) { if( cond ) return a; return b; }

int iabs( int v ) { if( v < 0 ) return -v; return v; }
int imin( int a, int b ) { if( a < b ) return a; return b; }
int imax( int a, int b ) { if( a > b ) return a; return b; }
int isign( int v ) { if( v > 0 ) return 1; if( v < 0 ) return -1; return 0; }
int clampi( int v, int lo, int hi ) { if( v < lo ) return lo; if( v > hi ) return hi; return v; }

// 0..n-1 from the console's generator (seeded per stage, so a stage replays the same)
int rnd( int n ) { return rand() % n; }

#endif
