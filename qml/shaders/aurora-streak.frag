#version 440
#extension GL_GOOGLE_include_directive : enable
#include "aurora-field.glsl"
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 viewport;
    float fill;
    float time;
    float flow;
    float energy;
};

void main() {
    vec2 p = floor(qt_TexCoord0 * viewport) + 0.5;
    float top = viewport.y * (1.0 - 0.84 * clamp(fill / 100.0, 0.0, 1.0));
    float depth = p.y - top - 2.0 * sin(p.x * 0.036 + flow) - sin(p.x * 0.081 - time);
    float mask = smoothstep(-0.5, 0.5, depth) * step(0.001, fill);
    if (mask == 0.0) { fragColor = vec4(0); return; }
    float fold = sin(p.x * 0.036 + sin(depth * 0.027 - flow) * 1.7 + flow);
    float ribbon = pow(0.5 + 0.5 * fold, 12.0);
    float glint = pow(0.5 + 0.5 * sin(p.x * 0.12 + depth * 0.042 - flow * 2.0), 24.0);
    float edge = exp(-max(0.0, depth) / 1.7);
    vec3 tint = auroraColor(clamp(depth / 100.0, 0.0, 0.85), 0.5 + 0.5 * fold);
    vec3 color = vec3(0.025, 0.055, 0.11) + tint * (ribbon * 0.16 + glint * 0.035 + edge * 0.52) * (0.7 + energy * 0.55);
    float alpha = 0.94 * mask;
    fragColor = vec4(color * alpha, alpha) * qt_Opacity;
}
