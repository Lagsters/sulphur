#include "video.h"
#include "misc.h"
#include "time.h"
#include "../../src/gen/core.h"
void main()
{
    define_core_regions();
    while( true )
    {
        clear_screen( color_black );
        select_texture( core_tex[ CORE_WHITE ] );
        select_region( core_reg[ CORE_WHITE ] );
        set_drawing_scale( -4.0, 1.0 );
        draw_region_zoomed_at( 100, 100 );
        end_frame();
    }
}
