/* TextureAtlas.cpp
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

#include "TextureAtlas.h"

#include "../opengl.h"

#include <algorithm>

using namespace std;

TextureAtlas::TextureAtlas(int width, int height)
    : width(width), height(height) {
  glGenTextures(1, &texture);
  glBindTexture(GL_TEXTURE_2D, texture);

  // We use GL_RED for font glyphs as they are greyscale alpha masks.
  // We'll swizzle this to RGBA during rendering using shader or texture
  // swizzle.
  glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, width, height, 0, GL_RED,
               GL_UNSIGNED_BYTE, nullptr);

  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);

  // Swizzle the Red channel to Alpha, and set RGB to 1.f so we can draw white
  // text and color it with the uniform.
  GLint swizzleMask[] = {GL_ONE, GL_ONE, GL_ONE, GL_RED};
  glTexParameteriv(GL_TEXTURE_2D, GL_TEXTURE_SWIZZLE_RGBA, swizzleMask);
}

TextureAtlas::~TextureAtlas() {
  if (texture)
    glDeleteTextures(1, &texture);
}

void TextureAtlas::Bind() const { glBindTexture(GL_TEXTURE_2D, texture); }

bool TextureAtlas::Allocate(int reqWidth, int reqHeight, int &x, int &y) {
  // Add 1 pixel padding between glyphs to prevent bilinear bleeding
  int padWidth = reqWidth + 1;
  int padHeight = reqHeight + 1;

  // Will it fit on the current row?
  if (currentX + padWidth > width) {
    // Move to the next row.
    currentX = 0;
    currentY += currentRowHeight;
    currentRowHeight = 0;
  }

  // Will it fit vertically?
  if (currentY + padHeight > height)
    return false;

  // Assign coordinates.
  x = currentX;
  y = currentY;

  // Advance allocator.
  currentX += padWidth;
  currentRowHeight = max(currentRowHeight, padHeight);

  return true;
}

void TextureAtlas::Upload(int x, int y, int reqWidth, int reqHeight,
                          const void *data) {
  glBindTexture(GL_TEXTURE_2D, texture);
  // OpenGL requires 4-byte alignment by default, but FreeType bitmaps are
  // 1-byte aligned.
  glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
  glTexSubImage2D(GL_TEXTURE_2D, 0, x, y, reqWidth, reqHeight, GL_RED,
                  GL_UNSIGNED_BYTE, data);
  // Restore default alignment.
  glPixelStorei(GL_UNPACK_ALIGNMENT, 4);
}
