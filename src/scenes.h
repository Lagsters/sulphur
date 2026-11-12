// Story scenes. PLACEHOLDER: every scene ends at once. The scenes group replaces this file,
// keeping these names.
#ifndef SCENES_H
#define SCENES_H

#define SCENE_WROCLAW  0      // before chapter 1
#define SCENE_SLEZA    1      // before chapter 2
#define SCENE_KRAKOW   2      // before chapter 3
#define SCENE_ENDING   3      // after the dragon

void scene_start( int id ) {}

// draws one frame of the playing scene and reads the pad; true once it has ended
bool scene_frame() { return true; }

#endif
