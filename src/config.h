// Rules and sizes of the game, ported from BlasTIC (blastic.lua); names follow it.
#ifndef CONFIG_H
#define CONFIG_H

// a cell is 16 logic units and 20 screen pixels; heroes walk one unit a frame,
// 16 frames a cell, as fast as in BlasTIC (8 units every second frame)
#define TILE           16
#define TILE_PX        20
#define SPEED          1

// the battle arena; campaign stages are wider or taller and scroll
#define ARENA_W        32
#define ARENA_H        18
// map arrays are indexed r*MAP_STRIDE+c, wide enough for every stage
#define MAP_STRIDE     64
#define MAP_ROWS       36
#define MAP_CELLS      2304

#define MAX_BOMBS      1
#define BOMB_CAP       5
#define BOMB_TIMER     120
#define BLAST_LEN      2
#define LEN_CAP        6
#define BLAST_TIME     30
#define DEATH_TIME     40
#define POWERUP_CHANCE 25
#define SHIELD_INVUL   60
#define MATCH_WINS     3
#define MATCH_TIME     210

#define T_EMPTY        0
#define T_WALL         1
#define T_BLOCK        2

// items lying on the floor; exit and keys survive blasts (QUEST items)
#define ITEM_NONE      0
#define ITEM_BOMB      1
#define ITEM_RANGE     2
#define ITEM_SHIELD    3
#define ITEM_EXIT      4
#define ITEM_KEY       5

#define MAX_PLAYERS    6
#define MAX_BOMB_LIST  64
#define MAX_BLASTS     640
#define MAX_ITEMS      96

// the closing arena (frames)
#define SHRINK_DELAY   1800
#define SHRINK_PAUSE   120
#define SHRINK_WARN    300
#define SHRINK_CYCLE   420
#define ZONE_MIN_W     4
#define ZONE_MIN_H     2

// owner of a blast or bomb that belongs to nobody, or to a boss
#define OWNER_NONE     -1
#define OWNER_BOSS     -2

#endif
