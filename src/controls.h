// Human players on gamepads: the D-pad walks, A lays a sulphur bomb, B lets a sheep go.
#ifndef CONTROLS_H
#define CONTROLS_H

#include "battle.h"

bool launch_sheep( Player* p );

// true on the frame a button goes down (the console counts the frames it is held)
bool just_pressed( int held ) { return held == 1; }

void update_human( Player* p )
{
    select_gamepad( p->pad );
    int ox = p->x, oy = p->y;
    if( gamepad_up() > 0 )    { move_player( p, 0, -1 ); p->dir_x = 0;  p->dir_y = -1; }
    if( gamepad_down() > 0 )  { move_player( p, 0, 1 );  p->dir_x = 0;  p->dir_y = 1; }
    if( gamepad_left() > 0 )  { move_player( p, -1, 0 ); p->dir_x = -1; p->dir_y = 0; }
    if( gamepad_right() > 0 ) { move_player( p, 1, 0 );  p->dir_x = 1;  p->dir_y = 0; }
    if( p->x != ox || p->y != oy ) p->walk_anim++;
    if( just_pressed( gamepad_button_a() ) ) place_bomb( p );
    if( just_pressed( gamepad_button_b() ) ) launch_sheep( p );
    if( blast_hurts( p ) ) blast_hit( p );
}

#endif
