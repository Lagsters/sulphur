// Plays the four story scenes in a row, in English and then in Polish, and halts.
//     python tools/build.py tools/scenes/preview.c scenes_preview
#include "video.h"
#include "input.h"
#include "audio.h"
#include "time.h"
#include "math.h"
#include "misc.h"
#include "string.h"
#include "memcard.h"

#include "../../src/scenes.h"

void main()
{
    define_core_regions();
    text_init();
    sound_init();
    for( int l = 0; l < 2; l++ )
    {
        lang = l;
        for( int id = SCENE_WROCLAW; id <= SCENE_ENDING; id++ )
        {
            scene_start( id );
            while( !scene_frame() )
            {
                sound_frame();
                end_frame();
            }
            end_frame();
        }
    }
    exit();
}
