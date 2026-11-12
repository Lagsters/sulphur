// Drawing the arena. Logic units map to screen pixels at 20/16; the 32x18 battle grid fills
// the 640x360 screen exactly, its top wall row under the HUD.
#ifndef RENDER_H
#define RENDER_H

#include "campaign.h"
#include "gen/core.h"

int sx( int x ) { return TILE_PX + ( ( x - cam_x ) * TILE_PX ) / TILE; }
int sy( int y ) { return ( ( y - cam_y ) * TILE_PX ) / TILE; }

void init_render()
{
    define_core_regions();
}

void fill_rect( int x, int y, int w, int h, int color )
{
    select_texture( core_tex[ CORE_WHITE ] );
    select_region( core_reg[ CORE_WHITE ] );
    set_multiply_color( color );
    set_drawing_scale( w / 16.0, h / 16.0 );
    draw_region_zoomed_at( x, y );
    set_multiply_color( color_white );
}

int[ 6 ] PLAYER_COL = { 0xFFFFFFFF, 0xFF40C040, 0xFFFF8040, 0xFF4040FF, 0xFF40FFFF, 0xFFC0C0C0 };

void draw_arena_dev()
{
    clear_screen( 0xFF101418 );
    int c0 = cam_x / TILE, r0 = cam_y / TILE;
    for( int r = r0; r <= imin( H - 1, r0 + 18 ); r++ )
      for( int c = c0; c <= imin( W - 1, c0 + 32 ); c++ )
      {
          int t = mget( c, r );
          int x = sx( gpx( c ) ), y = sy( gpy( r ) );
          if( t == T_WALL ) fill_rect( x, y, TILE_PX, TILE_PX, 0xFF606870 );
          else if( t == T_BLOCK ) fill_rect( x + 1, y + 1, TILE_PX - 2, TILE_PX - 2, 0xFF2860A0 );
          else fill_rect( x, y, TILE_PX, TILE_PX, pick( ( c + r ) % 2 == 0, 0xFF283028, 0xFF243024 ) );
      }
    if( shrink_closing() >= 0 && frame % 16 < 8 )
      for( int i = 0; i < step_count; i++ ) fill_rect( sx( gpx( step_c[ i ] ) ), sy( gpy( step_r[ i ] ) ), TILE_PX, TILE_PX, 0xFF4080FF );
    for( int i = 0; i < item_count; i++ )
      fill_rect( sx( gpx( items[ i ].c ) ) + 6, sy( gpy( items[ i ].r ) ) + 6, 8, 8, pick( items[ i ].kind == ITEM_KEY, 0xFF00E0FF, pick( items[ i ].kind == ITEM_EXIT, 0xFF000000, 0xFFE0E040 ) ) );
    for( int i = 0; i < bomb_count; i++ )
      fill_rect( sx( gpx( bombs[ i ].c ) ) + 4, sy( gpy( bombs[ i ].r ) ) + 4, 12, 12, pick( bombs[ i ].t < 40 && frame % 6 < 3, 0xFFFFFFFF, 0xFF00D0F0 ) );
    for( int i = 0; i < blast_count; i++ )
      fill_rect( sx( gpx( blasts[ i ].c ) ) + 2, sy( gpy( blasts[ i ].r ) ) + 2, 16, 16, pick( blasts[ i ].sheep, 0xFFFFFFFF, 0xFF2090FF ) );
    for( int i = 0; i < monster_count; i++ )
      fill_rect( sx( monsters[ i ].x ) + 3, sy( monsters[ i ].y ) + 3, 14, 14, pick( monsters[ i ].kind == MON_BAT, 0xFF800080, 0xFF2020C0 ) );
    if( boss.kind != BOSS_NONE && boss.hp > 0 )
      fill_rect( sx( boss.x ), sy( boss.y ), 2 * TILE_PX, 2 * TILE_PX, pick( boss.inv > 0 && frame % 6 < 3, 0xFFFFFFFF, 0xFF0000A0 ) );
    for( int i = 0; i < MAX_SHEEP; i++ )
      if( sheep[ i ].alive ) fill_rect( sx( sheep[ i ].x ) + 3, sy( sheep[ i ].y ) + 3, 14, 14, pick( sheep[ i ].state == SHEEP_LIT, 0xFF0080FF, 0xFFF0F0F0 ) );
    for( int i = 0; i < player_count; i++ )
    {
        Player* p = &players[ i ];
        if( !p->alive && !( p->death_t > 0 && p->death_t % 4 < 2 ) ) continue;
        if( p->invul > 0 && frame % 8 < 4 ) continue;
        fill_rect( sx( p->x ) + 3, sy( p->y ) + 2, 14, 16, PLAYER_COL[ p->look % 6 ] );
    }
    fill_rect( 0, 0, 640, 20, 0xFF000000 );
}

#endif
