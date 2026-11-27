#version 440
#extension GL_GOOGLE_include_directive : enable

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec3 pulse0;
    vec3 pulse1;
    vec3 pulse2;
};
layout(binding = 1) uniform sampler2D source;
layout(binding = 2) uniform sampler2D panes;
#include "stained-glass-pulse.glsl"

void main() {
    vec2 uv = qt_TexCoord0;
    vec4 base = texture(source, uv);
    if (base.a <= 0.001 || min(pulse0.z, min(pulse1.z, pulse2.z)) >= 1.0) {
        fragColor = base * qt_Opacity;
        return;
    }
    vec3 cell = texture(panes, uv).rgb;
    vec3 color = base.rgb / base.a;
    float light = paneLight(cell.rg) * cell.b;
    vec3 transmission = min(vec3(1.0), color * (1.0 + 0.87 * light) + vec3(0.11 * light));
    fragColor = vec4(transmission * base.a, base.a) * qt_Opacity;
}
