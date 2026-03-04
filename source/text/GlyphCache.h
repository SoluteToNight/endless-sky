/* GlyphCache.h
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

// Metadata for a single rendered character glyph.
class GlyphInfo {
public:
  // UV coordinates in the TextureAtlas: (x, y, w, h)
  float uvRect[4];

  // Distance to advance the pen after drawing this glyph (logical, scaled).
  float advance;

  // Rendering offset from the pen position (logical, scaled).
  float bearingX;
  float bearingY;

  // Logical dimensions of the glyph (scaled down for layout).
  float width;
  float height;

  // Full hi-res bitmap dimensions (used for atlas and rendering).
  int bitmapW = 0;
  int bitmapH = 0;

  bool isWhitespace = false;
};
