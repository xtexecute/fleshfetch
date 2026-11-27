#version 440
#extension GL_GOOGLE_include_directive : enable
#include "prism-rain-field.glsl"
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 viewport;
    vec2 emitter;
    float extent;
    float energy;
    float sweep;
    vec2 bodyOrigin;
    vec2 bodySize;
    vec2 bodySquish;
    float bodyAngle;
};
layout(binding = 1) uniform sampler2D source;

void main() {
    vec4 texel = texture(source, qt_TexCoord0);
    vec2 local = (qt_TexCoord0 - 0.5) * bodySize * bodySquish;
    float c = cos(bodyAngle);
    float s = sin(bodyAngle);
    vec2 world = mat2(c, s, -s, c) * local + bodyOrigin + bodySize * 0.5;
    vec4 light = prismSpectrum(world, emitter, extent, energy, sweep);
    vec3 color = texel.rgb * (1.0 - light.a * 0.13)
               + light.rgb * texel.a * (0.30 + energy * 0.12);
    fragColor = vec4(min(color, vec3(texel.a)), texel.a) * qt_Opacity;
}
