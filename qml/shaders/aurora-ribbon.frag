#version 440
#extension GL_GOOGLE_include_directive : enable
#include "aurora-field.glsl"
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 viewport;
    vec2 center;
    float extent;
    float time;
    float flow;
    float energy;
    float front;
    vec3 stroke0;
    vec3 stroke1;
    vec3 stroke2;
    vec3 stroke3;
};

void main() {
    vec2 pixel = floor(qt_TexCoord0 * viewport) + 0.5;
    vec2 p = (pixel - center) / extent;
    fragColor = auroraCurtain(p, time, flow, energy, front, stroke0, stroke1, stroke2, stroke3) * qt_Opacity;
}
