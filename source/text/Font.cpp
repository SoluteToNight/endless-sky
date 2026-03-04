/* Font.cpp
Copyright (c) 2014-2020 by Michael Zahniser

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

#include "Font.h"

#include "../Color.h"
#include "../GameData.h"
#include "../Point.h"
#include "../Preferences.h"
#include "../Screen.h"
#include "Alignment.h"
#include "DisplayText.h"
#include "Truncate.h"
#include "Utf8.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <iostream>

using namespace std;

namespace {
bool showUnderlines = false;

/// Shared VAO and VBO quad (0,0) -> (1,1)
GLuint vao = 0;
GLuint vbo = 0;

GLint colorI = 0;
GLint scaleI = 0;
GLint glyphSizeI = 0;
GLint uvRectI = 0;
GLint aspectI = 0;
GLint positionI = 0;

GLint vertI;
GLint cornerI;

void EnableAttribArrays() {
  // Connect the xy to the "vert" attribute of the vertex shader.
  constexpr auto stride = 4 * sizeof(GLfloat);
  glEnableVertexAttribArray(vertI);
  glVertexAttribPointer(vertI, 2, GL_FLOAT, GL_FALSE, stride, nullptr);

  glEnableVertexAttribArray(cornerI);
  glVertexAttribPointer(cornerI, 2, GL_FLOAT, GL_FALSE, stride,
                        reinterpret_cast<const GLvoid *>(2 * sizeof(GLfloat)));
}

FT_Library ftLibrary = nullptr;

void InitFreeType() {
  if (!ftLibrary) {
    if (FT_Init_FreeType(&ftLibrary)) {
      cerr << "Could not initialize freetype library." << endl;
    }
  }
}
} // namespace

Font::Font() noexcept { InitFreeType(); }

Font::~Font() {
  for (auto face : faces)
    FT_Done_Face(face);
}

void Font::Load(const vector<filesystem::path> &fontPaths, int size) {
  this->size = size;

  // Render at renderScale times the nominal size for high-DPI quality.
  // Original PNGs used ~2x oversampling (14px -> 32px tall, 18px -> 36px tall).
  int renderSize = size * renderScale;

  for (const auto &path : fontPaths) {
    FT_Face face;
    if (FT_New_Face(ftLibrary, path.string().c_str(), 0, &face)) {
      cerr << "Failed to load font " << path << endl;
      continue;
    }

    FT_Set_Pixel_Sizes(face, 0, renderSize);
    faces.push_back(face);
  }

  if (faces.empty())
    return;

  // Atlas size to hold several thousand glyphs at the supersampled resolution.
  atlas = make_unique<TextureAtlas>(4096, 4096);

  // Pre-determine line height, ascender, and space width based on primary font.
  // Metrics from FreeType are in 26.6 fixed-point hi-res space.
  // Use ascender-descender (no linegap) to match original PNG cell height.
  FT_Face primary = faces.front();
  float fScale = static_cast<float>(renderScale);
  int ftAscender = primary->size->metrics.ascender >> 6;
  int ftDescender = primary->size->metrics.descender >> 6; // negative
  height = static_cast<int>((ftAscender - ftDescender) / fScale);
  ascender = static_cast<int>(ftAscender / fScale);
  const auto &spaceGlyph = GetGlyph(' ');
  space = static_cast<int>(spaceGlyph.advance);
  if (space <= 0)
    space = size / 3;

  SetUpShader();
  widthEllipses = WidthRawString("...");
}

void Font::Draw(const DisplayText &text, const Point &point,
                const Color &color) const {
  DrawAliased(text, round(point.X()), round(point.Y()), color);
}

void Font::DrawAliased(const DisplayText &text, double x, double y,
                       const Color &color) const {
  int width = -1;
  const string truncText = TruncateText(text, width);
  const auto &layout = text.GetLayout();
  if (width >= 0) {
    if (layout.align == Alignment::CENTER)
      x += (layout.width - width) / 2;
    else if (layout.align == Alignment::RIGHT)
      x += layout.width - width;
  }
  DrawAliased(truncText, x, y, color);
}

void Font::Draw(const string &str, const Point &point,
                const Color &color) const {
  DrawAliased(str, round(point.X()), round(point.Y()), color);
}

void Font::DrawAliased(const string &str, double x, double y,
                       const Color &color) const {
  if (!atlas)
    return;

  glUseProgram(shader->Object());
  atlas->Bind();

  if (OpenGL::HasVaoSupport())
    glBindVertexArray(vao);
  else {
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    EnableAttribArrays();
  }

  glUniform4fv(colorI, 1, color.Get());

  // Update the scale, only if the screen size has changed.
  if (Screen::Width() != screenWidth || Screen::Height() != screenHeight) {
    screenWidth = Screen::Width();
    screenHeight = Screen::Height();
    scale[0] = 2.f / screenWidth;
    scale[1] = -2.f / screenHeight;
  }
  glUniform2fv(scaleI, 1, scale);

  GLfloat textPos[2] = {static_cast<float>(x - 1.), static_cast<float>(y)};

  bool underlineChar = false;
  const GlyphInfo &underscoreGlyph = GetGlyph('_');

  size_t pos = 0;
  while (pos < str.length()) {
    char32_t codepoint = Utf8::DecodeCodePoint(str, pos);

    // Handle explicit custom underlines, maybe legacy specific logic?
    if (codepoint == '_') {
      underlineChar = showUnderlines;
      continue; // In legacy, it skipped the original underline and drew a
                // longer one.
    }

    if (codepoint == 0 || codepoint == static_cast<char32_t>(-1))
      continue;

    const GlyphInfo &info = GetGlyph(codepoint);

    if (!info.isWhitespace && info.bitmapW > 0 && info.bitmapH > 0) {
      // Use logical (scaled-down) dimensions for the screen quad size.
      // The UV rect still samples the full hi-res bitmap for quality.
      glUniform2f(glyphSizeI, static_cast<float>(info.width),
                  static_cast<float>(info.height));
      glUniform4fv(uvRectI, 1, info.uvRect);
      glUniform1f(aspectI, 1.f);

      // Position: X = pen + bearingX, Y = pen + (ascender - bearingY)
      // ascender is the distance from text top to baseline.
      // bearingY is the distance from baseline to glyph top.
      GLfloat drawPos[2] = {textPos[0] + info.bearingX,
                            textPos[1] + (ascender - info.bearingY)};
      glUniform2fv(positionI, 1, drawPos);

      glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    }

    textPos[0] += info.advance;

    if (underlineChar) {
      if (underscoreGlyph.bitmapW > 0 && underscoreGlyph.bitmapH > 0) {
        glUniform2f(glyphSizeI, static_cast<float>(underscoreGlyph.width),
                    static_cast<float>(underscoreGlyph.height));
        glUniform4fv(uvRectI, 1, underscoreGlyph.uvRect);
        // Make the underscore stretch over the previous character's advance
        float aspect = info.advance / max(underscoreGlyph.advance, 1.f);
        glUniform1f(aspectI, aspect);

        GLfloat underPos[2] = {
            textPos[0] - info.advance + underscoreGlyph.bearingX,
            textPos[1] + (ascender - underscoreGlyph.bearingY)};
        glUniform2fv(positionI, 1, underPos);

        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
      }
      underlineChar = false;
    }
  }

  if (OpenGL::HasVaoSupport())
    glBindVertexArray(0);
  else {
    glDisableVertexAttribArray(vertI);
    glDisableVertexAttribArray(cornerI);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
  }
  glUseProgram(0);
}

int Font::Width(const string &str, char after) const {
  return WidthRawString(str.c_str(), after);
}

int Font::FormattedWidth(const DisplayText &text, char after) const {
  int width = -1;
  const string truncText = TruncateText(text, width);
  return width < 0 ? WidthRawString(truncText.c_str(), after) : width;
}

int Font::Height() const noexcept { return height; }

int Font::Space() const noexcept { return space; }

void Font::ShowUnderlines(bool show) noexcept {
  showUnderlines = show || Preferences::Has("Always underline shortcuts");
}

const GlyphInfo &Font::GetGlyph(char32_t codepoint) const {
  auto it = cache.find(codepoint);
  if (it != cache.end())
    return it->second;

  GlyphInfo info{};
  if (codepoint == ' ' || codepoint == '\n' || codepoint == '\t')
    info.isWhitespace = true;

  FT_Face faceToUse = nullptr;
  FT_UInt glyphIndex = 0;

  for (auto face : faces) {
    glyphIndex = FT_Get_Char_Index(face, codepoint);
    if (glyphIndex != 0) {
      faceToUse = face;
      break;
    }
  }

  if (!faceToUse && !faces.empty())
    faceToUse = faces.front();

  if (faceToUse) {
    if (FT_Load_Glyph(faceToUse, glyphIndex, FT_LOAD_RENDER) == 0) {
      FT_GlyphSlot slot = faceToUse->glyph;

      // Store the full hi-res bitmap dimensions for rendering.
      info.bitmapW = slot->bitmap.width;
      info.bitmapH = slot->bitmap.rows;
      // Store logical (scaled-down) metrics for text layout using float
      // division.
      float fScale = static_cast<float>(renderScale);
      info.width = static_cast<float>(slot->bitmap.width) / fScale;
      info.height = static_cast<float>(slot->bitmap.rows) / fScale;
      info.bearingX = static_cast<float>(slot->bitmap_left) / fScale;
      info.bearingY = static_cast<float>(slot->bitmap_top) / fScale;
      info.advance = static_cast<float>(slot->advance.x >> 6) / fScale;

      if (info.advance == 0.f && info.isWhitespace)
        info.advance = static_cast<float>(size) / 3.f;

      if (info.bitmapW > 0 && info.bitmapH > 0) {
        int startX, startY;
        if (atlas->Allocate(info.bitmapW, info.bitmapH, startX, startY)) {
          atlas->Upload(startX, startY, info.bitmapW, info.bitmapH,
                        slot->bitmap.buffer);
          info.uvRect[0] = static_cast<float>(startX) / atlas->Width();
          info.uvRect[1] = static_cast<float>(startY) / atlas->Height();
          info.uvRect[2] = static_cast<float>(info.bitmapW) / atlas->Width();
          info.uvRect[3] = static_cast<float>(info.bitmapH) / atlas->Height();
        }
      }
    }
  }

  // Double buffering map insertion is safe if initialized.
  cache[codepoint] = info;
  return cache[codepoint];
}

void Font::SetUpShader() {
  shader = GameData::Shaders().Get("font");
  // Initialize the shared parameters only once
  if (!vbo) {
    vertI = shader->Attrib("vert");
    cornerI = shader->Attrib("corner");

    glUseProgram(shader->Object());
    glUniform1i(shader->Uniform("tex"), 0);
    glUseProgram(0);

    // Create the VAO and VBO.
    if (OpenGL::HasVaoSupport()) {
      glGenVertexArrays(1, &vao);
      glBindVertexArray(vao);
    }

    glGenBuffers(1, &vbo);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);

    GLfloat vertices[] = {0.f, 0.f, 0.f, 0.f, 0.f, 1.f, 0.f, 1.f,
                          1.f, 0.f, 1.f, 0.f, 1.f, 1.f, 1.f, 1.f};
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);

    if (OpenGL::HasVaoSupport())
      EnableAttribArrays();

    glBindBuffer(GL_ARRAY_BUFFER, 0);
    if (OpenGL::HasVaoSupport())
      glBindVertexArray(0);

    colorI = shader->Uniform("color");
    scaleI = shader->Uniform("scale");
    glyphSizeI = shader->Uniform("glyphSize");
    uvRectI = shader->Uniform("uv_rect");
    aspectI = shader->Uniform("aspect");
    positionI = shader->Uniform("position");
  }

  // We must update the screen size next time we draw.
  screenWidth = 0;
  screenHeight = 0;
}

int Font::WidthRawString(const char *str, char after) const noexcept {
  float width = 0.f;

  // Create a string so we can use Utf8::DecodeCodePoint nicely,
  // though creating string each time is an allocation. In Endless Sky
  // WidthRawString is mostly called for layout which is cached.
  string s(str);
  size_t pos = 0;
  while (pos < s.length()) {
    char32_t codepoint = Utf8::DecodeCodePoint(s, pos);
    if (codepoint == '_')
      continue;
    const GlyphInfo &info = GetGlyph(codepoint);
    width += info.advance;
  }

  if (after != '\0')
    width += GetGlyph(after).advance;

  return static_cast<int>(width + 0.5f);
}

// Param width will be set to the width of the return value, unless the layout
// width is negative.
string Font::TruncateText(const DisplayText &text, int &width) const {
  width = -1;
  const auto &layout = text.GetLayout();
  const string &str = text.GetText();
  if (layout.width < 0 ||
      (layout.align == Alignment::LEFT && layout.truncate == Truncate::NONE))
    return str;
  width = layout.width;
  switch (layout.truncate) {
  case Truncate::NONE:
    width = WidthRawString(str.c_str());
    return str;
  case Truncate::FRONT:
    return TruncateFront(str, width);
  case Truncate::MIDDLE:
    return TruncateMiddle(str, width);
  case Truncate::BACK:
  default:
    return TruncateBack(str, width);
  }
}

string Font::TruncateBack(const string &str, int &width) const {
  return TruncateEndsOrMiddle(str, width, [](const string &str, int charCount) {
    // TODO: UTF-8 safe truncate
    return str.substr(0, charCount) + "...";
  });
}

string Font::TruncateFront(const string &str, int &width) const {
  return TruncateEndsOrMiddle(str, width, [](const string &str, int charCount) {
    // TODO: UTF-8 safe truncate
    return "..." + str.substr(str.size() - charCount);
  });
}

string Font::TruncateMiddle(const string &str, int &width) const {
  return TruncateEndsOrMiddle(str, width, [](const string &str, int charCount) {
    // TODO: UTF-8 safe truncate
    return str.substr(0, (charCount + 1) / 2) + "..." +
           str.substr(str.size() - charCount / 2);
  });
}

string Font::TruncateEndsOrMiddle(
    const string &str, int &width,
    function<string(const string &, int)> getResultString) const {
  int firstWidth = WidthRawString(str.c_str());
  if (firstWidth <= width) {
    width = firstWidth;
    return str;
  }

  int workingChars = 0;
  int workingWidth = 0;

  // Note: for UTF-8 this binary search of byte chars will slice middle of
  // runes. Fixes for CJK truncating are left for Phase 4 where we audit UTF8
  // safety.
  int low = 0, high = str.size() - 1;
  while (low <= high) {
    // Think "how many chars to take from both ends, omitting in the middle".
    int nextChars = (low + high) / 2;
    int nextWidth = WidthRawString(getResultString(str, nextChars).c_str());
    if (nextWidth <= width) {
      if (nextChars > workingChars) {
        workingChars = nextChars;
        workingWidth = nextWidth;
      }
      low = nextChars + (nextChars == low);
    } else
      high = nextChars - 1;
  }
  width = workingWidth;
  return getResultString(str, workingChars);
}
