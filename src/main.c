// Sulphur: the sulphur legend, an arena game for Vircon32 (a fork of BlasTIC for TIC-80).
#include "video.h"
#include "input.h"
#include "audio.h"
#include "time.h"
#include "math.h"
#include "misc.h"
#include "string.h"
#include "memcard.h"

#include "ui.h"

void main()
{
    init_strings();
    init_sprites();
    text_init();
    sound_init();
    ui_init();
    load_save();
    srand( get_time() + 1 );
    enter( ST_TITLE );
    while( true )
    {
        frame++;
        clear_screen( color_black );
        ui_frame();
        sound_frame();
        for( int e = 0; e < EV_COUNT; e++ ) events[ e ] = 0;
        end_frame();
    }
}
