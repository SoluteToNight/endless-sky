/* TextureAtlas.h
Copyright (c) 2014-202X by Michael Zahniser

Endless Sky is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Endless Sky is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <https://www.gnu.org/licenses/>.
*/

#pragma once

#include "../opengl.h"

// Class that manages a dynamic OpenGL texture atlas. Space is allocated for
// individual glyphs using a shelf-packing algorithm.
class TextureAtlas {
public:
  // Create an empty atlas of the given dimensions.
  TextureAtlas(int width, int height);

  // No copy or assignment.
  TextureAtlas(const TextureAtlas &) = delete;
  TextureAtlas &operator=(const TextureAtlas &) = delete;

  // Destructor deletes the OpenGL texture.
  ~TextureAtlas();

  // Bind the texture to the current OpenGL context.
  void Bind() const;

  // Try to allocate space for a bitmap of size width x height.
  // Returns true and writes the coordinates to (x, y) on success.
  // Returns false if there is not enough room in the atlas.
  bool Allocate(int width, int height, int &x, int &y);

  // Upload pixel data to the specified coordinates.
  // The data must be an array of size width * height bytes (GL_RED).
  void Upload(int x, int y, int width, int height, const void *data);

  // Get dimensions.
  int Width() const noexcept { return width; }
  int Height() const noexcept { return height; }

private:
  GLuint texture = 0;
  int width;
  int height;

  // Current allocator state for shelf-packing.
  int currentX = 0;
  int currentY = 0;
  int currentRowHeight = 0;
};
