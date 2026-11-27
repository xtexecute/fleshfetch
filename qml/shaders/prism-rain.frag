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
    float pixelSize;
};

float lineDistance(vec2 p, vec2 a, vec2 b) {
    vec2 delta = b - a;
    float projection = clamp(dot(p - a, delta) / dot(delta, delta), 0.0, 1.0);
    return length(p - a - projection * delta);
}

void main() {
    vec2 p = (floor(qt_TexCoord0 * viewport / pixelSize) + 0.5) * pixelSize;
    vec4 bands = prismSpectrum(p, emitter, extent, energy, sweep);
    vec2 entry = emitter + vec2(-8.0, -7.0) * pixelSize;
    vec2 source = entry + vec2(-0.61, -0.29) * extent;
    float d = lineDistance(p, source, entry);
    float core = 1.0 - smoothstep(0.35 * pixelSize, 1.05 * pixelSize, d);
    float halo = 1.0 - smoothstep(pixelSize, 4.0 * pixelSize, d);
    float beam = core * (0.25 + energy * 0.56) + halo * (0.025 + energy * 0.04);
    vec3 white = vec3(0.88, 0.96, 1.00);
    vec4 incident = vec4(white * beam, beam);
    fragColor = (incident + bands * (1.0 - incident.a)) * qt_Opacity;
}
